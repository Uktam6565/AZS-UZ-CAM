Write-Host ""
Write-Host "Starting GasQ Backend..."
Write-Host ""

cd $PSScriptRoot

Write-Host "Installing dependencies..."
pip install -r requirements.txt

Write-Host ""
Write-Host "Starting FastAPI server..."
Write-Host ""

python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000