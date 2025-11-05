# build_app.py - Script para compilar la aplicación
import PyInstaller.__main__
import os
import shutil

# Limpiar builds anteriores
if os.path.exists('dist'):
    shutil.rmtree('dist')
if os.path.exists('build'):
    shutil.rmtree('build')

print("🔨 Compilando aplicación...")

PyInstaller.__main__.run([
    'main.py',                          # Archivo principal
    '--name=SistemaRiego',              # Nombre del ejecutable
    '--onefile',                         # Un solo archivo
    '--windowed',                        # Sin consola (GUI pura)
    '--icon=assets/zapata.png',         # Icono (si existe)
    '--add-data=assets;assets',         # Incluir carpeta assets
    '--hidden-import=win32print',       # Incluir pywin32
    '--hidden-import=win32api',
    '--hidden-import=matplotlib',
    '--hidden-import=openpyxl',
    '--clean',                           # Limpiar cache
])

print("✅ Compilación completada!")
print("📁 Ejecutable en: dist/SistemaRiego.exe")
