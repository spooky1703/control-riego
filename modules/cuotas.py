# modules/cuotas.py - Sistema de Cuotas de Cooperación

import sqlite3
import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Tuple

# Ruta de la base de datos de CUOTAS (separada de riego.db)
CUOTAS_DB_PATH = os.path.join('database', 'cuotas.db')

def get_cuotas_connection():
    """Obtiene una conexión a la base de datos de cuotas"""
    os.makedirs('database', exist_ok=True)
    conn = sqlite3.connect(CUOTAS_DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.isolation_level = None
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 10000")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn

def init_cuotas_db():
    """Inicializa la base de datos de cuotas"""
    conn = get_cuotas_connection()
    cursor = conn.cursor()
    
    # Tabla de tipos de cuotas (ej: "Limpieza Canal", "Mantenimiento Bomba")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tipos_cuota (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            monto REAL NOT NULL CHECK(monto > 0),
            descripcion TEXT,
            activa BOOLEAN DEFAULT 1,
            folio_actual INTEGER DEFAULT 1,
            fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabla de asignación de cuotas a campesinos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cuotas_campesinos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campesino_id INTEGER NOT NULL,
            tipo_cuota_id INTEGER NOT NULL,
            numero_lote TEXT NOT NULL,
            nombre_campesino TEXT NOT NULL,
            barrio TEXT NOT NULL,
            monto REAL NOT NULL,
            fecha_asignacion TEXT DEFAULT CURRENT_TIMESTAMP,
            pagado BOOLEAN DEFAULT 0,
            fecha_pago TEXT,
            recibo_folio INTEGER,
            FOREIGN KEY (tipo_cuota_id) REFERENCES tipos_cuota(id)
        )
    ''')
        # Tabla de recibos de cuotas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recibos_cuotas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folio INTEGER NOT NULL,
            tipo_cuota_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            hora TEXT NOT NULL,
            cuota_campesino_id INTEGER NOT NULL,
            campesino_id INTEGER NOT NULL,
            numero_lote TEXT NOT NULL,
            nombre_campesino TEXT NOT NULL,
            barrio TEXT NOT NULL,
            nombre_cuota TEXT NOT NULL,
            monto REAL NOT NULL,
            eliminado BOOLEAN DEFAULT 0,
            fecha_eliminacion TEXT,
            motivo_eliminacion TEXT,
            FOREIGN KEY (cuota_campesino_id) REFERENCES cuotas_campesinos(id),
            UNIQUE(tipo_cuota_id, folio)
        )
    ''')

    
    # Tabla de configuración de cuotas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS configuracion_cuotas (
            clave TEXT PRIMARY KEY,
            valor TEXT NOT NULL
        )
    ''')
    
    # Índices
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_cuota_campesino ON cuotas_campesinos(campesino_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_cuota_pagado ON cuotas_campesinos(pagado)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_recibo_cuota_folio ON recibos_cuotas(folio)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_recibo_cuota_fecha ON recibos_cuotas(fecha)')
    
    # Configuración por defecto
    cursor.execute('''
        INSERT OR IGNORE INTO configuracion_cuotas (clave, valor)
        VALUES ('folio_actual_cuotas', '1')
    ''')
    
    conn.commit()
    conn.close()
    print("✓ Base de datos de CUOTAS inicializada correctamente")

# ==================== TIPOS DE CUOTA ====================

def crear_tipo_cuota(nombre: str, monto: float, descripcion: str = "") -> int:
    """Crea un nuevo tipo de cuota"""
    conn = get_cuotas_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO tipos_cuota (nombre, monto, descripcion)
            VALUES (?, ?, ?)
        ''', (nombre, monto, descripcion))
        
        tipo_id = cursor.lastrowid
        conn.commit()
        return tipo_id
    except sqlite3.IntegrityError:
        conn.close()
        raise ValueError(f"Ya existe una cuota con el nombre '{nombre}'")
    finally:
        conn.close()

