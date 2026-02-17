@echo off
echo === Visual Regression Scanner - Build ===
cd /d "%~dp0"

if not exist ".venv" (
    echo Bitte zuerst setup-dev-environment.bat ausfuehren!
    pause
    exit /b 1
)

echo.
echo [1/3] Installiere PyInstaller...
.venv\Scripts\pip.exe install pyinstaller

echo [2/3] Erstelle Executable...
.venv\Scripts\pyinstaller.exe ^
    --name visual-regression-scanner ^
    --onedir ^
    --console ^
    --add-data "src\visual_regression_scanner\app.tcss;visual_regression_scanner" ^
    --hidden-import visual_regression_scanner ^
    --hidden-import visual_regression_scanner.app ^
    --hidden-import visual_regression_scanner.models ^
    --hidden-import visual_regression_scanner.models.scan_result ^
    --hidden-import visual_regression_scanner.models.sitemap ^
    --hidden-import visual_regression_scanner.services ^
    --hidden-import visual_regression_scanner.services.baseline ^
    --hidden-import visual_regression_scanner.services.comparator ^
    --hidden-import visual_regression_scanner.services.image_viewer ^
    --hidden-import visual_regression_scanner.services.reporter ^
    --hidden-import visual_regression_scanner.services.screenshotter ^
    --hidden-import visual_regression_scanner.screens ^
    --hidden-import visual_regression_scanner.screens.about ^
    --hidden-import visual_regression_scanner.screens.diff_detail ^
    --hidden-import visual_regression_scanner.screens.reset_confirm ^
    --hidden-import visual_regression_scanner.screens.scan_mode ^
    --hidden-import visual_regression_scanner.widgets ^
    --hidden-import visual_regression_scanner.widgets.diff_detail_view ^
    --hidden-import visual_regression_scanner.widgets.results_table ^
    --hidden-import visual_regression_scanner.widgets.summary_panel ^
    --collect-submodules rich._unicode_data ^
    src\visual_regression_scanner\__main__.py

echo [3/3] Fertig!
echo.
echo Executable in: dist\visual-regression-scanner\
pause
