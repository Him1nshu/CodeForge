@echo off
setlocal EnableExtensions

set "ROOT=%~dp0"
set "VENV=%ROOT%.venv"
set "PYTHON=%VENV%\Scripts\python.exe"

echo.
echo ========================================
echo   CODEFORGE local setup
echo ========================================
echo.

where py >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python Launcher ^(py^) was not found.
    echo Install Python 3.11 or newer and run this file again.
    exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
    echo ERROR: npm was not found.
    echo Install Node.js 18 or newer and run this file again.
    exit /b 1
)

if not exist "%PYTHON%" (
    echo [1/6] Creating Python virtual environment...
    py -3 -m venv "%VENV%"
    if errorlevel 1 goto :error
) else (
    echo [1/6] Using existing Python virtual environment.
)

echo [2/6] Installing backend and collector dependencies...
"%PYTHON%" -m pip install --upgrade pip
if errorlevel 1 goto :error
"%PYTHON%" -m pip install -r "%ROOT%backend\requirements.txt"
if errorlevel 1 goto :error
"%PYTHON%" -m pip install --editable "%ROOT%collector"
if errorlevel 1 goto :error

echo [3/6] Installing frontend dependencies...
pushd "%ROOT%frontend"
call npm install
if errorlevel 1 (
    popd
    goto :error
)
popd

echo [4/6] Applying database migrations using SQLite...
set "CODEFORGE_DATABASE_URL=sqlite:///./codeforge.db"
pushd "%ROOT%backend"
"%PYTHON%" -m alembic upgrade head
if errorlevel 1 (
    popd
    goto :error
)
popd

echo [5/6] Starting the backend API...
start "CODEFORGE API" /D "%ROOT%backend" cmd /k ""%PYTHON%" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

echo [6/6] Starting the frontend dashboard...
start "CODEFORGE Frontend" /D "%ROOT%frontend" cmd /k "npm run dev -- --host 127.0.0.1"

echo.
echo Setup complete.
echo API:      http://localhost:8000/docs
echo Dashboard: http://127.0.0.1:5173
echo.
exit /b 0

:error
echo.
echo ERROR: Setup failed. Review the command output above.
exit /b 1