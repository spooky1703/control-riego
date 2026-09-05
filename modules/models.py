# modules/models.py - Modelos de Base de Datos
# Definición de tablas SQLite y funciones CRUD
import sqlite3
import os
import json
import pandas as pd
import chardet
from datetime import datetime
from typing import Optional, List, Dict, Tuple
from modules.cuotas import actualizar_datos_campesino_en_cuotas
# Ruta de la base de datos
DB_PATH = os.path.join('database', 'riego.db')
def get_connection():
    """Obtiene una conexión a la base de datos con mejor manejo de timeouts"""
    os.makedirs('database', exist_ok=True)
    
    # Crear conexión con timeout más alto y modo journal
    conn = sqlite3.connect(DB_PATH, timeout=10.0, check_same_thread=False)  # Thread-safe
    conn.row_factory = sqlite3.Row
    
    # IMPORTANTE: Autocommit mode para evitar deadlocks.
    # Sin esto, funciones como eliminar_recibo() que llaman a registrar_auditoria()
    # (que abre su propia conexión) causan "database is locked" porque la primera
    # conexión mantiene un lock de escritura mientras la segunda intenta escribir.
    conn.isolation_level = None
    conn.execute("PRAGMA journal_mode = WAL")  # Write-Ahead Logging
    conn.execute("PRAGMA busy_timeout = 10000")  # 10 segundos en modo busy
    conn.execute("PRAGMA synchronous = NORMAL")  # Mejor rendimiento
    
    return conn

def init_db():
    """Inicializa la base de datos con todas las tablas necesarias"""
    conn = get_connection()
    cursor = conn.cursor()
    # Tabla campesinos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS campesinos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_lote TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL,
            localidad TEXT NOT NULL,
            barrio TEXT NOT NULL,
            superficie REAL NOT NULL CHECK(superficie > 0),
            extension_tierra TEXT,
            activo BOOLEAN DEFAULT 1,
            fecha_registro TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Tabla siembras
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS siembras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campesino_id INTEGER NOT NULL,
            cultivo TEXT NOT NULL,
            numero_riegos INTEGER DEFAULT 0,
            ciclo TEXT NOT NULL,
            fecha_inicio TEXT DEFAULT CURRENT_DATE,
            fecha_fin TEXT,
            activa BOOLEAN DEFAULT 1,
            FOREIGN KEY (campesino_id) REFERENCES campesinos(id)
        )
    ''')
    # Tabla recibos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recibos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folio INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            hora TEXT NOT NULL,
            campesino_id INTEGER NOT NULL,
            siembra_id INTEGER NOT NULL,
            cultivo TEXT NOT NULL,
            numero_riego INTEGER NOT NULL,
            tipo_accion TEXT NOT NULL,
            costo REAL NOT NULL,
            ciclo TEXT NOT NULL,
            eliminado BOOLEAN DEFAULT 0,
            fecha_eliminacion TEXT,
            motivo_eliminacion TEXT,
            FOREIGN KEY (campesino_id) REFERENCES campesinos(id),
            FOREIGN KEY (siembra_id) REFERENCES siembras(id)
        )
    ''')
    # Tabla configuracion
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS configuracion (
            clave TEXT PRIMARY KEY,
            valor TEXT NOT NULL
        )
    ''')
    # Tabla auditoria
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS auditoria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_hora TEXT DEFAULT CURRENT_TIMESTAMP,
            tipo_evento TEXT NOT NULL,
            usuario TEXT DEFAULT 'Sistema',
            descripcion TEXT NOT NULL,
            datos_previos TEXT
        )
    ''')
    # Crear índices
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_campesino_lote ON campesinos(numero_lote)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_campesino_nombre ON campesinos(nombre)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_recibo_fecha ON recibos(fecha)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_recibo_folio ON recibos(folio)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_siembra_activa ON siembras(activa)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_siembra_campesino ON siembras(campesino_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_recibo_eliminado ON recibos(eliminado)')
    # Insertar configuración por defecto
    configuracion_default = {
        'folio_actual': '1',
        'ciclo_actual': 'OCTUBRE 2025',
        'nombre_oficina': 'ASOCIACIÓN DE CAMPESINOS DE BOMBEO Y REBOMBEO DEL CERRO DEL XICUCO',
        'tarifa_hectarea': '450',
        'ubicacion': 'Tezontepec de Aldama, Hgo.',
        'fecha_ultimo_cierre': '',
        'impresora_predeterminada': '',
        'margen_superior': '5'
    }
    for clave, valor in configuracion_default.items():
        cursor.execute('''
            INSERT OR IGNORE INTO configuracion (clave, valor) 
            VALUES (?, ?)
        ''', (clave, valor))
    conn.commit()
    conn.close()
    print("Base de datos inicializada correctamente")
    print(""" 
                 █████╗ ██╗      ██████╗ ███╗   ██╗███████╗ ██████╗      ██████╗ ██████╗ ██████╗ ██╗███╗   ██╗ ██████╗ 
                ██╔══██╗██║     ██╔═══██╗████╗  ██║██╔════╝██╔═══██╗    ██╔════╝██╔═══██╗██╔══██╗██║████╗  ██║██╔════╝ 
                ███████║██║     ██║   ██║██╔██╗ ██║███████╗██║   ██║    ██║     ██║   ██║██║  ██║██║██╔██╗ ██║██║  ███╗
                ██╔══██║██║     ██║   ██║██║╚██╗██║╚════██║██║   ██║    ██║     ██║   ██║██║  ██║██║██║╚██╗██║██║   ██║
                ██║  ██║███████╗╚██████╔╝██║ ╚████║███████║╚██████╔╝    ╚██████╗╚██████╔╝██████╔╝██║██║ ╚████║╚██████╔╝
                ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═══╝╚══════╝ ╚═════╝      ╚═════╝ ╚═════╝ ╚═════╝ ╚═╝╚═╝  ╚═══╝ ╚═════╝                                                                  
                """)

# ==================== FUNCIONES DE CAMPESINOS ====================
def reparar_lotes_flotantes():
    """Corrige lotes importados como flotantes por Pandas (ex: '25.0' -> '25')"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, numero_lote FROM campesinos WHERE numero_lote LIKE '%.0'")
        for row in cursor.fetchall():
            nuevo_lote = row['numero_lote'][:-2]
            cursor.execute("UPDATE campesinos SET numero_lote = ? WHERE id = ?", (nuevo_lote, row['id']))
        conn.commit()
    except Exception as e:
        print(f"Error reparando lotes: {e}")
    finally:
        conn.close()

def revertir_alfalfa_vieja():
    """Restaura ALFALFA VIEJA de regreso a ALFALFA original en caso de que se haya migrado accidentalmente."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE siembras SET cultivo = 'ALFALFA' WHERE cultivo = 'ALFALFA VIEJA'")
        conn.commit()
    except Exception as e:
        print(f"Error revirtiendo alfalfa: {e}")
    finally:
        conn.close()

