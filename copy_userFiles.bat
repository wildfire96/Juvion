@echo off
REM ===========================================================================
REM Copy script for Writingway to get all Projects and settings files from a 
REM previous version (Windows)
REM Usage: copy_userFiles.bat source_directory
REM    Copy from within the new Writingway directory, and specify the
REM    path to the old Writingway directory.
REM ==========================================================================

REM Check if the source directory is provided
if "%~1"=="" (
    echo Usage: %0 source_directory
    exit /b 1
)

set "SOURCE_DIR=%~1"

REM Copy specific files and directories to the current directory
echo Copying project_settings.json
copy "%SOURCE_DIR%\project_settings.json" .\
echo Copying projects.json
copy "%SOURCE_DIR%\projects.json" .\
echo Copying settings.json
copy "%SOURCE_DIR%\settings.json" .\
echo Copying prompts.bak.json
copy "%SOURCE_DIR%\prompts.bak.json" .\
echo Copying prompts.json
copy "%SOURCE_DIR%\prompts.json" .\
echo Copying conversations.json
copy "%SOURCE_DIR%\conversations.json" .\
echo Copying Projects directory
xcopy "%SOURCE_DIR%\Projects" "Projects" /E /I /Y
echo Copying assets directory
xcopy "%SOURCE_DIR%\assets" "assets" /E /I /Y

REM Find all project structure files (e.g., MyFirstProject_structure.json)
for %%F in ("%SOURCE_DIR%\*_structure.json") do (
    echo Copying %%~nxF
    copy "%%F" .\
)

echo All user files from "%SOURCE_DIR%" have been copied.
pause