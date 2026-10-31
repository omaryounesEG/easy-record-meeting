@echo off
REM ============================================================
REM  Easy Record Meeting — build the portable executable
REM  مسجّل الاجتماعات — بناء النسخة المحمولة
REM ============================================================
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo [1/3] Checking the virtual environment / فحص البيئة
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv || goto :fail
)
call ".venv\Scripts\activate.bat"
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt pyinstaller || goto :fail

echo [2/3] Running the test suite / تشغيل الاختبارات
python -m unittest discover -s tests -t . || goto :tests_failed

echo [3/3] Building OMAR_REC.exe / بناء الملف التنفيذي
python -m PyInstaller --noconfirm --clean ^
    --onefile --windowed ^
    --name "OMAR_REC" ^
    --icon "assets\icon.ico" ^
    --add-data "assets;assets" ^
    --collect-all soundcard ^
    --collect-all lameenc ^
    --hidden-import soundfile ^
    --hidden-import numpy ^
    omar_rec.py || goto :fail

if not exist "ffmpeg.exe" (
    echo [warn] ffmpeg.exe not found next to the build — copy it beside the exe.
)
echo.
echo ============================================================
echo   DONE: dist\OMAR_REC.exe
echo   تم البناء بنجاح: dist\OMAR_REC.exe
echo ============================================================
exit /b 0

:tests_failed
echo.
echo [error] Tests failed - build stopped. / الاختبارات فشلت - تم إيقاف البناء.
exit /b 1

:fail
echo.
echo [error] Build failed. / فشل البناء.
exit /b 1