def actualizar_cultivo_siembra(campesino_id: int, nuevo_cultivo: str) -> bool:
    """Actualiza el nombre del cultivo de la siembra activa sin modificar sus fechas."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE siembras 
            SET cultivo = ? 
            WHERE campesino_id = ? AND activa = 1
        ''', (nuevo_cultivo, campesino_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error actualizando cultivo: {e}")
        return False
    finally:
        conn.close()

def buscar_campesino(termino: str) -> List[Dict]:
    """
    Busca campesinos de forma INTELIGENTE:
    - Si es número puro (ej: 1, 5, 10): búsqueda EXACTA por lote
    - Si tiene letras: búsqueda PARCIAL por nombre o lote
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Limpiar el término
    termino = termino.strip()
    
    # DETECTAR SI ES SOLO NÚMEROS
    es_numero_puro = termino.isdigit()
    
    if es_numero_puro:
        # ✅ BÚSQUEDA EXACTA por lote (sin LIKE)
        try:
            cursor.execute('''
                SELECT * FROM campesinos
                WHERE numero_lote = ? AND activo = 1
                ORDER BY numero_lote
            ''', (termino,))
        except:
            conn.close()
            return []
    else:
        # ✅ BÚSQUEDA PARCIAL (contiene letras)
        termino_busqueda = f"%{termino}%"
        cursor.execute('''
            SELECT * FROM campesinos
            WHERE (nombre LIKE ? OR numero_lote LIKE ?)
            AND activo = 1
            ORDER BY nombre, numero_lote
        ''', (termino_busqueda, termino_busqueda))
    
    resultados = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return resultados

