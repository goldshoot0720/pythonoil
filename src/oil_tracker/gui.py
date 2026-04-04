from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import random
import threading
import sys
import webbrowser

try:
    import tkinter as tk
    from tkinter import ttk
    TK_IMPORT_ERROR: ModuleNotFoundError | None = None
except ModuleNotFoundError as exc:
    tk = None
    ttk = None
    TK_IMPORT_ERROR = exc

try:
    from .gme import fetch_price_record
    from .paths import default_db_path
    from .github_stats import (
        CachedGitHubCommitStats,
        GitHubCommitStats,
        fetch_github_commit_stats,
        load_cached_github_commit_stats,
        save_cached_github_commit_stats,
    )
    from .brent_spot import (
        BRENT_SPOT_SOURCE_URL,
        BrentSpotPoint,
        fetch_brent_spot_series,
    )
    from .pizza_watch import (
        PizzaWatchHistoryEntry,
        PizzaWatchSnapshot,
        calculate_pizza_watch_streaks,
        fetch_pizza_watch_snapshot,
        update_pizza_watch_history,
    )
    from .settings import AppSettings, load_settings, save_settings
    from .storage import OilPriceRepository, SaveResult
    from .taiwan_lottery import GAME_CONFIGS, build_group_summaries, fetch_all_lottery_draws
    from .us_debt import USDebtRecord, fetch_us_national_debt, load_us_debt_history, save_us_debt_record
except ImportError:
    from gme import fetch_price_record
    from paths import default_db_path
    from github_stats import (
        CachedGitHubCommitStats,
        GitHubCommitStats,
        fetch_github_commit_stats,
        load_cached_github_commit_stats,
        save_cached_github_commit_stats,
    )
    from brent_spot import (
        BRENT_SPOT_SOURCE_URL,
        BrentSpotPoint,
        fetch_brent_spot_series,
    )
    from pizza_watch import (
        PizzaWatchHistoryEntry,
        PizzaWatchSnapshot,
        calculate_pizza_watch_streaks,
        fetch_pizza_watch_snapshot,
        update_pizza_watch_history,
    )
    from settings import AppSettings, load_settings, save_settings
    from storage import OilPriceRepository, SaveResult
    from taiwan_lottery import GAME_CONFIGS, build_group_summaries, fetch_all_lottery_draws
    from us_debt import USDebtRecord, fetch_us_national_debt, load_us_debt_history, save_us_debt_record


@dataclass(frozen=True)
class BirthdayEasterEgg:
    month: int
    day: int
    title: str
    subtitle: str
    status_text: str
    canvas_line: str


BIRTHDAY_EASTER_EGGS: tuple[BirthdayEasterEgg, ...] = (
    BirthdayEasterEgg(
        month=4,
        day=3,
        title="塗哥生日快樂",
        subtitle="今彩539頭獎得主鋒兄",
        status_text="塗哥生日快樂特效啟動中，今彩539頭獎得主鋒兄一起登場。",
        canvas_line="鋒兄把 539 喜氣一起帶來",
    ),
    BirthdayEasterEgg(
        month=11,
        day=27,
        title="鋒兄生日快樂",
        subtitle="高考三級資訊處理榜首鋒兄",
        status_text="鋒兄生日快樂特效啟動中，高考三級資訊處理榜首鋒兄閃亮登場。",
        canvas_line="榜首鋒兄今天主場全開",
    ),
)


def get_birthday_easter_egg(now: datetime | None = None) -> BirthdayEasterEgg | None:
    current = now or datetime.now()
    for easter_egg in BIRTHDAY_EASTER_EGGS:
        if current.month == easter_egg.month and current.day == easter_egg.day:
            return easter_egg
    return None


def is_birthday_easter_egg_day(now: datetime | None = None) -> bool:
    return get_birthday_easter_egg(now) is not None


