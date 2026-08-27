@echo off
setlocal
if not exist build mkdir build
g++ -O2 -std=c++17 -Wall -Wextra -c src\bloom.cpp -o build\bloom.o || (echo ERR: compile bloom failed & exit /b 1)
g++ -O2 -std=c++17 -Wall -Wextra -c src\hashmap.cpp -o build\hashmap.o || (echo ERR: compile hashmap failed & exit /b 1)
g++ -O2 -std=c++17 -Wall -Wextra -c src\pipeline.cpp -o build\pipeline.o || (echo ERR: compile pipeline failed & exit /b 1)
g++ -O2 -std=c++17 -Wall -Wextra -c src\main.cpp -o build\main.o || (echo ERR: compile main failed & exit /b 1)
g++ -static build\bloom.o build\hashmap.o build\pipeline.o build\main.o -o build\pulse.exe || (echo ERR: link failed & exit /b 1)
echo build complete; binary: build\pulse.exe
exit /b 0