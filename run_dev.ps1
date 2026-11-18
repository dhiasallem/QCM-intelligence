# Script de lancement simultané du Backend (FastAPI) et du Frontend (Next.js)

Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "  Démarrage de QCM Intelligence (Backend + Frontend) " -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

# 1. Lancer le Backend FastAPI dans une nouvelle fenêtre
Write-Host "-> Lancement du Backend FastAPI sur http://localhost:8000 ..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; .\venv\Scripts\activate; Write-Host 'Backend FastAPI démarré sur http://localhost:8000' -ForegroundColor Green; uvicorn app.main:app --reload --port 8000"

# 2. Lancer le Frontend Next.js dans une nouvelle fenêtre
Write-Host "-> Lancement du Frontend Next.js sur http://localhost:3000 ..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; Write-Host 'Frontend Next.js démarré sur http://localhost:3000' -ForegroundColor Green; npm run dev"

Write-Host ""
Write-Host "Deux fenêtres ont été ouvertes :" -ForegroundColor Yellow
Write-Host "  - Backend API : http://localhost:8000 (Swagger docs : http://localhost:8000/docs)" -ForegroundColor Yellow
Write-Host "  - Frontend UI : http://localhost:3000" -ForegroundColor Yellow
Write-Host "=====================================================" -ForegroundColor Cyan
