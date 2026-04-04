from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
import ssl
import urllib.request
import xml.etree.ElementTree as ET


HENREN_HANDLE_URL = "https://www.youtube.com/@henren778"
HENREN_HANDLE_URLS = (
    "https://www.youtube.com/@henren778",
    "https://www.youtube.com/@henren778/featured",
    "https://www.youtube.com/@henren778/videos",
)
HENREN_JINA_URLS = (
    "https://r.jina.ai/http://www.youtube.com/@henren778",
    "https://r.jina.ai/http://www.youtube.com/@henren778/videos",
)
HENREN_USER_FEED_URL = "https://www.youtube.com/feeds/videos.xml?user=henren778"
HENREN_FEED_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"


@dataclass(frozen=True)
class HenrenVideo:
    title: str
    link: str
    published: datetime
    thumbnail_url: str
    index_value: float | None = None


@dataclass(frozen=True)
class HenrenSnapshot:
    channel_title: str
    updated: datetime | None
    videos: list[HenrenVideo]


def _ssl_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


def _fetch_text(url: str, timeout: int) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "zh-TW,zh-CN;q=0.9,en;q=0.8",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout, context=_ssl_context()) as response:
        return response.read().decode("utf-8", errors="replace")


def _parse_iso_datetime(value: str) -> datetime:
    clean = value.strip()
    if clean.endswith("Z"):
        clean = clean.replace("Z", "+00:00")
    return datetime.fromisoformat(clean)


def fetch_henren_snapshot(limit: int = 12, timeout: int = 20) -> HenrenSnapshot:
    last_error: Exception | None = None
    try:
        xml_text = _fetch_text(HENREN_USER_FEED_URL, timeout=timeout)
        return parse_henren_feed(xml_text, limit=limit)
    except Exception as exc:
        last_error = exc

    try:
        channel_id = fetch_channel_id_from_handle(timeout=timeout)
        feed_url = HENREN_FEED_URL.format(channel_id=channel_id)
        xml_text = _fetch_text(feed_url, timeout=timeout)
        return parse_henren_feed(xml_text, limit=limit)
    except Exception as exc:
        last_error = exc

    if last_error:
        raise last_error
    raise ValueError("無法取得 YouTube 影片列表")


def fetch_channel_id_from_handle(timeout: int = 20) -> str:
    html_text = _fetch_handle_html(timeout=timeout)
    match = re.search(r"channelId\":\"(UC[^\"]+)\"", html_text)
    if not match:
        match = re.search(r"externalId\":\"(UC[^\"]+)\"", html_text)
    if not match:
        match = re.search(r"https://www\.youtube\.com/channel/(UC[\w-]+)", html_text)
    if not match:
        raise ValueError("無法解析 YouTube channel ID")
    return match.group(1)


def _fetch_handle_html(timeout: int = 20) -> str:
    last_error: Exception | None = None
    for url in HENREN_HANDLE_URLS + HENREN_JINA_URLS:
        try:
            return _fetch_text(url, timeout=timeout)
        except Exception as exc:
            last_error = exc
            continue
    if last_error:
        raise last_error
    raise ValueError("無法取得 YouTube 頻道資訊")


def parse_henren_feed(xml_text: str, limit: int = 12) -> HenrenSnapshot:
    namespace = {
        "atom": "http://www.w3.org/2005/Atom",
        "media": "http://search.yahoo.com/mrss/",
    }
    root = ET.fromstring(xml_text)
    title_node = root.find("atom:title", namespace)
    channel_title = title_node.text.strip() if title_node is not None and title_node.text else "一个狠人"
    updated_node = root.find("atom:updated", namespace)
    updated = _parse_iso_datetime(updated_node.text) if updated_node is not None and updated_node.text else None

    videos: list[HenrenVideo] = []
    for entry in root.findall("atom:entry", namespace)[:limit]:
        title_node = entry.find("atom:title", namespace)
        link_node = entry.find("atom:link", namespace)
        published_node = entry.find("atom:published", namespace)
        thumb_node = entry.find("media:group/media:thumbnail", namespace)
        if not (title_node is not None and link_node is not None and published_node is not None):
            continue
        title = title_node.text.strip() if title_node.text else "Untitled"
        link = link_node.attrib.get("href", "")
        published = _parse_iso_datetime(published_node.text or "")
        thumbnail = thumb_node.attrib.get("url", "") if thumb_node is not None else ""
        index_value = _extract_index_value(title)
        videos.append(
            HenrenVideo(
                title=title,
                link=link,
                published=published,
                thumbnail_url=thumbnail,
                index_value=index_value,
            )
        )

    return HenrenSnapshot(channel_title=channel_title, updated=updated, videos=videos)


def _extract_index_value(title: str) -> float | None:
    match = re.search(r"(?:倒台指數|倒台指数)[^\d]*?(\d+(?:\.\d+)?)", title)
    if match:
        return float(match.group(1))
    match = re.search(r"\b(\d+(?:\.\d+)?)\b", title)
    if match:
        return float(match.group(1))
    return None
