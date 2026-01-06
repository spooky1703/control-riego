import os
import sys
import threading

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

def ejecutar_en_hilo(root, funcion_pesada, callback_exito=None, callback_error=None, 
                     mensaje_espera="Procesando...", boton_a_deshabilitar=None):
    """
    Ejecuta una función pesada en un hilo secundario para no congelar la UI.
    
    Args:
        root: Ventana raíz de Tkinter (para usar after())
        funcion_pesada: Función que ejecuta la operación pesada (debe retornar resultado)
        callback_exito: Función a llamar con el resultado si todo sale bien
        callback_error: Función a llamar con la excepción si hay error
        mensaje_espera: Mensaje para mostrar en cursor de espera (no usado actualmente)
        boton_a_deshabilitar: Botón TTK a deshabilitar durante la operación
    """
    resultado = {'valor': None, 'error': None, 'terminado': False}
    
    # Deshabilitar botón si se proporcionó
    if boton_a_deshabilitar:
        try:
            boton_a_deshabilitar.config(state='disabled')
        except:
            pass
    
    # Cambiar cursor a espera
    try:
        root.config(cursor="wait")
        root.update_idletasks()
    except:
        pass
    
    def hilo_trabajo():
        try:
            resultado['valor'] = funcion_pesada()
        except Exception as e:
            resultado['error'] = e
        finally:
            resultado['terminado'] = True
    
    def verificar_completado():
        if resultado['terminado']:
            # Restaurar cursor
            try:
                root.config(cursor="")
            except:
                pass
            
            # Rehabilitar botón
            if boton_a_deshabilitar:
                try:
                    boton_a_deshabilitar.config(state='normal')
                except:
                    pass
            
            # Ejecutar callback apropiado
            if resultado['error']:
                if callback_error:
                    callback_error(resultado['error'])
            else:
                if callback_exito:
                    callback_exito(resultado['valor'])
        else:
            # Seguir verificando cada 100ms
            root.after(100, verificar_completado)
    
    # Iniciar hilo de trabajo
    thread = threading.Thread(target=hilo_trabajo, daemon=True)
    thread.start()
    
    # Iniciar verificación periódica
    root.after(100, verificar_completado)
