#

## Compile jr3 DLL

On Windows, navigate to the jr3 subfolder from the command line and compile with g++

```g++ -O -ansi -shared .\jr3_dll.cpp -o jr3.dll```

or with warnings:

```g++ -Wall -Wextra -O -ansi -pedantic -shared .\jr3_dll.cpp -o jr3.dll```