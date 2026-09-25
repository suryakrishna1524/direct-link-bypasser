@echo off
title BypassDirect - Direct Link Bypasser Server
echo ========================================================
echo Starting BypassDirect Web Server...
echo Access the site at: http://127.0.0.1:8000
echo API Documentation at: http://127.0.0.1:8000/docs
echo ========================================================
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
pause
