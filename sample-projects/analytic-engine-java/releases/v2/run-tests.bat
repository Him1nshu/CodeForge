@echo off
setlocal
if not exist build\classes mkdir build\classes
if exist build\test-sources.txt del build\test-sources.txt
for /f %%f in ('dir /s /b src\test\java\*.java') do echo %%f>> build\test-sources.txt
javac -cp build\classes;..\..\tools\junit\junit-platform-console-standalone-1.11.4.jar -d build\classes @build\test-sources.txt || (echo ERR: test compile failed & exit /b 1)
for /f %%v in (version.txt) do set VER=%%v
java -Davlog.version=%VER% -jar ..\..\tools\junit\junit-platform-console-standalone-1.11.4.jar --class-path build\classes --scan-class-path --reports-dir build\test-results
set RC=%ERRORLEVEL%
exit /b %RC%