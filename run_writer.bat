@echo off
chcp 65001 > nul
cd /d "%~dp0"
python web_app.py
if errorlevel 1 (
    echo.
    echo [오류] 실행 중 문제가 발생했습니다. Python 설치 및 requirements.txt 설치 여부를 확인해 주세요.
    echo        pip install -r requirements.txt
    pause
)
