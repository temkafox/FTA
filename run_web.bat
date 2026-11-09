@echo off
rem ActPilot web — статический интерфейс: маршрут кампании + дерево пассивов.
cd /d "%~dp0"
echo.
echo   ActPilot web  ^|  http://127.0.0.1:8765
echo   С телефона в той же Wi-Fi: http://^<IP этого компа^>:8765
ipconfig | findstr /i "IPv4"
echo.
echo   Закрыть окно — остановить сервер.
echo.
start "" cmd /c "timeout /t 1 >nul & start http://127.0.0.1:8765"
py -3 -m http.server 8765 -d web
