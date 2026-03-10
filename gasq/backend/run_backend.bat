cd gasq\backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
pause