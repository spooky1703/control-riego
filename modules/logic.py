#models/logic.py
from datetime import datetime

from typing import Dict, Optional, Tuple

import shutil

import os

from modules.models import (
    obtener_configuracion, actualizar_configuracion,
    obtener_siembra_activa, crear_siembra, cerrar_siembra,
    incrementar_riegos, crear_recibo, registrar_auditoria,
    obtener_campesino_por_id, obtener_recibos_dia, DB_PATH,
    actualizar_siembra, eliminar_siembra, decrementar_riegos,
    obtener_siembra_por_id, actualizar_recibo, eliminar_recibo as eliminar_recibo_db,
    obtener_recibo_por_id  
)

# ==================== CÁLCULOS ====================

def calcular_costo(superficie: float) -> float:

    """Calcula el costo de un riego basado en la superficie"""

    tarifa = float(obtener_configuracion('tarifa_hectarea') or 450)

    return superficie * tarifa

def validar_campesino(datos: Dict) -> Tuple[bool, str]:

    """Valida los datos de un campesino antes de crear/actualizar"""

    lote = datos.get('numero_lote', '').strip()

    if not lote:

        return False, "El número de lote es obligatorio"

    if any(char in lote for char in ['<', '>', '/', '\\', '|', '*', '?']):

        return False, "El número de lote contiene caracteres no permitidos"

    nombre = datos.get('nombre', '').strip()

    if not nombre or len(nombre) < 3:

        return False, "El nombre debe tener al menos 3 caracteres"

    if not datos.get('localidad'):

        return False, "La localidad es obligatoria"

    if not datos.get('barrio'):

        return False, "El barrio es obligatorio"

    try:

        superficie = float(datos.get('superficie', 0))

        if superficie <= 0:

            return False, "La superficie debe ser mayor a 0"

        if superficie > 100:

            return False, "La superficie parece incorrecta (mayor a 100 ha)"

    except (ValueError, TypeError):

        return False, "La superficie debe ser un número válido"

    return True, "OK"

def validar_siembra(datos: Dict) -> Tuple[bool, str]:

    """Valida los datos de una siembra antes de crear/actualizar"""

    if not datos.get('cultivo'):

        return False, "El cultivo es obligatorio"

    if not datos.get('ciclo'):

        return False, "El ciclo es obligatorio"

    try:

        fecha_inicio = datetime.strptime(datos.get('fecha_inicio', ''), '%Y-%m-%d')

    except ValueError:

        return False, "Fecha de inicio inválida (formato YYYY-MM-DD)"

    try:

        fecha_fin = datos.get('fecha_fin')

        if fecha_fin:

            datetime.strptime(fecha_fin, '%Y-%m-%d')

    except ValueError:

        return False, "Fecha de fin inválida (formato YYYY-MM-DD)"

    return True, "OK"

def validar_recibo(datos: Dict) -> Tuple[bool, str]:

    """Valida los datos de un recibo antes de crear/actualizar"""

    if not datos.get('folio'):

        return False, "El folio es obligatorio"

    if not datos.get('fecha'):

        return False, "La fecha es obligatoria"

    if not datos.get('hora'):

        return False, "La hora es obligatoria"

    if datos.get('costo') is None:

        return False, "El costo es obligatorio"

    try:

        datetime.strptime(datos.get('fecha', ''), '%Y-%m-%d')

    except ValueError:

        return False, "Fecha inválida (formato YYYY-MM-DD)"

    try:

        datetime.strptime(datos.get('hora', ''), '%H:%M:%S')

    except ValueError:

        return False, "Hora inválida (formato HH:MM:SS)"

    try:

        float(datos['costo'])

    except (ValueError, TypeError):

        return False, "El costo debe ser un número válido"

    return True, "OK"

# ==================== GESTIÓN DE FOLIOS Y CICLOS ====================

def obtener_folio_actual() -> int:

    """Obtiene el folio actual del sistema"""

    folio_str = obtener_configuracion('folio_actual') or '1'

    return int(folio_str)

