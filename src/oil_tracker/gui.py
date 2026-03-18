from __future__ import annotations

from pathlib import Path
import threading
import tkinter as tk
from tkinter import ttk

try:
    from .gme import fetch_price_record
    from .storage import OilPriceRepository, SaveResult
except ImportError:
    from gme import fetch_price_record
    from storage import OilPriceRepository, SaveResult


class OilTrackerApp:
    def __init__(self, root: tk.Tk, db_path: Path) -> None:
        self.root = root
        self.db_path = db_path
        self.repository = OilPriceRepository(db_path)

        self.root.title("OQD Daily Marker Price Tracker")
        self.root.geometry("1180x760")
        self.root.minsize(920, 620)
        self.root.configure(bg="#efe6d6")

        self.style = ttk.Style()
        self.style.theme_use("clam")
        self._configure_styles()

        self.status_var = tk.StringVar(value="Ready")
        self.date_var = tk.StringVar(value="-")
        self.price_var = tk.StringVar(value="-")
        self.change_var = tk.StringVar(value="-")
        self.source_var = tk.StringVar(value="https://www.gulfmerc.com/")
        self.chart_hint_var = tk.StringVar(value="No history yet")

        self._build_layout()
        self.refresh_history()

    def _configure_styles(self) -> None:
        self.style.configure("Root.TFrame", background="#efe6d6")
        self.style.configure("Card.TFrame", background="#16302b")
        self.style.configure("Panel.TFrame", background="#f9f5ee")
        self.style.configure("ChartPanel.TFrame", background="#fffaf2")
        self.style.configure("Title.TLabel", background="#efe6d6", foreground="#16302b", font=("Georgia", 24, "bold"))
        self.style.configure("Subtitle.TLabel", background="#efe6d6", foreground="#5a4c3b", font=("Georgia", 11))
        self.style.configure("CardLabel.TLabel", background="#16302b", foreground="#e7d7b1", font=("Segoe UI", 10, "bold"))
        self.style.configure("CardValue.TLabel", background="#16302b", foreground="#fff9ec", font=("Georgia", 26, "bold"))
        self.style.configure("PanelTitle.TLabel", background="#f9f5ee", foreground="#16302b", font=("Georgia", 15, "bold"))
        self.style.configure("ChartTitle.TLabel", background="#fffaf2", foreground="#16302b", font=("Georgia", 15, "bold"))
        self.style.configure("Status.TLabel", background="#efe6d6", foreground="#5a4c3b", font=("Segoe UI", 10))
        self.style.configure("Hint.TLabel", background="#fffaf2", foreground="#6f6355", font=("Segoe UI", 10))
        self.style.configure("Accent.TButton", font=("Segoe UI", 11, "bold"), padding=(16, 10), background="#b86a2c", foreground="#ffffff")
        self.style.map("Accent.TButton", background=[("active", "#9e5923")])
        self.style.configure("Treeview", font=("Consolas", 10), rowheight=28)
        self.style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

    def _build_layout(self) -> None:
        container = ttk.Frame(self.root, style="Root.TFrame", padding=24)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(2, weight=1)

        header = ttk.Frame(container, style="Root.TFrame")
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text="OQD Daily Marker Price", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, text="Track Gulf Mercantile Exchange daily oil prices with local history and trend chart.", style="Subtitle.TLabel").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.fetch_button = ttk.Button(header, text="抓取最新油價", style="Accent.TButton", command=self.fetch_latest)
        self.fetch_button.grid(row=0, column=1, rowspan=2, sticky="e")

        cards = ttk.Frame(container, style="Root.TFrame")
        cards.grid(row=1, column=0, sticky="ew", pady=(24, 18))
        for index in range(3):
            cards.columnconfigure(index, weight=1)

        self._build_card(cards, 0, "日期", self.date_var)
        self._build_card(cards, 1, "價格", self.price_var)
        self._build_card(cards, 2, "漲跌", self.change_var)

        content = ttk.Frame(container, style="Root.TFrame")
        content.grid(row=2, column=0, sticky="nsew")
        content.columnconfigure(0, weight=3)
        content.columnconfigure(1, weight=2)
        content.rowconfigure(0, weight=1)

        chart_panel = ttk.Frame(content, style="ChartPanel.TFrame", padding=18)
        chart_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        chart_panel.columnconfigure(0, weight=1)
        chart_panel.rowconfigure(1, weight=1)

        ttk.Label(chart_panel, text="最近 30 筆價格走勢", style="ChartTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(chart_panel, textvariable=self.chart_hint_var, style="Hint.TLabel").grid(row=0, column=1, sticky="e")

        self.chart_canvas = tk.Canvas(chart_panel, bg="#fffaf2", highlightthickness=0)
        self.chart_canvas.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(14, 0))
        self.chart_canvas.bind("<Configure>", lambda _event: self.draw_chart())

        table_panel = ttk.Frame(content, style="Panel.TFrame", padding=18)
        table_panel.grid(row=0, column=1, sticky="nsew")
        table_panel.columnconfigure(0, weight=1)
        table_panel.rowconfigure(1, weight=1)

        ttk.Label(table_panel, text="最近紀錄", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w")
        self.tree = ttk.Treeview(table_panel, columns=("date", "price"), show="headings", height=14)
        self.tree.heading("date", text="Date")
        self.tree.heading("price", text="Price")
        self.tree.column("date", width=130, anchor="center")
        self.tree.column("price", width=100, anchor="e")
        self.tree.grid(row=1, column=0, sticky="nsew", pady=(12, 0))

        scrollbar = ttk.Scrollbar(table_panel, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=1, column=1, sticky="ns", pady=(12, 0))
        self.tree.configure(yscrollcommand=scrollbar.set)

        footer = ttk.Frame(container, style="Root.TFrame")
        footer.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        footer.columnconfigure(0, weight=1)
        ttk.Label(footer, textvariable=self.status_var, style="Status.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(footer, textvariable=self.source_var, style="Status.TLabel").grid(row=1, column=0, sticky="w", pady=(4, 0))

    def _build_card(self, parent: ttk.Frame, column: int, title: str, variable: tk.StringVar) -> None:
        card = ttk.Frame(parent, style="Card.TFrame", padding=18)
        card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 10, 0))
        ttk.Label(card, text=title, style="CardLabel.TLabel").pack(anchor="w")
        ttk.Label(card, textvariable=variable, style="CardValue.TLabel").pack(anchor="w", pady=(14, 0))

    def fetch_latest(self) -> None:
        self.fetch_button.state(["disabled"])
        self.status_var.set("Fetching latest price from gulfmerc.com...")
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
        self.status_var.set(f"{state_text} Database: {self.db_path}")
        self.source_var.set(result.record.source_url)
        self.refresh_history()
        self.fetch_button.state(["!disabled"])

    def _show_error(self, message: str) -> None:
        self.status_var.set(f"Fetch failed: {message}")
        self.fetch_button.state(["!disabled"])

    def refresh_history(self) -> None:
        recent_records = self.repository.list_recent(limit=30)

        for item in self.tree.get_children():
            self.tree.delete(item)

        for record in recent_records:
            self.tree.insert("", "end", values=(record.price_date.isoformat(), f"{record.price:.2f}"))

        if recent_records:
            latest = recent_records[0]
            previous = recent_records[1] if len(recent_records) > 1 else None
            self.date_var.set(latest.price_date.isoformat())
            self.price_var.set(f"{latest.price:.2f}")
            self.change_var.set("N/A" if previous is None else f"{latest.price - previous.price:+.2f}")
            self.source_var.set(latest.source_url)

        self._chart_records = list(reversed(recent_records))
        self.draw_chart()

    def draw_chart(self) -> None:
        canvas = self.chart_canvas
        canvas.delete("all")

        width = max(canvas.winfo_width(), 300)
        height = max(canvas.winfo_height(), 240)
        canvas.create_rectangle(0, 0, width, height, fill="#fffaf2", outline="")

        records = getattr(self, "_chart_records", [])
        if len(records) == 0:
            canvas.create_text(width / 2, height / 2, text="尚無資料可繪圖", fill="#8a7b68", font=("Segoe UI", 14, "bold"))
            return

        if len(records) == 1:
            record = records[0]
            canvas.create_text(width / 2, height / 2 - 12, text=f"{record.price_date.isoformat()}", fill="#6f6355", font=("Segoe UI", 11))
            canvas.create_text(width / 2, height / 2 + 18, text=f"{record.price:.2f}", fill="#16302b", font=("Georgia", 24, "bold"))
            self.chart_hint_var.set("Only one record")
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

        grid_color = "#e7dccb"
        axis_color = "#9f8f7a"
        line_color = "#b86a2c"
        fill_color = "#d89a5b"
        text_color = "#5c4f40"

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
        canvas.create_polygon(area_points, fill="#f3d7b6", outline="")
        canvas.create_line(*points, fill=line_color, width=3, smooth=True)

        for index, record in enumerate(records):
            x = x_for(index)
            y = y_for(record.price)
            radius = 4 if index != len(records) - 1 else 5
            canvas.create_oval(x - radius, y - radius, x + radius, y + radius, fill=fill_color, outline="#fffaf2", width=2)

        label_indexes = sorted(set([0, len(records) // 2, len(records) - 1]))
        for index in label_indexes:
            x = x_for(index)
            canvas.create_text(x, height - padding_bottom + 18, text=records[index].price_date.strftime("%m-%d"), fill=text_color, font=("Segoe UI", 9))

        last_record = records[-1]
        last_x = x_for(len(records) - 1)
        last_y = y_for(last_record.price)
        canvas.create_text(last_x - 8, last_y - 16, text=f"{last_record.price:.2f}", fill="#16302b", font=("Segoe UI", 10, "bold"), anchor="e")

        delta = records[-1].price - records[0].price
        self.chart_hint_var.set(f"Range {records[0].price_date.isoformat()} to {records[-1].price_date.isoformat()} | {delta:+.2f}")


def main() -> None:
    root = tk.Tk()
    app = OilTrackerApp(root, Path("data/oil_prices.db"))
    root.after(150, app.fetch_latest)
    root.mainloop()


if __name__ == "__main__":
    main()