def obtener_tipos_cuota_activos() -> List[Dict]:
    """Obtiene todos los tipos de cuota activos"""
    conn = get_cuotas_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM tipos_cuota
        WHERE activa = 1
        ORDER BY nombre
    ''')
    
    resultados = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return resultados

def actualizar_tipo_cuota(tipo_id: int, nombre: str = None, monto: float = None, descripcion: str = None):
    """Actualiza un tipo de cuota"""
    conn = get_cuotas_connection()
    cursor = conn.cursor()
    
    campos = []
    valores = []
    
    if nombre is not None:
        campos.append("nombre = ?")
        valores.append(nombre)
    
    if monto is not None:
        campos.append("monto = ?")
        valores.append(monto)
    
    if descripcion is not None:
        campos.append("descripcion = ?")
        valores.append(descripcion)
    
    if not campos:
        conn.close()
        return False
    
    valores.append(tipo_id)
    query = f"UPDATE tipos_cuota SET {', '.join(campos)} WHERE id = ?"
    cursor.execute(query, valores)
    
    conn.commit()
    conn.close()
    return True

def desactivar_tipo_cuota(tipo_id: int):
    """Desactiva un tipo de cuota"""
    conn = get_cuotas_connection()
    cursor = conn.cursor()
    
    cursor.execute('UPDATE tipos_cuota SET activa = 0 WHERE id = ?', (tipo_id,))
    
    conn.commit()
    conn.close()

# ==================== ASIGNACIÓN DE CUOTAS ====================
# ==================== ASIGNACIÓN DE CUOTAS ====================

def asignar_cuota_a_campesino(campesino_id: int, numero_lote: str, nombre_campesino: str, 
                               barrio: str, tipo_cuota_id: int, superficie: float) -> int:
    """Asigna una cuota a un campesino (MONTO PROPORCIONAL A SUPERFICIE)"""
    conn = get_cuotas_connection()
    cursor = conn.cursor()
    
    # Obtener la tarifa por hectárea del tipo de cuota
    cursor.execute('SELECT monto, nombre FROM tipos_cuota WHERE id = ?', (tipo_cuota_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        raise ValueError("Tipo de cuota no encontrado")
    
    tarifa_por_hectarea = row['monto']
    
    # ✅ CALCULAR MONTO SEGÚN SUPERFICIE (igual que riegos)
    monto = superficie * tarifa_por_hectarea
    
    cursor.execute('''
        INSERT INTO cuotas_campesinos 
        (campesino_id, tipo_cuota_id, numero_lote, nombre_campesino, barrio, monto)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (campesino_id, tipo_cuota_id, numero_lote, nombre_campesino, barrio, monto))
    
    cuota_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return cuota_id