def obtener_campesino_por_id(campesino_id: int) -> Optional[Dict]:
    """Obtiene un campesino por su ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM campesinos WHERE id = ?', (campesino_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def obtener_campesino_por_lote(lote: str) -> Optional[Dict]:
    """Obtiene un campesino por su número de lote"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM campesinos WHERE numero_lote = ?', (lote,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def crear_campesino(datos: Dict) -> int:
    """Crea un nuevo campesino"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO campesinos 
            (numero_lote, nombre, localidad, barrio, superficie, extension_tierra)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            datos['numero_lote'],
            datos['nombre'],
            datos['localidad'],
            datos['barrio'],
            datos['superficie'],
            datos.get('extension_tierra', '')
        ))
        campesino_id = cursor.lastrowid
        conn.commit()
    except sqlite3.IntegrityError:
        raise ValueError(f"El lote {datos['numero_lote']} ya existe")
    finally:
        conn.close()
        
    # Auditoría DESPUÉS de cerrar la conexión para evitar locks anidados
    registrar_auditoria(
        'CREAR_CAMPESINO',
        f"Nuevo campesino registrado: {datos['nombre']} (Lote: {datos['numero_lote']})",
        None
    )
    return campesino_id

def actualizar_campesino(campesino_id: int, datos: Dict) -> bool:
    """Actualiza los datos de un campesino"""
    datos_previos = obtener_campesino_por_id(campesino_id)
    if 'superficie' in datos and datos['superficie'] != datos_previos['superficie']:
        siembra_activa = obtener_siembra_activa(campesino_id)
        if siembra_activa:
            raise ValueError("No se puede cambiar la superficie con siembra activa")
            
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        campos_actualizar = []
        valores = []
        campos_permitidos = ['nombre', 'localidad', 'barrio', 'superficie', 'extension_tierra']
        for campo in campos_permitidos:
            if campo in datos:
                campos_actualizar.append(f"{campo} = ?")
                valores.append(datos[campo])
        if not campos_actualizar:
            return False
            
        valores.append(campesino_id)
        query = f"UPDATE campesinos SET {', '.join(campos_actualizar)} WHERE id = ?"
        cursor.execute(query, valores)
        conn.commit()
    finally:
        conn.close()
        
    # Auditoría y sincronización DESPUÉS de cerrar la conexión principal
    registrar_auditoria(
        'EDITAR_CAMPESINO',
        f"Campesino actualizado: {datos_previos['nombre']} (ID: {campesino_id})",
        json.dumps(datos_previos)
    )
    try:
        actualizar_datos_campesino_en_cuotas(campesino_id, datos)
    except Exception as e:
        print(f"Advertencia: No se pudo sincronizar con cuotas.db: {e}")
        
    return True

def eliminar_campesino(campesino_id: int) -> bool:
    """Eliminación lógica de un campesino"""
    import time
    
    siembra_activa = obtener_siembra_activa(campesino_id)
    if siembra_activa:
        raise ValueError("No se puede eliminar un campesino con siembra activa")
        
    datos_previos = obtener_campesino_por_id(campesino_id)
    nuevo_lote = f"{datos_previos['numero_lote']}_ELIMINADO_{int(time.time())}"
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Renombramos el lote para liberar el número original (por el constraint UNIQUE)
        cursor.execute('UPDATE campesinos SET activo = 0, numero_lote = ? WHERE id = ?', (nuevo_lote, campesino_id))
        conn.commit()
    finally:
        conn.close()
        
    # Sincronizar el renombre con la base de datos de cuotas para que el historial refleje la eliminación
    try:
        actualizar_datos_campesino_en_cuotas(campesino_id, {"numero_lote": nuevo_lote})
    except Exception as e:
        print(f"Advertencia: No se pudo actualizar el historial de cuotas: {e}")
        
    registrar_auditoria(
        'ELIMINAR_CAMPESINO',
        f"Campesino eliminado: {datos_previos['nombre']} (Lote original: {datos_previos['numero_lote']})",
        json.dumps(datos_previos)
    )
    return True

def obtener_todos_campesinos() -> List[Dict]:
    """Obtiene todos los campesinos activos"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM campesinos 
        WHERE activo = 1 
        ORDER BY nombre
    ''')
    resultados = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return resultados

def contar_campesinos() -> int:
    """Cuenta el número de campesinos activos"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM campesinos WHERE activo = 1')
    count = cursor.fetchone()[0]
    conn.close()
    return count

# ==================== FUNCIONES DE SIEMBRAS ====================

def obtener_siembra_activa(campesino_id: int) -> Optional[Dict]:
    """Obtiene la siembra activa de un campesino"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM siembras 
        WHERE campesino_id = ? AND activa = 1
        ORDER BY fecha_inicio DESC
        LIMIT 1
    ''', (campesino_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def obtener_historial_siembras(campesino_id: int) -> List[Dict]:
    """Obtiene el historial completo de siembras de un campesino"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM siembras 
        WHERE campesino_id = ?
        ORDER BY fecha_inicio DESC
    ''', (campesino_id,))
    resultados = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return resultados

def crear_siembra(campesino_id: int, cultivo: str, ciclo: str) -> int:
    """Crea una nueva siembra"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO siembras 
        (campesino_id, cultivo, numero_riegos, ciclo, fecha_inicio, activa)
        VALUES (?, ?, 0, ?, date('now'), 1)
    ''', (campesino_id, cultivo, ciclo))
    siembra_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return siembra_id

def actualizar_siembra(siembra_id: int, datos: Dict) -> bool:
    """
    Actualiza datos de una siembra en la base de datos
    IMPORTANTE: Ahora incluye COMMIT para guardar cambios
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Construir dinámicamente la consulta UPDATE
        campos = []
        valores = []
        
        if 'cultivo' in datos:
            campos.append('cultivo = ?')
            valores.append(datos['cultivo'])
        
        if 'ciclo' in datos:
            campos.append('ciclo = ?')
            valores.append(datos['ciclo'])
        
        if 'fecha_inicio' in datos:
            campos.append('fecha_inicio = ?')
            valores.append(datos['fecha_inicio'])
        
        if 'fecha_fin' in datos:
            campos.append('fecha_fin = ?')
            valores.append(datos['fecha_fin'])
        
        if 'numero_riegos' in datos:
            campos.append('numero_riegos = ?')
            valores.append(datos['numero_riegos'])
        
        if 'activa' in datos:
            campos.append('activa = ?')
            valores.append(datos['activa'])
        
        # Si no hay campos para actualizar, retornar False
        if not campos:
            return False
        
        # Agregar el ID al final de los valores
        valores.append(siembra_id)
        
        # Ejecutar UPDATE
        sql = f"UPDATE siembras SET {', '.join(campos)} WHERE id = ?"
        cursor.execute(sql, valores)
        
        # CRÍTICO: Hacer COMMIT para guardar los cambios en la BD
        conn.commit()
        
        # Verificar si se actualizó alguna fila
        return cursor.rowcount > 0
    
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error al actualizar siembra: {e}")
        raise
    
    finally:
        if conn:
            conn.close()

def eliminar_siembra(siembra_id: int) -> bool:
    """Elimina una siembra (marca como inactiva)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE siembras 
            SET activa = 0
            WHERE id = ?
        """, (siembra_id,))
        
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def obtener_siembra_por_id(siembra_id: int) -> Optional[Dict]:
    """Obtiene una siembra por su ID"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM siembras WHERE id = ?
    """, (siembra_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None

def obtener_todas_las_siembras() -> List[Dict]:
    """Obtiene todas las siembras (activas e inactivas)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM siembras ORDER BY fecha_inicio DESC')
    resultados = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return resultados

def cerrar_siembra(siembra_id: int):
    """Marca una siembra como finalizada"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE siembras 
        SET activa = 0, fecha_fin = date('now')
        WHERE id = ?
    ''', (siembra_id,))
    conn.commit()
    conn.close()

