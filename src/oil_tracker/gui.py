from __future__ import annotations

from datetime import datetime
from pathlib import Path
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
    from .github_stats import GitHubCommitStats, fetch_github_commit_stats
    from .settings import AppSettings, load_settings, save_settings
    from .storage import OilPriceRepository, SaveResult
except ImportError:
    from gme import fetch_price_record
    from paths import default_db_path
    from github_stats import GitHubCommitStats, fetch_github_commit_stats
    from settings import AppSettings, load_settings, save_settings
    from storage import OilPriceRepository, SaveResult


class OilTrackerApp:
    def __init__(self, root: tk.Tk, db_path: Path) -> None:
        self.root = root
        self.db_path = db_path
        self.repository = OilPriceRepository(db_path)
        self._chart_records: list = []

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
        self.style.configure("Card.TFrame", background="#112742")
        self.style.configure("Panel.TFrame", background="#102238")
        self.style.configure("MutedCard.TFrame", background="#0c1a2d")
        self.style.configure("ChartPanel.TFrame", background="#0a1626")
        self.style.configure("StatsPanel.TFrame", background="#0c1a2d")

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
        container.rowconfigure(2, weight=1)

        header = ttk.Frame(container, style="Hero.TFrame", padding=24)
        header.grid(row=0, column=0, sticky="ew")
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

        hero_meta = ttk.Frame(header, style="Hero.TFrame")
        hero_meta.grid(row=0, column=1, rowspan=3, sticky="nsew", padx=(24, 0))
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
        cards.grid(row=1, column=0, sticky="ew", pady=(22, 18))
        for index in range(5):
            cards.columnconfigure(index, weight=1)

        self._build_card(cards, 0, "SESSION DATE", self.date_var, "Latest captured pricing session")
        self._build_card(cards, 1, "LAST PRICE", self.price_var, "OQD marker close")
        self._build_card(cards, 2, "DAY CHANGE", self.change_var, "Versus prior saved record")
        self._build_card(cards, 3, "DATA WINDOW", self.records_var, "Stored local history")
        self._build_card(cards, 4, "TRADING RANGE", self.range_var, "Observed across loaded window")

        content = ttk.Frame(container, style="Root.TFrame")
        content.grid(row=2, column=0, sticky="nsew")
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

        footer = ttk.Frame(container, style="Root.TFrame")
        footer.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        footer.columnconfigure(0, weight=1)
        ttk.Label(footer, textvariable=self.status_var, style="Status.TLabel").grid(row=0, column=0, sticky="w")
        source_link = ttk.Label(footer, textvariable=self.source_var, style="Link.TLabel", cursor="hand2")
        source_link.grid(row=1, column=0, sticky="w", pady=(4, 0))
        source_link.bind("<Button-1>", lambda _event: self.open_source_link())

    def _build_menu(self) -> None:
        menu_bar = tk.Menu(self.root)
        stats_menu = tk.Menu(menu_bar, tearoff=False)
        stats_menu.add_command(label="Commits", command=self.open_commit_stats_window)
        menu_bar.add_cascade(label="統計", menu=stats_menu)
        settings_menu = tk.Menu(menu_bar, tearoff=False)
        settings_menu.add_command(label="GitHub Token", command=self.open_github_token_settings)
        menu_bar.add_cascade(label="設定", menu=settings_menu)
        self.root.configure(menu=menu_bar)

    def open_github_token_settings(self) -> None:
        settings = load_settings()
        window = tk.Toplevel(self.root)
        window.title("GitHub Token")
        window.geometry("720x320")
        window.minsize(620, 280)
        window.configure(bg="#07111f")
        window.transient(self.root)

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
            self.root.after(0, lambda: self._show_error(str(exc)))

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

        loading_var = tk.StringVar(value="載入 GitHub repositories commits 統計中...")
        ttk.Label(
            container,
            textvariable=loading_var,
            style="Status.TLabel",
            wraplength=780,
            justify="left",
        ).grid(row=2, column=0, sticky="w")

        summary = ttk.Frame(container, style="StatsPanel.TFrame", padding=16)
        summary.grid(row=3, column=0, sticky="ew", pady=(14, 0))
        for index in range(4):
            summary.columnconfigure(index, weight=1)

        total_repositories_var = tk.StringVar(value="-")
        total_commits_var = tk.StringVar(value="-")
        top_ten_total_var = tk.StringVar(value="-")
        account_var = tk.StringVar(value=username)
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

        def apply_stats(stats: GitHubCommitStats) -> None:
            if not window.winfo_exists():
                return

            total_repositories_var.set(str(stats.total_repositories))
            total_commits_var.set(str(stats.total_commits))
            top_ten_total_var.set(str(stats.top_commit_total))
            loading_var.set("GitHub commits 統計已更新。")

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

        def worker() -> None:
            try:
                stats = fetch_github_commit_stats(
                    username,
                    timeout=8,
                    max_repositories=10,
                    progress_callback=lambda stage, current, total, repo_name, commit_count: self.root.after(
                        0, lambda: update_progress(stage, current, total, repo_name, commit_count)
                    ),
                )
                self.root.after(0, lambda: apply_stats(stats))
            except Exception as exc:
                self.root.after(0, lambda: show_error(str(exc)))

        top_tree.bind("<Double-1>", open_selected_repo)
        threading.Thread(target=worker, daemon=True).start()


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
