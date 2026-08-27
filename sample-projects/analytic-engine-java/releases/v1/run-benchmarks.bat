@echo off
java -cp build\classes avlog.Main --bench
exit /b %ERRORLEVEL%