#models/reports.py
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import mm, cm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle

from datetime import datetime

import os
import time
import sys
import subprocess
import platform

if platform.system() == "Windows":
    try:
        import win32print
        import win32api
    except ImportError:
        win32print = None
        win32api = None
        print("Advertencia: pywin32 no está instalado. La impresión en Windows puede fallar. Instale con: pip install pywin32")

from typing import Dict, List

from modules.models import obtener_recibo_por_id, obtener_configuracion

# ==================== CONFIGURACIÓN DE RECIBO ====================

# IMPORTANTE: Recibo en formato 1/3 carta - ORIENTACIÓN VERTICAL
RECIBO_ANCHO = 21.6 * cm
RECIBO_ALTO = 9.3 * cm

# Ruta del logo
LOGO_PATH = os.path.join('assets', 'logo.png')

# ==================== UTILIDADES DE IMPRESIÓN (Windows) ====================

def _buscar_sumatra() -> str | None:
    """
    Busca SumatraPDF en rutas comunes (x64/x86) y retorna la ruta si existe.
    """
    posibles = [
        r"C:\Program Files\SumatraPDF\SumatraPDF.exe",
        r"C:\Program Files (x86)\SumatraPDF\SumatraPDF.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\SumatraPDF\SumatraPDF.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\SumatraPDF.exe"),
    ]
    for p in posibles:
        if os.path.exists(p):
            return p
    return None

def _imprimir_pdf_windows(ruta_pdf: str, impresora: str | None = None) -> None:
    """
    Imprime en Windows con múltiples fallbacks:
    1) SumatraPDF (mejor opción)
    2) Abrir PDF y dejar que el usuario imprima manualmente
    """
    import subprocess
    
    # 1) Intentar con SumatraPDF
    sumatra = _buscar_sumatra()
    if sumatra:
        try:
            args = [sumatra]
            if impresora:
                args += ["-print-to", impresora]
            else:
                args += ["-print-to-default"]
            args += ["-exit-on-print", ruta_pdf]
            subprocess.run(args, check=True, timeout=10)
            print(f"✓ Impreso con SumatraPDF: {ruta_pdf}")
            return
        except Exception as e:
            print(f"⚠ SumatraPDF falló: {e}")
    
    # 2) Fallback: Solo ABRIR el PDF (el usuario imprime manualmente)
    try:
        os.startfile(ruta_pdf)
        print(f"⚠ PDF abierto para impresión manual: {ruta_pdf}")
        # Mostrar mensaje al usuario
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo(
            "Impresión Manual", 
            "El PDF se ha abierto.\n\n"
            "Por favor, presiona Ctrl+P para imprimir manualmente.\n\n"
            "Recomendación: Instala SumatraPDF para impresión automática."
        )
        root.destroy()
        return
    except Exception as e:
        raise RuntimeError(
            f"No se puede imprimir en Windows.\n\n"
            f"Soluciones:\n"
            f"1. Instala SumatraPDF (https://www.sumatrapdfreader.org/)\n"
            f"2. Configura una impresora predeterminada en Windows\n"
            f"3. Asocia PDFs con Adobe Reader\n\n"
            f"Error: {e}"
        )


# ==================== GENERACIÓN DE RECIBOS ====================

def generar_recibo_pdf(recibo_id: int, es_reimpresion: bool = False) -> str:
    """Genera el PDF de un recibo en formato 1/3 carta - VERTICAL"""
    recibo = obtener_recibo_por_id(recibo_id)
    if not recibo:
        raise ValueError("Recibo no encontrado")

    nombre_oficina = obtener_configuracion('nombre_oficina') or 'ASOCIACIÓN DE RIEGO'
    ubicacion = obtener_configuracion('ubicacion') or 'Tezontepec de Aldama, Hgo.'

    recibos_dir = os.path.join('database', 'recibos')
    os.makedirs(recibos_dir, exist_ok=True)

    sufijo = '_REIMPRESION' if es_reimpresion else ''
    filename = f"recibo_{recibo['folio']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{sufijo}.pdf"
    filepath = os.path.join(recibos_dir, filename)

    # Crear canvas con tamaño en orientación VERTICAL
    c = canvas.Canvas(filepath, pagesize=(RECIBO_ANCHO, RECIBO_ALTO))
    _dibujar_recibo_principal(c, recibo, nombre_oficina, ubicacion, es_reimpresion)
    c.save()

    return filepath

