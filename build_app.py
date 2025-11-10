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
    '--onefile',                        # Un solo archivo
    '--windowed',                       # Sin consola (GUI pura)
    '--icon=assets/zapata.png',         # Icono (si existe)
    
    # DATOS Y RECURSOS
    '--add-data=assets;assets',         # Incluir carpeta assets
    
    # DEPENDENCIAS CRÍTICAS PARA TU APP
    '--hidden-import=chardet',          # ← NUEVO: Para detección de encoding
    '--hidden-import=pandas',           # Para leer CSV
    '--hidden-import=openpyxl',         # Para Excel (pandas dependency)
    '--hidden-import=sqlite3',          # Base de datos
    
    # DEPENDENCIAS PYWIN32
    '--hidden-import=win32print',       
    '--hidden-import=win32api',
    '--hidden-import=win32com',         # ← NUEVO: Puede ser necesario
    
    # DEPENDENCIAS MATPLOTLIB
    '--hidden-import=matplotlib',
    '--hidden-import=matplotlib.backends.backend_tkagg',  # ← NUEVO
    
    # OTRAS DEPENDENCIAS COMUNES
    '--hidden-import=PIL',              # Para imágenes (si usas Pillow)
    '--hidden-import=reportlab',        # Para PDFs (si generas reportes)
    
    '--clean',                          # Limpiar cache
])

print("✅ Compilación completada!")
print("📁 Ejecutable en: dist/SistemaRiego.exe")
