from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from io import BytesIO, StringIO
import csv
import json
import ssl
import urllib.request
import zipfile


OFFICIAL_DOWNLOAD_API = "https://api.taiwanlottery.com/TLCAPIWeB/Lottery/ResultDownload?year={year}"
START_YEAR = 2007


@dataclass(frozen=True)
class LotteryPick:
    label: str
    main_numbers: tuple[int, ...]
    special_number: int | None = None


@dataclass(frozen=True)
class LotteryGameConfig:
    key: str
    title: str
    source_url: str
    csv_prefix: str
    main_number_fields: tuple[str, ...]
    special_field: str | None
    picks: tuple[LotteryPick, ...]
    special_label: str | None = None


@dataclass(frozen=True)
class LotteryComparison:
    label: str
    matched_main: int
    total_main: int
    special_matched: bool | None
    exact_match: bool

    def summary(self, special_label: str | None = None) -> str:
        base = f"{self.label} {self.matched_main}/{self.total_main}"
        if self.special_matched is None:
            return f"{base} 全中" if self.exact_match else base
        special_text = "中" if self.special_matched else "未中"
        full = f"{base} + {special_label or '特別號'}{special_text}"
        return f"{full} 全中" if self.exact_match else full


@dataclass(frozen=True)
class LotteryDraw:
    issue: str
    draw_date: str
    main_numbers: tuple[int, ...]
    special_number: int | None
    comparisons: tuple[LotteryComparison, ...]

    def numbers_text(self, special_label: str | None = None) -> str:
        main = " ".join(f"{number:02d}" for number in self.main_numbers)
        if self.special_number is None:
            return main
        label = special_label or "特別號"
        return f"{main} | {label} {self.special_number:02d}"

    def comparisons_text(self, special_label: str | None = None) -> str:
        return " | ".join(item.summary(special_label) for item in self.comparisons)


GAME_CONFIGS: tuple[LotteryGameConfig, ...] = (
    LotteryGameConfig(
        key="super_lotto638",
        title="威力彩",
        source_url="https://www.taiwanlottery.com/lotto/result/super_lotto638",
        csv_prefix="威力彩_",
        main_number_fields=("獎號1", "獎號2", "獎號3", "獎號4", "獎號5", "獎號6"),
        special_field="第二區",
        special_label="第二區",
        picks=(
            LotteryPick("第一組", (7, 11, 23, 32, 33, 38), 2),
            LotteryPick("第二組", (7, 11, 23, 32, 33, 38), 1),
            LotteryPick("第三組", (19, 8, 11, 27, 37, 16), 8),
            LotteryPick("第四組", (19, 8, 4, 3, 37, 16), 8),
        ),
    ),
    LotteryGameConfig(
        key="lotto649",
        title="大樂透",
        source_url="https://www.taiwanlottery.com/lotto/result/lotto649",
        csv_prefix="大樂透_",
        main_number_fields=("獎號1", "獎號2", "獎號3", "獎號4", "獎號5", "獎號6"),
        special_field=None,
        picks=(
            LotteryPick("第一組", (19, 8, 11, 27, 37, 16)),
            LotteryPick("第二組", (19, 8, 4, 3, 37, 16)),
        ),
    ),
    LotteryGameConfig(
        key="daily_cash",
        title="今彩539",
        source_url="https://www.taiwanlottery.com/lotto/result/daily_cash",
        csv_prefix="今彩539_",
        main_number_fields=("獎號1", "獎號2", "獎號3", "獎號4", "獎號5"),
        special_field=None,
        picks=(
            LotteryPick("第一組", (19, 8, 11, 27, 37)),
            LotteryPick("第二組", (19, 8, 4, 3, 37)),
        ),
    ),
)

GAME_CONFIG_MAP = {config.key: config for config in GAME_CONFIGS}


def _ssl_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    # The official API currently serves a certificate chain that fails verification
    # in some local Python environments, so we relax verification for this source.
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


def available_years(end_year: int | None = None) -> list[int]:
    final_year = end_year or datetime.now().year
    return list(range(START_YEAR, final_year + 1))