class OilTrackerApp:
    def __init__(self, root: tk.Tk, db_path: Path) -> None:
        self.root = root
        self.db_path = db_path
        self.repository = OilPriceRepository(db_path)
        self._chart_records: list = []
        self._lottery_draws: dict[str, list] | None = None
        self._pizza_watch_snapshot: PizzaWatchSnapshot | None = None
        self._birthday_easter_egg = get_birthday_easter_egg()
        self._birthday_mode = self._birthday_easter_egg is not None
        self._birthday_sparkles: list[dict[str, float | str]] = []
        self._birthday_animation_tick = 0

        self.root.title("OQD Market Terminal")
        self.root.geometry("1320x860")
        self.root.minsize(1080, 700)
        self.root.configure(bg="#07111f")

        self.style = ttk.Style()
        self.style.theme_use("clam")
        self._configure_styles()

        self.status_var = tk.StringVar(value="System ready")
        self.date_var = tk.StringVar(value="-")
        self.price_var = tk.StringVar(value="-")
        self.change_var = tk.StringVar(value="-")
        self.source_var = tk.StringVar(value="https://www.gulfmerc.com/")
        self.chart_hint_var = tk.StringVar(value="Awaiting market history")
        self.trend_var = tk.StringVar(value="No signal")
        self.records_var = tk.StringVar(value="0 sessions")
        self.range_var = tk.StringVar(value="No range")
        self.last_sync_var = tk.StringVar(value="Not synced yet")

        self._build_layout()
        self.refresh_history()

    def _configure_styles(self) -> None:
        self.style.configure("Root.TFrame", background="#07111f")
        self.style.configure("Hero.TFrame", background="#0b1628")
        self.style.configure("Birthday.TFrame", background="#27103b")
        self.style.configure("Card.TFrame", background="#112742")
        self.style.configure("Panel.TFrame", background="#102238")
        self.style.configure("MutedCard.TFrame", background="#0c1a2d")
        self.style.configure("ChartPanel.TFrame", background="#0a1626")
        self.style.configure("StatsPanel.TFrame", background="#0c1a2d")

        self.style.configure(
            "BirthdayTitle.TLabel",
            background="#27103b",
            foreground="#fff1a8",
            font=("Bahnschrift SemiBold", 26),
        )
        self.style.configure(
            "BirthdayBody.TLabel",
            background="#27103b",
            foreground="#ffe8ff",
            font=("Segoe UI Semibold", 11),
        )
        self.style.configure(
            "Eyebrow.TLabel",
            background="#0b1628",
            foreground="#69c7ff",
            font=("Segoe UI Semibold", 10),
        )
        self.style.configure(
            "Title.TLabel",
            background="#0b1628",
            foreground="#f5fbff",
            font=("Bahnschrift SemiBold", 29),
        )
        self.style.configure(
            "Subtitle.TLabel",
            background="#0b1628",
            foreground="#8ea4bd",
            font=("Segoe UI", 11),
        )
        self.style.configure(
            "HeroMetricLabel.TLabel",
            background="#0b1628",
            foreground="#6f86a0",
            font=("Segoe UI Semibold", 10),
        )
        self.style.configure(
            "HeroMetricValue.TLabel",
            background="#0b1628",
            foreground="#f4fbff",
            font=("Segoe UI Semibold", 18),
        )
        self.style.configure(
            "CardLabel.TLabel",
            background="#112742",
            foreground="#6f86a0",
            font=("Segoe UI Semibold", 10),
        )
        self.style.configure(
            "CardValue.TLabel",
            background="#112742",
            foreground="#f3fbff",
            font=("Bahnschrift SemiBold", 24),
        )
        self.style.configure(
            "CardMeta.TLabel",
            background="#112742",
            foreground="#6dc6ff",
            font=("Segoe UI", 10),
        )
        self.style.configure(
            "PanelTitle.TLabel",
            background="#102238",
            foreground="#f3fbff",
            font=("Segoe UI Semibold", 14),
        )
        self.style.configure(
            "PanelBody.TLabel",
            background="#102238",
            foreground="#8fa8c3",
            font=("Segoe UI", 10),
        )
        self.style.configure(
            "MutedPanelBody.TLabel",
            background="#0c1a2d",
            foreground="#8fa8c3",
            font=("Segoe UI", 10),
        )
        self.style.configure(
            "Ascii.TLabel",
            background="#0c1a2d",
            foreground="#7fd4ff",
            font=("Consolas", 10),
        )
        self.style.configure(
            "AsciiHero.TLabel",
            background="#0b1628",
            foreground="#7fd4ff",
            font=("Consolas", 10),
        )
        self.style.configure(
            "ChartTitle.TLabel",
            background="#0a1626",
            foreground="#f3fbff",
            font=("Segoe UI Semibold", 14),
        )
        self.style.configure(
            "ChartHint.TLabel",
            background="#0a1626",
            foreground="#6dc6ff",
            font=("Segoe UI", 10),
        )
        self.style.configure(
            "Status.TLabel",
            background="#07111f",
            foreground="#90a7c1",
            font=("Segoe UI", 10),
        )
        self.style.configure(
            "Link.TLabel",
            background="#07111f",
            foreground="#7fd4ff",
            font=("Segoe UI", 10, "underline"),
        )
        self.style.configure(
            "StatsLabel.TLabel",
            background="#0c1a2d",
            foreground="#6f86a0",
            font=("Segoe UI Semibold", 10),
        )
        self.style.configure(
            "StatsValue.TLabel",
            background="#0c1a2d",
            foreground="#f4fbff",
            font=("Segoe UI Semibold", 18),
        )
        self.style.configure(
            "Accent.TButton",
            font=("Segoe UI Semibold", 11),
            padding=(18, 12),
            background="#1aa3ff",
            foreground="#041220",
            borderwidth=0,
        )
        self.style.map(
            "Accent.TButton",
            background=[("active", "#57bdff"), ("disabled", "#35506c")],
            foreground=[("disabled", "#7e91a5")],
        )

        self.style.configure(
            "Treeview",
            background="#0d1b2d",
            foreground="#dbe9f6",
            fieldbackground="#0d1b2d",
            bordercolor="#0d1b2d",
            rowheight=30,
            font=("Consolas", 10),
        )
        self.style.map("Treeview", background=[("selected", "#163d63")], foreground=[("selected", "#f4fbff")])
        self.style.configure(
            "Treeview.Heading",
            background="#102238",
            foreground="#7fd4ff",
            bordercolor="#102238",
            font=("Segoe UI Semibold", 10),
            relief="flat",
        )
        self.style.map("Treeview.Heading", background=[("active", "#16314d")])
        self.style.configure(
            "Vertical.TScrollbar",
            background="#16314d",
            troughcolor="#091321",
            arrowcolor="#7fd4ff",
            bordercolor="#091321",
        )

    def _build_layout(self) -> None:
        self._build_menu()
        container = ttk.Frame(self.root, style="Root.TFrame", padding=28)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        content_row = 2

        if self._birthday_mode:
            self._build_birthday_banner(container)
            content_row = 3

        container.rowconfigure(content_row, weight=1)

        header = ttk.Frame(container, style="Hero.TFrame", padding=24)
        header.grid(row=1 if self._birthday_mode else 0, column=0, sticky="ew")
        header.columnconfigure(0, weight=3)
        header.columnconfigure(1, weight=2)

        ttk.Label(header, text="MARKET MONITOR", style="Eyebrow.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, text="OQD Daily Marker Terminal", style="Title.TLabel").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Label(
            header,
            text="Tech-finance desktop intelligence for Gulf Mercantile Exchange pricing, designed for quick reads, daily sync, and sharp review sessions.",
            style="Subtitle.TLabel",
            wraplength=660,
            justify="left",
        ).grid(row=2, column=0, sticky="w", pady=(10, 0))

        hero_ascii = (
            " ________  ________  ________   ________  ________  ________  \n"
            "|\\  _____\\|\\  ___  \\|\\   ___  \\|\\   ____\\|\\   __  \\|\\   __  \\ \n"
            "\\ \\  \\__/\\ \\  \\\\ \\  \\ \\  \\\\ \\  \\ \\  \\___|\\ \\  \\|\\  \\ \\  \\|\\  \\\n"
            " \\ \\   __\\\\ \\  \\\\ \\  \\ \\  \\\\ \\  \\ \\  \\  __\\ \\   _  _\\ \\   __  \\\n"
            "  \\ \\  \\_| \\ \\  \\\\ \\  \\ \\  \\\\ \\  \\ \\  \\|\\  \\ \\  \\\\  \\\\ \\  \\ \\  \\\n"
            "   \\ \\__\\   \\ \\__\\\\ \\__\\ \\__\\\\ \\__\\ \\_______\\ \\__\\\\ _\\\\ \\__\\ \\__\\\n"
            "    \\|__|    \\|__| \\|__|\\|__| \\|__|\\|_______|\\|__|\\|__|\\|__|\\|__|\n"
            "                          ＦＥＮＧ　ＢＲＯ\n"
        )
        ttk.Label(
            header,
            text=hero_ascii,
            style="AsciiHero.TLabel",
            justify="left",
        ).grid(row=3, column=0, sticky="w", pady=(12, 0))

        hero_meta = ttk.Frame(header, style="Hero.TFrame")
        hero_meta.grid(row=0, column=1, rowspan=4, sticky="nsew", padx=(24, 0))
        hero_meta.columnconfigure(0, weight=1)
        hero_meta.columnconfigure(1, weight=1)

        ttk.Label(hero_meta, text="TREND", style="HeroMetricLabel.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(hero_meta, text="LAST SYNC", style="HeroMetricLabel.TLabel").grid(row=0, column=1, sticky="w")
        ttk.Label(hero_meta, textvariable=self.trend_var, style="HeroMetricValue.TLabel").grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Label(hero_meta, textvariable=self.last_sync_var, style="HeroMetricValue.TLabel").grid(row=1, column=1, sticky="w", pady=(6, 0))
        ttk.Label(hero_meta, text="DESIGN", style="HeroMetricLabel.TLabel").grid(row=2, column=0, sticky="w", pady=(18, 0))
        ttk.Label(hero_meta, text="DATA VAULT", style="HeroMetricLabel.TLabel").grid(row=2, column=1, sticky="w", pady=(18, 0))
        ttk.Label(hero_meta, text="2026 trading desk aesthetic", style="PanelBody.TLabel").grid(row=3, column=0, sticky="w", pady=(6, 0))
        ttk.Label(hero_meta, text=str(self.db_path), style="PanelBody.TLabel", wraplength=280, justify="left").grid(
            row=3,
            column=1,
            sticky="w",
            pady=(6, 0),
        )
        self.fetch_button = ttk.Button(hero_meta, text="抓取最新油價", style="Accent.TButton", command=self.fetch_latest)
        self.fetch_button.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(22, 0))

        cards = ttk.Frame(container, style="Root.TFrame")
        cards.grid(row=2 if self._birthday_mode else 1, column=0, sticky="ew", pady=(22, 18))
        for index in range(5):
            cards.columnconfigure(index, weight=1)

        self._build_card(cards, 0, "SESSION DATE", self.date_var, "Latest captured pricing session")
        self._build_card(cards, 1, "LAST PRICE", self.price_var, "OQD marker close")
        self._build_card(cards, 2, "DAY CHANGE", self.change_var, "Versus prior saved record")
        self._build_card(cards, 3, "DATA WINDOW", self.records_var, "Stored local history")
        self._build_card(cards, 4, "TRADING RANGE", self.range_var, "Observed across loaded window")

        content = ttk.Frame(container, style="Root.TFrame")
        content.grid(row=content_row, column=0, sticky="nsew")
        content.columnconfigure(0, weight=7)
        content.columnconfigure(1, weight=4)
        content.rowconfigure(0, weight=1)

        chart_panel = ttk.Frame(content, style="ChartPanel.TFrame", padding=20)
        chart_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        chart_panel.columnconfigure(0, weight=1)
        chart_panel.rowconfigure(1, weight=1)

        ttk.Label(chart_panel, text="Market Curve / Recent 30 Sessions", style="ChartTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(chart_panel, textvariable=self.chart_hint_var, style="ChartHint.TLabel").grid(row=0, column=1, sticky="e")

        self.chart_canvas = tk.Canvas(chart_panel, bg="#0a1626", highlightthickness=0)
        self.chart_canvas.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(14, 0))
        self.chart_canvas.bind("<Configure>", lambda _event: self.draw_chart())

        right_panel = ttk.Frame(content, style="Root.TFrame")
        right_panel.grid(row=0, column=1, sticky="nsew")
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(0, weight=1)
        right_panel.rowconfigure(1, weight=1)

        table_panel = ttk.Frame(right_panel, style="Panel.TFrame", padding=18)
        table_panel.grid(row=0, column=0, sticky="nsew")
        table_panel.columnconfigure(0, weight=1)
        table_panel.rowconfigure(1, weight=1)

        ttk.Label(table_panel, text="Recent Records", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w")
        self.tree = ttk.Treeview(table_panel, columns=("date", "price"), show="headings", height=14)
        self.tree.heading("date", text="Date")
        self.tree.heading("price", text="Price")
        self.tree.column("date", width=130, anchor="center")
        self.tree.column("price", width=100, anchor="e")
        self.tree.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        self.tree.tag_configure("even", background="#0d1b2d")
        self.tree.tag_configure("odd", background="#102238")

        scrollbar = ttk.Scrollbar(table_panel, orient="vertical", command=self.tree.yview, style="Vertical.TScrollbar")
        scrollbar.grid(row=1, column=1, sticky="ns", pady=(12, 0))
        self.tree.configure(yscrollcommand=scrollbar.set)

        insight_panel = ttk.Frame(right_panel, style="MutedCard.TFrame", padding=18)
        insight_panel.grid(row=1, column=0, sticky="nsew", pady=(14, 0))
        insight_panel.columnconfigure(0, weight=1)
        ttk.Label(insight_panel, text="Desk Notes", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            insight_panel,
            text="Built for internal commodity reviews: keep recent sessions visible, read the acceleration quickly, and sync fresh pricing without leaving the desktop.",
            style="MutedPanelBody.TLabel",
            wraplength=320,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(10, 0))
        ttk.Label(insight_panel, text="SOURCE", style="HeroMetricLabel.TLabel").grid(row=2, column=0, sticky="w", pady=(20, 0))
        ttk.Label(
            insight_panel,
            textvariable=self.source_var,
            style="MutedPanelBody.TLabel",
            wraplength=320,
            justify="left",
        ).grid(row=3, column=0, sticky="w", pady=(6, 0))

        ascii_art = (
            " ________  ________  ________   ________  ________  ________  \n"
            "|\\  _____\\|\\  ___  \\|\\   ___  \\|\\   ____\\|\\   __  \\|\\   __  \\ \n"
            "\\ \\  \\__/\\ \\  \\\\ \\  \\ \\  \\\\ \\  \\ \\  \\___|\\ \\  \\|\\  \\ \\  \\|\\  \\\n"
            " \\ \\   __\\\\ \\  \\\\ \\  \\ \\  \\\\ \\  \\ \\  \\  __\\ \\   _  _\\ \\   __  \\\n"
            "  \\ \\  \\_| \\ \\  \\\\ \\  \\ \\  \\\\ \\  \\ \\  \\|\\  \\ \\  \\\\  \\\\ \\  \\ \\  \\\n"
            "   \\ \\__\\   \\ \\__\\\\ \\__\\ \\__\\\\ \\__\\ \\_______\\ \\__\\\\ _\\\\ \\__\\ \\__\\\n"
            "    \\|__|    \\|__| \\|__|\\|__| \\|__|\\|_______|\\|__|\\|__|\\|__|\\|__|\n"
            "                          ＦＥＮＧ　ＢＲＯ\n"
        )
        ttk.Label(
            insight_panel,
            text=ascii_art,
            style="Ascii.TLabel",
            justify="left",
        ).grid(row=4, column=0, sticky="w", pady=(12, 0))

        footer = ttk.Frame(container, style="Root.TFrame")
        footer.grid(row=content_row + 1, column=0, sticky="ew", pady=(12, 0))
        footer.columnconfigure(0, weight=1)
        ttk.Label(footer, textvariable=self.status_var, style="Status.TLabel").grid(row=0, column=0, sticky="w")
        source_link = ttk.Label(footer, textvariable=self.source_var, style="Link.TLabel", cursor="hand2")
        source_link.grid(row=1, column=0, sticky="w", pady=(4, 0))
        source_link.bind("<Button-1>", lambda _event: self.open_source_link())

    def _build_birthday_banner(self, parent: ttk.Frame) -> None:
        if self._birthday_easter_egg is None:
            return

        banner = ttk.Frame(parent, style="Birthday.TFrame", padding=18)
        banner.grid(row=0, column=0, sticky="ew", pady=(0, 18))
        banner.columnconfigure(0, weight=3)
        banner.columnconfigure(1, weight=2)

        ttk.Label(banner, text=self._birthday_easter_egg.title, style="BirthdayTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            banner,
            text=self._birthday_easter_egg.subtitle,
            style="BirthdayBody.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Label(
            banner,
            text=f"{datetime.now().year}年4月3日限定彩蛋",
            style="BirthdayBody.TLabel",
        ).grid(row=2, column=0, sticky="w", pady=(6, 0))

        self._birthday_canvas = tk.Canvas(
            banner,
            bg="#27103b",
            highlightthickness=0,
            height=90,
        )
        self._birthday_canvas.grid(row=0, column=1, rowspan=3, sticky="nsew", padx=(18, 0))

        self.status_var.set(self._birthday_easter_egg.status_text)
        self.root.after(120, self._animate_birthday_banner)

    def _animate_birthday_banner(self) -> None:
        if not self._birthday_mode or not hasattr(self, "_birthday_canvas"):
            return

        canvas = self._birthday_canvas
        if not canvas.winfo_exists():
            return

        width = max(canvas.winfo_width(), 260)
        height = max(canvas.winfo_height(), 90)
        canvas.delete("all")
        canvas.create_rectangle(0, 0, width, height, fill="#27103b", outline="")

        palette = ("#ffe066", "#ff8fab", "#7bdff2", "#b8f2e6", "#f7a072")
        self._birthday_animation_tick += 1

        if len(self._birthday_sparkles) < 28:
            for _ in range(5):
                self._birthday_sparkles.append(
                    {
                        "x": random.uniform(0, width),
                        "y": random.uniform(0, height),
                        "size": random.uniform(4, 10),
                        "dx": random.uniform(1.2, 3.6),
                        "dy": random.uniform(-0.4, 0.4),
                        "color": random.choice(palette),
                    }
                )

        next_sparkles: list[dict[str, float | str]] = []
        for sparkle in self._birthday_sparkles:
            x = float(sparkle["x"]) + float(sparkle["dx"])
            y = float(sparkle["y"]) + float(sparkle["dy"])
            size = float(sparkle["size"])
            color = str(sparkle["color"])
            if x - size > width:
                x = -size
                y = random.uniform(8, height - 8)
            canvas.create_oval(x - size, y - size, x + size, y + size, fill=color, outline="")
            canvas.create_text(x, y, text="✦", fill="#fff8d6", font=("Segoe UI Symbol", max(int(size * 1.5), 8)))
            sparkle["x"] = x
            sparkle["y"] = y
            next_sparkles.append(sparkle)

        pulse = "#fff3b0" if self._birthday_animation_tick % 12 < 6 else "#ffd166"
        canvas.create_text(
            width * 0.5,
            height * 0.35,
            text="HAPPY BIRTHDAY",
            fill=pulse,
            font=("Bahnschrift SemiBold", 18),
        )
        canvas.create_text(
            width * 0.5,
            height * 0.7,
            text=self._birthday_easter_egg.canvas_line if self._birthday_easter_egg is not None else "",
            fill="#ffe8ff",
            font=("Segoe UI Semibold", 11),
        )

        self._birthday_sparkles = next_sparkles
        self.root.after(120, self._animate_birthday_banner)

    def _build_menu(self) -> None:
        menu_bar = tk.Menu(self.root)
        debt_menu = tk.Menu(menu_bar, tearoff=False)
        debt_menu.add_command(label="US National Debt", command=self.open_us_debt_window)
        menu_bar.add_cascade(label="US Debt", menu=debt_menu)
        stats_menu = tk.Menu(menu_bar, tearoff=False)
        stats_menu.add_command(label="Commits", command=self.open_commit_stats_window)
        menu_bar.add_cascade(label="統計", menu=stats_menu)
        settings_menu = tk.Menu(menu_bar, tearoff=False)
        settings_menu.add_command(label="GitHub Token", command=self.open_github_token_settings)
        menu_bar.add_cascade(label="設定", menu=settings_menu)
        menu_bar.add_command(label="最瞎結婚理由", command=self.open_lottery_window)
        menu_bar.add_command(label="披薩監控", command=self.open_pizza_watch_window)
        menu_bar.add_command(label="Dated Brent 現貨", command=self.open_brent_spot_window)
        self.root.configure(menu=menu_bar)

    def open_creative_studio(self) -> None:
        window = tk.Toplevel(self.root)
        window.title("自由創作")
        window.geometry("920x680")
        window.minsize(760, 540)
        window.configure(bg="#07111f")

        container = ttk.Frame(window, style="Root.TFrame", padding=20)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(2, weight=1)

        ttk.Label(container, text="自由創作", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            container,
            text="自由記錄靈感、段落、歌詞、文案或任何草稿。內容會儲存在本機，下次打開會自動帶回。",
            style="Subtitle.TLabel",
            wraplength=760,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(8, 16))

        editor_panel = ttk.Frame(container, style="Panel.TFrame", padding=16)
        editor_panel.grid(row=2, column=0, sticky="nsew")
        editor_panel.columnconfigure(0, weight=1)
        editor_panel.rowconfigure(0, weight=1)

        editor = tk.Text(
            editor_panel,
            wrap="word",
            undo=True,
            bg="#0d1b2d",
            fg="#f4fbff",
            insertbackground="#f4fbff",
            relief="flat",
            font=("Consolas", 12),
            padx=14,
            pady=14,
        )
        editor.grid(row=0, column=0, sticky="nsew")
        editor.insert("1.0", load_creative_notes())
        editor.focus_set()

        scrollbar = ttk.Scrollbar(editor_panel, orient="vertical", command=editor.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        editor.configure(yscrollcommand=scrollbar.set)

        footer = ttk.Frame(container, style="Root.TFrame")
        footer.grid(row=3, column=0, sticky="ew", pady=(14, 0))
        footer.columnconfigure(0, weight=1)

        creative_status_var = tk.StringVar(value="內容尚未儲存")
        ttk.Label(footer, textvariable=creative_status_var, style="Status.TLabel").grid(row=0, column=0, sticky="w")

        buttons = ttk.Frame(footer, style="Root.TFrame")
        buttons.grid(row=0, column=1, sticky="e")

        def save_current_notes() -> None:
            save_creative_notes(editor.get("1.0", "end-1c"))
            creative_status_var.set("自由創作內容已儲存到本機。")
            self.status_var.set("自由創作內容已儲存。")

        def clear_notes() -> None:
            editor.delete("1.0", tk.END)
            creative_status_var.set("已清空編輯內容，記得按儲存。")

        def export_reference_vector_art() -> None:
            output_path = save_reference_vector_art()
            creative_status_var.set(f"已輸出附圖靈感向量圖：{output_path}")
            self.status_var.set(f"向量圖已輸出：{output_path}")

        ttk.Button(buttons, text="儲存", style="Accent.TButton", command=save_current_notes).pack(side="left")
        ttk.Button(buttons, text="清空", command=clear_notes).pack(side="left", padx=(10, 0))
        ttk.Button(buttons, text="附圖向量圖", command=export_reference_vector_art).pack(side="left", padx=(10, 0))

    def open_github_token_settings(self) -> None:
        settings = load_settings()
        window = tk.Toplevel(self.root)
        window.title("GitHub Token")
        window.geometry("720x320")
        window.minsize(620, 280)
        window.configure(bg="#07111f")
        window.transient(self.root)
        window.grab_set()

        container = ttk.Frame(window, style="Root.TFrame", padding=20)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(2, weight=1)

        ttk.Label(container, text="GitHub Token", style="Title.TLabel").grid(row=0, column=0, sticky="w")

        status_text = "目前已儲存 token" if settings.github_token else "目前沒有儲存 token"
        saved_status_var = tk.StringVar(value=status_text)
        ttk.Label(container, textvariable=saved_status_var, style="Status.TLabel").grid(row=1, column=0, sticky="w", pady=(8, 0))

        form = ttk.Frame(container, style="Panel.TFrame", padding=16)
        form.grid(row=2, column=0, sticky="nsew", pady=(16, 0))
        form.columnconfigure(0, weight=1)

        ttk.Label(
            form,
            text="貼上 GitHub Personal Access Token。環境變數 `GITHUB_TOKEN` 仍會優先於本機設定。",
            style="PanelBody.TLabel",
            wraplength=620,
            justify="left",
        ).grid(row=0, column=0, sticky="w")

        token_var = tk.StringVar(value=settings.github_token)
        show_token_var = tk.BooleanVar(value=False)

        token_entry = ttk.Entry(form, textvariable=token_var, show="*", font=("Consolas", 11))
        token_entry.grid(row=1, column=0, sticky="ew", pady=(14, 0))
        token_entry.focus_set()
        token_entry.selection_range(0, tk.END)

        edit_menu = tk.Menu(window, tearoff=False)

        def select_all(_event: tk.Event | None = None) -> str:
            token_entry.selection_range(0, tk.END)
            token_entry.icursor(tk.END)
            return "break"

        def paste_from_clipboard(_event: tk.Event | None = None) -> str:
            try:
                clipboard_text = window.clipboard_get()
            except tk.TclError:
                return "break"
            token_entry.insert(token_entry.index(tk.INSERT), clipboard_text)
            return "break"

        def copy_selection(_event: tk.Event | None = None) -> str:
            try:
                selected_text = token_entry.selection_get()
            except tk.TclError:
                return "break"
            window.clipboard_clear()
            window.clipboard_append(selected_text)
            return "break"

        def cut_selection(_event: tk.Event | None = None) -> str:
            try:
                selected_text = token_entry.selection_get()
                selection_start = token_entry.index(tk.SEL_FIRST)
                selection_end = token_entry.index(tk.SEL_LAST)
            except tk.TclError:
                return "break"
            window.clipboard_clear()
            window.clipboard_append(selected_text)
            token_entry.delete(selection_start, selection_end)
            return "break"

        def open_context_menu(event: tk.Event) -> str:
            edit_menu.tk_popup(event.x_root, event.y_root)
            return "break"

        edit_menu.add_command(label="貼上", command=paste_from_clipboard)
        edit_menu.add_command(label="複製", command=copy_selection)
        edit_menu.add_command(label="剪下", command=cut_selection)
        edit_menu.add_separator()
        edit_menu.add_command(label="全選", command=select_all)

        for sequence, handler in (
            ("<Command-v>", paste_from_clipboard),
            ("<Control-v>", paste_from_clipboard),
            ("<Shift-Insert>", paste_from_clipboard),
            ("<Command-c>", copy_selection),
            ("<Control-c>", copy_selection),
            ("<Command-x>", cut_selection),
            ("<Control-x>", cut_selection),
            ("<Command-a>", select_all),
            ("<Control-a>", select_all),
            ("<Button-2>", open_context_menu),
            ("<Button-3>", open_context_menu),
        ):
            token_entry.bind(sequence, handler)

        ttk.Checkbutton(
            form,
            text="顯示 token",
            variable=show_token_var,
            command=lambda: token_entry.configure(show="" if show_token_var.get() else "*"),
        ).grid(row=2, column=0, sticky="w", pady=(10, 0))

        buttons = ttk.Frame(form, style="Panel.TFrame")
        buttons.grid(row=3, column=0, sticky="ew", pady=(18, 0))

        def update_saved_status(token: str) -> None:
            if token.strip():
                saved_status_var.set("目前已儲存 token")
            else:
                saved_status_var.set("目前沒有儲存 token")

        def save_token() -> None:
            token = token_var.get().strip()
            save_settings(AppSettings(github_token=token))
            update_saved_status(token)
            self.status_var.set("GitHub token 已儲存到本機設定。")

        def clear_token() -> None:
            token_var.set("")
            save_settings(AppSettings(github_token=""))
            update_saved_status("")
            self.status_var.set("GitHub token 已從本機設定清除。")

        ttk.Button(buttons, text="儲存", style="Accent.TButton", command=save_token).pack(side="left")
        ttk.Button(buttons, text="清除", command=clear_token).pack(side="left", padx=(10, 0))

    def _build_card(self, parent: ttk.Frame, column: int, title: str, variable: tk.StringVar, meta: str) -> None:
        card = ttk.Frame(parent, style="Card.TFrame", padding=18)
        card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 10, 0))
        ttk.Label(card, text=title, style="CardLabel.TLabel").pack(anchor="w")
        ttk.Label(card, textvariable=variable, style="CardValue.TLabel").pack(anchor="w", pady=(12, 0))
        ttk.Label(card, text=meta, style="CardMeta.TLabel", wraplength=190, justify="left").pack(anchor="w", pady=(10, 0))

    def open_source_link(self) -> None:
        webbrowser.open_new_tab(self.source_var.get())

    def fetch_latest(self) -> None:
        self.fetch_button.state(["disabled"])
        self.status_var.set("Sync in progress. Pulling latest price from gulfmerc.com...")
        worker = threading.Thread(target=self._fetch_worker, daemon=True)
        worker.start()

    def _fetch_worker(self) -> None:
        try:
            record = fetch_price_record()
            result = self.repository.save(record)
            self.root.after(0, lambda: self._apply_result(result))
        except Exception as exc:
            self.root.after(0, lambda message=str(exc): self._show_error(message))

    def _apply_result(self, result: SaveResult) -> None:
        self.date_var.set(result.record.price_date.isoformat())
        self.price_var.set(f"{result.record.price:.2f}")
        self.change_var.set("N/A" if result.change is None else f"{result.change:+.2f}")

        state_text = "Saved new record." if result.inserted else "Record for this date already exists."
        self.last_sync_var.set(datetime.now().strftime("%H:%M"))
        self.status_var.set(f"{state_text} Vault: {self.db_path}")
        self.source_var.set(result.record.source_url)
        self.refresh_history()
        self.fetch_button.state(["!disabled"])

    def _show_error(self, message: str) -> None:
        self.status_var.set(f"Sync failed: {message}")
        self.fetch_button.state(["!disabled"])

    def refresh_history(self) -> None:
        recent_records = self.repository.list_recent(limit=30)

        for item in self.tree.get_children():
            self.tree.delete(item)

        for index, record in enumerate(recent_records):
            tag = "even" if index % 2 == 0 else "odd"
            self.tree.insert("", "end", values=(record.price_date.isoformat(), f"{record.price:.2f}"), tags=(tag,))

        if recent_records:
            latest = recent_records[0]
            previous = recent_records[1] if len(recent_records) > 1 else None
            self.date_var.set(latest.price_date.isoformat())
            self.price_var.set(f"{latest.price:.2f}")
            self.change_var.set("N/A" if previous is None else f"{latest.price - previous.price:+.2f}")
            self.source_var.set(latest.source_url)
            self.last_sync_var.set(datetime.now().strftime("%H:%M"))
        else:
            self.date_var.set("-")
            self.price_var.set("-")
            self.change_var.set("-")

        self._chart_records = list(reversed(recent_records))
        self._update_summary_metrics(recent_records)
        self.draw_chart()

    def _update_summary_metrics(self, recent_records: list) -> None:
        count = len(recent_records)
        self.records_var.set(f"{count} sessions")

        if count == 0:
            self.range_var.set("No range")
            self.trend_var.set("No signal")
            return

        prices = [record.price for record in recent_records]
        low = min(prices)
        high = max(prices)
        self.range_var.set(f"{low:.2f} / {high:.2f}")

        if count == 1:
            self.trend_var.set("Flat")
            return

        delta = recent_records[0].price - recent_records[-1].price
        if delta > 0:
            self.trend_var.set(f"Bullish {delta:+.2f}")
        elif delta < 0:
            self.trend_var.set(f"Soft {delta:+.2f}")
        else:
            self.trend_var.set("Flat 0.00")

    def draw_chart(self) -> None:
        canvas = self.chart_canvas
        canvas.delete("all")

        width = max(canvas.winfo_width(), 300)
        height = max(canvas.winfo_height(), 240)
        canvas.create_rectangle(0, 0, width, height, fill="#0a1626", outline="")

        records = self._chart_records
        if len(records) == 0:
            canvas.create_text(width / 2, height / 2, text="No market curve yet", fill="#5f7892", font=("Segoe UI Semibold", 14))
            return

        if len(records) == 1:
            record = records[0]
            canvas.create_text(width / 2, height / 2 - 12, text=record.price_date.isoformat(), fill="#7c95af", font=("Segoe UI", 11))
            canvas.create_text(width / 2, height / 2 + 18, text=f"{record.price:.2f}", fill="#f4fbff", font=("Bahnschrift SemiBold", 26))
            self.chart_hint_var.set("Single session on file")
            return

        padding_left = 58
        padding_right = 24
        padding_top = 26
        padding_bottom = 46
        plot_width = width - padding_left - padding_right
        plot_height = height - padding_top - padding_bottom

        prices = [record.price for record in records]
        min_price = min(prices)
        max_price = max(prices)
        price_span = max(max_price - min_price, 1.0)
        lower_bound = min_price - price_span * 0.12
        upper_bound = max_price + price_span * 0.12
        display_span = upper_bound - lower_bound

        def x_for(index: int) -> float:
            return padding_left + (plot_width * index / max(len(records) - 1, 1))

        def y_for(price: float) -> float:
            return padding_top + plot_height - ((price - lower_bound) / display_span) * plot_height

        grid_color = "#15304b"
        axis_color = "#284767"
        line_color = "#61cbff"
        fill_color = "#0ea5ff"
        text_color = "#7c95af"

        for step in range(5):
            y = padding_top + plot_height * step / 4
            value = upper_bound - (display_span * step / 4)
            canvas.create_line(padding_left, y, width - padding_right, y, fill=grid_color, width=1)
            canvas.create_text(padding_left - 10, y, text=f"{value:.2f}", fill=text_color, font=("Segoe UI", 9), anchor="e")

        canvas.create_line(padding_left, padding_top, padding_left, height - padding_bottom, fill=axis_color, width=1)
        canvas.create_line(padding_left, height - padding_bottom, width - padding_right, height - padding_bottom, fill=axis_color, width=1)

        points = []
        for index, record in enumerate(records):
            points.extend((x_for(index), y_for(record.price)))

        area_points = [padding_left, height - padding_bottom, *points, width - padding_right, height - padding_bottom]
        canvas.create_polygon(area_points, fill="#0c4d77", outline="")
        canvas.create_line(*points, fill=line_color, width=3, smooth=True)

        for index, record in enumerate(records):
            x = x_for(index)
            y = y_for(record.price)
            radius = 4 if index != len(records) - 1 else 5
            outline = "#0a1626" if index != len(records) - 1 else "#f4fbff"
            canvas.create_oval(x - radius, y - radius, x + radius, y + radius, fill=fill_color, outline=outline, width=2)

        label_indexes = sorted({0, len(records) // 2, len(records) - 1})
        for index in label_indexes:
            x = x_for(index)
            canvas.create_text(x, height - padding_bottom + 18, text=records[index].price_date.strftime("%m-%d"), fill=text_color, font=("Segoe UI", 9))

        last_record = records[-1]
        last_x = x_for(len(records) - 1)
        last_y = y_for(last_record.price)
        canvas.create_text(last_x - 8, last_y - 16, text=f"{last_record.price:.2f}", fill="#f4fbff", font=("Segoe UI Semibold", 10), anchor="e")

        delta = records[-1].price - records[0].price
        momentum = "Uptrend" if delta > 0 else "Downtrend" if delta < 0 else "Flat"
        self.chart_hint_var.set(
            f"{momentum} | {records[0].price_date.isoformat()} to {records[-1].price_date.isoformat()} | {delta:+.2f}"
        )

    def open_us_debt_window(self) -> None:
        window = tk.Toplevel(self.root)
        window.title("US National Debt")
        window.geometry("980x680")
        window.minsize(820, 560)
        window.configure(bg="#07111f")

        container = ttk.Frame(window, style="Root.TFrame", padding=20)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(4, weight=1)

        source_url = "https://www.usadebtclock.com/"
        status_var = tk.StringVar(value="Ready to load US national debt.")
        last_updated_var = tk.StringVar(value="History not loaded yet")
        current_value_var = tk.StringVar(value="-")
        current_date_var = tk.StringVar(value="-")
        change_var = tk.StringVar(value="-")
        range_var = tk.StringVar(value="-")
        history_records: list[USDebtRecord] = []

        ttk.Label(container, text="US National Debt", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        source_link = ttk.Label(container, text=source_url, style="Link.TLabel", cursor="hand2")
        source_link.grid(row=1, column=0, sticky="w", pady=(6, 0))
        source_link.bind("<Button-1>", lambda _event: webbrowser.open_new_tab(source_url))

        header_actions = ttk.Frame(container, style="Root.TFrame")
        header_actions.grid(row=0, column=0, sticky="e")
        refresh_button = ttk.Button(header_actions, text="Refresh")
        refresh_button.pack(anchor="e")

        ttk.Label(container, textvariable=status_var, style="Status.TLabel", wraplength=900, justify="left").grid(
            row=2,
            column=0,
            sticky="w",
            pady=(12, 0),
        )
        ttk.Label(container, textvariable=last_updated_var, style="Status.TLabel").grid(row=2, column=0, sticky="e")

        summary = ttk.Frame(container, style="StatsPanel.TFrame", padding=16)
        summary.grid(row=3, column=0, sticky="ew", pady=(14, 0))
        for index in range(4):
            summary.columnconfigure(index, weight=1)

        summary_vars = [
            ("Latest Debt", current_value_var),
            ("Snapshot Date", current_date_var),
            ("Change", change_var),
            ("30-Day Range", range_var),
        ]
        for column, (label, variable) in enumerate(summary_vars):
            block = ttk.Frame(summary, style="StatsPanel.TFrame")
            block.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 10, 0))
            block.columnconfigure(0, weight=1)
            ttk.Label(block, text=label, style="StatsLabel.TLabel").grid(row=0, column=0, sticky="w")
            ttk.Label(block, textvariable=variable, style="StatsValue.TLabel").grid(row=1, column=0, sticky="w", pady=(8, 0))

        content = ttk.Frame(container, style="Root.TFrame")
        content.grid(row=4, column=0, sticky="nsew", pady=(16, 0))
        content.columnconfigure(0, weight=7)
        content.columnconfigure(1, weight=3)
        content.rowconfigure(0, weight=1)

        chart_panel = ttk.Frame(content, style="ChartPanel.TFrame", padding=16)
        chart_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        chart_panel.columnconfigure(0, weight=1)
        chart_panel.rowconfigure(1, weight=1)
        ttk.Label(chart_panel, text="US National Debt / Recent 30 Snapshots", style="ChartTitle.TLabel").grid(
            row=0,
            column=0,
            sticky="w",
        )

        chart_hint_var = tk.StringVar(value="Awaiting local debt history")
        ttk.Label(chart_panel, textvariable=chart_hint_var, style="ChartHint.TLabel").grid(row=0, column=1, sticky="e")

        debt_canvas = tk.Canvas(chart_panel, bg="#0a1626", highlightthickness=0)
        debt_canvas.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(14, 0))

        table_panel = ttk.Frame(content, style="Panel.TFrame", padding=16)
        table_panel.grid(row=0, column=1, sticky="nsew")
        table_panel.columnconfigure(0, weight=1)
        table_panel.rowconfigure(1, weight=1)
        ttk.Label(table_panel, text="Snapshot History", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w")

        history_tree = ttk.Treeview(table_panel, columns=("date", "debt"), show="headings", height=14)
        history_tree.heading("date", text="Date")
        history_tree.heading("debt", text="US Debt")
        history_tree.column("date", width=120, anchor="center")
        history_tree.column("debt", width=200, anchor="e")
        history_tree.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        history_tree.tag_configure("even", background="#0d1b2d")
        history_tree.tag_configure("odd", background="#102238")

        scrollbar = ttk.Scrollbar(table_panel, orient="vertical", command=history_tree.yview, style="Vertical.TScrollbar")
        scrollbar.grid(row=1, column=1, sticky="ns", pady=(12, 0))
        history_tree.configure(yscrollcommand=scrollbar.set)

        def format_currency(cents: int) -> str:
            amount = cents / 100
            return f"${amount:,.2f}"

        def format_compact(cents: int) -> str:
            amount = cents / 100
            absolute = abs(amount)
            if absolute >= 1_000_000_000_000:
                return f"${amount / 1_000_000_000_000:.2f}T"
            if absolute >= 1_000_000_000:
                return f"${amount / 1_000_000_000:.2f}B"
            if absolute >= 1_000_000:
                return f"${amount / 1_000_000:.2f}M"
            return f"${amount:,.2f}"

        def redraw_chart() -> None:
            debt_canvas.delete("all")

            width = max(debt_canvas.winfo_width(), 320)
            height = max(debt_canvas.winfo_height(), 240)
            debt_canvas.create_rectangle(0, 0, width, height, fill="#0a1626", outline="")

            if not history_records:
                debt_canvas.create_text(
                    width / 2,
                    height / 2,
                    text="No US debt history yet",
                    fill="#5f7892",
                    font=("Segoe UI Semibold", 14),
                )
                return

            if len(history_records) == 1:
                record = history_records[0]
                debt_canvas.create_text(
                    width / 2,
                    height / 2 - 12,
                    text=record.snapshot_date.isoformat(),
                    fill="#7c95af",
                    font=("Segoe UI", 11),
                )
                debt_canvas.create_text(
                    width / 2,
                    height / 2 + 18,
                    text=format_compact(record.national_debt_cents),
                    fill="#f4fbff",
                    font=("Bahnschrift SemiBold", 26),
                )
                chart_hint_var.set("Single snapshot on file")
                return

            padding_left = 72
            padding_right = 24
            padding_top = 26
            padding_bottom = 46
            plot_width = width - padding_left - padding_right
            plot_height = height - padding_top - padding_bottom

            values = [record.national_debt_cents / 100 for record in history_records]
            minimum = min(values)
            maximum = max(values)
            span = max(maximum - minimum, 1.0)
            lower_bound = minimum - span * 0.12
            upper_bound = maximum + span * 0.12
            display_span = upper_bound - lower_bound

            def x_for(index: int) -> float:
                return padding_left + (plot_width * index / max(len(history_records) - 1, 1))

            def y_for(value: float) -> float:
                return padding_top + plot_height - ((value - lower_bound) / display_span) * plot_height

            grid_color = "#15304b"
            axis_color = "#284767"
            line_color = "#ffb347"
            fill_color = "#ff9f1a"
            text_color = "#7c95af"

            for step in range(5):
                y = padding_top + plot_height * step / 4
                value = upper_bound - (display_span * step / 4)
                debt_canvas.create_line(padding_left, y, width - padding_right, y, fill=grid_color, width=1)
                debt_canvas.create_text(
                    padding_left - 10,
                    y,
                    text=format_compact(int(value * 100)),
                    fill=text_color,
                    font=("Segoe UI", 9),
                    anchor="e",
                )

            debt_canvas.create_line(padding_left, padding_top, padding_left, height - padding_bottom, fill=axis_color, width=1)
            debt_canvas.create_line(
                padding_left,
                height - padding_bottom,
                width - padding_right,
                height - padding_bottom,
                fill=axis_color,
                width=1,
            )

            points = []
            for index, record in enumerate(history_records):
                points.extend((x_for(index), y_for(record.national_debt_cents / 100)))

            area_points = [padding_left, height - padding_bottom, *points, width - padding_right, height - padding_bottom]
            debt_canvas.create_polygon(area_points, fill="#5a3c12", outline="")
            debt_canvas.create_line(*points, fill=line_color, width=3, smooth=True)

            for index, record in enumerate(history_records):
                x = x_for(index)
                y = y_for(record.national_debt_cents / 100)
                radius = 4 if index != len(history_records) - 1 else 5
                outline = "#0a1626" if index != len(history_records) - 1 else "#f4fbff"
                debt_canvas.create_oval(x - radius, y - radius, x + radius, y + radius, fill=fill_color, outline=outline, width=2)

            label_indexes = sorted({0, len(history_records) // 2, len(history_records) - 1})
            for index in label_indexes:
                x = x_for(index)
                debt_canvas.create_text(
                    x,
                    height - padding_bottom + 18,
                    text=history_records[index].snapshot_date.strftime("%m-%d"),
                    fill=text_color,
                    font=("Segoe UI", 9),
                )

            last_record = history_records[-1]
            last_x = x_for(len(history_records) - 1)
            last_y = y_for(last_record.national_debt_cents / 100)
            debt_canvas.create_text(
                last_x - 8,
                last_y - 16,
                text=format_compact(last_record.national_debt_cents),
                fill="#f4fbff",
                font=("Segoe UI Semibold", 10),
                anchor="e",
            )

            delta_cents = history_records[-1].national_debt_cents - history_records[0].national_debt_cents
            momentum = "Uptrend" if delta_cents > 0 else "Downtrend" if delta_cents < 0 else "Flat"
            chart_hint_var.set(
                f"{momentum} | {history_records[0].snapshot_date.isoformat()} to {history_records[-1].snapshot_date.isoformat()} | {format_compact(delta_cents)}"
            )

        def refresh_view() -> int:
            recent_records = load_us_debt_history()[-30:]
            history_records.clear()
            history_records.extend(recent_records)

            for item in history_tree.get_children():
                history_tree.delete(item)

            for index, record in enumerate(reversed(recent_records)):
                tag = "even" if index % 2 == 0 else "odd"
                history_tree.insert(
                    "",
                    "end",
                    values=(record.snapshot_date.isoformat(), format_currency(record.national_debt_cents)),
                    tags=(tag,),
                )

            if recent_records:
                latest = recent_records[-1]
                current_value_var.set(format_compact(latest.national_debt_cents))
                current_date_var.set(latest.snapshot_date.isoformat())
                last_updated_var.set(f"Latest local snapshot: {latest.snapshot_date.isoformat()}")

                values = [record.national_debt_cents for record in recent_records]
                range_var.set(f"{format_compact(min(values))} / {format_compact(max(values))}")
                if len(recent_records) > 1:
                    delta_cents = recent_records[-1].national_debt_cents - recent_records[-2].national_debt_cents
                    change_var.set(format_compact(delta_cents))
                else:
                    change_var.set("N/A")
            else:
                current_value_var.set("-")
                current_date_var.set("-")
                change_var.set("-")
                range_var.set("-")
                last_updated_var.set("History not loaded yet")

            redraw_chart()
            return len(recent_records)

        def show_error(message: str) -> None:
            record_count = len(history_records)
            if record_count > 0:
                status_var.set(f"US debt refresh failed: {message} | Showing {record_count} cached snapshots.")
            else:
                status_var.set(f"US debt refresh failed: {message}")
            refresh_button.state(["!disabled"])

        def apply_result(result) -> None:
            if result.inserted:
                status_var.set("Saved a new US debt snapshot.")
            elif result.updated:
                status_var.set("Updated the latest US debt snapshot.")
            else:
                status_var.set("Latest US debt snapshot already matches local history.")
            refresh_view()
            refresh_button.state(["!disabled"])

        def worker() -> None:
            try:
                record = fetch_us_national_debt(timeout=12)
                result = save_us_debt_record(record)
                self.root.after(0, lambda: apply_result(result))
            except Exception as exc:
                self.root.after(0, lambda message=str(exc): show_error(message))

        def start_refresh() -> None:
            refresh_button.state(["disabled"])
            status_var.set("Loading US national debt from usadebtclock.com...")
            threading.Thread(target=worker, daemon=True).start()

        debt_canvas.bind("<Configure>", lambda _event: redraw_chart())
        refresh_button.configure(command=start_refresh)
        cached_count = refresh_view()
        if cached_count > 0:
            status_var.set(f"Loaded {cached_count} cached US debt snapshots. Refresh to fetch the latest value.")
        else:
            status_var.set("No cached US debt history. Refresh to fetch the first snapshot.")
        start_refresh()

    def open_commit_stats_window(self) -> None:
        window = tk.Toplevel(self.root)
        window.title("Commits 統計")
        window.geometry("860x620")
        window.minsize(760, 520)
        window.configure(bg="#07111f")

        container = ttk.Frame(window, style="Root.TFrame", padding=20)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(4, weight=1)

        username = "goldshoot0720"
        profile_url = f"https://github.com/{username}?tab=repositories"

        ttk.Label(container, text="Commits 統計", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        profile_link = ttk.Label(container, text=profile_url, style="Link.TLabel", cursor="hand2")
        profile_link.grid(row=1, column=0, sticky="w", pady=(6, 16))
        profile_link.bind("<Button-1>", lambda _event: webbrowser.open_new_tab(profile_url))

        header_actions = ttk.Frame(container, style="Root.TFrame")
        header_actions.grid(row=0, column=0, sticky="e")
        refresh_button = ttk.Button(header_actions, text="重新抓取")
        refresh_button.pack(anchor="e")

        loading_var = tk.StringVar(value="載入 GitHub repositories commits 統計中...")
        window._loading_var = loading_var
        ttk.Label(
            container,
            textvariable=loading_var,
            style="Status.TLabel",
            wraplength=780,
            justify="left",
        ).grid(row=2, column=0, sticky="w")
        last_updated_var = tk.StringVar(value="最後更新時間：尚未抓取")
        ttk.Label(container, textvariable=last_updated_var, style="Status.TLabel").grid(row=2, column=0, sticky="e")

        summary = ttk.Frame(container, style="StatsPanel.TFrame", padding=16)
        summary.grid(row=3, column=0, sticky="ew", pady=(14, 0))
        for index in range(4):
            summary.columnconfigure(index, weight=1)

        total_repositories_var = tk.StringVar(value="-")
        total_commits_var = tk.StringVar(value="-")
        top_ten_total_var = tk.StringVar(value="-")
        account_var = tk.StringVar(value=username)
        window._commit_summary_vars = {
            "repositories": total_repositories_var,
            "total_commits": total_commits_var,
            "top_ten_total": top_ten_total_var,
            "account": account_var,
        }
        running_commit_total = {"value": 0}
        summary_vars = [
            ("Repositories", total_repositories_var),
            ("總 Commits", total_commits_var),
            ("前 10 合計", top_ten_total_var),
            ("GitHub 帳號", account_var),
        ]
        for column, (label, variable) in enumerate(summary_vars):
            block = ttk.Frame(summary, style="StatsPanel.TFrame")
            block.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 10, 0))
            block.columnconfigure(0, weight=1)
            ttk.Label(block, text=label, style="StatsLabel.TLabel").grid(row=0, column=0, sticky="w")
            ttk.Label(block, textvariable=variable, style="StatsValue.TLabel").grid(row=1, column=0, sticky="w", pady=(8, 0))

        content = ttk.Frame(container, style="Root.TFrame")
        content.grid(row=4, column=0, sticky="nsew", pady=(16, 0))
        content.columnconfigure(0, weight=1)
        content.rowconfigure(0, weight=1)

        top_panel = ttk.Frame(content, style="Panel.TFrame", padding=16)
        top_panel.grid(row=0, column=0, sticky="nsew")
        top_panel.columnconfigure(0, weight=1)
        top_panel.rowconfigure(1, weight=1)
        ttk.Label(top_panel, text="前十大 Commits 倉庫", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w")

        top_tree = ttk.Treeview(top_panel, columns=("rank", "repo", "commits"), show="headings", height=14)
        top_tree.heading("rank", text="排名")
        top_tree.heading("repo", text="Repository")
        top_tree.heading("commits", text="Commits")
        top_tree.column("rank", width=80, anchor="center")
        top_tree.column("repo", width=440, anchor="w")
        top_tree.column("commits", width=120, anchor="e")
        top_tree.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        top_tree.insert("", "end", values=("-", "載入中...", "-"))

        scrollbar = ttk.Scrollbar(top_panel, orient="vertical", command=top_tree.yview)
        scrollbar.grid(row=1, column=1, sticky="ns", pady=(12, 0))
        top_tree.configure(yscrollcommand=scrollbar.set)

        def apply_stats(stats: GitHubCommitStats, fetched_at: str | None = None) -> None:
            if not window.winfo_exists():
                return

            total_repositories_var.set(str(stats.total_repositories))
            total_commits_var.set(str(stats.total_commits))
            top_ten_total_var.set(str(stats.top_commit_total))
            loading_var.set("GitHub commits 統計已更新。")
            if fetched_at:
                last_updated_var.set(f"最後更新時間：{fetched_at}")

            for item in top_tree.get_children():
                top_tree.delete(item)

            if not stats.top_repositories:
                top_tree.insert("", "end", values=("-", "查無公開 repositories commits 資料", "-"))
                return

            for index, repo in enumerate(stats.top_repositories, start=1):
                top_tree.insert("", "end", values=(index, repo.name, repo.commit_count))

        def update_progress(stage: str, current: int, total: int, repo_name: str | None, commit_count: int | None) -> None:
            if not window.winfo_exists():
                return
            if stage == "repositories_loaded":
                loading_var.set(f"已取得 repositories 清單，準備統計 {total} 個 repo...")
                total_repositories_var.set(str(total))
                total_commits_var.set("0")
                top_ten_total_var.set("0")
                running_commit_total["value"] = 0
                return
            if stage == "repo_commits_loading":
                total_repositories_var.set(f"{current}/{total}")
                loading_var.set(f"統計進度 {current}/{total}：正在讀取 {repo_name} commits...")
                return
            if stage == "repo_commits_loaded":
                running_commit_total["value"] += commit_count or 0
                total_repositories_var.set(f"{current}/{total}")
                total_commits_var.set(str(running_commit_total["value"]))
                top_ten_total_var.set(str(running_commit_total["value"]))
                loading_var.set(f"統計進度 {current}/{total}：已完成 {repo_name}")

        def open_selected_repo(_event: tk.Event) -> None:
            selection = top_tree.selection()
            if not selection:
                return
            values = top_tree.item(selection[0], "values")
            if len(values) < 2:
                return
            repo_name = str(values[1])
            webbrowser.open_new_tab(f"https://github.com/{username}/{repo_name}")

        def show_error(message: str) -> None:
            if not window.winfo_exists():
                return
            total_repositories_var.set("-")
            total_commits_var.set("-")
            top_ten_total_var.set("-")
            loading_var.set(f"讀取失敗: {message}。請確認目前電腦可連上 GitHub。")
            for item in top_tree.get_children():
                top_tree.delete(item)
            top_tree.insert("", "end", values=("-", "無法載入 GitHub 資料", "-"))
            refresh_button.state(["!disabled"])

        def worker() -> None:
            try:
                stats = fetch_github_commit_stats(
                    username,
                    timeout=8,
                    progress_callback=lambda stage, current, total, repo_name, commit_count: self.root.after(
                        0, lambda: update_progress(stage, current, total, repo_name, commit_count)
                    ),
                )
                cached = save_cached_github_commit_stats(stats)
                self.root.after(0, lambda: apply_stats(stats, cached.fetched_at))
                self.root.after(0, lambda: refresh_button.state(["!disabled"]))
            except Exception as exc:
                self.root.after(0, lambda message=str(exc): show_error(message))

        def start_refresh() -> None:
            refresh_button.state(["disabled"])
            loading_var.set("載入 GitHub repositories commits 統計中...")
            threading.Thread(target=worker, daemon=True).start()

        cached = load_cached_github_commit_stats()
        if cached is not None and cached.stats.username == username:
            apply_stats(cached.stats, cached.fetched_at)
            loading_var.set("已載入快取資料，可按「重新抓取」更新。")

        refresh_button.configure(command=start_refresh)
        top_tree.bind("<Double-1>", open_selected_repo)
        start_refresh()

    def open_pizza_watch_window(self) -> None:
        window = tk.Toplevel(self.root)
        window.title("披薩監控")
        window.geometry("1080x720")
        window.minsize(920, 580)
        window.configure(bg="#07111f")

        container = ttk.Frame(window, style="Root.TFrame", padding=20)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=3)
        container.columnconfigure(1, weight=2)
        container.rowconfigure(3, weight=1)

        ttk.Label(container, text="披薩監控", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        source_link = ttk.Label(container, text="https://www.pizzint.watch/", style="Link.TLabel", cursor="hand2")
        source_link.grid(row=1, column=0, sticky="w", pady=(6, 0))
        source_link.bind("<Button-1>", lambda _event: webbrowser.open_new_tab("https://www.pizzint.watch/"))

        header_actions = ttk.Frame(container, style="Root.TFrame")
        header_actions.grid(row=0, column=1, sticky="e")
        refresh_button = ttk.Button(header_actions, text="Refresh")
        refresh_button.pack(anchor="e")

        status_var = tk.StringVar(value="準備載入 PizzINT 快照...")
        ttk.Label(container, textvariable=status_var, style="Status.TLabel", wraplength=1020, justify="left").grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(12, 0),
        )

        chart_panel = ttk.Frame(container, style="ChartPanel.TFrame", padding=18)
        chart_panel.grid(row=3, column=0, sticky="nsew", padx=(0, 14), pady=(16, 0))
        chart_panel.columnconfigure(0, weight=1)
        chart_panel.rowconfigure(1, weight=1)
        ttk.Label(chart_panel, text="PizzINT History Chart", style="ChartTitle.TLabel").grid(row=0, column=0, sticky="w")

        chart_hint_var = tk.StringVar(value="等待資料")
        ttk.Label(chart_panel, textvariable=chart_hint_var, style="ChartHint.TLabel").grid(row=0, column=1, sticky="e")

        chart_canvas = tk.Canvas(chart_panel, bg="#0a1626", highlightthickness=0)
        chart_canvas.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(14, 0))

        side_panel = ttk.Frame(container, style="Root.TFrame")
        side_panel.grid(row=3, column=1, sticky="nsew", pady=(16, 0))
        side_panel.columnconfigure(0, weight=1)
        side_panel.rowconfigure(1, weight=1)

        summary_panel = ttk.Frame(side_panel, style="StatsPanel.TFrame", padding=16)
        summary_panel.grid(row=0, column=0, sticky="ew")
        for index in range(6):
            summary_panel.columnconfigure(index, weight=1)

        doughcon_var = tk.StringVar(value="-")
        message_var = tk.StringVar(value="-")
        monitored_var = tk.StringVar(value="-")
        nearest_var = tk.StringVar(value="-")
        streak_days_var = tk.StringVar(value="-")
        streak_weeks_var = tk.StringVar(value="-")
        for column, (label, variable) in enumerate(
            (
                ("Doughcon", doughcon_var),
                ("Watch", message_var),
                ("Locations", monitored_var),
                ("Nearest", nearest_var),
                ("連續天數", streak_days_var),
                ("連續週數", streak_weeks_var),
            )
        ):
            block = ttk.Frame(summary_panel, style="StatsPanel.TFrame")
            block.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 10, 0))
            block.columnconfigure(0, weight=1)
            ttk.Label(block, text=label, style="StatsLabel.TLabel").grid(row=0, column=0, sticky="w")
            ttk.Label(block, textvariable=variable, style="StatsValue.TLabel").grid(row=1, column=0, sticky="w", pady=(8, 0))

        table_panel = ttk.Frame(side_panel, style="Panel.TFrame", padding=16)
        table_panel.grid(row=1, column=0, sticky="nsew", pady=(14, 0))
        table_panel.columnconfigure(0, weight=1)
        table_panel.rowconfigure(1, weight=1)
        ttk.Label(table_panel, text="Monitored Pizza Shops", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w")

        shop_tree = ttk.Treeview(table_panel, columns=("name", "status", "distance"), show="headings", height=14)
        shop_tree.heading("name", text="Store")
        shop_tree.heading("status", text="Status")
        shop_tree.heading("distance", text="Miles")
        shop_tree.column("name", width=260, anchor="w")
        shop_tree.column("status", width=90, anchor="center")
        shop_tree.column("distance", width=90, anchor="e")
        shop_tree.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        shop_tree.tag_configure("even", background="#0d1b2d")
        shop_tree.tag_configure("odd", background="#102238")

        scrollbar = ttk.Scrollbar(table_panel, orient="vertical", command=shop_tree.yview, style="Vertical.TScrollbar")
        scrollbar.grid(row=1, column=1, sticky="ns", pady=(12, 0))
        shop_tree.configure(yscrollcommand=scrollbar.set)

        current_snapshot: dict[str, PizzaWatchSnapshot | None] = {"value": None}
        history_entries: dict[str, list[PizzaWatchHistoryEntry]] = {"value": []}

        def redraw_chart() -> None:
            snapshot = current_snapshot["value"]
            entries = history_entries["value"]
            chart_canvas.delete("all")

            width = max(chart_canvas.winfo_width(), 420)
            height = max(chart_canvas.winfo_height(), 280)
            chart_canvas.create_rectangle(0, 0, width, height, fill="#0a1626", outline="")

            if snapshot is None:
                chart_canvas.create_text(
                    width / 2,
                    height / 2,
                    text="No pizza watch data yet",
                    fill="#5f7892",
                    font=("Segoe UI Semibold", 14),
                )
                return

            padding_left = 54
            padding_right = 24
            padding_top = 34
            padding_bottom = 58
            plot_width = width - padding_left - padding_right
            plot_height = height - padding_top - padding_bottom
            if not entries:
                chart_canvas.create_text(
                    width / 2,
                    height / 2,
                    text="Waiting for pizza history",
                    fill="#5f7892",
                    font=("Segoe UI Semibold", 14),
                )
                return

            doughcon_max = max(max(entry.doughcon_level for entry in entries), 1)
            open_max = max(max(entry.open_shop_count for entry in entries), 1)
            step_width = plot_width / max(len(entries) - 1, 1)

            chart_canvas.create_line(
                padding_left,
                height - padding_bottom,
                width - padding_right,
                height - padding_bottom,
                fill="#284767",
                width=1,
            )
            midline_y = padding_top + plot_height * 0.45
            chart_canvas.create_line(
                padding_left,
                midline_y,
                width - padding_right,
                midline_y,
                fill="#15304b",
                width=1,
                dash=(4, 4),
            )

            points: list[float] = []
            bar_width = max(min(step_width * 0.45, 28), 12)
            for index, entry in enumerate(entries):
                x = padding_left + index * step_width
                doughcon_y = padding_top + (midline_y - padding_top) * (1 - (entry.doughcon_level / doughcon_max))
                points.extend((x, doughcon_y))

                x0 = x - bar_width / 2
                x1 = x + bar_width / 2
                bar_height = (height - padding_bottom - (midline_y + 16)) * (entry.open_shop_count / open_max)
                y0 = height - padding_bottom - bar_height
                color = "#33d17a" if entry.open_shop_count > 0 else "#ff7b72"
                chart_canvas.create_rectangle(x0, y0, x1, height - padding_bottom, fill=color, outline="")
                chart_canvas.create_text(
                    x,
                    y0 - 12,
                    text=str(entry.open_shop_count),
                    fill="#dbe9f6",
                    font=("Segoe UI", 9),
                )
                chart_canvas.create_text(
                    x,
                    height - padding_bottom + 18,
                    text=entry.snapshot_date.strftime("%m-%d"),
                    fill="#7c95af",
                    font=("Segoe UI", 8),
                )

            if len(points) >= 4:
                chart_canvas.create_line(*points, fill="#7fd4ff", width=3, smooth=True)
            for index, entry in enumerate(entries):
                x = padding_left + index * step_width
                doughcon_y = padding_top + (midline_y - padding_top) * (1 - (entry.doughcon_level / doughcon_max))
                chart_canvas.create_oval(x - 4, doughcon_y - 4, x + 4, doughcon_y + 4, fill="#7fd4ff", outline="#0a1626", width=2)
                chart_canvas.create_text(
                    x,
                    doughcon_y - 14,
                    text=f"D{entry.doughcon_level}",
                    fill="#dbe9f6",
                    font=("Segoe UI", 8),
                )

            chart_canvas.create_text(
                padding_left,
                padding_top - 8,
                text="Doughcon trend",
                fill="#7fd4ff",
                font=("Segoe UI Semibold", 10),
                anchor="w",
            )
            chart_canvas.create_text(
                padding_left,
                midline_y + 10,
                text="Open shops by day",
                fill="#33d17a",
                font=("Segoe UI Semibold", 10),
                anchor="w",
            )

        def apply_snapshot(snapshot: PizzaWatchSnapshot) -> None:
            self._pizza_watch_snapshot = snapshot
            current_snapshot["value"] = snapshot
            updated_history = update_pizza_watch_history(snapshot)
            history_entries["value"] = updated_history[-14:]
            streaks = calculate_pizza_watch_streaks(updated_history)
            for item in shop_tree.get_children():
                shop_tree.delete(item)
            for index, shop in enumerate(snapshot.shops):
                tag = "even" if index % 2 == 0 else "odd"
                shop_tree.insert("", "end", values=(shop.name, shop.status, f"{shop.distance_miles:.1f}"), tags=(tag,))

            nearest_shop = min(snapshot.shops, key=lambda shop: shop.distance_miles)
            doughcon_var.set(str(snapshot.doughcon_level))
            message_var.set(snapshot.doughcon_title)
            monitored_var.set(str(snapshot.monitored_locations))
            nearest_var.set(f"{nearest_shop.distance_miles:.1f} mi")
            streak_days_var.set(str(streaks.consecutive_days))
            streak_weeks_var.set(str(streaks.consecutive_weeks))
            chart_hint_var.set(f"{snapshot.doughcon_message} | {snapshot.site_status} | {len(history_entries['value'])} day chart")
            status_var.set(
                f"PizzINT 快照已更新。連續 {streaks.consecutive_days} 天 / {streaks.consecutive_weeks} 週有監控紀錄。"
            )
            redraw_chart()
            refresh_button.state(["!disabled"])

        def show_error(message: str) -> None:
            refresh_button.state(["!disabled"])
            status_var.set(f"PizzINT 載入失敗: {message}")

        def worker(force_refresh: bool) -> None:
            try:
                snapshot = self._pizza_watch_snapshot
                if force_refresh or snapshot is None:
                    snapshot = fetch_pizza_watch_snapshot()
                self.root.after(0, lambda: apply_snapshot(snapshot))
            except Exception as exc:
                self.root.after(0, lambda message=str(exc): show_error(message))

        def start_refresh(force_refresh: bool) -> None:
            refresh_button.state(["disabled"])
            status_var.set("載入 PizzINT 即時快照中...")
            threading.Thread(target=lambda: worker(force_refresh), daemon=True).start()

        chart_canvas.bind("<Configure>", lambda _event: redraw_chart())
        refresh_button.configure(command=lambda: start_refresh(True))
        start_refresh(False)

    def open_lottery_window(self) -> None:
        window = tk.Toplevel(self.root)
        window.title("最瞎結婚理由")
        window.geometry("1180x760")
        window.minsize(980, 620)
        window.configure(bg="#07111f")

        container = ttk.Frame(window, style="Root.TFrame", padding=20)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(3, weight=1)

        ttk.Label(container, text="最瞎結婚理由", style="Title.TLabel").grid(row=0, column=0, sticky="w")

        sources = ttk.Frame(container, style="Root.TFrame")
        sources.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        for index, config in enumerate(GAME_CONFIGS):
            source_link = ttk.Label(sources, text=config.source_url, style="Link.TLabel", cursor="hand2")
            source_link.grid(row=index, column=0, sticky="w", pady=(0 if index == 0 else 6, 0))
            source_link.bind("<Button-1>", lambda _event, url=config.source_url: webbrowser.open_new_tab(url))

        header_actions = ttk.Frame(container, style="Root.TFrame")
        header_actions.grid(row=0, column=0, sticky="e")
        refresh_button = ttk.Button(header_actions, text="Refresh")
        refresh_button.pack(anchor="e")

        status_var = tk.StringVar(value="準備載入台灣彩券資料...")
        ttk.Label(container, textvariable=status_var, style="Status.TLabel", wraplength=1060, justify="left").grid(
            row=2,
            column=0,
            sticky="w",
            pady=(12, 0),
        )

        notebook = ttk.Notebook(container)
        notebook.grid(row=3, column=0, sticky="nsew", pady=(16, 0))

        tab_views: dict[str, tuple[tk.StringVar, ttk.Treeview]] = {}
        for config in GAME_CONFIGS:
            tab = ttk.Frame(notebook, style="Root.TFrame", padding=12)
            tab.columnconfigure(0, weight=1)
            tab.rowconfigure(1, weight=1)
            notebook.add(tab, text=config.title)

            summary_var = tk.StringVar(value="尚未載入資料")
            ttk.Label(tab, textvariable=summary_var, style="Status.TLabel", wraplength=1020, justify="left").grid(
                row=0,
                column=0,
                sticky="w",
                pady=(0, 10),
            )

            table_wrap = ttk.Frame(tab, style="Panel.TFrame", padding=10)
            table_wrap.grid(row=1, column=0, sticky="nsew")
            table_wrap.columnconfigure(0, weight=1)
            table_wrap.rowconfigure(0, weight=1)

            tree = ttk.Treeview(
                table_wrap,
                columns=("issue", "date", "numbers", "compare"),
                show="headings",
                height=18,
            )
            tree.heading("issue", text="期別")
            tree.heading("date", text="開獎日期")
            tree.heading("numbers", text="開獎號碼")
            tree.heading("compare", text="比對結果")
            tree.column("issue", width=120, anchor="center")
            tree.column("date", width=110, anchor="center")
            tree.column("numbers", width=290, anchor="center")
            tree.column("compare", width=600, anchor="w")
            tree.grid(row=0, column=0, sticky="nsew")
            tree.tag_configure("even", background="#0d1b2d")
            tree.tag_configure("odd", background="#102238")

            scrollbar = ttk.Scrollbar(table_wrap, orient="vertical", command=tree.yview, style="Vertical.TScrollbar")
            scrollbar.grid(row=0, column=1, sticky="ns")
            tree.configure(yscrollcommand=scrollbar.set)
            tab_views[config.key] = (summary_var, tree)

        def apply_lottery_draws(draw_map: dict[str, list]) -> None:
            self._lottery_draws = draw_map
            for config in GAME_CONFIGS:
                summary_var, tree = tab_views[config.key]
                for item in tree.get_children():
                    tree.delete(item)
                draws = draw_map.get(config.key, [])
                summary_var.set(
                    f"共 {len(draws)} 期 | " + " | ".join(build_group_summaries(config, draws))
                    if draws
                    else "查無資料"
                )
                for index, draw in enumerate(reversed(draws)):
                    tag = "even" if index % 2 == 0 else "odd"
                    tree.insert(
                        "",
                        "end",
                        values=(
                            draw.issue,
                            draw.draw_date,
                            draw.numbers_text(config.special_label),
                            draw.comparisons_text(config.special_label),
                        ),
                        tags=(tag,),
                    )
            refresh_button.state(["!disabled"])
            status_var.set("台灣彩券資料已更新，已列出每期號碼與指定組合比對結果。")

        def show_lottery_error(message: str) -> None:
            refresh_button.state(["!disabled"])
            status_var.set(f"台灣彩券資料載入失敗: {message}")

        def worker(force_refresh: bool) -> None:
            try:
                draw_map = self._lottery_draws
                if force_refresh or draw_map is None:
                    draw_map = fetch_all_lottery_draws()
                self.root.after(0, lambda: apply_lottery_draws(draw_map))
            except Exception as exc:
                self.root.after(0, lambda message=str(exc): show_lottery_error(message))

        def start_refresh(force_refresh: bool) -> None:
            refresh_button.state(["disabled"])
            status_var.set("載入官方台灣彩券年度資料中，這會花一點時間...")
            threading.Thread(target=lambda: worker(force_refresh), daemon=True).start()

        refresh_button.configure(command=lambda: start_refresh(True))
        start_refresh(False)

    def open_brent_spot_window(self) -> None:
        window = tk.Toplevel(self.root)
        window.title("Dated Brent 現貨")
        window.geometry("1080x720")
        window.minsize(920, 580)
        window.configure(bg="#07111f")

        container = ttk.Frame(window, style="Root.TFrame", padding=20)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=3)
        container.columnconfigure(1, weight=2)
        container.rowconfigure(3, weight=1)

        ttk.Label(container, text="Dated Brent 現貨原油", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        source_link = ttk.Label(container, text=BRENT_SPOT_SOURCE_URL, style="Link.TLabel", cursor="hand2")
        source_link.grid(row=1, column=0, sticky="w", pady=(6, 0))
        source_link.bind("<Button-1>", lambda _event: webbrowser.open_new_tab(BRENT_SPOT_SOURCE_URL))

        header_actions = ttk.Frame(container, style="Root.TFrame")
        header_actions.grid(row=0, column=1, sticky="e")
        refresh_button = ttk.Button(header_actions, text="Refresh")
        refresh_button.pack(anchor="e")

        status_var = tk.StringVar(value="準備載入 Brent 現貨資料...")
        ttk.Label(container, textvariable=status_var, style="Status.TLabel", wraplength=1020, justify="left").grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(12, 0),
        )
        headline = "供不應求！布蘭特原油現貨曾破141美元　創2008年以來高"
        ttk.Label(container, text=headline, style="Status.TLabel", wraplength=1020, justify="left").grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(36, 0),
        )

        chart_panel = ttk.Frame(container, style="ChartPanel.TFrame", padding=18)
        chart_panel.grid(row=3, column=0, sticky="nsew", padx=(0, 14), pady=(16, 0))
        chart_panel.columnconfigure(0, weight=1)
        chart_panel.rowconfigure(1, weight=1)
        ttk.Label(chart_panel, text="Dated Brent Spot Price (USD/bbl)", style="ChartTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )

        chart_hint_var = tk.StringVar(value="等待資料")
        ttk.Label(chart_panel, textvariable=chart_hint_var, style="ChartHint.TLabel").grid(row=0, column=1, sticky="e")

        chart_canvas = tk.Canvas(chart_panel, bg="#0a1626", highlightthickness=0)
        chart_canvas.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(14, 0))

        side_panel = ttk.Frame(container, style="Root.TFrame")
        side_panel.grid(row=3, column=1, sticky="nsew", pady=(16, 0))
        side_panel.columnconfigure(0, weight=1)
        side_panel.rowconfigure(1, weight=1)

        summary_panel = ttk.Frame(side_panel, style="StatsPanel.TFrame", padding=16)
        summary_panel.grid(row=0, column=0, sticky="ew")
        for index in range(3):
            summary_panel.columnconfigure(index, weight=1)

        latest_price_var = tk.StringVar(value="-")
        latest_date_var = tk.StringVar(value="-")
        change_var = tk.StringVar(value="-")
        for column, (label, variable) in enumerate(
            (
                ("Latest", latest_price_var),
                ("Date", latest_date_var),
                ("Change", change_var),
            )
        ):
            block = ttk.Frame(summary_panel, style="StatsPanel.TFrame")
            block.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 10, 0))
            block.columnconfigure(0, weight=1)
            ttk.Label(block, text=label, style="StatsLabel.TLabel").grid(row=0, column=0, sticky="w")
            ttk.Label(block, textvariable=variable, style="StatsValue.TLabel").grid(row=1, column=0, sticky="w", pady=(8, 0))

        table_panel = ttk.Frame(side_panel, style="Panel.TFrame", padding=16)
        table_panel.grid(row=1, column=0, sticky="nsew", pady=(14, 0))
        table_panel.columnconfigure(0, weight=1)
        table_panel.rowconfigure(1, weight=1)
        ttk.Label(table_panel, text="Recent Brent Spot", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w")

        price_tree = ttk.Treeview(table_panel, columns=("date", "price"), show="headings", height=14)
        price_tree.heading("date", text="Date")
        price_tree.heading("price", text="USD/bbl")
        price_tree.column("date", width=120, anchor="center")
        price_tree.column("price", width=120, anchor="e")
        price_tree.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        price_tree.tag_configure("even", background="#0d1b2d")
        price_tree.tag_configure("odd", background="#102238")

        scrollbar = ttk.Scrollbar(table_panel, orient="vertical", command=price_tree.yview, style="Vertical.TScrollbar")
        scrollbar.grid(row=1, column=1, sticky="ns", pady=(12, 0))
        price_tree.configure(yscrollcommand=scrollbar.set)

        series_cache: dict[str, list[BrentSpotPoint]] = {"value": []}

        def redraw_chart() -> None:
            points = series_cache["value"]
            chart_canvas.delete("all")

            width = max(chart_canvas.winfo_width(), 420)
            height = max(chart_canvas.winfo_height(), 280)
            chart_canvas.create_rectangle(0, 0, width, height, fill="#0a1626", outline="")

            if not points:
                chart_canvas.create_text(
                    width / 2,
                    height / 2,
                    text="No Brent spot data yet",
                    fill="#5f7892",
                    font=("Segoe UI Semibold", 14),
                )
                return

            padding_left = 54
            padding_right = 24
            padding_top = 34
            padding_bottom = 54
            plot_width = width - padding_left - padding_right
            plot_height = height - padding_top - padding_bottom

            prices = [point.price for point in points]
            min_price = min(prices)
            max_price = max(prices)
            span = max(max_price - min_price, 1.0)
            lower = min_price - span * 0.1
            upper = max_price + span * 0.1
            display_span = upper - lower

            def x_for(index: int) -> float:
                return padding_left + plot_width * index / max(len(points) - 1, 1)

            def y_for(price: float) -> float:
                return padding_top + plot_height - ((price - lower) / display_span) * plot_height

            chart_canvas.create_line(
                padding_left,
                height - padding_bottom,
                width - padding_right,
                height - padding_bottom,
                fill="#284767",
                width=1,
            )
            chart_canvas.create_line(
                padding_left,
                padding_top,
                padding_left,
                height - padding_bottom,
                fill="#284767",
                width=1,
            )
            ref_price = 141.0
            if lower <= ref_price <= upper:
                ref_y = y_for(ref_price)
                chart_canvas.create_line(
                    padding_left,
                    ref_y,
                    width - padding_right,
                    ref_y,
                    fill="#ffb347",
                    width=2,
                    dash=(6, 4),
                )
                chart_canvas.create_text(
                    width - padding_right - 6,
                    ref_y - 10,
                    text="141 (2008 high)",
                    fill="#ffcf99",
                    font=("Segoe UI Semibold", 9),
                    anchor="e",
                )

            points_line: list[float] = []
            for index, point in enumerate(points):
                points_line.extend((x_for(index), y_for(point.price)))

            if len(points_line) >= 4:
                chart_canvas.create_line(*points_line, fill="#7fd4ff", width=3, smooth=True)

            for index, point in enumerate(points):
                x = x_for(index)
                y = y_for(point.price)
                chart_canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill="#7fd4ff", outline="#0a1626", width=2)

            label_indexes = sorted({0, len(points) // 2, len(points) - 1})
            for index in label_indexes:
                x = x_for(index)
                chart_canvas.create_text(
                    x,
                    height - padding_bottom + 18,
                    text=points[index].price_date.strftime("%m-%d"),
                    fill="#7c95af",
                    font=("Segoe UI", 8),
                )

            chart_canvas.create_text(
                padding_left,
                padding_top - 8,
                text="Spot price trend",
                fill="#7fd4ff",
                font=("Segoe UI Semibold", 10),
                anchor="w",
            )

        def apply_series(points: list[BrentSpotPoint]) -> None:
            series_cache["value"] = points
            for item in price_tree.get_children():
                price_tree.delete(item)
            for index, point in enumerate(reversed(points[-30:])):
                tag = "even" if index % 2 == 0 else "odd"
                price_tree.insert("", "end", values=(point.price_date.isoformat(), f"{point.price:.2f}"), tags=(tag,))

            latest = points[-1]
            previous = points[-2] if len(points) > 1 else None
            latest_price_var.set(f"{latest.price:.2f}")
            latest_date_var.set(latest.price_date.isoformat())
            change_var.set("N/A" if previous is None else f"{latest.price - previous.price:+.2f}")
            chart_hint_var.set(f"{len(points)} data points")
            status_var.set("Brent 現貨圖表已更新。資料來源為 EIA spot price 資料集。")
            redraw_chart()
            refresh_button.state(["!disabled"])

        def show_error(message: str) -> None:
            refresh_button.state(["!disabled"])
            status_var.set(f"Brent 現貨資料載入失敗: {message}")

        def worker(force_refresh: bool) -> None:
            try:
                points = series_cache["value"]
                if force_refresh or not points:
                    points = fetch_brent_spot_series()
                self.root.after(0, lambda: apply_series(points))
            except Exception as exc:
                self.root.after(0, lambda message=str(exc): show_error(message))

        def start_refresh(force_refresh: bool) -> None:
            refresh_button.state(["disabled"])
            status_var.set("載入 Brent 現貨資料中...")
            threading.Thread(target=lambda: worker(force_refresh), daemon=True).start()

        chart_canvas.bind("<Configure>", lambda _event: redraw_chart())
        refresh_button.configure(command=lambda: start_refresh(True))
        start_refresh(False)


def main() -> None:
    if TK_IMPORT_ERROR is not None:
        print("GUI is unavailable because this Python installation does not include tkinter.", file=sys.stderr)
        print("On macOS, install a Python build with Tk support, or use the CLI command: oil-tracker", file=sys.stderr)
        raise SystemExit(1) from TK_IMPORT_ERROR

    root = tk.Tk()
    app = OilTrackerApp(root, default_db_path())
    root.after(150, app.fetch_latest)
    root.mainloop()


if __name__ == "__main__":
    main()