def incrementar_riegos(siembra_id: int):
    """Incrementa el contador de riegos de una siembra"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE siembras 
        SET numero_riegos = numero_riegos + 1
        WHERE id = ?
    ''', (siembra_id,))
    conn.commit()
    conn.close()

def decrementar_riegos(siembra_id: int) -> bool:
    """Decrementa en 1 el número de riegos de una siembra"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE siembras 
            SET numero_riegos = numero_riegos - 1
            WHERE id = ? AND numero_riegos > 0
        """, (siembra_id,))
        
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

# ==================== FUNCIONES DE RECIBOS ====================

def crear_recibo(datos: Dict) -> int:
    """Crea un nuevo recibo"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO recibos 
        (folio, fecha, hora, campesino_id, siembra_id, cultivo, numero_riego, 
         tipo_accion, costo, ciclo, cargo_documentos, eliminado)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
    ''', (
        datos['folio'],
        datos['fecha'],
        datos['hora'],
        datos['campesino_id'],
        datos['siembra_id'],
        datos['cultivo'],
        datos['numero_riego'],
        datos['tipo_accion'],
        datos['costo'],
        datos['ciclo'],
        datos.get('cargo_documentos', 0)
    ))
    recibo_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return recibo_id

def obtener_recibos_dia(fecha: str) -> List[Dict]:
    """Obtiene todos los recibos de un día (no eliminados)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT r.*, c.nombre, c.numero_lote, c.localidad, c.barrio, c.superficie
        FROM recibos r
        JOIN campesinos c ON r.campesino_id = c.id
        WHERE r.fecha = ? AND r.eliminado = 0
        ORDER BY r.hora
    ''', (fecha,))
    resultados = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return resultados

def obtener_recibo_por_id(recibo_id: int) -> Optional[Dict]:
    """Obtiene un recibo por su ID con todos los datos"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT r.*, c.nombre, c.numero_lote, c.localidad, c.barrio, c.superficie
        FROM recibos r
        JOIN campesinos c ON r.campesino_id = c.id
        WHERE r.id = ?
    ''', (recibo_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def eliminar_recibo(recibo_id: int, motivo: str = ""):
    """Marca un recibo como eliminado"""
    recibo = obtener_recibo_por_id(recibo_id)
    if not recibo:
        raise ValueError("Recibo no encontrado")
        
    conn = get_connection()
    cursor = conn.cursor()
        
    try:
        cursor.execute('''
            UPDATE recibos 
            SET eliminado = 1, 
                fecha_eliminacion = datetime('now'),
                motivo_eliminacion = ?
            WHERE id = ?
        ''', (motivo, recibo_id))
        conn.commit()
    finally:
        conn.close()
        
    registrar_auditoria(
        'ELIMINAR_RECIBO',
        f"Recibo eliminado: Folio {recibo['folio']} - {recibo['nombre']} - ${recibo['costo']:.2f}",
        json.dumps(recibo, default=str)
    )

def eliminar_recibo_db(recibo_id: int, motivo: str = ""):
    """
    Elimina un recibo de la base de datos (marcándolo como eliminado).
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Obtener datos previos para auditoría
        cursor.execute("SELECT * FROM recibos WHERE id = ?", (recibo_id,))
        recibo_previo = cursor.fetchone()
        if not recibo_previo:
            raise ValueError("Recibo no encontrado para eliminar")

        # Marcar como eliminado en lugar de borrar físicamente
        cursor.execute("UPDATE recibos SET eliminado = 1, motivo_eliminacion = ? WHERE id = ?", (motivo, recibo_id))
        conn.commit()

        # Registrar en auditoría DESPUÉS del commit
        detalles_auditoria = json.dumps({
            "motivo_eliminacion": motivo,
            "datos_previos": dict(recibo_previo)
        })
        registrar_auditoria('ELIMINAR_RECIBO', f"Recibo eliminado: Folio {recibo_previo['folio']}", detalles_auditoria)
    finally:
        conn.close()

