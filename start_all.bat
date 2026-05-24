@echo off
title Punokawan V2 — Autonomous Trading System
color 0A

echo ===============================================================
echo   Punokawan V2 — 4 MCP Server Trading System
echo   XAUUSD Autonomous Scalping
echo ===============================================================
echo.

:: Check if MT5 is running
tasklist /fi "imagename eq terminal64.exe" 2>nul | find /i "terminal64.exe" >nul
if errorlevel 1 (
    echo [WARNING] MetaTrader 5 terminal not detected!
    echo Please start MT5 and login before running trading servers.
    echo.
)

:: Create required directories
if not exist "charts" mkdir charts
if not exist "logs" mkdir logs
if not exist "data" mkdir data

echo [INFO] Starting MCP servers...
echo.

:: Server 1: mcp-market-analysis (Port 8082)
echo [1/4] Starting mcp-market-analysis on port 8082...
start "Market Analysis" cmd /c "cd /d "D:\Punokawan V2\mcp-market-analysis" && set PYTHONPATH=D:\Punokawan V2\mcp-market-analysis\src && python -m market_analysis_server.server --port 8082"
timeout /t 2 /nobreak >nul

:: Server 2: mcp-learning-self (Port 8083)
echo [2/4] Starting mcp-learning-self on port 8083...
start "Learning Self" cmd /c "cd /d "D:\Punokawan V2\mcp-learning-self" && set PYTHONPATH=D:\Punokawan V2\mcp-learning-self\src && python -m learning_server.server --port 8083"
timeout /t 2 /nobreak >nul

:: Server 3: mcp-risk-guardrail (Port 8084)
echo [3/4] Starting mcp-risk-guardrail on port 8084...
start "Risk Guardrail" cmd /c "cd /d "D:\Punokawan V2\mcp-risk-guardrail" && set PYTHONPATH=D:\Punokawan V2\mcp-risk-guardrail\src && python -m risk_guardrail_server.server --port 8084"
timeout /t 2 /nobreak >nul

:: Server 4: mcp-metatrader-ext (Port 8081)
echo [4/4] Starting mcp-metatrader-ext on port 8081...
start "MT5 Extended" cmd /c "cd /d "D:\Punokawan V2\mcp-metatrader-ext" && set PYTHONPATH=D:\Punokawan V2\mcp-metatrader-ext\src && python -m metatrader_mcp_ext.server --port 8081"

echo.
echo ===============================================================
echo   All servers started!
echo.
echo   Port Map:
echo     mcp-market-analysis : 8082
echo     mcp-learning-self   : 8083
echo     mcp-risk-guardrail  : 8084
echo     mcp-metatrader-ext  : 8081
echo.
echo   Also ensure these are running:
echo     metatrader-mcp (existing) : 8080
echo     MT5 Terminal              : local
echo ===============================================================
echo.
echo Press any key to STOP all servers...
pause >nul

echo.
echo [INFO] Stopping all servers...
taskkill /f /fi "WINDOWTITLE eq Market Analysis*" /t 2>nul
taskkill /f /fi "WINDOWTITLE eq Learning Self*" /t 2>nul
taskkill /f /fi "WINDOWTITLE eq Risk Guardrail*" /t 2>nul
taskkill /f /fi "WINDOWTITLE eq MT5 Extended*" /t 2>nul

echo [INFO] All servers stopped.
timeout /t 3 /nobreak >nul
