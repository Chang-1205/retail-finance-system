@echo off
color 0A
echo ==================================================
echo      KHOI DONG HE THONG ERP FINANCE 3-TIER
echo ==================================================
echo.

echo [1] Dang don dep cac tien trinh cu bi treo ngam...
taskkill /F /IM python.exe /T >nul 2>&1
taskkill /F /IM uvicorn.exe /T >nul 2>&1
timeout /t 2 /nobreak >nul

echo [2] Dang bat Nha Bep (Backend API)...
start "Backend API (KHONG TAT)" cmd /k "cd backend_fastapi && ..\venv\Scripts\activate && uvicorn main:app --host 127.0.0.1 --port 8000"

echo [3] Doi 3 giay de nha bep nong may...
timeout /t 3 /nobreak >nul

echo [4] Dang bat Mat tien (Frontend Streamlit)...
start "Frontend UI (KHONG TAT)" cmd /k "cd frontend_streamlit && ..\venv\Scripts\activate && streamlit run app.py"

echo.
echo HOAN TAT! He thong dang chay...
echo (Luu y: Thu nho 2 cua so den xuong, KHONG duoc tat)
pause