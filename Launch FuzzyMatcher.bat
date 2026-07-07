@echo off
REM FuzzyMatcher launcher for Windows
REM Double-click this file to start the application.

cd /d "%~dp0"
call .venv\Scripts\activate.bat
pythonw main.py
