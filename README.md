# Python Oil Tracker

這個專案會從 [Gulf Mercantile Exchange](https://www.gulfmerc.com/) 首頁抓取 `OQD Daily Marker Price`，並把每天的油價存進 SQLite，方便長期追蹤漲跌。

## 功能

- 抓取 `OQD Daily Marker Price`
- 解析網站顯示的價格日期
- 每日資料寫入 `SQLite`
- 輸出相較前一次紀錄的漲跌
- 提供本地圖形化介面顯示最新價格、歷史紀錄與價格走勢圖
- 同一天重複執行時不重複寫入

## 安裝

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

不需要額外第三方套件，安裝後即可執行。

## 執行

命令列模式：

```bash
oil-tracker
```

或直接用 Python：

```bash
python -m oil_tracker.cli
```

圖形化介面：

```bash
oil-tracker-gui
```

或：

```bash
python -m oil_tracker.gui
```

在 `src\oil_tracker` 目錄也可直接執行：

```bash
python gui.py
```

指定資料庫位置：

```bash
python -m oil_tracker.cli --db data\oil_prices.db
```

## Windows 自動抓取

目前已設定為：

- 每天下午 `13:00` 由 Windows 工作排程自動抓取一次
- 每次登入 Windows 時再執行一次補抓

這樣如果電腦在當天 `13:00` 之後才第一次開機並登入，登入後也會自動補抓。因為程式會依日期去重，所以同一天即使執行多次，也不會重複寫入。

相關檔案：

- `D:\codes\codexs\pythonoil\run-oil-tracker.cmd`
- `C:\Users\chbon\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\PythonOilDailyTracker-Logon.cmd`
- `D:\codes\codexs\pythonoil\setup-scheduled-task.ps1`

## 測試

```bash
python -m unittest discover -s tests
```
