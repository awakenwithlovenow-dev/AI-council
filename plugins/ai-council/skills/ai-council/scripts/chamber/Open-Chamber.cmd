@echo off
rem Opens the Council hub in its own window. Needs Python 3 for Windows (pythonw, or the py launcher).
where pythonw >nul 2>nul && (start "" pythonw "%~dp0launch.py") || (start "" pyw "%~dp0launch.py")
