import os
import sys

def resource_path(relative_path):
    """
    Obtiene la ruta absoluta al recurso, funciona para dev y para PyInstaller.
    
    Args:
        relative_path (str): Ruta relativa al recurso (ej: 'assets/logo.png')
        
    Returns:
        str: Ruta absoluta al recurso
    """
    try:
        # PyInstaller crea una carpeta temporal y guarda la ruta en _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)