def incrementar_folio() -> int:

    """Incrementa el folio y devuelve el nuevo valor"""

    folio_actual = obtener_folio_actual()

    nuevo_folio = folio_actual + 1

    actualizar_configuracion('folio_actual', str(nuevo_folio))

    return folio_actual

def reiniciar_folios_y_ciclo(nuevo_ciclo: str) -> bool:

    """
    MODIFICADO: Solo reinicia el contador de folios a 1 y actualiza el ciclo.
    NO borra los datos de los usuarios ni de las siembras.
    """

    try:

        crear_backup(f"Reinicio de ciclo - {nuevo_ciclo}")

        # Solo actualizar el folio actual y el ciclo
        actualizar_configuracion('folio_actual', '1')

        actualizar_configuracion('ciclo_actual', nuevo_ciclo)

        registrar_auditoria(

            'REINICIO_CICLO',

            f"Ciclo reiniciado: {nuevo_ciclo}. Folios reiniciados a 1. Datos de usuarios preservados.",

            None

        )

        return True

    except Exception as e:

        print(f"Error al reiniciar ciclo: {e}")

        return False

def actualizar_folio_actual(nuevo_folio: int) -> bool:

    """Actualiza manualmente el folio actual"""

    try:

        if nuevo_folio < 1:

            raise ValueError("El folio debe ser un número entero positivo.")

        actualizar_configuracion('folio_actual', str(nuevo_folio))

        registrar_auditoria(

            'ACTUALIZAR_FOLIO',

            f"Folio actualizado manualmente a: {nuevo_folio}",

            None

        )

        return True

    except Exception as e:

        print(f"Error al actualizar folio: {e}")

        return False

# ==================== OPERACIONES DE VENTA ====================

def nueva_siembra(campesino_id: int, cultivo: str, cargo_documentos: bool = False) -> Dict:

    """Inicia una nueva siembra para un campesino con opción de cargo por documentos (duplica precio)"""

    campesino = obtener_campesino_por_id(campesino_id)

    if not campesino:

        raise ValueError("Campesino no encontrado")

    siembra_anterior = obtener_siembra_activa(campesino_id)

    if siembra_anterior:

        cerrar_siembra(siembra_anterior['id'])

    ciclo_actual = obtener_configuracion('ciclo_actual') or 'SIN CICLO'

    siembra_id = crear_siembra(campesino_id, cultivo, ciclo_actual)

    recibo_datos = _generar_datos_recibo(

        campesino,

        siembra_id,

        cultivo,

        1,

        "Nueva siembra",

        ciclo_actual,

        cargo_documentos

    )

    recibo_id = crear_recibo(recibo_datos)

    incrementar_riegos(siembra_id)

    incrementar_folio()

    registrar_auditoria(

        'NUEVA_SIEMBRA',

        f"Nueva siembra: {campesino['nombre']} - {cultivo} - Ciclo: {ciclo_actual}",

        None

    )

    return {

        'recibo_id': recibo_id,

        'siembra_id': siembra_id,

        'folio': recibo_datos['folio'],

        'costo': recibo_datos['costo']

    }

def vender_riego(campesino_id: int, cargo_documentos: bool = False) -> Dict:

    """Vende un riego adicional a un campesino con siembra activa, con opción de cargo por documentos (duplica precio)"""

    campesino = obtener_campesino_por_id(campesino_id)

    if not campesino:

        raise ValueError("Campesino no encontrado")

    siembra_activa = obtener_siembra_activa(campesino_id)

    if not siembra_activa:

        raise ValueError("El campesino no tiene siembra activa. Debe iniciar una nueva siembra primero.")

    ciclo_actual = obtener_configuracion('ciclo_actual') or 'SIN CICLO'

    numero_riego = siembra_activa['numero_riegos'] + 1

    recibo_datos = _generar_datos_recibo(

        campesino,

        siembra_activa['id'],

        siembra_activa['cultivo'],

        numero_riego,

        "Riego adicional",

        ciclo_actual,

        cargo_documentos

    )

    recibo_id = crear_recibo(recibo_datos)

    incrementar_riegos(siembra_activa['id'])

    incrementar_folio()

    registrar_auditoria(

        'VENTA_RIEGO',

        f"Riego vendido: {campesino['nombre']} - Riego #{numero_riego} - {siembra_activa['cultivo']}",

        None

    )

    return {

        'recibo_id': recibo_id,

        'siembra_id': siembra_activa['id'],

        'folio': recibo_datos['folio'],

        'numero_riego': numero_riego,

        'costo': recibo_datos['costo']

    }

