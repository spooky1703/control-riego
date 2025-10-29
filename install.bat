@echo off
title Instalador - Sistema de Control de Riegos Agrícolas
color 0A

echo ========================================
echo     SISTEMA DE CONTROL DE RIEGOS
echo        Instalador para Windows
echo ========================================
echo.

REM --- 1. Verificar Python ---
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no está instalado o no está en el PATH.
    echo.
    echo Por favor, instala Python desde:
    echo https://www.python.org/downloads/
    echo.
    echo Asegúrate de marcar la opción:
    echo "Add Python to PATH" durante la instalación.
    echo.
    pause
    exit /b 1
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [OK] Python detectado (v%PYVER%)
echo.

REM --- 2. Crear carpetas principales ---
echo [1/4] Verificando estructura de carpetas...
for %%d in (modules database\backups database\recibos database\reportes assets) do (
    if not exist "%%d" (
        mkdir "%%d"
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
