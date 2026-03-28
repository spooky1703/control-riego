#!/usr/bin/env python3
"""
🗺️ Extractor de Geometría DXF → JSON
Convierte SECCION 4.dxf en un archivo JSON ligero con toda la geometría
y etiquetas de lotes. Solo se ejecuta UNA VEZ.

Uso: python3 extraer_mapa.py
"""
import ezdxf
import json
import re
import os
import sys
import time

# Rutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DXF_PATH = os.path.join(BASE_DIR, 'SECCION 4.dxf')
JSON_PATH = os.path.join(BASE_DIR, 'database', 'mapa_geometria.json')


def convertir_lote_id(raw_id: str) -> str:
    """Convierte IDs del DXF al formato de la BD (52xxx→xxx, 53xxx→1xxx)."""
    if not raw_id or not raw_id.isdigit():
        return raw_id
    if raw_id.startswith('52') and len(raw_id) == 5:
        return str(int(raw_id[2:]))
    elif raw_id.startswith('53') and len(raw_id) == 5:
        return '1' + raw_id[2:]
    elif raw_id.startswith('552') and len(raw_id) == 6:
        return str(int(raw_id[3:]))
    return raw_id

def extraer_geometria():
    """Extrae polilíneas y textos del DXF y los guarda como JSON."""
    
    if not os.path.exists(DXF_PATH):
        print(f"❌ No se encontró: {DXF_PATH}")
        print("   Convierte SECCION 4.dwg a .dxf primero.")
        sys.exit(1)
    
    print(f"📂 Leyendo: {DXF_PATH}")
    t0 = time.time()
    doc = ezdxf.readfile(DXF_PATH)
    msp = doc.modelspace()
    print(f"   Cargado en {time.time()-t0:.1f}s")
    
    # ── Extraer textos (números de lote) de la capa 'cuentas' ──
    print("📝 Extrayendo etiquetas de lotes...")
    textos = []
    for entity in msp:
        layer = entity.dxf.layer
        dtype = entity.dxftype()
        
        if layer == 'cuentas':
            if dtype == 'MTEXT':
                raw = entity.text.strip()
                # Limpiar códigos de formato DXF: {\fArial|b0|i0|...; texto}
                clean = re.sub(r'\\f[^;]*;', '', raw)
                clean = re.sub(r'\\[a-zA-Z][0-9.]*', '', clean)
                clean = clean.replace('{', '').replace('}', '').replace('\\P', '\n').strip()
                if clean:
                    pos = entity.dxf.insert
                    textos.append({
                        'text': clean,
                        'x': round(pos[0], 2),
                        'y': round(pos[1], 2)
                    })
            elif dtype == 'TEXT':
                raw = entity.dxf.text.strip()
                if raw:
                    pos = entity.dxf.insert
                    textos.append({
                        'text': raw,
                        'x': round(pos[0], 2),
                        'y': round(pos[1], 2)
                    })
    
    print(f"   {len(textos)} etiquetas encontradas")
    
    # ── Extraer polilíneas (parcelas) de la capa 'parcelas' ──
    print("📐 Extrayendo geometría de parcelas...")
    parcelas = []
    for entity in msp:
        if entity.dxftype() == 'LWPOLYLINE' and entity.dxf.layer == 'parcelas':
            pts = [(round(p[0], 2), round(p[1], 2)) for p in entity.get_points()]
            if len(pts) >= 3:
                cx = round(sum(p[0] for p in pts) / len(pts), 2)
                cy = round(sum(p[1] for p in pts) / len(pts), 2)
                parcelas.append({
                    'coords': pts,
                    'centroid': [cx, cy],
                    'closed': entity.is_closed,
                })
    
    print(f"   {len(parcelas)} parcelas encontradas")
    
    # ── Asociar cada texto al polígono que lo contiene ──
    print("🔗 Asociando etiquetas a parcelas...")
    from matplotlib.path import Path
    
    asociados = 0
    no_asociados = 0
    
    for parcela in parcelas:
        coords = parcela['coords']
        # Crear path cerrado
        path = Path(coords + [coords[0]])
        
        # Buscar texto DENTRO del polígono
        mejor_texto = None
        mejor_dist = float('inf')
        
        for txt in textos:
            punto = (txt['x'], txt['y'])
            if path.contains_point(punto):
                # Si hay múltiples, usar el más cercano al centroide
                cx, cy = parcela['centroid']
                dist = ((txt['x'] - cx)**2 + (txt['y'] - cy)**2)**0.5
                if dist < mejor_dist:
                    mejor_dist = dist
                    mejor_texto = txt['text']
        
        if mejor_texto is None:
            # Fallback: texto más cercano al centroide
            cx, cy = parcela['centroid']
            for txt in textos:
                dist = ((txt['x'] - cx)**2 + (txt['y'] - cy)**2)**0.5
                if dist < mejor_dist:
                    mejor_dist = dist
                    mejor_texto = txt['text']
        
        if mejor_texto:
            parcela['lote_id'] = convertir_lote_id(mejor_texto)
            asociados += 1
        else:
            parcela['lote_id'] = None
            no_asociados += 1
    
    print(f"   ✅ {asociados} asociados, ⚠️  {no_asociados} sin etiqueta")
    
    # ── Guardar JSON ──
    output = {
        'parcelas': parcelas,
        'textos': textos,
        'stats': {
            'total_parcelas': len(parcelas),
            'total_textos': len(textos),
            'asociados': asociados,
            'sin_etiqueta': no_asociados,
        }
    }
    
    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False)
    
    size_kb = os.path.getsize(JSON_PATH) / 1024
    print(f"\n✅ Guardado: {JSON_PATH} ({size_kb:.0f} KB)")
    print(f"   {len(parcelas)} parcelas con geometría")
    
    # Análisis rápido de IDs
    ids = [p['lote_id'] for p in parcelas if p['lote_id']]
    numeric_ids = sorted(set(int(i) for i in ids if i.isdigit()))
    if numeric_ids:
        print(f"   Rango de IDs numéricos: {min(numeric_ids)} → {max(numeric_ids)}")
        print(f"   IDs únicos: {len(numeric_ids)}")

if __name__ == '__main__':
    extraer_geometria()
