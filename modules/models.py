# modules/models.py - Modelos de Base de Datos
# Definición de tablas SQLite y funciones CRUD
import sqlite3
import os
import json
import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict, Tuple
# Ruta de la base de datos
DB_PATH = os.path.join('database', 'riego.db')
def get_connection():
    """Obtiene una conexión a la base de datos"""
    os.makedirs('database', exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
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
# ==================== FUNCIONES DE CAMPESINOS ====================
def buscar_campesino(termino: str) -> List[Dict]:
    """Busca campesinos por lote o nombre"""
    conn = get_connection()
    cursor = conn.cursor()
    termino = f"%{termino}%"
    cursor.execute('''
        SELECT * FROM campesinos 
        WHERE (numero_lote LIKE ? OR nombre LIKE ?) 
        AND activo = 1
        ORDER BY nombre
    ''', (termino, termino))
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
        registrar_auditoria(
            'CREAR_CAMPESINO',
            f"Nuevo campesino registrado: {datos['nombre']} (Lote: {datos['numero_lote']})",
            None
        )
        conn.commit()
        return campesino_id
    except sqlite3.IntegrityError:
        conn.close()
        raise ValueError(f"El lote {datos['numero_lote']} ya existe")
    finally:
        conn.close()
def actualizar_campesino(campesino_id: int, datos: Dict) -> bool:
    """Actualiza los datos de un campesino"""
    conn = get_connection()
    cursor = conn.cursor()
    datos_previos = obtener_campesino_por_id(campesino_id)
    if 'superficie' in datos and datos['superficie'] != datos_previos['superficie']:
        siembra_activa = obtener_siembra_activa(campesino_id)
        if siembra_activa:
            conn.close()
            raise ValueError("No se puede cambiar la superficie con siembra activa")
    try:
        campos_actualizar = []
        valores = []
        campos_permitidos = ['nombre', 'localidad', 'barrio', 'superficie', 'extension_tierra']
        for campo in campos_permitidos:
            if campo in datos:
                campos_actualizar.append(f"{campo} = ?")
                valores.append(datos[campo])
        if not campos_actualizar:
            conn.close()
            return False
        valores.append(campesino_id)
        query = f"UPDATE campesinos SET {', '.join(campos_actualizar)} WHERE id = ?"
        cursor.execute(query, valores)
        registrar_auditoria(
            'EDITAR_CAMPESINO',
            f"Campesino actualizado: {datos_previos['nombre']} (ID: {campesino_id})",
            json.dumps(datos_previos)
        )
        conn.commit()
        return True
    finally:
        conn.close()
def eliminar_campesino(campesino_id: int) -> bool:
    """Eliminación lógica de un campesino"""
    conn = get_connection()
    cursor = conn.cursor()
    siembra_activa = obtener_siembra_activa(campesino_id)
    if siembra_activa:
        conn.close()
        raise ValueError("No se puede eliminar un campesino con siembra activa")
    datos_previos = obtener_campesino_por_id(campesino_id)
    cursor.execute('UPDATE campesinos SET activo = 0 WHERE id = ?', (campesino_id,))
    registrar_auditoria(
        'ELIMINAR_CAMPESINO',
        f"Campesino eliminado: {datos_previos['nombre']} (Lote: {datos_previos['numero_lote']})",
        json.dumps(datos_previos)
    )
    conn.commit()
    conn.close()
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
def actualizar_siembra(siembra_id: int, nuevos_datos: Dict) -> bool:
    """Actualiza los datos de una siembra (cultivo, ciclo, fecha_inicio, fecha_fin, activa)"""
    conn = get_connection()
    cursor = conn.cursor()
    datos_previos = obtener_siembra_por_id(siembra_id)
    try:
        campos_actualizar = []
        valores = []
        campos_permitidos = ['cultivo', 'ciclo', 'fecha_inicio', 'fecha_fin', 'activa']
        for campo in campos_permitidos:
            if campo in nuevos_datos:
                campos_actualizar.append(f"{campo} = ?")
                valores.append(nuevos_datos[campo])
        if not campos_actualizar:
            conn.close()
            return False
        valores.append(siembra_id)
        query = f"UPDATE siembras SET {', '.join(campos_actualizar)} WHERE id = ?"
        cursor.execute(query, valores)
        registrar_auditoria(
            'EDITAR_SIEMBRA',
            f"Siembra actualizada: ID {siembra_id}",
            json.dumps(datos_previos)
        )
        conn.commit()
        return True
    finally:
        conn.close()
def eliminar_siembra(siembra_id: int) -> bool:
    """Elimina una siembra (lógicamente, marcando como inactiva)"""
    conn = get_connection()
    cursor = conn.cursor()
    datos_previos = obtener_siembra_por_id(siembra_id)
    cursor.execute('''
        UPDATE siembras 
        SET activa = 0, fecha_fin = date('now')
        WHERE id = ?
    ''', (siembra_id,))
    registrar_auditoria(
        'ELIMINAR_SIEMBRA',
        f"Siembra eliminada (cerrada): ID {siembra_id}",
        json.dumps(datos_previos)
    )
    conn.commit()
    conn.close()
    return True
def obtener_siembra_por_id(siembra_id: int) -> Optional[Dict]:
    """Obtiene una siembra por su ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM siembras WHERE id = ?', (siembra_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None
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
def decrementar_riegos(siembra_id: int):
    """Decrementa el contador de riegos de una siembra (si > 0)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE siembras 
        SET numero_riegos = CASE 
            WHEN numero_riegos > 0 THEN numero_riegos - 1 
            ELSE 0 
        END
        WHERE id = ?
    ''', (siembra_id,))
    conn.commit()
    conn.close()
# ==================== FUNCIONES DE RECIBOS ====================
def crear_recibo(datos: Dict) -> int:
    """Crea un nuevo recibo"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO recibos 
        (folio, fecha, hora, campesino_id, siembra_id, cultivo, numero_riego, 
         tipo_accion, costo, ciclo, eliminado)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
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
        datos['ciclo']
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
    conn = get_connection()
    cursor = conn.cursor()
    recibo = obtener_recibo_por_id(recibo_id)
    cursor.execute('''
        UPDATE recibos 
        SET eliminado = 1, 
            fecha_eliminacion = datetime('now'),
            motivo_eliminacion = ?
        WHERE id = ?
    ''', (motivo, recibo_id))
    registrar_auditoria(
        'ELIMINAR_RECIBO',
        f"Recibo eliminado: Folio {recibo['folio']} - {recibo['nombre']} - ${recibo['costo']:.2f}",
        json.dumps(recibo, default=str)
    )
    conn.commit()
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
        registrar_auditoria(
            'EDITAR_RECIBO',
            f"Recibo actualizado: Folio {datos_previos['folio']}",
            json.dumps(datos_previos)
        )
        conn.commit()
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
    cursor.execute('''
        INSERT OR REPLACE INTO configuracion (clave, valor)
        VALUES (?, ?)
    ''', (clave, valor))
    conn.commit()
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
    cursor.execute('''
        INSERT INTO auditoria (fecha_hora, tipo_evento, usuario, descripcion, datos_previos)
        VALUES (datetime('now', 'localtime'), ?, 'Sistema', ?, ?)
    ''', (tipo_evento, descripcion, datos_previos))
    conn.commit()
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
    """Carga los campesinos desde el archivo CSV inicial"""
    df_raw = pd.read_csv(ruta_csv, encoding='latin-1', header=None)
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
    for barrio, inicio, fin in barrios_ordenados:
        for idx in range(inicio + 2, fin):
            row = df_raw.iloc[idx]
            lote = str(row[1]).strip()
            nombre = str(row[2]).strip()
            superficie = str(row[3]).strip()
            if lote == 'nan' or nombre == 'nan' or lote == '' or nombre == '':
                continue
            try:
                sup_valor = float(superficie)
                cursor.execute('''
                    INSERT OR IGNORE INTO campesinos 
                    (numero_lote, nombre, localidad, barrio, superficie, activo)
                    VALUES (?, ?, ?, ?, ?, 1)
                ''', (lote, nombre, 'Tezontepec de Aldama', barrio, sup_valor))
                if cursor.rowcount > 0:
                    total_cargados += 1
            except:
                continue
    conn.commit()
    conn.close()
    print(f"Total de campesinos cargados: {total_cargados}")
    return total_cargados