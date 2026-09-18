@echo off
if not exist newongs.db (
  echo newongs.db nao encontrado.
  pause
  exit /b 1
)
for /f "tokens=1-4 delims=/ " %%a in ('date /t') do set DATA=%%a-%%b-%%c-%%d
copy /Y newongs.db newongs-backup.db >nul
 echo Backup criado: newongs-backup.db
pause
