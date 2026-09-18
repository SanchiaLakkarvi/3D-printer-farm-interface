# Build a native Windows CLI from Linux/WSL without modifying the host PATH.
set(CMAKE_SYSTEM_NAME Windows)
set(CMAKE_C_COMPILER x86_64-w64-mingw32-gcc)
set(CMAKE_CXX_COMPILER x86_64-w64-mingw32-g++)
set(CMAKE_RC_COMPILER x86_64-w64-mingw32-windres)
# Keep the converter self-contained (no MinGW runtime DLL installation).
set(CMAKE_EXE_LINKER_FLAGS_INIT "-static")
