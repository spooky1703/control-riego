# main.py - Sistema de Control de Riegos Agrícolas
# Aplicación principal - Ventana principal del sistema
import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os
from datetime import datetime
# Importar módulos del sistema
from modules.models import init_db, cargar_campesinos_desde_csv
from modules.ui_components import VentanaPrincipal

def main():
    """Función principal del sistema"""
    try:
        # Inicializar la base de datos
        print("Inicializando base de datos...")
        init_db()

        # Verificar si hay campesinos en la BD, si no, cargar desde CSV
        from modules.models import contar_campesinos
        if contar_campesinos() == 0:
            print("Cargando campesinos desde CSV...")
            if os.path.exists('XICUCO.csv'):
                cargar_campesinos_desde_csv('XICUCO.csv')
                print("Campesinos cargados exitosamente")
            else:
                print("ADVERTENCIA: No se encontró XICUCO.csv. La BD estará vacía.")

        # Crear ventana principal
        root = tk.Tk()
        
        # ===== AGREGAR ICONO (SIN PILLOW) =====
        # Verificar si el archivo de icono existe
        icon_path = os.path.join('assets', 'zapata.png')
        
        if os.path.exists(icon_path):
            try:
                # Convertir JPG a GIF o usar directamente si es .ico
                import tempfile
                from PIL import Image, ImageTk
                
                # Abrir la imagen
                imagen = Image.open(icon_path)
                
                # Redimensionar a tamaño de icono
                imagen.thumbnail((64, 64), Image.Resampling.LANCZOS)
                
                # Usar en la ventana
                # Método 1: Para Windows (necesita convertir a GIF)
                if os.name == 'nt':
                    # Convertir a GIF temporalmente
                    temp_gif = os.path.join(tempfile.gettempdir(), 'temp_icon.gif')
                    imagen.save(temp_gif, 'GIF')
                    root.iconbitmap(default=temp_gif)
                else:
                    # Para Mac/Linux - usar PhotoImage
                    foto = ImageTk.PhotoImage(imagen)
                    root.iconphoto(False, foto)
                    # Guardar la referencia para evitar que se recolecte basura
                    root._icon_photo = foto
                    
                print(f"Icono cargado exitosamente desde {icon_path}")
                
            except Exception as e:
                print(f"Advertencia: No se pudo cargar el icono: {e}")
        else:
            print(f"Advertencia: Archivo de icono no encontrado en {icon_path}")
        # ===== FIN ICONO =====
        
        app = VentanaPrincipal(root)

        # Configurar el cierre de la aplicación
        def on_closing():
            if messagebox.askokcancel("Salir", "¿Desea cerrar el sistema?"):
                root.destroy()

        root.protocol("WM_DELETE_WINDOW", on_closing)

        # Iniciar el loop principal
        root.mainloop()

    except Exception as e:
        messagebox.showerror("Error Fatal", f"Error al iniciar el sistema:\n{str(e)}")
        sys.exit(1)
if __name__ == "__main__":
    main()