def obtener_recibos_campesino(campesino_id: int) -> List[Dict]:
    """Obtiene todos los recibos de un campesino"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM recibos 
        WHERE campesino_id = ? AND eliminado = 0
        ORDER BY fecha DESC, hora DESC
    ''', (campesino_id,))
    resultados = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return resultados

def obtener_todos_los_recibos() -> List[Dict]:
    """Obtiene todos los recibos (activos e inactivos)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT r.*, c.nombre, c.numero_lote, c.localidad, c.barrio, c.superficie
        FROM recibos r
        JOIN campesinos c ON r.campesino_id = c.id
        ORDER BY r.fecha DESC, r.hora DESC
    ''')
    resultados = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return resultados

def actualizar_recibo(recibo_id: int, nuevos_datos: Dict) -> bool:
    """Actualiza los datos de un recibo (menos folio, fecha, hora, campesino_id, siembra_id)"""
    conn = get_connection()
    cursor = conn.cursor()
    datos_previos = obtener_recibo_por_id(recibo_id)
    try:
        campos_actualizar = []
        valores = []
        campos_permitidos = ['cultivo', 'numero_riego', 'tipo_accion', 'costo', 'ciclo', 'eliminado']
        for campo in campos_permitidos:
            if campo in nuevos_datos:
                campos_actualizar.append(f"{campo} = ?")
                valores.append(nuevos_datos[campo])
        if not campos_actualizar:
            conn.close()
            return False
        valores.append(recibo_id)
        query = f"UPDATE recibos SET {', '.join(campos_actualizar)} WHERE id = ?"
        cursor.execute(query, valores)
        conn.commit()
        registrar_auditoria(
            'EDITAR_RECIBO',
            f"Recibo actualizado: Folio {datos_previos['folio']}",
            json.dumps(datos_previos)
        )
        return True
    finally:
        conn.close()

# ==================== FUNCIONES DE CONFIGURACIÓN ====================

def obtener_configuracion(clave: str) -> Optional[str]:
    """Obtiene un valor de configuración"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT valor FROM configuracion WHERE clave = ?', (clave,))
    row = cursor.fetchone()
    conn.close()
    return row['valor'] if row else None

def actualizar_configuracion(clave: str, valor: str):
    """Actualiza un valor de configuración"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO configuracion (clave, valor)
            VALUES (?, ?)
        ''', (clave, valor))
        conn.commit()
    finally:
        conn.close()

def obtener_toda_configuracion() -> Dict:
    """Obtiene toda la configuración del sistema"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT clave, valor FROM configuracion')
    config = {row['clave']: row['valor'] for row in cursor.fetchall()}
    conn.close()
    return config

# ==================== FUNCIONES DE AUDITORÍA ====================

def registrar_auditoria(tipo_evento: str, descripcion: str, datos_previos: Optional[str] = None):
    """Registra un evento en la tabla de auditoría"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO auditoria (fecha_hora, tipo_evento, usuario, descripcion, datos_previos)
            VALUES (datetime('now', 'localtime'), ?, 'Sistema', ?, ?)
        ''', (tipo_evento, descripcion, datos_previos))
        conn.commit()
    finally:
        conn.close()

def obtener_auditoria(limite: int = 100) -> List[Dict]:
    """Obtiene los últimos registros de auditoría"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM auditoria 
        ORDER BY fecha_hora DESC 
        LIMIT ?
    ''', (limite,))
    resultados = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return resultados

# ==================== FUNCIÓN DE CARGA INICIAL ====================

