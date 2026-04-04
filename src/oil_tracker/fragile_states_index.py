from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
import re
import ssl
import urllib.parse
import urllib.request
import zipfile
from xml.etree import ElementTree as ET


FSI_DOWNLOAD_PAGE = "https://fragilestatesindex.org/excel/"


@dataclass(frozen=True)
class FSIChinaPoint:
    year: int
    total_score: float
    rank: int


def _ssl_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


def fetch_fsi_download_links(timeout: int = 30) -> dict[int, str]:
    request = urllib.request.Request(FSI_DOWNLOAD_PAGE, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=timeout, context=_ssl_context()) as response:
        html = response.read().decode("utf-8", errors="replace")

    links: dict[int, str] = {}
    matches = re.findall(r"href=['\"]([^'\"]+\\.xlsx[^'\"]*)['\"]", html, re.IGNORECASE)
    if not matches:
        matches = re.findall(r"(https?://[^\\s'\"]+\\.xlsx[^\\s'\"]*)", html, re.IGNORECASE)
    for match in matches:
        url_text = match.strip()
        year_match = re.search(r"(20\d{2})", url_text)
        if not year_match:
            continue
        year = int(year_match.group(1))
        url = urllib.parse.urljoin(FSI_DOWNLOAD_PAGE, url_text)
        links[year] = url
    if links:
        return dict(sorted(links.items()))

    fallback = {
        2023: "https://fragilestatesindex.org/wp-content/uploads/2023/06/FSI-2023-DOWNLOAD.xlsx",
        2022: "https://fragilestatesindex.org/wp-content/uploads/2022/07/fsi-2022-download.xlsx",
        2021: "https://fragilestatesindex.org/wp-content/uploads/2021/05/fsi-2021.xlsx",
        2020: "https://fragilestatesindex.org/wp-content/uploads/2020/05/fsi-2020.xlsx",
        2019: "https://fragilestatesindex.org/wp-content/uploads/2019/04/fsi-2019.xlsx",
        2018: "https://fragilestatesindex.org/wp-content/uploads/2018/04/fsi-2018.xlsx",
    }
    for year in range(2006, 2018):
        fallback[year] = f"https://fragilestatesindex.org/wp-content/uploads/data/fsi-{year}.xlsx"
    return dict(sorted(fallback.items()))


def fetch_fsi_china_series(timeout: int = 60) -> list[FSIChinaPoint]:
    links = fetch_fsi_download_links(timeout=timeout)
    points: list[FSIChinaPoint] = []
    for year, url in links.items():
        rows = parse_fsi_xlsx(download_xlsx(url, timeout=timeout))
        point = extract_china_point(rows, year)
        if point is not None:
            points.append(point)
    points.sort(key=lambda item: item.year)
    return points


def download_xlsx(url: str, timeout: int = 60) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=timeout, context=_ssl_context()) as response:
        return response.read()


def parse_fsi_xlsx(xlsx_bytes: bytes) -> list[dict[str, str]]:
    zf = zipfile.ZipFile(BytesIO(xlsx_bytes))
    shared_strings = _read_shared_strings(zf)
    sheet_xml = zf.read("xl/worksheets/sheet1.xml")
    root = ET.fromstring(sheet_xml)
    ns = {"s": root.tag.split("}")[0].strip("{")}

    headers: list[str] = []
    rows: list[dict[str, str]] = []
    for row in root.findall("s:sheetData/s:row", ns):
        values: dict[int, str] = {}
        for cell in row.findall("s:c", ns):
            ref = cell.get("r", "")
            idx = _column_index(ref)
            value = _cell_value(cell, shared_strings, ns)
            values[idx] = value
        if not values:
            continue
        max_index = max(values)
        row_values = [values.get(i, "") for i in range(max_index + 1)]
        if not headers:
            headers = [item.strip() for item in row_values]
            continue
        data = {headers[i]: row_values[i] for i in range(min(len(headers), len(row_values)))}
        rows.append(data)
    return rows


def extract_china_point(rows: list[dict[str, str]], year: int) -> FSIChinaPoint | None:
    for row in rows:
        country = (row.get("Country") or "").strip()
        if _is_china(country):
            total = _parse_float(row.get("Total"))
            rank = _parse_int(row.get("Rank"))
            if total is None or rank is None:
                return None
            return FSIChinaPoint(year=year, total_score=total, rank=rank)
    return None


def _is_china(country: str) -> bool:
    normalized = country.lower().strip()
    return normalized == "china" or normalized.startswith("china,")


def _parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).strip())
    except ValueError:
        return None


def _parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    match = re.search(r"(\d+)", text)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _read_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    ns = {"s": root.tag.split("}")[0].strip("{")}
    strings: list[str] = []
    for si in root.findall("s:si", ns):
        text = "".join([t.text or "" for t in si.findall(".//s:t", ns)])
        strings.append(text)
    return strings


def _cell_value(cell: ET.Element, shared_strings: list[str], ns: dict[str, str]) -> str:
    value = cell.find("s:v", ns)
    if value is None or value.text is None:
        return ""
    if cell.get("t") == "s":
        index = int(value.text)
        if 0 <= index < len(shared_strings):
            return shared_strings[index]
    return value.text


def _column_index(cell_ref: str) -> int:
    match = re.match(r"([A-Z]+)", cell_ref)
    if not match:
        return 0
    letters = match.group(1)
    index = 0
    for char in letters:
        index = index * 26 + (ord(char) - ord("A") + 1)
    return index - 1
