import sqlite3, os, random, datetime, string

def get_db_path():
    """
    Busca la ruta real de riego.db utilizada por el sistema.
    Por defecto busca ./database/riego.db o ./riego.db
    """
    db_path = os.path.join("database", "riego.db")
    if os.path.exists(db_path):
        return db_path
    db_path2 = "riego.db"
    if os.path.exists(db_path2):
        return db_path2
    raise FileNotFoundError("No se encuentra riego.db en la ruta esperada.")

def random_string(length=7):
    letras = string.ascii_uppercase + string.digits
    return ''.join(random.choices(letras, k=length))

def inject_data():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Insertar campesinos hasta llegar a 1200
    cursor.execute("SELECT COUNT(*) FROM campesinos")
    n_camp = cursor.fetchone()[0]
    records_to_add = max(0, 1200 - n_camp)
    
    print(f"Campesinos actuales: {n_camp}")
    print(f"Agregando {records_to_add} campesinos...")
    
    nombres = ["GARCÍA", "HERNÁNDEZ", "LÓPEZ", "MARTÍNEZ", "RODRÍGUEZ", "PÉREZ", "SÁNCHEZ", "RAMÍREZ", "FLORES", "TORRES"]
    apellidos = ["JUAN", "PEDRO", "JOSÉ", "LUIS", "CARLOS", "MIGUEL", "ANTONIO", "FRANCISCO", "JORGE", "MANUEL"]
    
    for i in range(records_to_add):
        lote = f"{random.randint(1, 9999):04d}"
        nombre = f"{random.choice(nombres)} {random.choice(apellidos)} {random.choice(apellidos)}"
        localidad = "Tezontepec de Aldama"
        barrio = random.choice(["PANUAYA", "TEZONTEPEC", "ATENGO", "MANGAS", "PRESAS", "HUITEL"])
        superficie = round(random.uniform(0.5, 5.0), 2)
        extension = random.choice(["Hectárea", "Media Hectárea", "Cuarto de Hectárea"])
        
        try:
            cursor.execute(
                "INSERT INTO campesinos (numero_lote, nombre, localidad, barrio, superficie, extension_tierra, activo) VALUES (?, ?, ?, ?, ?, ?, 1)", 
                (lote, nombre, localidad, barrio, superficie, extension, 1)
            )
        except sqlite3.IntegrityError:
            continue
        
        if (i + 1) % 100 == 0:
            print(f"  Insertados {i + 1} campesinos...")
    
    conn.commit()
    
    # Obtener todos los campesinos
    cursor.execute("SELECT id FROM campesinos")
    ids = [row[0] for row in cursor.fetchall()]
    total_campesinos = len(ids)
    
    # 2. Insertar siembras para el 70% de los campesinos
    campesinos_con_siembra = int(total_campesinos * 0.7)
    print(f"\nTotal de campesinos: {total_campesinos}")
    print(f"Agregando siembras al 70%: {campesinos_con_siembra} campesinos...")
    
    cultivos = ["MAÍZ", "FRIJOL", "TRIGO", "SORGO", "ALFALFA", "AVENA", "CEBADA", "CHILE"]
    ciclos = ["OTOÑO 2025", "PRIMAVERA 2025", "VERANO 2025"]
    
    campesinos_seleccionados = random.sample(ids, campesinos_con_siembra)
    siembras_insertadas = 0
    
    for i, cid in enumerate(campesinos_seleccionados):
        # Algunos campesinos pueden tener más de una siembra
        num_siembras = random.choices([1, 2, 3], weights=[70, 25, 5])[0]
        
        for _ in range(num_siembras):
            cultivo = random.choice(cultivos)
            ciclo = random.choice(ciclos)
            fecha_inicio = (datetime.date.today() - datetime.timedelta(days=random.randint(0, 180))).isoformat()
            numero_riegos = random.randint(0, 8)
            
            cursor.execute(
                "INSERT INTO siembras (campesino_id, cultivo, ciclo, fecha_inicio, numero_riegos, activa) VALUES (?, ?, ?, ?, ?, 1)", 
                (cid, cultivo, ciclo, fecha_inicio, numero_riegos)
            )
            siembras_insertadas += 1
        
        if (i + 1) % 100 == 0:
            print(f"  Procesados {i + 1} campesinos con siembras...")
    
    conn.commit()
    print(f"Total de siembras insertadas: {siembras_insertadas}")
    
    # 3. Obtener siembras para insertar recibos
    cursor.execute("SELECT id, campesino_id, cultivo, ciclo FROM siembras")
    siembras = cursor.fetchall()
    
    # Insertar recibos para cada siembra (entre 1 y 6 recibos por siembra)
    print(f"\nInsertando recibos para {len(siembras)} siembras...")
    recibos_insertados = 0
    
    # Obtener folio actual de la configuración
    cursor.execute("SELECT valor FROM configuracion WHERE clave='folio_actual'")
    folio_base = int(cursor.fetchone()[0])
    
    for i, (sid, cid, cultivo, ciclo) in enumerate(siembras):
        num_recibos = random.randint(1, 6)
        
        for j in range(num_recibos):
            folio = folio_base + recibos_insertados
            fecha = (datetime.date.today() - datetime.timedelta(days=random.randint(0, 120))).isoformat()
            hora = f"{random.randint(8,17):02}:{random.randint(0,59):02}:{random.randint(0,59):02}"
            numero_riego = j + 1
            tipo_accion = "Nueva siembra" if j == 0 else "Riego adicional"
            
            # Obtener superficie del campesino para calcular costo
            cursor.execute("SELECT superficie FROM campesinos WHERE id=?", (cid,))
            superficie = cursor.fetchone()[0]
            
            # Calcular costo basado en tarifa por hectárea
            cursor.execute("SELECT valor FROM configuracion WHERE clave='tarifa_hectarea'")
            tarifa = float(cursor.fetchone()[0])
            costo = round(superficie * tarifa, 2)
            
            try:
                cursor.execute(
                    "INSERT INTO recibos (folio, fecha, hora, campesino_id, siembra_id, cultivo, numero_riego, tipo_accion, costo, ciclo, eliminado) VALUES (?,?,?,?,?,?,?,?,?,?,0)", 
                    (folio, fecha, hora, cid, sid, cultivo, numero_riego, tipo_accion, costo, ciclo)
                )
                recibos_insertados += 1
            except Exception as e:
                print(f"Error insertando recibo: {e}")
                continue
        
        if (i + 1) % 100 == 0:
            print(f"  Procesadas {i + 1} siembras...")
    
    # Actualizar folio actual en configuración
    nuevo_folio = folio_base + recibos_insertados
    cursor.execute("UPDATE configuracion SET valor=? WHERE clave='folio_actual'", (str(nuevo_folio),))
    
    conn.commit()
    print(f"Total de recibos insertados: {recibos_insertados}")
    print(f"Folio actualizado a: {nuevo_folio}")
    
    # Resumen final
    print("\n" + "="*60)
    print("RESUMEN DE DATOS INYECTADOS")
    print("="*60)
    cursor.execute("SELECT COUNT(*) FROM campesinos")
    print(f"Total campesinos: {cursor.fetchone()[0]}")
    cursor.execute("SELECT COUNT(*) FROM siembras")
    print(f"Total siembras: {cursor.fetchone()[0]}")
    cursor.execute("SELECT COUNT(*) FROM recibos WHERE eliminado=0")
    print(f"Total recibos activos: {cursor.fetchone()[0]}")
    print("="*60)
    
    conn.close()
    return db_path

if __name__=="__main__":
    print("\n🌾 INYECTOR DE DATOS - SISTEMA DE RIEGO 🌾\n")
    try:
        db_path = inject_data()
        print(f"\n✅ Datos inyectados exitosamente a: {db_path}")
    except Exception as e:
        print(f"\n❌ Error: {e}")