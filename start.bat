@echo off
title J.A.R.V.I.S. // Smart Plug & Chatbot Controller
color 0b
echo ======================================================================
echo    J.A.R.V.I.S. -- CHATBOT ^& WIRELESS SMART PLUG CONTROLLER
echo ======================================================================
echo.

if not exist .venv (
    echo [*] Creating virtual environment...
    python -m venv .venv
)

echo [*] Activating virtual environment...
call .venv\Scripts\activate.bat

echo [*] Checking dependencies...
pip install -r requirements.txt

echo.
echo [*] Starting J.A.R.V.I.S. Engine...
python run.py

pause