def cargar_campesinos_desde_csv(ruta_csv: str):
    """Carga los campesinos desde el archivo CSV inicial con detección automática de encoding"""
    
    # 1. DETECTAR EL ENCODING CORRECTO
    with open(ruta_csv, 'rb') as file:
        raw_data = file.read()
        detected = chardet.detect(raw_data)
        encoding_detectado = detected['encoding']
        confianza = detected['confidence']
    
    print(f"Encoding detectado: {encoding_detectado} (Confianza: {confianza:.2%})")
    
    # 2. LEER EL CSV CON EL ENCODING CORRECTO
    try:
        df_raw = pd.read_csv(ruta_csv, encoding=encoding_detectado, header=None)
    except Exception as e:
        print(f"Error con encoding {encoding_detectado}, intentando UTF-8...")
        df_raw = pd.read_csv(ruta_csv, encoding='utf-8', header=None)
    
    barrios_ordenados = [
        ('PANUAYA', 0, 201),
        ('TEZONTEPEC', 201, 367),
        ('ATENGO', 367, 512),
        ('MANGAS', 512, 737),
        ('PRESAS', 737, 998),
        ('HUITEL', 998, len(df_raw))
    ]
    
    conn = get_connection()
    cursor = conn.cursor()
    total_cargados = 0
    errores = []
    
    try:
        for barrio, inicio, fin in barrios_ordenados:
            for idx in range(inicio + 2, fin):
                try:
                    row = df_raw.iloc[idx]
                    lote = str(row[1]).strip()
                    if lote.endswith('.0'):
                        lote = lote[:-2]
                    nombre = str(row[2]).strip()
                    superficie = str(row[3]).strip()
                    
                    if lote == 'nan' or nombre == 'nan' or lote == '' or nombre == '':
                        continue
                    
                    sup_valor = float(superficie)
                    
                    cursor.execute('''
                        INSERT OR IGNORE INTO campesinos 
                        (numero_lote, nombre, localidad, barrio, superficie, activo)
                        VALUES (?, ?, ?, ?, ?, 1)
                    ''', (lote, nombre, 'Tezontepec de Aldama', barrio, sup_valor))
                    
                    if cursor.rowcount > 0:
                        total_cargados += 1
                        
                except Exception as e:
                    errores.append(f"Fila {idx}: {str(e)}")
                    continue
        
        conn.commit()
    finally:
        conn.close()
    
    print(f"✓ Total de campesinos cargados: {total_cargados}")
    if errores:
        print(f"⚠ Errores encontrados: {len(errores)}")
        for error in errores[:5]:  # Mostrar solo los primeros 5
            print(f"  - {error}")
    
    return total_cargados

def obtener_estadisticas_generales() -> Dict:
    """
    Obtiene estadísticas generales de todos los campesinos y siembras.
    Retorna:
    - total_campesinos
    - total_hectareas
    - hectareas_sembradas
    - porcentaje_sembrado
    - siembras_por_cultivo (dict)
    - hectareas_por_cultivo (dict)
    - campesinos_sin_siembra
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Total de campesinos
    cursor.execute("SELECT COUNT(*) FROM campesinos WHERE activo = 1")
    total_campesinos = cursor.fetchone()[0]
    
    # Total de hectáreas
    cursor.execute("SELECT SUM(superficie) FROM campesinos WHERE activo = 1")
    total_hectareas = cursor.fetchone()[0] or 0
    
    # Hectáreas sembradas (con siembra activa)
    cursor.execute("""
        SELECT SUM(c.superficie) 
        FROM campesinos c
        INNER JOIN siembras s ON c.id = s.campesino_id
        WHERE s.activa = 1
    """)
    hectareas_sembradas = cursor.fetchone()[0] or 0
    
    # Porcentaje sembrado
    porcentaje_sembrado = (hectareas_sembradas / total_hectareas * 100) if total_hectareas > 0 else 0
    
    # Siembras por cultivo (cantidad)
    cursor.execute("""
        SELECT cultivo, COUNT(*) as cantidad
        FROM siembras
        WHERE activa = 1
        GROUP BY cultivo
        ORDER BY cantidad DESC
    """)
    siembras_por_cultivo = {row[0]: row[1] for row in cursor.fetchall()}
    
    # Hectáreas por cultivo
    cursor.execute("""
        SELECT s.cultivo, SUM(c.superficie) as hectareas
        FROM siembras s
        INNER JOIN campesinos c ON s.campesino_id = c.id
        WHERE s.activa = 1
        GROUP BY s.cultivo
        ORDER BY hectareas DESC
    """)
    hectareas_por_cultivo = {row[0]: row[1] for row in cursor.fetchall()}
    
    # Campesinos sin siembra
    cursor.execute("""
        SELECT COUNT(*) 
        FROM campesinos c
        LEFT JOIN siembras s ON c.id = s.campesino_id AND s.activa = 1
        WHERE s.id IS NULL AND c.activo = 1
    """)
    campesinos_sin_siembra = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'total_campesinos': total_campesinos,
        'total_hectareas': round(total_hectareas, 2),
        'hectareas_sembradas': round(hectareas_sembradas, 2),
        'hectareas_sin_sembrar': round(total_hectareas - hectareas_sembradas, 2),
        'porcentaje_sembrado': round(porcentaje_sembrado, 2),
        'siembras_por_cultivo': siembras_por_cultivo,
        'hectareas_por_cultivo': hectareas_por_cultivo,
        'campesinos_sin_siembra': campesinos_sin_siembra
    }

def obtener_estadisticas_por_cultivo(cultivo: str) -> Dict:
    """Obtiene estadísticas de un cultivo específico"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Campesinos con este cultivo
    cursor.execute("""
        SELECT COUNT(DISTINCT s.campesino_id)
        FROM siembras s
        WHERE s.cultivo = ? AND s.activa = 1
    """, (cultivo,))
    total_campesinos = cursor.fetchone()[0]
    
    # Hectáreas totales
    cursor.execute("""
        SELECT SUM(c.superficie)
        FROM siembras s
        INNER JOIN campesinos c ON s.campesino_id = c.id
        WHERE s.cultivo = ? AND s.activa = 1
    """, (cultivo,))
    total_hectareas = cursor.fetchone()[0] or 0
    
    # Riegos promedio
    cursor.execute("""
        SELECT AVG(s.numero_riegos)
        FROM siembras s
        WHERE s.cultivo = ? AND s.activa = 1
    """, (cultivo,))
    riegos_promedio = cursor.fetchone()[0] or 0
    
    # Total de riegos vendidos
    cursor.execute("""
        SELECT SUM(s.numero_riegos)
        FROM siembras s
        WHERE s.cultivo = ? AND s.activa = 1
    """, (cultivo,))
    total_riegos = cursor.fetchone()[0] or 0
    
    conn.close()
    
    return {
        'cultivo': cultivo,
        'total_campesinos': total_campesinos,
        'total_hectareas': round(total_hectareas, 2),
        'riegos_promedio': round(riegos_promedio, 1),
        'total_riegos': total_riegos
    }
    
