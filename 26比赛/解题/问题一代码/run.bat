@echo off
chcp 65001 >nul
set "TASK_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if not exist "%TASK_PYTHON%" set "TASK_PYTHON=python"
"%TASK_PYTHON%" -X utf8 "%~dp0run_question1.py" %*
exit /b %errorlevel%
