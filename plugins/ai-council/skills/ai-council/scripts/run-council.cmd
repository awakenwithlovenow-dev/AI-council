@echo off
rem Windows Task Scheduler entry point. Edit the two paths for your machine.
"%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe" "%~dp0council.py" --marathon
