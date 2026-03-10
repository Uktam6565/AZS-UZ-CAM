@echo off
title GasQ Backend
cd /d C:\Users\matku\Desktop\AZS-UZ-CAM\gasq\backend
python -m uvicorn app.main:app --reload
pause