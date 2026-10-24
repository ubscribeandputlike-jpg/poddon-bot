@echo off
chcp 65001 > nul
echo Установка зависимостей...
py -m pip install -r requirements.txt
echo.
echo Запуск бота...
py bot.py
pause
