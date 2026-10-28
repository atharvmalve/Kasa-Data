# Run Kasa locally
Write-Host "Checking YugabyteDB container..." -ForegroundColor Cyan
docker compose up -d

Write-Host "Running database migrations..." -ForegroundColor Cyan
& ".\backend\.venv\Scripts\alembic.exe" -c ".\backend\alembic.ini" upgrade head

Write-Host "Starting Backend on http://127.0.0.1:8000..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; .\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000 --reload"

Write-Host "Starting Frontend on http://localhost:3000..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev"

Write-Host "Kasa services launched!" -ForegroundColor Green
Write-Host "Frontend: http://localhost:3000"
Write-Host "Backend API: http://127.0.0.1:8000/docs"