def partir_lote(campesino_id: int, num_divisiones: int, superficies: List[float]) -> List[int]:
    """
    Parte un lote en múltiples sublotes.
    
    Args:
        campesino_id: ID del campesino original
        num_divisiones: Número de nuevos lotes a crear (no incluye el original)
        superficies: Lista con las superficies [original, sublote1, sublote2, ...]
    
    Returns:
        Lista con los IDs de los nuevos campesinos creados
        
    Ejemplo:
        Lote 803 (1.0 ha) se parte en 3:
        - 803 (original): 0.5 ha
        - 803-1: 0.25 ha
        - 803-2: 0.25 ha
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Transacción explícita: UPDATE + múltiples INSERTs deben ser atómicos
        cursor.execute("BEGIN")
        # Obtener datos del campesino original
        cursor.execute("SELECT * FROM campesinos WHERE id = ?", (campesino_id,))
        row = cursor.fetchone()
        
        if not row:
            raise ValueError("Campesino no encontrado")
        
        original = dict(row)
        
        # Validar que la suma de superficies sea igual a la original
        superficie_total = sum(superficies)
        if abs(superficie_total - original['superficie']) > 0.01:
            raise ValueError(
                f"Error: La suma de superficies ({superficie_total:.2f} ha) "
                f"no coincide con la original ({original['superficie']:.2f} ha)"
            )
        
        # Validar que el número de superficies coincida
        if len(superficies) != num_divisiones + 1:
            raise ValueError(
                f"Error: Se esperaban {num_divisiones + 1} superficies "
                f"pero se recibieron {len(superficies)}"
            )
        
        # 1. Actualizar el lote original con la nueva superficie
        cursor.execute("""
            UPDATE campesinos 
            SET superficie = ?
            WHERE id = ?
        """, (superficies[0], campesino_id))
        
        # 2. Crear los nuevos sublotes
        nuevos_ids = []
        lote_base = original['numero_lote']
        
        for i in range(num_divisiones):
            nuevo_lote = f"{lote_base}-{i+1}"
            nueva_superficie = superficies[i+1]
            
            # Crear nuevo campesino (sublote)
            cursor.execute("""
                INSERT INTO campesinos (
                    numero_lote, nombre, localidad, barrio, superficie
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                nuevo_lote,
                f"{original['nombre']} (Heredero {i+1})",  # Nombre temporal
                original['localidad'],
                original['barrio'],
                nueva_superficie
            ))
            
            nuevos_ids.append(cursor.lastrowid)
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
        
    # Registrar en auditoría y sincronizar DESPUÉS de cerrar la conexión principal
    registrar_auditoria(
        'LOTE_PARTIDO',
        f"Lote {lote_base} partido en {num_divisiones + 1} sublotes. "
        f"Superficies: {', '.join([f'{s:.4f}' for s in superficies])} ha",
        json.dumps({'campesino_id': campesino_id, 'lote': lote_base})
    )
    
    # ✅ SINCRONIZAR CON CUOTAS.DB (Actualizar superficie del original)
    try:
        actualizar_datos_campesino_en_cuotas(campesino_id, {'superficie': superficies[0]})
    except Exception as e:
        print(f"Advertencia: No se pudo sincronizar con cuotas.db: {e}")
        
    return nuevos_ids