def generar_recibo_pdf_temporal(recibo_id: int, es_reimpresion: bool = False) -> str:
    """
    Genera el PDF de un recibo TEMPORAL que será eliminado después de imprimir.
    No lo guarda permanentemente en database/recibos/
    """
    recibo = obtener_recibo_por_id(recibo_id)
    if not recibo:
        raise ValueError("Recibo no encontrado")

    nombre_oficina = obtener_configuracion('nombre_oficina') or 'ASOCIACIÓN DE RIEGO'
    ubicacion = obtener_configuracion('ubicacion') or 'Tezontepec de Aldama, Hgo.'

    # Crear carpeta temporal en /tmp (Mac/Linux) o %TEMP% (Windows)
    if platform.system() == "Windows":
        temp_dir = os.path.join(os.environ.get('TEMP', os.getcwd()), 'recibos_temp')
    else:
        temp_dir = os.path.join('/tmp', 'recibos_temp')

    os.makedirs(temp_dir, exist_ok=True)

    sufijo = '_REIMPRESION' if es_reimpresion else ''
    filename = f"recibo_{recibo['folio']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{sufijo}.pdf"
    filepath = os.path.join(temp_dir, filename)

    c = canvas.Canvas(filepath, pagesize=(RECIBO_ANCHO, RECIBO_ALTO))
    _dibujar_recibo_principal(c, recibo, nombre_oficina, ubicacion, es_reimpresion)
    c.save()

    return filepath

# ==================== IMPRESIÓN (TEMPORALES) ====================

def imprimir_recibo_y_limpiar(pdf_path: str):
    """
    Intenta imprimir un archivo PDF en Windows o macOS y luego lo elimina.
    """
    sistema = platform.system()
    print(f"Intentando imprimir en {sistema} desde: {pdf_path}")

    if not os.path.exists(pdf_path):
        print(f"Error: El archivo PDF no existe: {pdf_path}")
        return

    impreso = False

    if sistema == "Windows":
        if win32print and win32api:
            try:
                # Usar win32api para imprimir
                win32api.ShellExecute(0, "print", pdf_path, None, ".", 0)
                print(f"Comando de impresión enviado para win32: {pdf_path}")
                impreso = True
            except Exception as e:
                 print(f"Error con win32api.ShellExecute: {e}")
        else:
             print("pywin32 no disponible. Intentando alternativas...")

        if not impreso:
            # Alternativa menos confiable: os.startfile
            try:
                os.startfile(pdf_path, "print") # Esta acción puede no ser silenciosa
                print(f"Comando de impresión enviado para os.startfile: {pdf_path}")
                impreso = True
            except Exception as e:
                 print(f"Error con os.startfile: {e}")

    elif sistema == "Darwin": # macOS
        try:
            # Usar 'lp' para imprimir en macOS (requiere CUPS instalado, que generalmente lo está)
            subprocess.run(["lp", pdf_path], check=True)
            print(f"PDF impreso en macOS usando lp: {pdf_path}")
            impreso = True
        except subprocess.CalledProcessError as e:
            print(f"Error al imprimir con 'lp' en macOS: {e}")
        except FileNotFoundError:
            print("Comando 'lp' no encontrado en macOS. Verifique la instalación de CUPS o la ruta.")

    else: # Linux u Otro
        try:
            # Usar 'lp' para imprimir en Linux (requiere CUPS instalado)
            subprocess.run(["lp", pdf_path], check=True)
            print(f"PDF impreso en Linux usando lp: {pdf_path}")
            impreso = True
        except subprocess.CalledProcessError as e:
            print(f"Error al imprimir con 'lp' en Linux: {e}")
        except FileNotFoundError:
            print("Comando 'lp' no encontrado. Verifique la instalación de CUPS o la ruta.")

    # Esperar un momento para que el comando de impresión se procese
    import time
    time.sleep(1) # Ajusta si es necesario

    # Eliminar el archivo temporal después del intento de impresión
    try:
        os.remove(pdf_path)
        print(f"Archivo temporal eliminado: {pdf_path}")
    except OSError as e:
        print(f"Error al eliminar archivo temporal {pdf_path}: {e}")

