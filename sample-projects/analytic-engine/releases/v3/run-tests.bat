@echo off
build\pulse.exe --selftest
exit /b %ERRORLEVEL%

