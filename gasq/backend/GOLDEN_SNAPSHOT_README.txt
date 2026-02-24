@"
GASQ — GOLDEN SNAPSHOT
Дата: 2026-02-08
ZIP: gasq_golden_snapshot_20260208_0758.zip

Быстрый запуск после распаковки:
1) docker compose up -d
2) backend:
   cd backend
   python -m venv .venv
   .\.venv\Scripts\activate.ps1
   pip install -r requirements.txt
   alembic upgrade head
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
3) frontend:
   cd ..\frontend
   python serve_frontend.py

URL:
- Backend health: http://localhost:8000/health
- Swagger:        http://localhost:8000/docs
- Terminal:       http://localhost:5500/terminal/index.html
- Admin:          http://localhost:5500/admin/index.html
- Reports:        http://localhost:5500/admin/reports.html
- Driver:         http://localhost:5500/driver/index.html
"@ | Set-Content -Encoding UTF8 .\backups\GOLDEN_SNAPSHOT_README.txt
