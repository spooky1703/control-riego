#!/bin/bash
# install.sh - Script de instalación para Linux/macOS
# Sistema de Control de Riegos Agrícolas

echo "========================================"
echo "  SISTEMA DE CONTROL DE RIEGOS"
echo "  Instalador para Linux/macOS"
echo "========================================"
echo ""

# Verificar si Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 no está instalado"
    echo ""
    echo "Para instalar Python:"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-pip python3-tk"
    echo "  macOS: brew install python@3.11"
    exit 1
fi

echo "[OK] Python encontrado"
python3 --version
echo ""

# Verificar archivos necesarios
if [ ! -f "main.py" ]; then
    echo "ERROR: No se encuentra main.py"
    exit 1
fi

if [ ! -f "requirements.txt" ]; then
    echo "ERROR: No se encuentra requirements.txt"
    exit 1
fi

# Crear carpeta modules si no existe
if [ ! -d "modules" ]; then
    echo "Creando carpeta modules..."
    mkdir -p modules
fi

echo "[1/3] Instalando dependencias de Python..."
echo ""
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Falló la instalación de dependencias"
    echo "Intenta ejecutar manualmente: python3 -m pip install -r requirements.txt"
    exit 1
fi

echo ""
echo "[OK] Dependencias instaladas correctamente"
echo ""

# Verificar XICUCO.csv
if [ -f "XICUCO.csv" ]; then
    echo "[2/3] Archivo XICUCO.csv encontrado"
else
    echo "[ADVERTENCIA] No se encuentra XICUCO.csv"
    echo "El sistema se iniciará sin datos precargados"
    echo "Puedes agregar campesinos manualmente desde la interfaz"
fi

echo ""
echo "[3/3] Creando estructura de carpetas..."
mkdir -p database/backups
mkdir -p database/recibos
mkdir -p database/reportes
mkdir -p assets

echo "[OK] Carpetas creadas"
echo ""
echo "========================================"
echo "   INSTALACION COMPLETADA"
echo "========================================"
echo ""