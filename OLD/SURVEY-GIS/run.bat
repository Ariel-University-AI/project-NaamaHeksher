@echo off
chcp 65001 > nul
title SurveyGIS - מערכת המרת קבצים

echo.
echo  ============================================================
echo   SurveyGIS - מפעיל את המערכת...
echo   פרויקט גמר | גיאודזיה ומיפוי | אוניברסיטת אריאל
echo  ============================================================
echo.

:: בדיקה שההתקנה בוצעה
if not exist "venv\Scripts\activate.bat" (
    echo  [!] המערכת לא הותקנה עדיין.
    echo.
    echo      הפעל תחילה את:  setup.bat
    echo.
    pause
    exit /b 1
)

if not exist "SURVEYGIS\server.py" (
    echo  [!] קבצי המערכת לא נמצאו.
    echo      וודא שאתה מפעיל את run.bat מתיקיית הפרויקט.
    echo.
    pause
    exit /b 1
)

:: הפעלה
call venv\Scripts\activate.bat

echo  המערכת עולה...
echo  הדפדפן יפתח אוטומטית בכתובת: http://localhost:7654
echo.
echo  לעצירת המערכת: לחץ Ctrl+C בחלון זה
echo  (אל תסגור את החלון בזמן השימוש במערכת)
echo.
echo  ============================================================
echo.

python SURVEYGIS\server.py

echo.
echo  המערכת נעצרה.
pause
