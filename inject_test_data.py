# inject_test_data.py
# -------------------------------------------------
# Inyección de datos de prueba en database/riego.db
# -------------------------------------------------
# Este script **no crea** nuevos campesinos ni siembras.
# Actualiza los registros existentes (≈ 1224) para que el
# mapa de calor por riegos muestre "manchones" de parcelas
# contiguas con valores de riego entre 0 y 6.

import random
from datetime import datetime

from modules.models import get_connection, init_db

# -------------------------------------------------
# Configuración del dataset de prueba
# -------------------------------------------------
MAX_RIEGOS = 6                     # Valor máximo que mostrará el mapa
CULTIVOS = ['MAÍZ', 'FRIJOL', 'FRIJOL EJOTERO','TRIGO', 'SORGO', 'ALFALFA', 'CHILE', 'TOMATE', 'CEBOLLA', 'AJO', 'NABO' ,'AVENA','HABA','CALABAZA','CEBADA','ARBOL FRUTAL','PASTO','BROCOLI','COLIFLOR']

def chunked(iterable, size):
    """Divide una lista en trozos de *size* elementos."""
    for i in range(0, len(iterable), size):
        yield iterable[i:i + size]

def main():
    # Aseguramos que la BD exista
    init_db()
    conn = get_connection()
    cur = conn.cursor()

    # -------------------------------------------------
    # 1️⃣  Obtener todos los campesinos ordenados por lote
    # -------------------------------------------------
    cur.execute("SELECT id, numero_lote FROM campesinos WHERE activo = 1 ORDER BY CAST(numero_lote AS INTEGER)")
    campesinos = cur.fetchall()
    if not campesinos:
        print("⚠️  No hay campesinos para actualizar.")
        conn.close()
        return

    # -------------------------------------------------
    # 2️⃣  Actualizar siembras en bloques contiguos
    # -------------------------------------------------
    # Definimos el tamaño del bloque (manchón). 5 parcelas = 1 bloque.
    bloque_tamano = 5
    for bloque in chunked(campesinos, bloque_tamano):
        # Elegimos un número de riegos y un cultivo para todo el bloque
        riego_val = random.randint(0, MAX_RIEGOS)
        cultivo_val = random.choice(CULTIVOS)
        for row in bloque:
            cid = row["id"]
            # Buscamos la siembra asociada (asumimos una por campesino)
            cur.execute("SELECT id FROM siembras WHERE campesino_id = ?", (cid,))
            siembra = cur.fetchone()
            if siembra:
                siembra_id = siembra["id"]
                cur.execute(
                    """
                    UPDATE siembras
                    SET numero_riegos = ?, cultivo = ?, activa = 1
                    WHERE id = ?
                    """,
                    (riego_val, cultivo_val, siembra_id),
                )
            else:
                # Si no existe siembra, la creamos con los valores aleatorios
                cur.execute(
                    """
                    INSERT INTO siembras (campesino_id, cultivo, numero_riegos, ciclo, activa)
                    VALUES (?, ?, ?, ?, 1)
                    """,
                    (cid, cultivo_val, riego_val, "OCTUBRE 2025"),
                )
    conn.commit()
    conn.close()
    print(f"✅  Actualizados {len(campesinos)} campesinos con riegos 0‑{MAX_RIEGOS} y cultivos aleatorios.")

if __name__ == "__main__":
    main()