def _generar_datos_recibo(campesino: Dict, siembra_id: int, cultivo: str, numero_riego: int, tipo_accion: str, ciclo: str, cargo_documentos: bool = False) -> Dict:

    """Genera los datos para crear un recibo (función auxiliar)"""

    folio = obtener_folio_actual()

    ahora = datetime.now()

    fecha = ahora.strftime('%Y-%m-%d')

    hora = ahora.strftime('%H:%M:%S')

    costo = calcular_costo(campesino['superficie'])

    # Si hay cargo por documentos, duplicar el costo

    if cargo_documentos:

        costo = costo * 2

    return {

        'folio': folio,

        'fecha': fecha,

        'hora': hora,

        'campesino_id': campesino['id'],

        'siembra_id': siembra_id,

        'cultivo': cultivo,

        'numero_riego': numero_riego,

        'tipo_accion': tipo_accion,

        'costo': costo,

        'ciclo': ciclo,

        'cargo_documentos': 1 if cargo_documentos else 0

    }

# ==================== GESTIÓN DEL DÍA ====================

def calcular_total_dia(fecha: Optional[str] = None) -> float:

    """Calcula el total de ventas del día"""

    if not fecha:

        fecha = datetime.now().strftime('%Y-%m-%d')

    recibos = obtener_recibos_dia(fecha)

    total = sum(r['costo'] for r in recibos)

    return total

def eliminar_recibo_dia(recibo_id: int, motivo: str = "") -> float:
    """
    Elimina un recibo del día y revierte la operación (siembra o riego).
    
    IMPORTANTE:
    - Si es "Nueva siembra" con 1 riego: Elimina la siembra completa
    - Si es "Nueva siembra" con más riegos: Solo decrementa riegos
    - Si es "Riego adicional": Decrementa el contador de riegos
    - Decrementa el folio actual si es el último recibo
    """
    
    # Obtener datos del recibo
    recibo = obtener_recibo_por_id(recibo_id)
    if not recibo:
        raise ValueError("Recibo no encontrado")
    
    # Validar que sea del día actual
    fecha_hoy = datetime.now().strftime('%Y-%m-%d')
    if recibo['fecha'] != fecha_hoy:
        raise ValueError("Solo se pueden eliminar recibos del día actual")
    
    if recibo['eliminado']:
        raise ValueError("El recibo ya está eliminado")
    
    # Obtener la siembra asociada
    siembra = obtener_siembra_por_id(recibo['siembra_id'])
    if not siembra:
        raise ValueError("Siembra asociada no encontrada")
    
    # ===== REVERTIR LA OPERACIÓN SEGÚN EL TIPO =====
    if recibo['tipo_accion'] == 'Nueva siembra':
        # Si es nueva siembra Y solo tiene 1 riego, eliminar la siembra completa
        if siembra['numero_riegos'] == 1:
            eliminar_siembra(recibo['siembra_id'])
            mensaje_auditoria = (
                f"Recibo #{recibo['folio']} eliminado (Nueva siembra). "
                f"Siembra #{recibo['siembra_id']} eliminada completamente. "
                f"Campesino: {recibo['nombre']}. Motivo: {motivo}"
            )
        else:
            # Si tiene más riegos, solo decrementar
            decrementar_riegos(recibo['siembra_id'])
            mensaje_auditoria = (
                f"Recibo #{recibo['folio']} eliminado (Nueva siembra con múltiples riegos). "
                f"Riego decrementado en siembra #{recibo['siembra_id']}. "
                f"Campesino: {recibo['nombre']}. Motivo: {motivo}"
            )
    else:
        # Si es "Riego adicional", solo decrementar el contador
        if siembra['numero_riegos'] > 0:
            decrementar_riegos(recibo['siembra_id'])
            mensaje_auditoria = (
                f"Recibo #{recibo['folio']} eliminado (Riego adicional). "
                f"Riego decrementado en siembra #{recibo['siembra_id']}. "
                f"Campesino: {recibo['nombre']}. Motivo: {motivo}"
            )
        else:
            mensaje_auditoria = (
                f"Recibo #{recibo['folio']} eliminado (Riego adicional). "
                f"No se pudo decrementar riego (ya estaba en 0). "
                f"Campesino: {recibo['nombre']}. Motivo: {motivo}"
            )
    
    # ===== VERIFICAR SI ES EL ÚLTIMO RECIBO =====
    folio_actual = obtener_folio_actual()
    es_ultimo_recibo = (recibo['folio'] == folio_actual - 1)
    
    # Eliminar el recibo (marcarlo como eliminado en la BD)
    eliminar_recibo_db(recibo_id, motivo)
    
    # ===== DECREMENTAR FOLIO SI ES EL ÚLTIMO =====
    if es_ultimo_recibo:
        nuevo_folio = decrementar_folio()
        mensaje_auditoria += f" | Folio decrementado de {folio_actual} a {nuevo_folio}."
    else:
        mensaje_auditoria += f" | Folio NO decrementado (no era el más reciente)."
    
    # Registrar en auditoría
    registrar_auditoria('RECIBO_ELIMINADO', mensaje_auditoria, None)
    
    return recibo['costo']

