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
                print(""" 
                 █████╗ ██╗      ██████╗ ███╗   ██╗███████╗ ██████╗      ██████╗ ██████╗ ██████╗ ██╗███╗   ██╗ ██████╗ 
                ██╔══██╗██║     ██╔═══██╗████╗  ██║██╔════╝██╔═══██╗    ██╔════╝██╔═══██╗██╔══██╗██║████╗  ██║██╔════╝ 
                ███████║██║     ██║   ██║██╔██╗ ██║███████╗██║   ██║    ██║     ██║   ██║██║  ██║██║██╔██╗ ██║██║  ███╗
                ██╔══██║██║     ██║   ██║██║╚██╗██║╚════██║██║   ██║    ██║     ██║   ██║██║  ██║██║██║╚██╗██║██║   ██║
                ██║  ██║███████╗╚██████╔╝██║ ╚████║███████║╚██████╔╝    ╚██████╗╚██████╔╝██████╔╝██║██║ ╚████║╚██████╔╝
                ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═══╝╚══════╝ ╚═════╝      ╚═════╝ ╚═════╝ ╚═════╝ ╚═╝╚═╝  ╚═══╝ ╚═════╝                                                                  
                """)
            else:
                print("ADVERTENCIA: No se encontró XICUCO.csv. La BD estará vacía.")
        # Crear ventana principal
        root = tk.Tk()
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