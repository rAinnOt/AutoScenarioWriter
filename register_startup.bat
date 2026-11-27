@echo off
chcp 65001 > nul
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "TARGET_BAT=%~dp0run_writer_bg.bat"

(
  echo @echo off
  echo cd /d "%~dp0"
  echo start "" /min pythonw web_app.py --no-open
) > "%TARGET_BAT%"

copy /Y "%TARGET_BAT%" "%STARTUP_DIR%\AutoScenarioWriter.bat" > nul
echo [완료] Windows 부팅 시 AutoScenarioWriter가 백그라운드로 자동 시작되도록 등록했습니다.
echo 해제하려면 "%STARTUP_DIR%\AutoScenarioWriter.bat" 파일을 삭제하세요.
pause