# ==================== DIBUJO DE RECIBO ====================

def _dibujar_recibo_principal(c, recibo: Dict, nombre_oficina: str, ubicacion: str, es_reimpresion: bool):
    """Dibuja el recibo principal en el canvas - FORMATO VERTICAL"""
    y_pos = RECIBO_ALTO - 1*cm
    margen_izq = 1*cm
    margen_der = RECIBO_ANCHO - 1*cm
    margen_sup = RECIBO_ALTO - 0.5*cm  # Margen superior para el logo

    if es_reimpresion:
        c.saveState()
        c.setFont("Helvetica-Bold", 40)
        c.setFillColorRGB(0.9, 0.9, 0.9)
        c.rotate(45)
        c.drawString(5*cm, -2*cm, "REIMPRESIÓN")
        c.restoreState()

    # --- Añadir Logo ---
    logo_width = 0
    logo_height = 0
    if os.path.exists(LOGO_PATH):
        try:
            # Ajusta el ancho y alto según sea necesario
            logo_width = 1.5 * cm
            logo_height = 1.5 * cm
            # Coloca el logo en la esquina superior izquierda
            c.drawImage(LOGO_PATH, margen_izq, margen_sup - logo_height, width=logo_width, height=logo_height, mask='auto')
        except Exception as e:
            print(f"Error al añadir logo: {e}")
    # --------------------

    # ENCABEZADO
    encabezado_y_pos = margen_sup - logo_height - 0.3*cm  # Espacio debajo del logo
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(RECIBO_ANCHO/2, encabezado_y_pos, nombre_oficina.upper())
    y_pos = encabezado_y_pos - 0.5*cm
    c.line(margen_izq, y_pos, margen_der, y_pos)
    y_pos -= 0.5*cm

    # DATOS PRINCIPALES
    c.setFont("Helvetica", 8)
    col1_x = margen_izq
    col2_x = RECIBO_ANCHO/2

    c.setFont("Helvetica-Bold", 8)
    c.drawString(col1_x, y_pos, f"No. Recibo: {recibo['folio']}")
    c.drawString(col2_x, y_pos, f"Ciclo: {recibo['ciclo']}")
    y_pos -= 0.4*cm

    c.drawString(col1_x, y_pos, f"No. Lote: {recibo['numero_lote']}")
    c.drawString(col2_x, y_pos, f"Sup: {recibo['superficie']} ha")
    y_pos -= 0.4*cm

    c.drawString(col1_x, y_pos, f"Cultivo: {recibo['cultivo']}")
    c.drawString(col2_x, y_pos, f"Riego No.: {recibo['numero_riego']}")
    y_pos -= 0.5*cm

    # RECIBÍ DE
    c.setFont("Helvetica", 9)
    c.drawString(margen_izq, y_pos, "Recibí de:")
    y_pos -= 0.4*cm

    c.setFont("Helvetica-Bold", 10)
    c.drawString(margen_izq + 0.5*cm, y_pos, recibo['nombre'].upper())
    y_pos -= 0.5*cm

    # LOCALIDAD Y BARRIO
    c.setFont("Helvetica", 8)
    c.drawString(margen_izq, y_pos, f"Localidad: {recibo['localidad']}")
    c.drawString(col2_x, y_pos, f"Barrio: {recibo['barrio']}")
    y_pos -= 0.5*cm

    c.line(margen_izq, y_pos, margen_der, y_pos)
    y_pos -= 0.5*cm

    # MONTO
    c.setFont("Helvetica-Bold", 12)
    monto_texto = f"${recibo['costo']:.2f}"
    c.drawRightString(margen_der, y_pos, monto_texto)
    y_pos -= 0.5*cm

    c.line(margen_izq, y_pos, margen_der, y_pos)
    y_pos -= 0.4*cm

    # TOTAL
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margen_izq, y_pos, "TOTAL:")
    c.drawRightString(margen_der, y_pos, monto_texto)
    y_pos -= 0.5*cm

    c.line(margen_izq, y_pos, margen_der, y_pos)
    y_pos -= 0.4*cm

    # FECHA, HORA Y FIRMA
    c.setFont("Helvetica", 7)
    fecha_obj = datetime.strptime(recibo['fecha'], '%Y-%m-%d')
    fecha_texto = f"{ubicacion} A: {fecha_obj.strftime('%d/%m/%Y')}"

    hora_obj = datetime.strptime(recibo['hora'], '%H:%M:%S')
    am_pm = 'a.m.' if hora_obj.hour < 12 else 'p.m.'
    hora_12 = hora_obj.hour if hora_obj.hour <= 12 else hora_obj.hour - 12
    if hora_12 == 0:
        hora_12 = 12
    hora_texto = f"{hora_12:02d}:{hora_obj.minute:02d}:{hora_obj.second:02d} {am_pm}"

    c.drawString(margen_izq, y_pos, fecha_texto)
    c.drawRightString(margen_der, y_pos, f"Hora: {hora_texto}")
    y_pos -= 0.5*cm

    # Firma
    c.setFont("Helvetica", 8)
    c.drawRightString(margen_der, y_pos, "Firma Recaudador")
    y_pos -= 0.3*cm
    c.line(margen_der - 4*cm, y_pos, margen_der, y_pos)

