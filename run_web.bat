@echo off
rem ActPilot web — статический интерфейс: маршрут кампании + дерево пассивов + план камней.
rem serve.py отдаёт файлы с Cache-Control: no-store, поэтому правки видны сразу после F5.
cd /d "%~dp0"
echo.
echo   ActPilot web  ^|  http://127.0.0.1:8765
echo   С телефона в той же Wi-Fi — адрес печатает serve.py.
echo.
echo   Закрыть окно — остановить сервер.
echo.
start "" cmd /c "timeout /t 1 >nul & start http://127.0.0.1:8765"
py -3 "%~dp0web\serve.py"
