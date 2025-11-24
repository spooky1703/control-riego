import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os
from datetime import datetime
from modules.models import init_db, cargar_campesinos_desde_csv
from modules.ui_components import VentanaPrincipal
from modules.cuotas import init_cuotas_db, migrar_folios_individuales, recrear_tabla_recibos_cuotas

def main():
    """Función principal del sistema"""
    try:
        # Inicializar BASE DE DATOS DE RIEGOS
        print("Inicializando base de datos de RIEGOS...")
        init_db()
        
        # ✅ INICIALIZAR BASE DE DATOS DE CUOTAS (SEPARADA)
        print("Inicializando base de datos de CUOTAS...")
        init_cuotas_db()
        
        # Ejecutar migraciones
        print("Ejecutando migraciones...")
        from modules.models import migrar_agregar_cargo_documentos
        from modules.cuotas import migrar_agregar_sobrecargo, migrar_sobrecargo_por_tipo
        
        migrar_folios_individuales()
        recrear_tabla_recibos_cuotas()
        migrar_agregar_cargo_documentos()
        migrar_agregar_sobrecargo()
        migrar_sobrecargo_por_tipo()

        from modules.models import contar_campesinos
        
        if contar_campesinos() == 0:
            print("Cargando campesinos desde CSV...")
            if os.path.exists('XICUCO.csv'):
                cargar_campesinos_desde_csv('XICUCO.csv')
                print("Campesinos cargados exitosamente")
            else:
                print("ADVERTENCIA: No se encontró XICUCO.csv. La BD estará vacía.")
        
        root = tk.Tk()
        
        icon_path = os.path.join('assets', 'zapata.png')
        if os.path.exists(icon_path):
            try:
                import tempfile
                from PIL import Image, ImageTk
                imagen = Image.open(icon_path)
                imagen.thumbnail((64, 64), Image.Resampling.LANCZOS)
                
                if os.name == 'nt':
                    temp_gif = os.path.join(tempfile.gettempdir(), 'temp_icon.gif')
                    imagen.save(temp_gif, 'GIF')
                    root.iconbitmap(default=temp_gif)
                else:
                    # Mac/Linux
                    foto = ImageTk.PhotoImage(imagen)
                    root.iconphoto(False, foto)
                    root._icon_photo = foto
                
                print(f"Icono cargado exitosamente desde {icon_path}")
            except Exception as e:
                print(f"Advertencia: No se pudo cargar el icono: {e}")
        else:
            print(f"Advertencia: Archivo de icono no encontrado en {icon_path}")
        
        app = VentanaPrincipal(root)
        
        def on_closing():
            if messagebox.askokcancel("Salir", "¿Desea cerrar el sistema?"):
                root.destroy()
        
        root.protocol("WM_DELETE_WINDOW", on_closing)
        root.mainloop()
    
    except Exception as e:
        messagebox.showerror("Error Fatal", f"Error al iniciar el sistema:\n{str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()