def asignar_cuota_masiva(tipo_cuota_id: int, campesinos_lista: List[Dict]) -> int:
    """Asigna una cuota a múltiples campesinos (MONTO PROPORCIONAL A SUPERFICIE)"""
    conn = get_cuotas_connection()
    cursor = conn.cursor()
    
    # Obtener la tarifa por hectárea del tipo de cuota
    cursor.execute('SELECT monto FROM tipos_cuota WHERE id = ?', (tipo_cuota_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        raise ValueError("Tipo de cuota no encontrado")
    
    tarifa_por_hectarea = row['monto']
    total_asignados = 0
    
    for campesino in campesinos_lista:
        try:
            # ✅ CALCULAR MONTO SEGÚN SUPERFICIE
            monto = campesino['superficie'] * tarifa_por_hectarea
            
            cursor.execute('''
                INSERT INTO cuotas_campesinos 
                (campesino_id, tipo_cuota_id, numero_lote, nombre_campesino, barrio, monto)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                campesino['id'],
                tipo_cuota_id,
                campesino['numero_lote'],
                campesino['nombre'],
                campesino['barrio'],
                monto
            ))
            total_asignados += 1
        except:
            continue
    
    conn.commit()
    conn.close()
    return total_asignados


def obtener_cuotas_campesino(campesino_id: int) -> List[Dict]:
    """Obtiene todas las cuotas de un campesino (pagadas y pendientes)"""
    conn = get_cuotas_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT cc.*, tc.nombre as nombre_tipo_cuota
        FROM cuotas_campesinos cc
        JOIN tipos_cuota tc ON cc.tipo_cuota_id = tc.id
        WHERE cc.campesino_id = ?
        ORDER BY cc.fecha_asignacion DESC
    ''', (campesino_id,))
    
    resultados = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return resultados

def obtener_cuotas_pendientes_campesino(campesino_id: int) -> List[Dict]:
    """Obtiene solo las cuotas pendientes de un campesino"""
    conn = get_cuotas_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT cc.*, tc.nombre as nombre_tipo_cuota
        FROM cuotas_campesinos cc
        JOIN tipos_cuota tc ON cc.tipo_cuota_id = tc.id
        WHERE cc.campesino_id = ? AND cc.pagado = 0
        ORDER BY cc.fecha_asignacion ASC
    ''', (campesino_id,))
    
    resultados = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return resultados

def obtener_resumen_cuota(tipo_cuota_id: int) -> Dict:
    """Obtiene resumen de una cuota: total asignados, pagados, pendientes, monto recaudado"""
    conn = get_cuotas_connection()
    cursor = conn.cursor()
    
    # Total asignados
    cursor.execute('''
        SELECT COUNT(*) as total, SUM(monto) as monto_total
        FROM cuotas_campesinos
        WHERE tipo_cuota_id = ?
    ''', (tipo_cuota_id,))
    row_total = cursor.fetchone()
    
    # Pagados
    cursor.execute('''
        SELECT COUNT(*) as pagados, SUM(monto) as monto_pagado
        FROM cuotas_campesinos
        WHERE tipo_cuota_id = ? AND pagado = 1
    ''', (tipo_cuota_id,))
    row_pagados = cursor.fetchone()
    
    # Pendientes
    cursor.execute('''
        SELECT COUNT(*) as pendientes, SUM(monto) as monto_pendiente
        FROM cuotas_campesinos
        WHERE tipo_cuota_id = ? AND pagado = 0
    ''', (tipo_cuota_id,))
    row_pendientes = cursor.fetchone()
    
    conn.close()
    
    return {
        'total_asignados': row_total['total'] or 0,
        'monto_total': row_total['monto_total'] or 0.0,
        'total_pagados': row_pagados['pagados'] or 0,
        'monto_recaudado': row_pagados['monto_pagado'] or 0.0,
        'total_pendientes': row_pendientes['pendientes'] or 0,
        'monto_pendiente': row_pendientes['monto_pendiente'] or 0.0
    }

def obtener_todas_cuotas_con_estado() -> List[Dict]:
    """Obtiene todas las cuotas creadas con su estado de recaudación"""
    conn = get_cuotas_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT tc.id, tc.nombre, tc.monto, tc.descripcion, tc.fecha_creacion,
               COUNT(cc.id) as total_asignados,
               SUM(CASE WHEN cc.pagado = 1 THEN 1 ELSE 0 END) as total_pagados,
               SUM(CASE WHEN cc.pagado = 0 THEN 1 ELSE 0 END) as total_pendientes,
               SUM(CASE WHEN cc.pagado = 1 THEN cc.monto ELSE 0 END) as monto_recaudado,
               SUM(CASE WHEN cc.pagado = 0 THEN cc.monto ELSE 0 END) as monto_pendiente
        FROM tipos_cuota tc
        LEFT JOIN cuotas_campesinos cc ON tc.id = cc.tipo_cuota_id
        WHERE tc.activa = 1
        GROUP BY tc.id
        ORDER BY tc.fecha_creacion DESC
    ''')
    
    resultados = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return resultados

# ==================== PAGO DE CUOTAS ====================

def pagar_cuota(cuota_campesino_id: int) -> Dict:
    """Marca una cuota como pagada y genera un recibo"""
    conn = get_cuotas_connection()
    cursor = conn.cursor()
    
    # Obtener datos de la cuota
    cursor.execute('''
        SELECT cc.*, tc.nombre as nombre_cuota, tc.folio_actual
        FROM cuotas_campesinos cc
        JOIN tipos_cuota tc ON cc.tipo_cuota_id = tc.id
        WHERE cc.id = ?
    ''', (cuota_campesino_id,))
    
    cuota = cursor.fetchone()
    
    if not cuota:
        conn.close()
        raise ValueError("Cuota no encontrada")
    
    if cuota['pagado']:
        conn.close()
        raise ValueError("Esta cuota ya fue pagada")
    
    # Obtener folio individual del tipo de cuota
    folio = cuota['folio_actual']
    tipo_cuota_id = cuota['tipo_cuota_id']
    
    # Datos del recibo
    ahora = datetime.now()
    fecha = ahora.strftime('%Y-%m-%d')
    hora = ahora.strftime('%H:%M:%S')
    
    # Crear recibo (✅ AHORA INCLUYE tipo_cuota_id)
    cursor.execute('''
        INSERT INTO recibos_cuotas 
        (folio, tipo_cuota_id, fecha, hora, cuota_campesino_id, campesino_id, numero_lote, 
         nombre_campesino, barrio, nombre_cuota, monto)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        folio, tipo_cuota_id, fecha, hora, cuota_campesino_id,
        cuota['campesino_id'], cuota['numero_lote'],
        cuota['nombre_campesino'], cuota['barrio'],
        cuota['nombre_cuota'], cuota['monto']
    ))
    
    recibo_id = cursor.lastrowid
    
    # Marcar cuota como pagada
    cursor.execute('''
        UPDATE cuotas_campesinos 
        SET pagado = 1, fecha_pago = ?, recibo_folio = ?
        WHERE id = ?
    ''', (fecha, folio, cuota_campesino_id))
    
    # Incrementar el folio solo para este tipo de cuota
    nuevo_folio = folio + 1
    cursor.execute('''
        UPDATE tipos_cuota 
        SET folio_actual = ? 
        WHERE id = ?
    ''', (nuevo_folio, tipo_cuota_id))
    
    conn.commit()
    conn.close()
    
    return {
        'recibo_id': recibo_id,
        'folio': folio,
        'fecha': fecha,
        'hora': hora,
        'monto': cuota['monto'],
        'nombre_cuota': cuota['nombre_cuota'],
        'numero_lote': cuota['numero_lote'],
        'nombre_campesino': cuota['nombre_campesino'],
        'barrio': cuota['barrio']
    }


def obtener_recibo_cuota(recibo_id: int) -> Optional[Dict]:
    """Obtiene un recibo de cuota por su ID"""
    conn = get_cuotas_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM recibos_cuotas WHERE id = ?', (recibo_id,))
    row = cursor.fetchone()
    
    conn.close()
    return dict(row) if row else None

def obtener_recibos_cuotas_dia(fecha: Optional[str] = None) -> List[Dict]:
    """Obtiene todos los recibos de cuotas de un día específico"""
    if not fecha:
        fecha = datetime.now().strftime('%Y-%m-%d')
    
    conn = get_cuotas_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM recibos_cuotas
        WHERE fecha = ? AND eliminado = 0
        ORDER BY hora DESC
    ''', (fecha,))
    
    resultados = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return resultados

def calcular_total_recaudado_cuota(tipo_cuota_id: int) -> float:
    """Calcula el total recaudado de una cuota específica"""
    conn = get_cuotas_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT SUM(monto) as total
        FROM cuotas_campesinos
        WHERE tipo_cuota_id = ? AND pagado = 1
    ''', (tipo_cuota_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    return row['total'] or 0.0

# ==================== ESTADÍSTICAS ====================

def obtener_estadisticas_generales_cuotas() -> Dict:
    """Obtiene estadísticas generales del sistema de cuotas"""
    conn = get_cuotas_connection()
    cursor = conn.cursor()
    
    # Total de tipos de cuotas activas
    cursor.execute("SELECT COUNT(*) FROM tipos_cuota WHERE activa = 1")
    total_tipos_cuotas = cursor.fetchone()[0]
    
    # Total de cuotas asignadas
    cursor.execute("SELECT COUNT(*) FROM cuotas_campesinos")
    total_cuotas_asignadas = cursor.fetchone()[0]
    
    # Total pagadas
    cursor.execute("SELECT COUNT(*) FROM cuotas_campesinos WHERE pagado = 1")
    total_pagadas = cursor.fetchone()[0]
    
    # Total pendientes
    cursor.execute("SELECT COUNT(*) FROM cuotas_campesinos WHERE pagado = 0")
    total_pendientes = cursor.fetchone()[0]
    
    # Monto total recaudado
    cursor.execute("SELECT SUM(monto) FROM cuotas_campesinos WHERE pagado = 1")
    monto_recaudado = cursor.fetchone()[0] or 0.0
    
    # Monto total pendiente
    cursor.execute("SELECT SUM(monto) FROM cuotas_campesinos WHERE pagado = 0")
    monto_pendiente = cursor.fetchone()[0] or 0.0
    
    conn.close()
    
    return {
        'total_tipos_cuotas': total_tipos_cuotas,
        'total_cuotas_asignadas': total_cuotas_asignadas,
        'total_pagadas': total_pagadas,
        'total_pendientes': total_pendientes,
        'monto_recaudado': monto_recaudado,
        'monto_pendiente': monto_pendiente,
        'monto_total': monto_recaudado + monto_pendiente
    }
    
def migrar_folios_individuales():
    """Migración: Agrega folio_actual a tipos de cuota existentes"""
    conn = get_cuotas_connection()
    cursor = conn.cursor()
    
    try:
        # Verificar si la columna ya existe
        cursor.execute("PRAGMA table_info(tipos_cuota)")
        columnas = [col[1] for col in cursor.fetchall()]
        
        if 'folio_actual' not in columnas:
            # Agregar la columna
            cursor.execute('ALTER TABLE tipos_cuota ADD COLUMN folio_actual INTEGER DEFAULT 1')
            print("✓ Columna folio_actual agregada a tipos_cuota")
            
            # Inicializar folios según recibos existentes
            cursor.execute('SELECT id FROM tipos_cuota')
            tipos = cursor.fetchall()
            
            for tipo in tipos:
                tipo_id = tipo[0]
                # Obtener el máximo folio usado para este tipo de cuota
                cursor.execute('''
                    SELECT MAX(folio) FROM recibos_cuotas
                    WHERE nombre_cuota IN (
                        SELECT nombre FROM tipos_cuota WHERE id = ?
                    )
                ''', (tipo_id,))
                
                max_folio = cursor.fetchone()[0]
                nuevo_folio = (max_folio + 1) if max_folio else 1
                
                cursor.execute('UPDATE tipos_cuota SET folio_actual = ? WHERE id = ?', 
                               (nuevo_folio, tipo_id))
            
            conn.commit()
            print("✓ Folios inicializados correctamente")
        else:
            print("✓ La columna folio_actual ya existe")
            
    except Exception as e:
        print(f"Error en migración: {e}")
    finally:
        conn.close()

def recrear_tabla_recibos_cuotas():
    """Recrea la tabla recibos_cuotas con la nueva estructura"""
    conn = get_cuotas_connection()
    cursor = conn.cursor()
    
    try:
        # Respaldar datos existentes
        cursor.execute("SELECT * FROM recibos_cuotas")
        recibos_viejos = cursor.fetchall()
        
        # Eliminar tabla vieja
        cursor.execute("DROP TABLE IF EXISTS recibos_cuotas")
        
        # Crear tabla nueva
        cursor.execute('''
            CREATE TABLE recibos_cuotas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                folio INTEGER NOT NULL,
                tipo_cuota_id INTEGER NOT NULL,
                fecha TEXT NOT NULL,
                hora TEXT NOT NULL,
                cuota_campesino_id INTEGER NOT NULL,
                campesino_id INTEGER NOT NULL,
                numero_lote TEXT NOT NULL,
                nombre_campesino TEXT NOT NULL,
                barrio TEXT NOT NULL,
                nombre_cuota TEXT NOT NULL,
                monto REAL NOT NULL,
                eliminado BOOLEAN DEFAULT 0,
                fecha_eliminacion TEXT,
                motivo_eliminacion TEXT,
                FOREIGN KEY (cuota_campesino_id) REFERENCES cuotas_campesinos(id),
                UNIQUE(tipo_cuota_id, folio)
            )
        ''')
        
        # Restaurar datos con tipo_cuota_id
        for recibo in recibos_viejos:
            # Obtener tipo_cuota_id del nombre
            cursor.execute('SELECT id FROM tipos_cuota WHERE nombre = ?', (recibo['nombre_cuota'],))
            tipo = cursor.fetchone()
            tipo_cuota_id = tipo[0] if tipo else 1
            
            cursor.execute('''
                INSERT INTO recibos_cuotas 
                (id, folio, tipo_cuota_id, fecha, hora, cuota_campesino_id, campesino_id, 
                 numero_lote, nombre_campesino, barrio, nombre_cuota, monto, eliminado)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                recibo['id'], recibo['folio'], tipo_cuota_id, recibo['fecha'], 
                recibo['hora'], recibo['cuota_campesino_id'], recibo['campesino_id'],
                recibo['numero_lote'], recibo['nombre_campesino'], recibo['barrio'],
                recibo['nombre_cuota'], recibo['monto'], recibo['eliminado']
            ))
        
        conn.commit()
        print("✓ Tabla recibos_cuotas migrada correctamente")
        
    except Exception as e:
        print(f"Error en migración: {e}")
        conn.rollback()
    finally:
        conn.close()
