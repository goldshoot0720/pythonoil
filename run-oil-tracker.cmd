@echo off
cd /d D:\codes\codexs\pythonoil
set PYTHONPATH=src
python -m oil_tracker.cli --db data\oil_prices.db
