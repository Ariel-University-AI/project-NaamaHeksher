@echo off
chcp 65001 > nul
title SurveyGIS - התקנה

echo.
echo  ============================================================
echo   SurveyGIS - התקנה אוטומטית
echo   פרויקט גמר | גיאודזיה ומיפוי | אוניברסיטת אריאל
echo  ============================================================
echo.


:: ── שלב 1: בדיקת Python ──────────────────────────────────────
echo  [1/4]  בודק Python...
python --version > nul 2>&1
if errorlevel 1 (
    echo.
    echo  [!] Python לא מותקן, או לא נמצא ב-PATH.
    echo.
    echo      הורד והתקן Python מ:
    echo      https://www.python.org/downloads/
    echo.
    echo      חשוב: בעת ההתקנה סמן את הוספה התיבה
    echo             "Add Python to PATH"
    echo.
    echo      לאחר ההתקנה - הפעל שוב את הקובץ הזה.
    echo.
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo         Python %PY_VER% - נמצא


:: ── שלב 2: יצירת סביבת Python (venv) ────────────────────────
echo.
echo  [2/4]  מכין סביבת Python...
if not exist "venv\" (
    python -m venv venv
    if errorlevel 1 (
        echo.
        echo  [!] לא ניתן ליצור סביבת Python.
        echo      נסה להריץ כמנהל מערכת (Run as Administrator).
        echo.
        pause
        exit /b 1
    )
    echo         סביבת Python נוצרה
) else (
    echo         סביבת Python קיימת - ממשיך
)


:: ── שלב 3: התקנת ספריות ──────────────────────────────────────
echo.
echo  [3/4]  מתקין ספריות Python (אינטרנט נדרש)...
call venv\Scripts\activate.bat
pip install ezdxf==1.3.6 pyshp==2.3.1 pyproj==3.7.1 --quiet --disable-pip-version-check
if errorlevel 1 (
    echo.
    echo  [!] התקנת הספריות נכשלה.
    echo      בדוק שיש חיבור לאינטרנט ונסה שוב.
    echo.
    pause
    exit /b 1
)
echo         ספריות הותקנו בהצלחה


:: ── שלב 4: חיפוש ODA File Converter ─────────────────────────
echo.
echo  [4/4]  מחפש ODA File Converter...
set ODA_FOUND=0

if exist "C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe"        set ODA_FOUND=1
if exist "C:\Program Files (x86)\ODA\ODAFileConverter\ODAFileConverter.exe"  set ODA_FOUND=1

for /d %%d in ("C:\Program Files\ODA\ODAFileConverter*") do (
    if exist "%%d\ODAFileConverter.exe" set ODA_FOUND=1
)
for /d %%d in ("C:\Program Files (x86)\ODA\ODAFileConverter*") do (
    if exist "%%d\ODAFileConverter.exe" set ODA_FOUND=1
)

if "%ODA_FOUND%"=="1" (
    echo         ODA File Converter - נמצא
    goto :done
)

echo.
echo  [!] ODA File Converter לא נמצא במחשב.
echo.
echo      ללא תוכנה זו המערכת לא תוכל לפתוח קבצי DWG.
echo.
echo      הורד והתקן בחינם מ:
echo      https://www.opendesign.com/guestfiles/oda_file_converter
echo.
echo      לאחר ההתקנה - הפעל שוב את setup.bat לאימות.
echo.


:done
echo.
echo  ============================================================
if "%ODA_FOUND%"=="1" (
    echo   ההתקנה הושלמה בהצלחה!
    echo.
    echo   להפעלת המערכת:
    echo   לחץ פעמיים על  run.bat
) else (
    echo   ההתקנה הושלמה - ODA חסר בלבד
    echo.
    echo   התקן ODA ואז הפעל שוב את setup.bat
    echo   לאחר מכן: לחץ פעמיים על run.bat
)
echo  ============================================================
echo.
pause