def renombrar_campesino(campesino_id: int, nuevo_nombre: str) -> bool:
    """
    Cambia el nombre del dueño de un lote.
    
    Args:
        campesino_id: ID del campesino
        nuevo_nombre: Nuevo nombre del dueño
    
    Returns:
        True si se actualizó correctamente
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Obtener nombre anterior
        cursor.execute("SELECT nombre, numero_lote FROM campesinos WHERE id = ?", (campesino_id,))
        row = cursor.fetchone()
        
        if not row:
            raise ValueError("Campesino no encontrado")
        
        nombre_anterior = row[0]
        numero_lote = row[1]
        
        # Actualizar nombre
        cursor.execute("""
            UPDATE campesinos 
            SET nombre = ?
            WHERE id = ?
        """, (nuevo_nombre, campesino_id))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
        
    # Registrar en auditoría y sincronizar DESPUÉS de cerrar conexión principal
    registrar_auditoria(
        'CAMPESINO_RENOMBRADO',
        f"Lote {numero_lote}: '{nombre_anterior}' → '{nuevo_nombre}'",
        json.dumps({'campesino_id': campesino_id, 'nombre_anterior': nombre_anterior})
    )
    
    # ✅ SINCRONIZAR CON CUOTAS.DB
    try:
        actualizar_datos_campesino_en_cuotas(campesino_id, {'nombre': nuevo_nombre})
    except Exception as e:
        print(f"Advertencia: No se pudo sincronizar con cuotas.db: {e}")
        
    return True

def cambiar_numero_lote(campesino_id: int, nuevo_lote: str) -> bool:
    """
    Cambia el número de lote de un campesino.

    Sólo toca la fila indicada: no renumera a nadie más, no mueve superficies y
    no altera siembras, recibos ni cuotas (que van ligados por campesino_id, no
    por el número de lote). Lo único que impide el cambio es que otro lote ya
    tenga ese número, porque la columna es UNIQUE.

    Args:
        campesino_id: ID del campesino
        nuevo_lote: Nuevo número de lote

    Returns:
        True si se actualizó correctamente
    """
    nuevo_lote = str(nuevo_lote or '').strip()
    if not nuevo_lote:
        raise ValueError("El número de lote no puede estar vacío")

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT nombre, numero_lote FROM campesinos WHERE id = ?", (campesino_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError("Campesino no encontrado")

        nombre = row[0]
        lote_anterior = row[1]

        if nuevo_lote == lote_anterior:
            return False

        # El número no puede estar ocupado por otro lote (constraint UNIQUE).
        cursor.execute(
            "SELECT nombre, activo FROM campesinos WHERE numero_lote = ? AND id != ?",
            (nuevo_lote, campesino_id))
        ocupado = cursor.fetchone()
        if ocupado:
            estado = "" if ocupado[1] else " (dado de baja)"
            raise ValueError(
                f"El lote {nuevo_lote} ya existe{estado}, pertenece a {ocupado[0]}.\n"
                f"Elige otro número o edita primero ese lote.")

        cursor.execute("UPDATE campesinos SET numero_lote = ? WHERE id = ?",
                       (nuevo_lote, campesino_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

    registrar_auditoria(
        'CAMBIO_NUMERO_LOTE',
        f"{nombre}: lote '{lote_anterior}' → '{nuevo_lote}'",
        json.dumps({'campesino_id': campesino_id, 'lote_anterior': lote_anterior})
    )

    # Sincronizar con cuotas.db para que el historial muestre el número nuevo
    try:
        actualizar_datos_campesino_en_cuotas(campesino_id, {'numero_lote': nuevo_lote})
    except Exception as e:
        print(f"Advertencia: No se pudo sincronizar con cuotas.db: {e}")

    return True

def actualizar_superficie_campesino(campesino_id: int, nueva_superficie: float) -> bool:
    """
    Actualiza la superficie de un campesino.
    
    Args:
        campesino_id: ID del campesino
        nueva_superficie: Nueva superficie en hectáreas
    
    Returns:
        True si se actualizó correctamente
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Obtener datos anteriores
        cursor.execute("SELECT nombre, numero_lote, superficie FROM campesinos WHERE id = ?", (campesino_id,))
        row = cursor.fetchone()
        
        if not row:
            raise ValueError("Campesino no encontrado")
        
        nombre = row[0]
        numero_lote = row[1]
        superficie_anterior = row[2]
        
        # Actualizar superficie
        cursor.execute("""
            UPDATE campesinos 
            SET superficie = ?
            WHERE id = ?
        """, (nueva_superficie, campesino_id))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
        
    # Registrar en auditoría y sincronizar DESPUÉS de cerrar conexión principal
    registrar_auditoria(
        'SUPERFICIE_ACTUALIZADA',
        f"Lote {numero_lote} ({nombre}): {superficie_anterior} ha → {nueva_superficie} ha",
        json.dumps({'campesino_id': campesino_id, 'superficie_anterior': superficie_anterior})
    )
    
    # ✅ SINCRONIZAR CON CUOTAS.DB
    try:
        actualizar_datos_campesino_en_cuotas(campesino_id, {'superficie': nueva_superficie})
    except Exception as e:
        print(f"Advertencia: No se pudo sincronizar con cuotas.db: {e}")
        
    return True

def migrar_agregar_cargo_documentos():
    """Migración: Agrega columna cargo_documentos a la tabla recibos"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Verificar si la columna ya existe
        cursor.execute("PRAGMA table_info(recibos)")
        columnas = [col[1] for col in cursor.fetchall()]
        
        if 'cargo_documentos' not in columnas:
            # Agregar la columna
            cursor.execute('ALTER TABLE recibos ADD COLUMN cargo_documentos BOOLEAN DEFAULT 0')
            conn.commit()
            print("✓ Columna cargo_documentos agregada a tabla recibos")
        else:
            print("✓ La columna cargo_documentos ya existe en tabla recibos")
    except Exception as e:
        print(f"Error en migración cargo_documentos: {e}")
        conn.rollback()
    finally:
        conn.close()
