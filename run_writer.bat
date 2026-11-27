@echo off
chcp 65001 > nul
cd /d "%~dp0"
python web_app.py
if errorlevel 1 (
    echo.
    echo [ERROR] AutoScenarioWriter 실행 중 오류가 발생했습니다.
    echo Python 및 패키지 설치 여부를 확인해 주세요: pip install -r requirements.txt
    pause
)