def decrementar_folio() -> int:
    """
    Decrementa el folio actual en 1 (usado al eliminar el último recibo).
    No permite que el folio baje de 1.
    """
    folio_actual = obtener_folio_actual()
    
    if folio_actual > 1:
        nuevo_folio = folio_actual - 1
        actualizar_configuracion('folio_actual', str(nuevo_folio))
        return nuevo_folio
    else:
        # Si ya está en 1, mantenerlo
        return 1

def cerrar_dia() -> Dict:

    """Cierra el día actual generando un reporte y guardando la fecha de cierre"""

    fecha_hoy = datetime.now().strftime('%Y-%m-%d')

    recibos = obtener_recibos_dia(fecha_hoy)

    total = calcular_total_dia(fecha_hoy)

    actualizar_configuracion('fecha_ultimo_cierre', fecha_hoy)

    registrar_auditoria(

        'CIERRE_DIA',

        f"Día cerrado: {fecha_hoy} - Total: ${total:.2f} - Recibos: {len(recibos)}",

        None

    )

    return {

        'fecha': fecha_hoy,

        'total': total,

        'cantidad_recibos': len(recibos),

        'recibos': recibos

    }

# ==================== BACKUPS ====================

def crear_backup(motivo: str) -> str:

    """Crea un backup de la base de datos"""

    try:

        backup_dir = os.path.join('database', 'backups')

        os.makedirs(backup_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        backup_filename = f"riego_backup_{timestamp}.db"

        backup_path = os.path.join(backup_dir, backup_filename)

        shutil.copy2(DB_PATH, backup_path)

        registrar_auditoria(

            'BACKUP_CREADO',

            f"Backup creado: {backup_filename} - Motivo: {motivo}",

            None

        )

        limpiar_backups_antiguos()

        return backup_path

    except Exception as e:

        print(f"Error al crear backup: {e}")

        return ""

def limpiar_backups_antiguos(mantener: int = 10):

    """Mantiene solo los últimos N backups"""

    try:

        backup_dir = os.path.join('database', 'backups')

        if not os.path.exists(backup_dir):

            return

        backups = []

        for filename in os.listdir(backup_dir):

            if filename.startswith('riego_backup_') and filename.endswith('.db'):

                filepath = os.path.join(backup_dir, filename)

                backups.append((filepath, os.path.getmtime(filepath)))

        backups.sort(key=lambda x: x[1], reverse=True)

        for backup_path, _ in backups[mantener:]:

            try:

                os.remove(backup_path)

                print(f"Backup antiguo eliminado: {os.path.basename(backup_path)}")

            except:

                pass

    except Exception as e:

        print(f"Error al limpiar backups: {e}")

# ==================== CAMBIO DE CULTIVO ====================

def cambiar_cultivo_siembra(campesino_id: int, nuevo_cultivo: str, justificacion: str = "") -> int:

    """Cierra la siembra actual y crea una nueva con el cultivo especificado"""

    siembra_activa = obtener_siembra_activa(campesino_id)

    if not siembra_activa:

        raise ValueError("No hay siembra activa para cambiar")

    cerrar_siembra(siembra_activa['id'])

    ciclo_actual = obtener_configuracion('ciclo_actual') or 'SIN CICLO'

    nueva_siembra_id = crear_siembra(campesino_id, nuevo_cultivo, ciclo_actual)

    campesino = obtener_campesino_por_id(campesino_id)

    registrar_auditoria(

        'CAMBIO_CULTIVO',

        f"Cambio de cultivo: {campesino['nombre']} - {siembra_activa['cultivo']} → {nuevo_cultivo}. {justificacion}",

        None

    )

    return nueva_siembra_id

# ==================== GESTIÓN MANUAL DE DATOS ====================

def crear_siembra_manual(campesino_id: int, cultivo: str, ciclo: str, fecha_inicio: str = None) -> int:

    """Crea una siembra manualmente."""

    # crear_siembra solo acepta 3 parámetros (usa date('now') internamente)
    return crear_siembra(campesino_id, cultivo, ciclo)

def crear_riego_manual(campesino_id: int, siembra_id: int, folio: int, fecha: str, hora: str, tipo_accion: str, costo: float) -> int:

    """Crea un riego manualmente."""

    from modules.models import get_connection, incrementar_riegos, obtener_siembra_por_id

    conn = get_connection()

    cursor = conn.cursor()

    # Obtener cultivo y ciclo de la siembra

    siembra = obtener_siembra_por_id(siembra_id)

    if not siembra or siembra['campesino_id'] != campesino_id:

        conn.close()

        raise ValueError("Siembra no encontrada o no pertenece al campesino.")

    # Calcular número de riego

    cursor.execute("SELECT COUNT(*) FROM recibos WHERE siembra_id = ?", (siembra_id,))

    numero_riego = cursor.fetchone()[0] + 1

    # Datos para crear recibo

    datos_recibo = {

        'folio': folio,

        'fecha': fecha,

        'hora': hora,

        'campesino_id': campesino_id,

        'siembra_id': siembra_id,

        'cultivo': siembra['cultivo'],

        'numero_riego': numero_riego,

        'tipo_accion': tipo_accion,

        'costo': costo,

        'ciclo': siembra['ciclo']

    }

    recibo_id = crear_recibo(datos_recibo)

    # Incrementar riegos en la siembra

    incrementar_riegos(siembra_id)

    conn.close()

    return recibo_id

# ==================== BÚSQUEDA Y FILTROS ====================

def buscar_recibos_avanzado(filtros: Dict) -> list:

    """Búsqueda avanzada de recibos con múltiples filtros"""

    from modules.models import get_connection

    conn = get_connection()

    cursor = conn.cursor()

    query = '''

    SELECT r.*, c.nombre, c.numero_lote, c.localidad, c.barrio, c.superficie

    FROM recibos r

    JOIN campesinos c ON r.campesino_id = c.id

    WHERE 1=1

    '''

    params = []

    if filtros.get('fecha_inicio'):

        query += ' AND r.fecha >= ?'

        params.append(filtros['fecha_inicio'])

    if filtros.get('fecha_fin'):

        query += ' AND r.fecha <= ?'

        params.append(filtros['fecha_fin'])

    if filtros.get('cultivo'):

        query += ' AND r.cultivo = ?'

        params.append(filtros['cultivo'])

    if filtros.get('campesino_id'):

        query += ' AND r.campesino_id = ?'

        params.append(filtros['campesino_id'])

    if filtros.get('ciclo'):

        query += ' AND r.ciclo = ?'

        params.append(filtros['ciclo'])

    if not filtros.get('incluir_eliminados', False):

        query += ' AND r.eliminado = 0'

    query += ' ORDER BY r.fecha DESC, r.hora DESC'

    limite = filtros.get('limite', 100)

    query += f' LIMIT {limite}'

    cursor.execute(query, params)

    resultados = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return resultados