# modules/reports.py - Generación de Reportes y Recibos PDF
# Usa ReportLab para crear PDFs de recibos y reportes diarios
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm, cm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from datetime import datetime
import os
import sys
import subprocess
import platform
from typing import Dict, List
from modules.models import obtener_recibo_por_id, obtener_configuracion

# ==================== CONFIGURACIÓN DE RECIBO ====================
RECIBO_ANCHO = 21.6 * cm  
RECIBO_ALTO = 9.3 * cm    
# Ruta del logo
LOGO_PATH = os.path.join('assets', 'logo.png')

def generar_recibo_pdf(recibo_id: int, es_reimpresion: bool = False) -> str:
    """Genera el PDF de un recibo en formato 1/3 carta"""
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
    c = canvas.Canvas(filepath, pagesize=(RECIBO_ANCHO, RECIBO_ALTO))
    _dibujar_recibo_principal(c, recibo, nombre_oficina, ubicacion, es_reimpresion)
    c.save()
    return filepath

def _dibujar_recibo_principal(c, recibo: Dict, nombre_oficina: str, ubicacion: str, es_reimpresion: bool):
    """Dibuja el recibo principal en el canvas"""
    y_pos = RECIBO_ALTO - 1*cm
    margen_izq = 1*cm
    margen_der = RECIBO_ANCHO - 1*cm
    margen_sup = RECIBO_ALTO - 0.5*cm # Margen superior para el logo

    if es_reimpresion:
        c.saveState()
        c.setFont("Helvetica-Bold", 40)
        c.setFillColorRGB(0.9, 0.9, 0.9)
        c.rotate(45)
        c.drawString(5*cm, -2*cm, "REIMPRESIÓN")
        c.restoreState()

    # --- Añadir Logo ---
    if os.path.exists(LOGO_PATH):
        try:
            # Ajusta el ancho y alto según sea necesario
            logo_width = 1.5 * cm
            logo_height = 1.5 * cm
            # Coloca el logo en la esquina superior izquierda
            c.drawImage(LOGO_PATH, margen_izq, margen_sup - logo_height, width=logo_width, height=logo_height, mask='auto')
        except Exception as e:
            print(f"Error al añadir logo: {e}") # Opcional: manejar error silenciosamente o mostrarlo
    # --------------------

    # ENCABEZADO
    # Ajustar la posición Y después del logo
    encabezado_y_pos = margen_sup - logo_height - 0.3*cm # Espacio debajo del logo
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

def generar_reporte_diario(fecha: str, recibos: List[Dict]) -> str:
    """Genera un reporte PDF del día con todos los recibos"""
    reportes_dir = os.path.join('database', 'reportes')
    os.makedirs(reportes_dir, exist_ok=True)
    filename = f"reporte_diario_{fecha.replace('-', '')}.pdf"
    filepath = os.path.join(reportes_dir, filename)
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

# ==================== IMPRESIÓN ====================
def imprimir_recibo(ruta_pdf: str, impresora: str = None):
    """Envía el PDF a la impresora"""
    if not os.path.exists(ruta_pdf):
        raise FileNotFoundError(f"Archivo no encontrado: {ruta_pdf}")
    sistema = platform.system()
    try:
        if sistema == 'Windows':
            if impresora:
                os.startfile(ruta_pdf, 'print')
            else:
                os.startfile(ruta_pdf, 'print')
        elif sistema == 'Darwin':
            if impresora:
                subprocess.run(['lp', '-d', impresora, ruta_pdf], check=True)
            else:
                subprocess.run(['lp', ruta_pdf], check=True)
        elif sistema == 'Linux':
            if impresora:
                subprocess.run(['lp', '-d', impresora, ruta_pdf], check=True)
            else:
                subprocess.run(['lp', ruta_pdf], check=True)
        return True
    except Exception as e:
        print(f"Error al imprimir: {e}")
        return False

def obtener_impresoras_disponibles() -> List[str]:
    """Obtiene lista de impresoras disponibles en el sistema"""
    sistema = platform.system()
    impresoras = []
    try:
        if sistema == 'Windows':
            import win32print
            impresoras = [printer[2] for printer in win32print.EnumPrinters(2)]
        elif sistema in ['Darwin', 'Linux']:
            resultado = subprocess.run(['lpstat', '-p'], capture_output=True, text=True)
            for linea in resultado.stdout.split('\n'):
                if linea.startswith('printer'):
                    partes = linea.split()
                    if len(partes) >= 2:
                        impresoras.append(partes[1])
    except:
        pass
    return impresoras

def abrir_pdf(ruta_pdf: str):
    """Abre el PDF con el visor predeterminado del sistema"""
    if not os.path.exists(ruta_pdf):
        raise FileNotFoundError(f"Archivo no encontrado: {ruta_pdf}")
    sistema = platform.system()
    try:
        if sistema == 'Windows':
            os.startfile(ruta_pdf)
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
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Recibos"
        headers = ["Folio", "Fecha", "Hora", "Lote", "Nombre", "Localidad",
                  "Barrio", "Superficie", "Cultivo", "Riego No.", "Acción", "Costo"]
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center')
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
        for col in ws.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(cell.value)
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column].width = adjusted_width
        reportes_dir = os.path.join('database', 'reportes')
        os.makedirs(reportes_dir, exist_ok=True)
        filepath = os.path.join(reportes_dir, filename)
        wb.save(filepath)
        return filepath
    except ImportError:
        raise ImportError("La librería openpyxl no está instalada. Instálala con: pip install openpyxl")
    except Exception as e:
        raise Exception(f"Error al exportar a Excel: {e}")
