"""
Script de prueba - NOMBRE MÁS BAJO
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from datetime import datetime
import os

# ===== CONSTANTES =====
RECIBO_ANCHO = 21.6 * cm
RECIBO_ALTO = 7 * cm
LOGO_PATH = os.path.join('assets', 'lagoo.png')

# ===== COLORES =====
COLOR_VERDE = colors.HexColor('#B8D1BF')
COLOR_BEIGE = colors.HexColor('#F5F0E8')
COLOR_BEIGE_OSCURO = colors.HexColor('#C9B99A')
COLOR_TEXTO = colors.HexColor('#2C3E2E')
COLOR_TEXTO_GRIS = colors.HexColor('#666666')

def dibujar_recibo_nombre_mas_bajo(ruta_salida="recibo_NOMBRE_BAJO.pdf"):
    """
    NOMBRE TODAVÍA MÁS ABAJO
    """
    
    recibo = {
        'folio': '6',
        'numero_lote': '498',
        'numero_riego': '1',
        'cultivo': 'TRIGO',
        'superficie': '1.0',
        'ciclo': 'ALONSO',
        'barrio': 'HUITEL',
        'nombre': 'ABELINA RIVERA MARTÍNEZ',
        'costo': 450.00,
        'fecha': '2025-11-06',
        'hora': '18:22:16'
    }
    
    c = canvas.Canvas(ruta_salida, pagesize=(RECIBO_ANCHO, RECIBO_ALTO))
    
    # ===== FONDO BEIGE =====
    c.setFillColor(COLOR_BEIGE)
    c.roundRect(0.15*cm, 0.15*cm, RECIBO_ANCHO - 0.3*cm, RECIBO_ALTO - 0.3*cm, 
                0.5*cm, stroke=0, fill=1)
    
    # ===== HEADER VERDE =====
    c.setFillColor(COLOR_VERDE)
    c.roundRect(0.4*cm, RECIBO_ALTO - 2*cm, RECIBO_ANCHO - 0.8*cm, 1.6*cm, 
                0.4*cm, stroke=0, fill=1)
    
    # ===== LOGO =====
    if os.path.exists(LOGO_PATH):
        try:
            c.drawImage(LOGO_PATH, 0.7*cm, RECIBO_ALTO - 1.85*cm, 
                       width=1.4*cm, height=1.4*cm, mask='auto')
        except:
            pass
    
    # ===== TÍTULO =====
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawCentredString(RECIBO_ANCHO/2 + 0.5*cm, RECIBO_ALTO - 0.85*cm, 
                       "ASOCIACIÓN DE CAMPESINOS DE BOMBEO Y REBOMBEO")
    
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(RECIBO_ANCHO/2 + 0.5*cm, RECIBO_ALTO - 1.15*cm, 
                       "DEL CERRO DEL XICUCO A.C. M7-1")
    
    c.setFont("Helvetica", 7)
    c.drawCentredString(RECIBO_ANCHO/2 + 0.5*cm, RECIBO_ALTO - 1.5*cm, 
                       "RFC: ACB030619G68")
    
    # ===== SEPARADOR =====
    y_pos = RECIBO_ALTO - 2.15*cm
    c.setStrokeColor(COLOR_BEIGE_OSCURO)
    c.setLineWidth(0.5)
    c.line(0.7*cm, y_pos, RECIBO_ANCHO - 0.7*cm, y_pos)
    
    # ===== CAJA DE DATOS =====
    y_pos -= 0.15*cm
    c.setFillColor(colors.white)
    c.roundRect(0.7*cm, y_pos - 1.2*cm, RECIBO_ANCHO - 1.4*cm, 1.1*cm, 
                0.25*cm, stroke=1, fill=1)
    
    # ===== GRID DE DATOS =====
    c.setFillColor(COLOR_TEXTO)
    c.setFont("Helvetica-Bold", 7.5)
    
    col1 = 1*cm
    col2 = 6.5*cm
    col3 = 12*cm
    col4 = 17.5*cm
    
    row_y = y_pos - 0.35*cm
    
    # FILA 1
    c.drawString(col1, row_y, f"NO. RECIBO: {recibo['folio']}")
    c.drawString(col2, row_y, f"No. Lote: {recibo['numero_lote']}")
    c.drawString(col3, row_y, f"No. Riego: {recibo['numero_riego']}")
    c.drawString(col4, row_y, f"Barrio: {recibo['barrio']}")
    
    row_y -= 0.35*cm
    
    # FILA 2
    col1_fila2 = 1*cm
    col2_fila2 = 8.5*cm
    col3_fila2 = 16*cm
    
    c.drawString(col1_fila2, row_y, f"Cultivo: {recibo['cultivo']}")
    c.drawString(col2_fila2, row_y, f"Superficie: {recibo['superficie']} ha")
    c.drawString(col3_fila2, row_y, f"Ciclo: {recibo['ciclo']}")
    
    # ===== RECIBÍ DE (TODAVÍA MÁS ABAJO) =====
    y_pos = row_y - 0.75*cm  # ⬅️ AUMENTADO DE 0.65 A 0.75
    c.setFillColor(COLOR_TEXTO_GRIS)
    c.setFont("Helvetica", 7.5)
    c.drawString(0.8*cm, y_pos, "Recibí de:")
    
    c.setFillColor(COLOR_TEXTO)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(2.2*cm, y_pos, recibo['nombre'])
    
    # ===== CONCEPTO =====
    y_pos -= 0.35*cm
    c.setStrokeColor(COLOR_BEIGE_OSCURO)
    c.line(0.8*cm, y_pos, RECIBO_ANCHO - 0.8*cm, y_pos)
    
    y_pos -= 0.23*cm
    c.setFillColor(COLOR_TEXTO_GRIS)
    c.setFont("Helvetica", 7)
    c.drawString(0.8*cm, y_pos, "Concepto: Pago de cuota de riego para el ciclo agrícola")
    
    # ===== TOTAL + MONTO =====
    y_pos -= 0.35*cm
    
    c.setFillColor(COLOR_TEXTO)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(0.8*cm, y_pos, "TOTAL")
    
    # Caja del monto
    monto_x = RECIBO_ANCHO - 5*cm
    c.setFillColor(colors.white)
    c.setStrokeColor(COLOR_VERDE)
    c.setLineWidth(1.5)
    c.roundRect(monto_x, y_pos - 0.3*cm, 4.2*cm, 0.65*cm, 
                0.25*cm, stroke=1, fill=1)
    
    c.setFillColor(COLOR_TEXTO_GRIS)
    c.setFont("Helvetica", 6)
    c.drawString(monto_x + 0.2*cm, y_pos + 0.1*cm, "(pago en efectivo)")
    
    c.setFillColor(COLOR_TEXTO)
    c.setFont("Helvetica-Bold", 13)
    c.drawRightString(monto_x + 4*cm, y_pos - 0.1*cm, f"${recibo['costo']:.2f}")
    
    # ===== FOOTER =====
    y_pos -= 0.7*cm
    c.setStrokeColor(COLOR_BEIGE_OSCURO)
    c.setLineWidth(0.5)
    c.line(0.8*cm, y_pos, RECIBO_ANCHO - 0.8*cm, y_pos)
    
    y_pos -= 0.25*cm
    c.setFillColor(COLOR_TEXTO_GRIS)
    c.setFont("Helvetica", 7)
    
    fecha_obj = datetime.strptime(recibo['fecha'], '%Y-%m-%d')
    c.drawString(0.8*cm, y_pos, 
                f"C. Juan Aldama #25, Col. Centro, Tezontepec de Aldama. Fecha: {fecha_obj.strftime('%d/%m/%Y')}")
    
    y_pos -= 0.22*cm
    hora_obj = datetime.strptime(recibo['hora'], '%H:%M:%S')
    am_pm = "p.m." if hora_obj.hour >= 12 else "a.m."
    hora_12 = hora_obj.hour if hora_obj.hour <= 12 else hora_obj.hour - 12
    if hora_12 == 0:
        hora_12 = 12
    
    c.drawString(0.8*cm, y_pos, f"Hora: {hora_12:02d}:{hora_obj.minute:02d}:{hora_obj.second:02d} {am_pm}")
    
    # Firma
    c.drawRightString(RECIBO_ANCHO - 0.8*cm, y_pos + 0.22*cm, "Firma Recaudador")
    c.line(RECIBO_ANCHO - 4*cm, y_pos + 0.12*cm, RECIBO_ANCHO - 0.8*cm, y_pos + 0.12*cm)
    
    # ===== LEYENDA LEGAL =====
    y_pos -= 0.35*cm
    c.setFont("Helvetica", 5.5)
    
    c.drawString(0.7*cm, y_pos, 
                "Este recibo ampara el pago de cuota ordinaria destinada exclusivamente al mantenimiento y operación del módulo de riego, conforme al régimen fiscal")
    y_pos -= 0.17*cm
    c.drawString(0.7*cm, y_pos,
                "de personas morales con fines no lucrativos. Exento de IVA y de ISR conforme a los artículos 79 y 80 de la Ley del ISR y al artículo 15, fracción XII de la Ley del IVA.")
    
    c.save()
    print(f"✅ Recibo con nombre más bajo: {ruta_salida}")
    return ruta_salida


if __name__ == "__main__":
    ruta = dibujar_recibo_nombre_mas_bajo()
    
    import platform, subprocess
    try:
        if platform.system() == 'Darwin':
            subprocess.run(['open', ruta])
        elif platform.system() == 'Windows':
            os.startfile(ruta)
        else:
            subprocess.run(['xdg-open', ruta])
    except:
        print(f"Abre: {ruta}")
