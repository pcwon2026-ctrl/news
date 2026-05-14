@echo off

cd /d "C:\Users\intty\한국정치경제신문"

echo ===============================================
echo   GitHub Pages Upload
echo ===============================================
echo.

git add .
git commit -m "Daily update"
git push

echo.
echo ===============================================
echo   Upload complete!
echo   URL: https://pcwon2026-ctrl.github.io/news/
echo ===============================================
echo.
pause
