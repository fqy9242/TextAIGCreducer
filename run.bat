@echo off
setlocal EnableExtensions

cd /d "%~dp0"
set "ROOT=%cd%"

set "FORCE_INSTALL=0"
set "NO_START=0"
set "SKIP_MIGRATE=0"

:parse_args
if "%~1"=="" goto args_done
if /I "%~1"=="--install" (
    set "FORCE_INSTALL=1"
    shift
    goto parse_args
)
if /I "%~1"=="--no-start" (
    set "NO_START=1"
    shift
    goto parse_args
)
if /I "%~1"=="--skip-migrate" (
    set "SKIP_MIGRATE=1"
    shift
    goto parse_args
)
if /I "%~1"=="--help" goto usage
echo Unknown argument: %~1
goto usage

:args_done
call :require_cmd python || goto error
call :require_cmd npm || goto error

echo [1/6] Checking env files...
call :ensure_env_files || goto error

echo [2/6] Checking external De-AI skill repo...
call :ensure_external_repo || goto error

echo [3/6] Checking backend dependencies...
call :ensure_backend_deps || goto error

echo [4/6] Checking frontend dependencies...
call :ensure_frontend_deps || goto error

if "%SKIP_MIGRATE%"=="0" (
    echo [5/6] Running database migrations...
    call :run_migrate || goto error
) else (
    echo [5/6] Migration skipped.
)

if "%NO_START%"=="1" (
    echo [6/6] Start skipped by --no-start.
    goto done
)

echo [6/6] Starting backend and frontend...
call :start_services || goto error

:done
echo.
echo Done.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5173
exit /b 0

:usage
echo.
echo Usage: run.bat [--install] [--no-start] [--skip-migrate]
echo   --install      Force reinstall backend and frontend dependencies.
echo   --no-start     Run checks and migration only, do not start services.
echo   --skip-migrate Skip migration step.
echo.
exit /b 1

:require_cmd
where %~1 >nul 2>nul
if errorlevel 1 (
    echo Missing command: %~1
    exit /b 1
)
exit /b 0

:ensure_env_files
if not exist "backend\.env" (
    if exist "backend\.env.example" (
        copy /Y "backend\.env.example" "backend\.env" >nul
        echo Created backend\.env from template.
    ) else (
        echo Missing backend\.env.example
        exit /b 1
    )
)
if not exist "frontend\.env" (
    if exist "frontend\.env.example" (
        copy /Y "frontend\.env.example" "frontend\.env" >nul
        echo Created frontend\.env from template.
    ) else (
        echo Missing frontend\.env.example
        exit /b 1
    )
)
exit /b 0

:ensure_external_repo
set "EXT_DIR=backend\skills"
if exist "%EXT_DIR%\de-AI-writing\SKILL.md" (
    echo External skill repo already available in %EXT_DIR%.
    exit /b 0
)

echo External skill repo not found. Please ensure backend/skills contains the de-AI-writing rules.
exit /b 0

:ensure_backend_deps
pushd "backend" || exit /b 1
if "%FORCE_INSTALL%"=="1" (
    echo Installing backend dependencies...
    python -m pip install -r requirements.txt
    set "RET=%ERRORLEVEL%"
) else (
    python -c "import fastapi,sqlalchemy,alembic,langchain,langgraph,httpx" >nul 2>nul
    if errorlevel 1 (
        echo Installing backend dependencies...
        python -m pip install -r requirements.txt
    ) else (
        echo Backend dependencies already available.
    )
    set "RET=%ERRORLEVEL%"
)
popd
if not "%RET%"=="0" exit /b 1
exit /b 0

:ensure_frontend_deps
pushd "frontend" || exit /b 1
if "%FORCE_INSTALL%"=="1" (
    echo Installing frontend dependencies...
    call npm install
    set "RET=%ERRORLEVEL%"
) else (
    if not exist "node_modules" (
        echo Installing frontend dependencies...
        call npm install
    ) else (
        echo Frontend dependencies already available.
    )
    set "RET=%ERRORLEVEL%"
)
popd
if not "%RET%"=="0" exit /b 1
exit /b 0

:run_migrate
pushd "backend" || exit /b 1
set "PYTHONPATH=%cd%"
python -m alembic upgrade head
set "RET=%ERRORLEVEL%"
popd
if not "%RET%"=="0" exit /b 1
exit /b 0

:start_services
start "Text AIGC Reducer - Backend" powershell -NoExit -NoProfile -Command "Set-Location '%ROOT%\\backend'; $env:PYTHONPATH=(Get-Location).Path; python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
if errorlevel 1 exit /b 1
start "Text AIGC Reducer - Frontend" powershell -NoExit -NoProfile -Command "Set-Location '%ROOT%\\frontend'; npm run dev -- --host 0.0.0.0 --port 5173"
if errorlevel 1 exit /b 1
exit /b 0

:error
echo.
echo Failed. Fix the errors above and rerun.
exit /b 1
