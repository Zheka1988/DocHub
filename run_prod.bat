@echo off
cd /d C:\Projects\DocHub
call .venv\Scripts\activate.bat
waitress-serve --listen=*:8000 --threads=4 --connection-limit=100 DocHub.wsgi:application