# ==================== REPORTE DIARIO ====================

def generar_reporte_diario(fecha: str, recibos: List[Dict]) -> str:
    """Genera un reporte PDF del día con todos los recibos - ORIENTACIÓN VERTICAL"""
    reportes_dir = os.path.join('database', 'reportes')
    os.makedirs(reportes_dir, exist_ok=True)
    filename = f"reporte_diario_{fecha.replace('-', '')}.pdf"
    filepath = os.path.join(reportes_dir, filename)

    # Canvas con tamaño PORTRAIT (vertical) - letter = (8.5 x 11 inches)
    c = canvas.Canvas(filepath, pagesize=letter)

    nombre_oficina = obtener_configuracion('nombre_oficina') or 'ASOCIACIÓN DE RIEGO'

    # --- Añadir Logo al Reporte Diario ---
    if os.path.exists(LOGO_PATH):
        try:
            logo_width = 2 * cm
            logo_height = 2 * cm
            c.drawImage(LOGO_PATH, 2*cm, letter[1] - 3*cm, width=logo_width, height=logo_height, mask='auto')
        except Exception as e:
            print(f"Error al añadir logo al reporte diario: {e}")
    # --------------------------------------

    y_pos = letter[1] - 2*cm
    margen_izq = 2*cm
    margen_der = letter[0] - 2*cm

    # ENCABEZADO
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(letter[0]/2, y_pos, nombre_oficina.upper())
    y_pos -= 0.7*cm

    c.setFont("Helvetica-Bold", 12)
    fecha_obj = datetime.strptime(fecha, '%Y-%m-%d')
    c.drawCentredString(letter[0]/2, y_pos, f"REPORTE DIARIO - {fecha_obj.strftime('%d/%m/%Y')}")
    y_pos -= 0.7*cm

    c.setFont("Helvetica", 10)
    c.drawCentredString(letter[0]/2, y_pos, f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    y_pos -= 1*cm

    # TABLA DE RECIBOS
    if not recibos:
        c.setFont("Helvetica", 11)
        c.drawCentredString(letter[0]/2, y_pos, "No hay recibos registrados en este día")
    else:
        c.setFont("Helvetica-Bold", 8)
        col_widths = [1.5*cm, 2*cm, 1.5*cm, 5*cm, 2.5*cm, 1.5*cm, 2.5*cm, 2*cm]
        col_x = [margen_izq]
        for w in col_widths[:-1]:
            col_x.append(col_x[-1] + w)

        headers = ["Folio", "Hora", "Lote", "Nombre", "Cultivo", "Riego", "Acción", "Monto"]
        for i, header in enumerate(headers):
            c.drawString(col_x[i], y_pos, header)
        y_pos -= 0.3*cm
        c.line(margen_izq, y_pos, margen_der, y_pos)
        y_pos -= 0.4*cm

        c.setFont("Helvetica", 7)
        total_dia = 0

        for recibo in recibos:
            if y_pos < 3*cm:
                c.showPage()
                # Volver a dibujar el logo en la nueva página si es necesario
                if os.path.exists(LOGO_PATH):
                    try:
                        logo_width = 2 * cm
                        logo_height = 2 * cm
                        c.drawImage(LOGO_PATH, 2*cm, letter[1] - 3*cm, width=logo_width, height=logo_height, mask='auto')
                    except Exception as e:
                        print(f"Error al añadir logo a nueva página del reporte: {e}")

                y_pos = letter[1] - 2*cm
                c.setFont("Helvetica-Bold", 8)
                for i, header in enumerate(headers):
                    c.drawString(col_x[i], y_pos, header)
                y_pos -= 0.3*cm
                c.line(margen_izq, y_pos, margen_der, y_pos)
                y_pos -= 0.4*cm
                c.setFont("Helvetica", 7)

            c.drawString(col_x[0], y_pos, str(recibo['folio']))
            c.drawString(col_x[1], y_pos, recibo['hora'][:5])
            c.drawString(col_x[2], y_pos, recibo['numero_lote'])
            nombre = recibo['nombre'][:30] if len(recibo['nombre']) > 30 else recibo['nombre']
            c.drawString(col_x[3], y_pos, nombre)
            c.drawString(col_x[4], y_pos, recibo['cultivo'])
            c.drawString(col_x[5], y_pos, str(recibo['numero_riego']))
            tipo = "Nueva" if recibo['tipo_accion'] == 'Nueva siembra' else "Adicional"
            c.drawString(col_x[6], y_pos, tipo)
            c.drawRightString(col_x[7] + 2*cm, y_pos, f"${recibo['costo']:.2f}")
            total_dia += recibo['costo']
            y_pos -= 0.35*cm

        y_pos -= 0.2*cm
        c.line(margen_izq, y_pos, margen_der, y_pos)
        y_pos -= 0.5*cm

        c.setFont("Helvetica-Bold", 11)
        c.drawString(margen_izq, y_pos, f"TOTAL DEL DÍA:")
        c.drawRightString(margen_der, y_pos, f"${total_dia:.2f}")
        y_pos -= 0.5*cm

        c.setFont("Helvetica", 9)
        c.drawString(margen_izq, y_pos, f"Total de recibos emitidos: {len(recibos)}")

    c.save()
    return filepath

# ==================== IMPRESIÓN DIRECTA (NO TEMPORALES) ====================

def imprimir_recibo(ruta_pdf: str, impresora: str = None):
    """Envía el PDF a la impresora sin eliminar el archivo (para PDFs no temporales)"""
    if not os.path.exists(ruta_pdf):
        raise FileNotFoundError(f"Archivo no encontrado: {ruta_pdf}")

    sistema = platform.system()

    try:
        if sistema == 'Windows':
            _imprimir_pdf_windows(ruta_pdf, impresora)
        elif sistema == 'Darwin':
            cmd = ['lp', ruta_pdf] if not impresora else ['lp', '-d', impresora, ruta_pdf]
            subprocess.run(cmd, check=True)
        else:
            cmd = ['lp', ruta_pdf] if not impresora else ['lp', '-d', impresora, ruta_pdf]
            subprocess.run(cmd, check=True)
        return True
    except Exception as e:
        print(f"Error al imprimir: {e}")
        return False

# ==================== LISTA DE IMPRESORAS ====================

def obtener_impresoras_disponibles() -> List[str]:
    """
    Lista impresoras disponibles:
    - Windows: pywin32 si está, si no PowerShell/WMIC (fallback).
    - macOS/Linux: lpstat.
    """
    try:
        sistema = platform.system()

        if sistema == "Windows":
            # 1) Intento con pywin32
            try:
                import win32print  # type: ignore
                impresoras = win32print.EnumPrinters(2)
                return [imp[2] for imp in impresoras if len(imp) >= 3]
            except Exception:
                pass  # seguir al fallback

            # 2) PowerShell (Get-CimInstance)
            try:
                ps = [
                    "powershell", "-NoProfile", "-Command",
                    "Get-CimInstance -ClassName Win32_Printer | Select-Object -ExpandProperty Name"
                ]
                r = subprocess.run(ps, capture_output=True, text=True, timeout=5)
                names = [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]
                if names:
                    return names
            except Exception:
                pass

            # 3) WMIC (legacy pero aún frecuente)
            try:
                r = subprocess.run(["wmic", "printer", "get", "name"],
                                   capture_output=True, text=True, timeout=5)
                names = [ln.strip() for ln in r.stdout.splitlines()[1:] if ln.strip()]
                if names:
                    return names
            except Exception:
                pass

            return ["Impresora por defecto"]

        elif sistema == "Darwin":  # macOS
            r = subprocess.run(["lpstat", "-p", "-d"], capture_output=True, text=True, timeout=5)
            impresoras = []
            for ln in r.stdout.splitlines():
                if ln.startswith("printer"):
                    partes = ln.split()
                    if len(partes) >= 2:
                        impresoras.append(partes[1])
            return impresoras if impresoras else ["Impresora por defecto"]

        else:  # Linux
            r = subprocess.run(["lpstat", "-p", "-d"], capture_output=True, text=True, timeout=5)
            impresoras = []
            for ln in r.stdout.splitlines():
                if ln.startswith("printer"):
                    partes = ln.split()
                    if len(partes) >= 2:
                        impresoras.append(partes[1])
            return impresoras if impresoras else ["Impresora por defecto"]

    except Exception:
        return ["Impresora por defecto"]

# ==================== ABRIR PDF ====================

def abrir_pdf(ruta_pdf: str):
    """Abre el PDF con el visor predeterminado del sistema"""
    if not os.path.exists(ruta_pdf):
        raise FileNotFoundError(f"Archivo no encontrado: {ruta_pdf}")

    sistema = platform.system()

    try:
        if sistema == 'Windows':
            os.startfile(ruta_pdf)  # depende de asociación, solo para ver
        elif sistema == 'Darwin':
            subprocess.run(['open', ruta_pdf])
        else:
            subprocess.run(['xdg-open', ruta_pdf])
        return True
    except Exception as e:
        print(f"Error al abrir PDF: {e}")
        return False

# ==================== EXPORTACIÓN A EXCEL ====================

def exportar_a_excel(recibos: List[Dict], filename: str) -> str:
    """Exporta una lista de recibos a un archivo Excel"""
    try:
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill

        # Crear libro de trabajo
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Recibos"

        # Encabezados
        headers = ['Folio', 'Fecha', 'Hora', 'Lote', 'Nombre', 'Localidad', 'Barrio',
                   'Superficie', 'Cultivo', 'Riego No.', 'Acción', 'Costo']

        # Estilo de encabezados
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")

        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center')

        # Datos
        for row, recibo in enumerate(recibos, 2):
            ws.cell(row=row, column=1, value=recibo['folio'])
            ws.cell(row=row, column=2, value=recibo['fecha'])
            ws.cell(row=row, column=3, value=recibo['hora'])
            ws.cell(row=row, column=4, value=recibo['numero_lote'])
            ws.cell(row=row, column=5, value=recibo['nombre'])
            ws.cell(row=row, column=6, value=recibo['localidad'])
            ws.cell(row=row, column=7, value=recibo['barrio'])
            ws.cell(row=row, column=8, value=recibo['superficie'])
            ws.cell(row=row, column=9, value=recibo['cultivo'])
            ws.cell(row=row, column=10, value=recibo['numero_riego'])
            ws.cell(row=row, column=11, value=recibo['tipo_accion'])
            ws.cell(row=row, column=12, value=recibo['costo'])

        # Ajustar anchos de columna
        for col in ws.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(cell.value)
                except Exception:
                    pass
            adjusted_width = min((max_length + 2), 50)
            ws.column_dimensions[column].width = adjusted_width

        # Guardar archivo
        reportes_dir = os.path.join('database', 'reportes')
        os.makedirs(reportes_dir, exist_ok=True)
        filepath = os.path.join(reportes_dir, filename)
        wb.save(filepath)

        return filepath

    except ImportError:
        raise ImportError("La librería 'openpyxl' no está instalada. Instálala con: pip install openpyxl")
    except Exception as e:
        raise Exception(f"Error al exportar a Excel: {e}")
