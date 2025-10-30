@echo off
title Instalador - Sistema de Control de Riegos Agrícolas
color 0A

echo ========================================
echo     SISTEMA DE CONTROL DE RIEGOS
echo        Instalador para Windows
echo ========================================
echo.

REM --- 1. Verificar si ya hay Python 3.12.6 ---
set TARGET_VERSION=3.12.6
set PYTHON_OK=0

python --version >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=2" %%v in ('python --version 2^>^&1') do (
        if "%%v" == "%TARGET_VERSION%" (
            set PYTHON_OK=1
        )
    )
)

if %PYTHON_OK% == 1 (
    echo [OK] Python %TARGET_VERSION% ya está instalado.
) else (
    echo [INFO] Python %TARGET_VERSION% no detectado. Instalando...
    echo.

    REM Descargar e instalar Python 3.12.6 x86-64
    set URL=https://www.python.org/ftp/python/3.12.6/python-3.12.6-amd64.exe
    set INSTALLER=python-3.12.6-amd64.exe

    echo Descargando Python %TARGET_VERSION% (x86-64)...
    powershell -Command "Invoke-WebRequest -Uri '%URL%' -OutFile '%INSTALLER%'"
    if errorlevel 1 (
        echo [ERROR] Falló la descarga de Python.
        echo Por favor, descarga manualmente desde:
        echo %URL%
        pause
        exit /b 1
    )

    echo Instalando Python %TARGET_VERSION%...
    echo (Agregando al PATH y asociando archivos .py)
    start /wait "" "%INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 SimpleInstall=1

    if errorlevel 1 (
        echo [ERROR] Falló la instalación de Python.
        del "%INSTALLER%"
        pause
        exit /b 1
    )

    del "%INSTALLER%"
    echo [OK] Python %TARGET_VERSION% instalado correctamente.
    echo.

    REM Refrescar el PATH en la sesión actual
    call refreshenv.bat >nul 2>&1
    where python >nul 2>&1
    if errorlevel 1 (
        echo [ADVERTENCIA] Python instalado, pero no disponible en PATH en esta sesión.
        echo Reinicia la terminal o ejecuta manualmente: 'python main.py'
        echo.
        pause
        exit /b 1
    )
)

REM --- 2. Crear carpetas principales ---
echo [1/4] Verificando estructura de carpetas...
for %%d in (modules database\backups database\recibos database\reportes assets) do (
    if not exist "%%d" (
        mkdir "%%d" >nul
        echo   Carpeta creada: %%d
    )
)
echo [OK] Estructura de carpetas lista.
echo.

REM --- 3. Verificar archivos requeridos ---
echo [2/4] Verificando archivos requeridos...
if not exist "main.py" (
    echo [ERROR] Falta el archivo principal: main.py
    pause
    exit /b 1
)
if not exist "requirements.txt" (
    echo [ERROR] Falta el archivo: requirements.txt
    pause
    exit /b 1
)
echo [OK] Archivos principales encontrados.
echo.

REM --- 4. Instalar dependencias ---
echo [3/4] Instalando dependencias de Python...
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERROR] Falló la instalación de dependencias.
    echo Ejecuta manualmente:
    echo     python -m pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)
echo [OK] Dependencias instaladas correctamente.
echo.

REM --- 5. Archivo opcional de datos ---
echo [4/4] Verificando archivo de datos iniciales...
if exist "XICUCO.csv" (
    echo [OK] Archivo XICUCO.csv encontrado.
) else (
    echo [ADVERTENCIA] No se encontró XICUCO.csv
    echo El sistema se iniciará sin datos precargados.
    echo Puedes agregar campesinos manualmente desde la interfaz.
)
echo.

REM --- 6. Crear archivo iniciar.bat ---
(
    echo @echo off
    echo title Sistema de Control de Riegos Agricolas
    echo python main.py
    echo pause
) > iniciar.bat

echo [OK] Archivo iniciar.bat creado.
echo.

echo ========================================
echo    INSTALACIÓN COMPLETADA EXITOSAMENTE
echo ========================================
echo.
echo Para iniciar el sistema, puedes:
echo   1. Escribir: python main.py
echo   2. O hacer doble clic en: iniciar.bat
echo.
pause
exit /b 0