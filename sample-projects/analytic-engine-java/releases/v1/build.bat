@echo off
setlocal
for /f "tokens=2 delims==" %%h in ('java -XshowSettings:properties -version 2^>^&1 ^| find "java.home"') do set JDK=%%h
if defined JDK set JDK=%JDK:~1%
set "JAR=%JDK%\bin\jar.exe"
if not exist build\classes mkdir build\classes
if exist build\sources.txt del build\sources.txt
for /f %%f in ('dir /s /b src\main\java\*.java') do echo %%f>> build\sources.txt
javac -Xlint:all -d build\classes @build\sources.txt || (echo ERR: compile failed & exit /b 1)
"%JAR%" --create --file build\analytic-engine.jar -C build\classes . || (echo ERR: jar failed & exit /b 1)
echo build complete; jar: build\analytic-engine.jar
exit /b 0