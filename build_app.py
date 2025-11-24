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
    '--icon=assets/zapata.ico',         # Icono (si existe)
    
    # DATOS Y RECURSOS
    '--add-data=assets;assets',         # Incluir carpeta assets
    '--add-data=database;database',     # ✅ NUEVO: Incluir base de datos inicial
    
    # DEPENDENCIAS CRÍTICAS PARA TU APP
    '--hidden-import=chardet',          # Para detección de encoding
    '--hidden-import=pandas',           # Para leer CSV
    '--hidden-import=openpyxl',         # Para Excel (pandas dependency)
    '--hidden-import=openpyxl.styles',  # Estilos de Excel
    '--hidden-import=openpyxl.utils',   # Utilidades de Excel
    '--hidden-import=sqlite3',          # Base de datos
    '--hidden-import=json',             # ✅ NUEVO: Para configuración y datos JSON
    '--hidden-import=time',             # ✅ NUEVO: Manejo de tiempo (delays, timestamps)
    '--hidden-import=sys',              # ✅ NUEVO: Sistema (paths, exit codes)
    '--hidden-import=shutil',           # ✅ NUEVO: Operaciones de archivos (backups)
    '--hidden-import=collections',      # ✅ NUEVO: Estructuras de datos
    
    # DEPENDENCIAS PYWIN32
    '--hidden-import=win32print',       
    '--hidden-import=win32api',
    '--hidden-import=win32com',
    '--hidden-import=pywintypes',       # ✅ NUEVO: Tipos de win32
    
    # DEPENDENCIAS MATPLOTLIB (NUEVO - Para gráficos en estadísticas)
    '--hidden-import=matplotlib',
    '--hidden-import=matplotlib.pyplot',               # ✅ NUEVO: Para crear gráficos
    '--hidden-import=matplotlib.backends.backend_agg', # ✅ NUEVO: Backend sin GUI
    '--hidden-import=matplotlib.backends.backend_tkagg',
    '--hidden-import=matplotlib.patches',              # ✅ NUEVO: Para formas en gráficos
    '--hidden-import=matplotlib.figure',               # ✅ NUEVO: Figuras
    
    # DEPENDENCIAS NUMPY (NUEVO - matplotlib lo requiere)
    '--hidden-import=numpy',                           # ✅ NUEVO: Para cálculos
    '--hidden-import=numpy.core',                      # ✅ NUEVO: Core de numpy
    '--hidden-import=numpy.core._multiarray_umath',    # ✅ NUEVO: Funciones matemáticas
    
    # DEPENDENCIAS REPORTLAB (Para PDFs)
    '--hidden-import=reportlab',
    '--hidden-import=reportlab.pdfgen',                # ✅ NUEVO: Generación de PDF
    '--hidden-import=reportlab.pdfgen.canvas',         # ✅ NUEVO: Canvas PDF
    '--hidden-import=reportlab.platypus',              # ✅ NUEVO: Tablas y layouts
    '--hidden-import=reportlab.lib',                   # ✅ NUEVO: Utilidades
    '--hidden-import=reportlab.lib.pagesizes',         # ✅ NUEVO: Tamaños de página
    '--hidden-import=reportlab.lib.units',             # ✅ NUEVO: Unidades (cm, mm)
    '--hidden-import=reportlab.lib.colors',            # ✅ NUEVO: Colores
    
    # OTRAS DEPENDENCIAS COMUNES
    '--hidden-import=PIL',              # Para imágenes (si usas Pillow)
    '--hidden-import=PIL.Image',        # ✅ NUEVO: Manipulación de imágenes
    '--hidden-import=tempfile',         # ✅ NUEVO: Archivos temporales (para gráficos)
    '--hidden-import=datetime',         # Fechas
    '--hidden-import=typing',           # Type hints
    '--hidden-import=subprocess',       # ✅ NUEVO: Para ejecutar comandos (impresión)
    '--hidden-import=platform',         # ✅ NUEVO: Detección de SO
    
    # DEPENDENCIAS TKINTER (ya incluidas pero por seguridad)
    '--hidden-import=tkinter',
    '--hidden-import=tkinter.ttk',
    '--hidden-import=tkinter.messagebox',
    '--hidden-import=tkinter.filedialog',
    '--hidden-import=tkinter.scrolledtext',
    '--hidden-import=tkinter.simpledialog',
    '--hidden-import=tkinter.font',         # ✅ NUEVO: Fuentes personalizadas
    
    # DEPENDENCIAS DE ENCODING Y STRINGS
    '--hidden-import=encodings',            # ✅ NUEVO: Encodings para archivos
    '--hidden-import=encodings.utf_8',      # ✅ NUEVO: UTF-8 encoding
    '--hidden-import=encodings.cp1252',     # ✅ NUEVO: Windows encoding
    '--hidden-import=string',               # ✅ NUEVO: Operaciones de strings
    
    # OPTIMIZACIONES Y FLAGS
    '--clean',                          # Limpiar cache
    '--noconfirm',                      # No pedir confirmación
    '--noupx',                          # ✅ NUEVO: Evitar falsos positivos de antivirus
    '--log-level=WARN',                 # ✅ NUEVO: Solo mostrar warnings/errors
])


print("✅ Compilación completada!")
print("📁 Ejecutable en: dist/SistemaRiego.exe")
print("\n📋 Siguiente paso:")
print("   Prueba el ejecutable: dist\\SistemaRiego.exe")