def _download_bytes(url: str, timeout: int = 30) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "PythonOil/0.1"})
    with urllib.request.urlopen(request, timeout=timeout, context=_ssl_context()) as response:
        return response.read()


def _result_download_url(year: int) -> str:
    payload = json.loads(_download_bytes(OFFICIAL_DOWNLOAD_API.format(year=year)).decode("utf-8"))
    content = payload.get("content") or {}
    path = content.get("path")
    if not path:
        raise ValueError(f"Missing Taiwan Lottery download URL for year {year}")
    return str(path)


def _decode_csv(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "cp950", "big5", "utf-8"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _find_csv_name(zip_file: zipfile.ZipFile, prefix: str) -> str | None:
    for name in zip_file.namelist():
        if name.startswith(prefix) and name.lower().endswith(".csv"):
            return name
    return None


def _compare_draw(
    config: LotteryGameConfig,
    main_numbers: tuple[int, ...],
    special_number: int | None,
) -> tuple[LotteryComparison, ...]:
    draw_main = set(main_numbers)
    results: list[LotteryComparison] = []
    for pick in config.picks:
        matched_main = len(draw_main.intersection(pick.main_numbers))
        special_matched = None if pick.special_number is None else pick.special_number == special_number
        exact_match = matched_main == len(pick.main_numbers) and (special_matched in (None, True))
        results.append(
            LotteryComparison(
                label=pick.label,
                matched_main=matched_main,
                total_main=len(pick.main_numbers),
                special_matched=special_matched,
                exact_match=exact_match,
            )
        )
    return tuple(results)


def parse_lottery_csv(csv_text: str, config: LotteryGameConfig) -> list[LotteryDraw]:
    reader = csv.DictReader(StringIO(csv_text))
    draws: list[LotteryDraw] = []
    for row in reader:
        main_numbers = tuple(int(str(row[field]).strip()) for field in config.main_number_fields)
        special_number = None
        if config.special_field is not None:
            special_value = str(row[config.special_field]).strip()
            special_number = int(special_value) if special_value else None
        draws.append(
            LotteryDraw(
                issue=str(row["期別"]).strip(),
                draw_date=str(row["開獎日期"]).strip(),
                main_numbers=main_numbers,
                special_number=special_number,
                comparisons=_compare_draw(config, main_numbers, special_number),
            )
        )
    draws.sort(key=lambda draw: draw.issue)
    return draws


def fetch_lottery_draws_for_year(year: int, config: LotteryGameConfig) -> list[LotteryDraw]:
    zip_url = _result_download_url(year)
    zip_bytes = _download_bytes(zip_url, timeout=60)
    with zipfile.ZipFile(BytesIO(zip_bytes)) as archive:
        csv_name = _find_csv_name(archive, config.csv_prefix)
        if csv_name is None:
            return []
        return parse_lottery_csv(_decode_csv(archive.read(csv_name)), config)


def fetch_all_lottery_draws(end_year: int | None = None) -> dict[str, list[LotteryDraw]]:
    results: dict[str, list[LotteryDraw]] = {config.key: [] for config in GAME_CONFIGS}
    for year in available_years(end_year):
        for config in GAME_CONFIGS:
            results[config.key].extend(fetch_lottery_draws_for_year(year, config))
    for draws in results.values():
        draws.sort(key=lambda draw: draw.issue)
    return results


def build_group_summaries(config: LotteryGameConfig, draws: list[LotteryDraw]) -> list[str]:
    summaries: list[str] = []
    for pick_index, pick in enumerate(config.picks):
        best_main = 0
        best_special = False
        exact_hits = 0
        for draw in draws:
            comparison = draw.comparisons[pick_index]
            best_main = max(best_main, comparison.matched_main)
            best_special = best_special or comparison.special_matched is True
            exact_hits += int(comparison.exact_match)
        if pick.special_number is None:
            summaries.append(f"{pick.label}: 完全相符 {exact_hits} 期，最高 {best_main}/{len(pick.main_numbers)}")
        else:
            special_text = "曾中" if best_special else "未中"
            summaries.append(
                f"{pick.label}: 完全相符 {exact_hits} 期，最高 {best_main}/{len(pick.main_numbers)}，{config.special_label or '特別號'}{special_text}"
            )
    return summaries
