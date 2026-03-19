# Python Oil Tracker

這個專案會從 [Gulf Mercantile Exchange](https://www.gulfmerc.com/) 首頁抓取 `OQD Daily Marker Price`，並把每天的油價存進 SQLite，方便長期追蹤漲跌。

## 功能

- 抓取 `OQD Daily Marker Price`
- 解析網站顯示的價格日期
- 每日資料寫入 `SQLite`
- 輸出相較前一次紀錄的漲跌
- 提供本地圖形化介面顯示最新價格、歷史紀錄與價格走勢圖
- 同一天重複執行時不重複寫入
- 自動排程可在背景靜默執行，不跳出終端機

## 安裝

macOS / Linux：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Windows：

```powershell
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

在 `src/oil_tracker` 目錄也可直接執行：

```bash
python gui.py
```

macOS 若想直接雙擊啟動，也可先給執行權限：

```bash
chmod +x run-oil-gui.command run-oil-tracker.command
```

之後可直接雙擊：

- `run-oil-gui.command`：開啟圖形介面
- `run-oil-tracker.command`：執行一次命令列抓取

若要在終端執行，也可以：

```bash
./run-oil-gui.command
./run-oil-tracker.command
```

如果 macOS 執行 GUI 時看到 `tkinter` 相關錯誤，代表目前的 Python 沒有包含 Tk。這種情況下：

- 命令列模式 `oil-tracker` 仍可正常使用
- GUI 需改用有 Tk 支援的 Python 發行版後再執行

## Windows 自動抓取

目前已設定為：

- 每天下午 `13:00` 由 Windows 工作排程自動抓取一次
- 每次登入 Windows 時再執行一次補抓
- 兩者都透過隱藏背景程序執行，不會跳出終端機視窗

這樣如果電腦在當天 `13:00` 之後才第一次開機並登入，登入後也會自動補抓。因為程式會依日期去重，所以同一天即使執行多次，也不會重複寫入。

背景執行相關檔案：

- `D:\codes\codexs\pythonoil\run_oil_tracker_silent.pyw`
- `D:\codes\codexs\pythonoil\run-oil-tracker-hidden.ps1`
- `D:\codes\codexs\pythonoil\run-oil-tracker.cmd`
- `C:\Users\chbon\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\PythonOilDailyTracker-Logon.lnk`

背景執行紀錄會寫到：

- `D:\codes\codexs\pythonoil\data\oil_tracker.log`

## macOS 自動抓取

如果是在 macOS 使用，建議不要使用這些 Windows 專用腳本：

- `run-oil-tracker-hidden.ps1`
- `run-oil-tracker.cmd`
- `run-oil-gui.bat`
- `setup-scheduled-task.ps1`

macOS 可直接使用：

```bash
python run_oil_tracker_silent.pyw
```

或改成：

```bash
python -m oil_tracker.cli
```

若之後需要，我也可以再幫你補一份 `launchd` 用的 macOS 排程設定。

## 測試

```bash
python -m unittest discover -s tests
```
