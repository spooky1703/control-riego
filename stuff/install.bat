@echo off
setlocal enabledelayedexpansion

echo ================================================
echo Instalador del Sistema de Control de Riegos
echo ================================================

REM Verificar si Python está instalado
echo.
echo 1. Verificando si Python 3.12.6 está instalado...
python --version >nul 2>&1
if errorlevel 1 (
    echo Python no encontrado. Descargando e instalando Python 3.12.6...
    REM Descargar Python 3.12.6 (ejecutable de Windows)
    REM Asegúrate de que la URL apunte a la versión correcta y compatible (x86 o x64)
    REM Por ejemplo, para Windows x64: https://www.python.org/ftp/python/3.12.6/python-3.12.6-amd64.exe
    powershell -command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.6/python-3.12.6-amd64.exe' -OutFile 'python_installer.exe'"
    if exist python_installer.exe (
        echo Instalando Python 3.12.6...
        python_installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
        del python_installer.exe
        REM Actualizar PATH para la sesión actual (opcional, puede no funcionar en todos los casos)
        REM call refreshenv.bat 2>nul
        echo Python 3.12.6 instalado exitosamente.
    ) else (
        echo Error: No se pudo descargar el instalador de Python.
        echo Por favor, instale Python manualmente desde https://www.python.org/downloads/
        pause
        exit /b 1
    )
) else (
    echo Python encontrado.
    python --version
)

REM Verificar si pip está disponible
echo.
echo 2. Verificando pip...
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo pip no encontrado. Intentando instalarlo...
    python -m ensurepip --upgrade
    if errorlevel 1 (
        echo Error: No se pudo instalar pip.
        pause
        exit /b 1
    )
    echo pip instalado exitosamente.
) else (
    echo pip encontrado.
)

REM Instalar dependencias
echo.
echo 3. Instalando dependencias desde requirements.txt...
if exist requirements.txt (
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Error: No se pudieron instalar las dependencias.
        pause
        exit /b 1
    )
    echo Dependencias instaladas exitosamente.
) else (
    echo Advertencia: No se encontró el archivo 'requirements.txt'. Asegúrese de tenerlo en el directorio.
    REM Si no hay requirements.txt, puedes instalar las dependencias manualmente aquí
    REM python -m pip install pandas reportlab openpyxl
    REM echo Dependencias instaladas manualmente.
)

REM Crear carpetas necesarias
echo.
echo 4. Creando carpetas necesarias...
mkdir database 2>nul
mkdir database\backups 2>nul
mkdir database\recibos 2>nul
mkdir database\reportes 2>nul
mkdir assets 2>nul
echo Carpetas creadas.

REM Crear run_app.bat
echo.
echo 5. Creando lanzador de la aplicacion (run_app.bat)...
(
echo @echo off
echo.
echo echo Iniciando el Sistema de Control de Riegos...
echo echo.
echo python main.py
echo.
echo pause
) > run_app.bat
echo Lanzador 'run_app.bat' creado exitosamente.

REM Mensaje final
echo.
echo ================================================
echo Instalacion completada exitosamente!
echo ================================================
echo.
echo Para ejecutar el sistema en el futuro, use: run_app.bat
echo Asegúrese de tener el archivo XICUCO.csv en la carpeta raíz si es necesario.
echo ================================================
pause