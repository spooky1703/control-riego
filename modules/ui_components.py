#models/ui_components.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext, simpledialog
from datetime import datetime
from typing import Optional, Dict, List
import os
import time
import platform
import sys           # ✅ AGREGAR ESTA LÍNEA
import subprocess
# Importaciones de módulos propios
from modules.models import (
    buscar_campesino, obtener_campesino_por_id, crear_campesino,
    actualizar_campesino, eliminar_campesino, obtener_todos_campesinos,
    obtener_siembra_activa, obtener_historial_siembras,
    obtener_recibos_dia, obtener_configuracion, actualizar_configuracion,
    obtener_toda_configuracion, obtener_auditoria, obtener_recibos_campesino,
    crear_siembra as crear_siembra_db, actualizar_siembra as actualizar_siembra_db,
    eliminar_siembra, obtener_siembra_por_id,
    crear_recibo as crear_recibo_db, actualizar_recibo as actualizar_recibo_db,
    eliminar_recibo as eliminar_recibo_db, obtener_recibo_por_id,
    obtener_todos_los_recibos, obtener_todas_las_siembras, incrementar_riegos,
    obtener_estadisticas_generales, obtener_estadisticas_por_cultivo,
    registrar_auditoria, actualizar_superficie_campesino
)

from modules.logic import (
    calcular_costo, validar_campesino, nueva_siembra, vender_riego,
    calcular_total_dia, eliminar_recibo_dia, cerrar_dia,
    reiniciar_folios_y_ciclo, crear_backup, cambiar_cultivo_siembra,
    actualizar_folio_actual, incrementar_folio
)

from modules.reports import (
    generar_recibo_pdf_temporal, imprimir_recibo_y_limpiar,
    generar_reporte_diario, abrir_pdf, exportar_a_excel, obtener_impresoras_disponibles,
    generar_corte_caja_excel  
)
from modules.cuotas import (
    crear_tipo_cuota, obtener_tipos_cuota_activos, obtener_todas_cuotas_con_estado,
    asignar_cuota_a_campesino, asignar_cuota_masiva, obtener_cuotas_campesino,
    obtener_cuotas_pendientes_campesino, obtener_resumen_cuota, pagar_cuota,
    obtener_recibo_cuota, obtener_recibos_cuotas_dia, obtener_estadisticas_generales_cuotas
)

# Lista de cultivos comunes
CULTIVOS = ['MAÍZ', 'FRIJOL', 'FRIJOL EJOTERO','TRIGO', 'SORGO', 'ALFALFA', 'CHILE', 'TOMATE', 'CEBOLLA', 'AJO', 'NABO' ,'AVENA','HABA','CALABAZA','CEBADA','ARBOL FRUTAL','PASTO','BROCOLI','COLIFLOR']

# ==================== VENTANA PRINCIPAL ====================

def crear_ventana_scrollable(parent_ventana, contenido_frame):
    """
    Agrega una scrollbar vertical a cualquier ventana/pop-up.
    Funciona con rueda de ratón y trackpad en Windows, Mac y Linux.
    
    Uso:
      1. Crear la ventana: ventana = tk.Toplevel(parent)
      2. Llamar a esta función: canvas, scrollable_frame = crear_ventana_scrollable(ventana, None)
      3. Colocar widgets en scrollable_frame
    """
    # Canvas para el scroll
    canvas = tk.Canvas(parent_ventana, highlightthickness=0, bd=0)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    # Scrollbar vertical
    scrollbar = ttk.Scrollbar(parent_ventana, orient=tk.VERTICAL, command=canvas.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    canvas.configure(yscrollcommand=scrollbar.set)
    
    # Frame scrollable dentro del canvas
    scrollable_frame = ttk.Frame(canvas)
    canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor=tk.NW)
    
    def _configure_scroll_region(event=None):
        """Actualiza la región de scroll cuando cambia el contenido"""
        canvas.configure(scrollregion=canvas.bbox("all"))
    
    scrollable_frame.bind('<Configure>', _configure_scroll_region)
    
    # Ajustar ancho del frame al canvas
    def _configure_canvas_width(event):
        """Ajusta el ancho del frame scrollable al ancho del canvas"""
        canvas_width = event.width
        canvas.itemconfig(canvas_window, width=canvas_width)
    
    canvas.bind('<Configure>', _configure_canvas_width)
    
    # Detectar sistema operativo
    sistema = platform.system()
    
    # Funciones de scroll según el SO
    def _on_scroll_windows(event):
        """Maneja scroll con rueda de ratón en Windows"""
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def _on_scroll_linux(event):
        """Maneja scroll con rueda de ratón en Linux"""
        if event.num == 4:
            canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            canvas.yview_scroll(1, "units")
    
    def _on_scroll_mac(event):
        """Maneja scroll con trackpad/rueda en Mac"""
        canvas.yview_scroll(int(-1*(event.delta)), "units")
    
    # Bind según el sistema operativo
    if sistema == "Windows":
        canvas.bind_all("<MouseWheel>", _on_scroll_windows)
    elif sistema == "Darwin":  # macOS
        canvas.bind_all("<MouseWheel>", _on_scroll_mac)
    else:  # Linux
        canvas.bind_all("<Button-4>", _on_scroll_linux)
        canvas.bind_all("<Button-5>", _on_scroll_linux)
    
    # Limpiar binds al cerrar la ventana
    def _cleanup():
        try:
            if sistema == "Windows":
                canvas.unbind_all("<MouseWheel>")
            elif sistema == "Darwin":
                canvas.unbind_all("<MouseWheel>")
            else:
                canvas.unbind_all("<Button-4>")
                canvas.unbind_all("<Button-5>")
        except:
            pass
    
    parent_ventana.bind("<Destroy>", lambda e: _cleanup() if e.widget == parent_ventana else None)
    
    # Permitir que canvas reciba focus para eventos de teclado
    canvas.focus_set()
    
    return canvas, scrollable_frame


class VentanaPrincipal:
    """Ventana principal del sistema"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Control de Riegos - XICUCO")
        
        # Configurar tamaño - Adaptable a diferentes resoluciones
        ancho = 1200
        alto = 590
        x = (self.root.winfo_screenwidth() // 2) - (ancho // 2)
        y = (self.root.winfo_screenheight() // 2) - (alto // 2)
        self.root.geometry(f'{ancho}x{alto}+{x}+{y}')
        
        # Hacer resizable
        self.root.resizable(True, True)
        
        # Variables
        self.total_dia = tk.DoubleVar(value=0.0)
        self.fecha_actual = datetime.now().strftime('%Y-%m-%d')
        self.campesino_seleccionado = None
        
        # Crear interfaz
        self.crear_widgets()
        
        # Actualizar total del día
        self.actualizar_total_dia()
    
    def crear_widgets(self):
        """Crea todos los widgets de la ventana principal - RESPONSIVE CON SCROLLBAR"""
        
        # ===== CANVAS SCROLLABLE PARA TODA LA VENTANA =====
        self.canvas, scrollable_frame = crear_ventana_scrollable(self.root, None)
        
        # Frame superior con título y total
        frame_superior = ttk.Frame(scrollable_frame, padding="10")
        frame_superior.pack(fill=tk.X)
        
        nombre_oficina = obtener_configuracion('nombre_oficina') or 'SISTEMA DE CONTROL DE RIEGOS'
        ttk.Label(frame_superior, text=f"🌾 {nombre_oficina[:60]}",
                  font=('Helvetica', 11, 'bold')).pack()
        
        fecha_texto = datetime.now().strftime('%d/%m/%Y')
        ttk.Label(frame_superior, text=f"📅 {fecha_texto}",
                  font=('Helvetica', 10)).pack()
        
        # Panel de venta del día
        frame_venta = ttk.LabelFrame(frame_superior, text="VENTA DEL DÍA", padding="10")
        frame_venta.pack(pady=5)
        
        ttk.Label(frame_venta, text="💵 $", font=('Helvetica', 20)).pack(side=tk.LEFT)
        label_total = ttk.Label(frame_venta, textvariable=self.total_dia,
                                font=('Helvetica', 20, 'bold'),
                                foreground='green')
        label_total.pack(side=tk.LEFT)
        
                # ===== FRAME DE BÚSQUEDA CON ORDENAMIENTO =====
        frame_busqueda = ttk.LabelFrame(scrollable_frame, text="Buscar Campesino", padding="10")
        frame_busqueda.pack(fill=tk.X, padx=10, pady=5)
        
        # Selector de orden
        ttk.Label(frame_busqueda, text="📋 Ordenado por: Lote (Numérico)", 
                font=('Helvetica', 9, 'bold')).pack(side=tk.LEFT, padx=5)

        # Botón para recargar
        ttk.Button(frame_busqueda, text="🔄 Actualizar",
                command=lambda: self.cargar_todos_campesinos(ordenar_por_lote=True),
                width=15).pack(side=tk.LEFT, padx=2)

        
        # Barra separadora vertical
        ttk.Separator(frame_busqueda, orient='vertical').pack(side=tk.LEFT, fill='y', padx=10, pady=2)
        
        # Campo de búsqueda
        ttk.Label(frame_busqueda, text="🔍").pack(side=tk.LEFT, padx=5)
        self.entry_busqueda = ttk.Entry(frame_busqueda, width=30, font=('Helvetica', 11))
        self.entry_busqueda.pack(side=tk.LEFT, padx=5)
        self.entry_busqueda.bind('<Return>', self.on_buscar)
        
        # Botones de búsqueda
        ttk.Button(frame_busqueda, text="Buscar",
                   command=self.on_buscar).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_busqueda, text="Limpiar",
                   command=self.limpiar_busqueda).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_busqueda, text="➕ Nuevo Campesino",
                   command=self.abrir_form_nuevo_campesino).pack(side=tk.LEFT, padx=20)




        # Frame de resultados
        frame_resultados = ttk.Frame(scrollable_frame, padding="10")
        frame_resultados.pack(fill=tk.BOTH, expand=True, padx=10)
        
        # Crear Treeview
        columnas = ('lote', 'nombre', 'localidad', 'barrio', 'superficie', 'cultivo', 'riegos')
        self.tree = ttk.Treeview(frame_resultados, columns=columnas, show='headings', height=12)
        
        # Encabezados
        self.tree.heading('lote', text='Lote')
        self.tree.heading('nombre', text='Nombre')
        self.tree.heading('localidad', text='Localidad')
        self.tree.heading('barrio', text='Barrio')
        self.tree.heading('superficie', text='Sup. (ha)')
        self.tree.heading('cultivo', text='Cultivo Actual')
        self.tree.heading('riegos', text='Riegos')
        
        # Anchos de columna - RESPONSIVE
        self.tree.column('lote', width=70)
        self.tree.column('nombre', width=200)
        self.tree.column('localidad', width=120)
        self.tree.column('barrio', width=80)
        self.tree.column('superficie', width=70)
        self.tree.column('cultivo', width=100)
        self.tree.column('riegos', width=70)
        
        # Scrollbar
        scrollbar_tree = ttk.Scrollbar(frame_resultados, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar_tree.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_tree.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind selección
        self.tree.bind('<<TreeviewSelect>>', self.on_seleccionar_campesino)
        self.tree.bind('<Double-1>', self.on_doble_click)
        
        # Frame de botones principales - CON WRAPPING EN WINDOWS
        frame_botones = ttk.Frame(scrollable_frame, padding="5")
        frame_botones.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Button(frame_botones, text="🌱 Siembra",
                   command=lambda: self.abrir_ventana_venta('nueva'),
                   width=12).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Button(frame_botones, text="💧 Riego",
                   command=lambda: self.abrir_ventana_venta('riego'),
                   width=12).pack(side=tk.LEFT, padx=2, pady=2)
        
        ttk.Button(frame_botones, text="💰 Cuota", command=self.abrir_gestionar_cuotas, width=12).pack(side=tk.LEFT, padx=2, pady=2)
        
        ttk.Button(frame_botones, text="📋 Detalle",
                   command=self.abrir_detalle_dia,
                   width=12).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Button(frame_botones, text="📜 Historial",
                   command=self.abrir_historial_campesino,
                   width=12).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Button(frame_botones, text="✏️ Editar Lote",
          command=self.abrir_editar_lote,
          width=12).pack(side=tk.LEFT, padx=2, pady=2)
        # Frame de botones inferiores
        frame_botones_inf = ttk.Frame(scrollable_frame, padding="5")
        frame_botones_inf.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Button(frame_botones_inf, text="📊 Reporte",
                   command=self.generar_reporte_dia, width=12).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Button(frame_botones_inf, text="🔒 Cerrar Día",
                   command=self.cerrar_dia_dialog, width=12).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Button(frame_botones_inf, text="🔄 Ciclo",
                   command=lambda: VentanaReiniciarCiclo(self.root), width=12).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Button(frame_botones_inf, text="⚙️ Config",
                   command=self.abrir_configuracion, width=12).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Button(frame_botones_inf, text="💾 Backup",
                   command=self.crear_backup_manual, width=12).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Button(frame_botones_inf, text="📊 Estadísticas",
          command=self.abrir_estadisticas, width=12).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Button(frame_botones_inf, text="🔧 Admin",
                   command=self.abrir_administrar_datos, width=12).pack(side=tk.LEFT, padx=2, pady=2)
        
        # Cargar todos los campesinos
        self.cargar_todos_campesinos(ordenar_por_lote=True)

    def cargar_todos_campesinos(self, ordenar_por_lote=True):
        """
        Carga todos los campesinos ordenados SIEMPRE por lote (numérico).
        """
        self.tree.delete(*self.tree.get_children())
        
        campesinos = obtener_todos_campesinos()
        
        # Ordenar SIEMPRE por número de lote (numérico, no alfabético)
        campesinos = sorted(campesinos, 
                        key=lambda c: int(c['numero_lote']) 
                                        if str(c['numero_lote']).isdigit() 
                                        else 999999)
        
        # Agregar a la tabla
        for camp in campesinos:
            siembra = obtener_siembra_activa(camp['id'])
            cultivo = siembra['cultivo'] if siembra else '-'
            riegos = siembra['numero_riegos'] if siembra else 0
            
            self.tree.insert('', tk.END, iid=camp['id'], values=(
                camp['numero_lote'],
                camp['nombre'],
                camp['localidad'],
                camp['barrio'],
                f"{camp['superficie']:.2f}",
                cultivo,
                riegos
            ), tags=(str(camp['id']),))
        
        # Actualizar contador
        self.actualizar_total_dia()
 
    def abrir_estadisticas(self):
        """Abre la ventana de estadísticas"""
        VentanaEstadisticas(self.root)

    def on_buscar(self, event=None):
        """Busca campesinos según el criterio introducido."""
        termino = self.entry_busqueda.get().strip()
        
        if not termino:
            self.cargar_todos_campesinos(ordenar_por_lote=True)
            return
        
        # Usar la función mejorada
        resultados = buscar_campesino(termino)
        
        # Mostrar en tabla
        self.tree.delete(*self.tree.get_children())
        
        if not resultados:
            # Si no hay resultados
            self.tree.insert('', 'end', values=(
                '', 'No hay coincidencias', '', '', '', '', ''
            ))
            return
        
        # Mostrar resultados ordenados por lote numérico
        resultados_ordenados = sorted(resultados, 
                                    key=lambda c: int(c['numero_lote']) 
                                                if str(c['numero_lote']).isdigit() 
                                                else 999999)
        
        for camp in resultados_ordenados:
            siembra = obtener_siembra_activa(camp['id'])
            cultivo = siembra['cultivo'] if siembra else '-'
            riegos = siembra['numero_riegos'] if siembra else 0
            
            self.tree.insert('', 'end', iid=camp['id'], values=(
                camp['numero_lote'],
                camp['nombre'],
                camp['localidad'],
                camp['barrio'],
                f"{camp['superficie']:.2f}",
                cultivo,
                riegos
            ), tags=(str(camp['id']),))
 
    def limpiar_busqueda(self):
        """Limpia la búsqueda"""
        self.entry_busqueda.delete(0, tk.END)
        self.cargar_todos_campesinos()
    
    def on_seleccionar_campesino(self, event):
        """Maneja la selección de un campesino"""
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            if item['tags']:
                campesino_id = int(item['tags'][0])
                self.campesino_seleccionado = obtener_campesino_por_id(campesino_id)
    
    def on_doble_click(self, event):
        """Abre ventana de venta con doble click"""
        if self.campesino_seleccionado:
            self.abrir_ventana_venta('riego')
    
    def abrir_ventana_venta(self, tipo):
        """Abre la ventana de venta"""
        if not self.campesino_seleccionado:
            messagebox.showwarning("Advertencia", "Debe seleccionar un campesino primero")
            return
        
        VentanaVenta(self.root, self.campesino_seleccionado, tipo, self)
    
    def abrir_detalle_dia(self):
        """Abre la ventana de detalle del día"""
        VentanaDetalleDia(self.root, self)
    
    def abrir_historial_campesino(self):
        """Abre el historial del campesino seleccionado"""
        if not self.campesino_seleccionado:
            messagebox.showwarning("Advertencia", "Debe seleccionar un campesino primero")
            return
        
        VentanaHistorial(self.root, self.campesino_seleccionado)
    
    def abrir_form_nuevo_campesino(self):
        """Abre la ventana de formulario para crear nuevo campesino"""
        VentanaFormularioNuevoCampesino(self.root, self)
   
    def abrir_configuracion(self):
        """Abre el diálogo de configuración"""
        DialogoConfiguracion(self.root)
    
    def abrir_administrar_datos(self):
        """Abre el diálogo de administración de datos"""
        VentanaAdministrarDatos(self.root, self)
    
    def actualizar_total_dia(self):
        """Actualiza el total del día"""
        total = calcular_total_dia(self.fecha_actual)
        self.total_dia.set(f"{total:,.2f}")
  
    def abrir_editar_lote(self):
        """Abre ventana para editar lote (renombrar o partir)"""
        if not self.campesino_seleccionado:
            messagebox.showwarning("Advertencia", "Debe seleccionar un campesino primero")
            return
        
        VentanaEditarLote(self.root, self.campesino_seleccionado, self)
    
    def generar_reporte_dia(self):
        """Abre el gestor de reportes"""
        VentanaGestorReportes(self.root, self.fecha_actual)

    def abrir_gestionar_cuotas(self):
        """Abre la ventana de gestión de cuotas"""
        VentanaGestionarCuotas(self.root, self)

    def cerrar_dia_dialog(self):
        """Diálogo para cerrar el día"""
        if messagebox.askyesno("Cerrar Día",
                               "¿Desea generar el reporte del día y cerrar?"):
            try:
                resultado = cerrar_dia()
                mensaje = f"Día cerrado exitosamente\n"
                mensaje += f"Fecha: {resultado['fecha']}\n"
                mensaje += f"Total: ${resultado['total']:,.2f}\n"
                mensaje += f"Recibos: {resultado['cantidad_recibos']}"
                
                messagebox.showinfo("Día Cerrado", mensaje)
                
                if messagebox.askyesno("Reiniciar Contador",
                                       "¿Desea reiniciar el contador de venta a $0.00?"):
                    self.total_dia.set(0.0)
            except Exception as e:
                messagebox.showerror("Error", f"Error al cerrar día:\n{str(e)}")
    
    def crear_backup_manual(self):
        """Crea un backup manual"""
        if messagebox.askyesno("Crear Backup",
                               "¿Desea crear un respaldo de la base de datos?"):
            try:
                ruta = crear_backup("Backup manual")
                if ruta:
                    messagebox.showinfo("Éxito", f"Backup creado exitosamente:\n{ruta}")
                else:
                    messagebox.showerror("Error", "No se pudo crear el backup")
            except Exception as e:
                messagebox.showerror("Error", f"Error al crear backup:\n{str(e)}")


# ==================== VENTANA DE VENTA ====================

class VentanaVenta:
    """Ventana para vender riegos o iniciar nueva siembra - CON SCROLLBAR"""
    
    def __init__(self, parent, campesino, tipo, ventana_principal):
        self.ventana = tk.Toplevel(parent)
        self.ventana.title("Venta de Riego")
        self.ventana.geometry("500x600")
        self.ventana.transient(parent)
        self.ventana.grab_set()
        
        self.campesino = campesino
        self.tipo = tipo
        self.ventana_principal = ventana_principal
        
        # Variable para checkbox de cargo extra
        self.var_cargo_documentos = tk.BooleanVar(value=False)
        
        # ===== USAR SCROLLBAR =====
        self.canvas, self.frame_principal = crear_ventana_scrollable(self.ventana, None)
        
        self.crear_widgets()
    
    def crear_widgets(self):
        """Crea los widgets de la ventana"""
        
        # Frame de información del campesino
        frame_info = ttk.LabelFrame(self.frame_principal, text="Información del Campesino", padding="10")
        frame_info.pack(fill=tk.X, padx=10, pady=10)
        
        info_text = f"""
            Nombre: {self.campesino['nombre']}
            Lote: {self.campesino['numero_lote']}
            Localidad: {self.campesino['localidad']}
            Barrio: {self.campesino['barrio']}
            Superficie: {self.campesino['superficie']} hectáreas
            """
        ttk.Label(frame_info, text=info_text, font=('Helvetica', 10)).pack(anchor=tk.W)
        
        # Información de siembra actual
        siembra = obtener_siembra_activa(self.campesino['id'])
        if siembra:
            info_siembra = f"\n✅ Siembra activa: {siembra['cultivo']} - {siembra['numero_riegos']} riegos realizados"
            ttk.Label(frame_info, text=info_siembra,
                      font=('Helvetica', 10, 'bold'),
                      foreground='green').pack(anchor=tk.W)
        else:
            ttk.Label(frame_info, text="\n⚠️ No tiene siembra activa",
                      font=('Helvetica', 10, 'bold'),
                      foreground='orange').pack(anchor=tk.W)
        
        # ===== SECCIÓN DE EDITAR SIEMBRA/RIEGO =====
        frame_editar = ttk.LabelFrame(self.frame_principal, text="✏️ Editar Siembra/Riego", padding="10")
        frame_editar.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(frame_editar, text="✏️ Administrar Siembra y Riegos",
                   command=self.abrir_editar_siembra_riego,
                   width=50).pack(padx=5, pady=5)
        
        ttk.Label(frame_editar, text="Haz clic para editar/agregar siembras y riegos",
                  font=('Helvetica', 9),
                  foreground='gray').pack()
        
        # Frame de opciones
        frame_opciones = ttk.LabelFrame(self.frame_principal, text="¿Qué desea hacer?", padding="15")
        frame_opciones.pack(fill=tk.X, padx=10, pady=10)
        
        self.var_accion = tk.StringVar(value=self.tipo)
        
        # Radio buttons
        rb_nueva = ttk.Radiobutton(frame_opciones,
                                    text="🌱 Iniciar nueva siembra (cerrará la siembra actual)",
                                    variable=self.var_accion,
                                    value='nueva',
                                    command=self.on_cambiar_accion)
        rb_nueva.pack(anchor=tk.W, pady=5)
        
        rb_riego = ttk.Radiobutton(frame_opciones,
                                    text="💧 Vender riego adicional",
                                    variable=self.var_accion,
                                    value='riego',
                                    command=self.on_cambiar_accion)
        rb_riego.pack(anchor=tk.W, pady=5)
        
        # Selección de cultivo
        frame_cultivo = ttk.Frame(frame_opciones)
        frame_cultivo.pack(fill=tk.X, pady=10)
        
        ttk.Label(frame_cultivo, text="Cultivo:", font=('Helvetica', 10)).pack(side=tk.LEFT, padx=5)
        self.combo_cultivo = ttk.Combobox(frame_cultivo,
                                          values=CULTIVOS,
                                          state='readonly',
                                          width=20)
        self.combo_cultivo.pack(side=tk.LEFT, padx=5)
        
        # Preseleccionar cultivo si hay siembra activa
        if siembra and self.tipo == 'riego':
            idx = CULTIVOS.index(siembra['cultivo']) if siembra['cultivo'] in CULTIVOS else -1
            if idx >= 0:
                self.combo_cultivo.current(idx)
                self.combo_cultivo.config(state='disabled')
        
        # Frame de checkbox de cargo extra
        frame_cargo = ttk.LabelFrame(self.frame_principal, text="📄 Opciones de Cobro", padding="10")
        frame_cargo.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Checkbutton(frame_cargo,
                       text="📄 Cargo extra por documentos (precio x2)",
                       variable=self.var_cargo_documentos,
                       command=self.actualizar_monto_mostrado).pack(anchor=tk.W, pady=5)
        
        # Frame de costo
        frame_costo = ttk.LabelFrame(self.frame_principal, text="💰 Monto a Cobrar", padding="15")
        frame_costo.pack(fill=tk.X, padx=10, pady=10)
        
        costo = calcular_costo(self.campesino['superficie'])
        self.label_costo = ttk.Label(frame_costo,
                  text=f"${costo:,.2f}",
                  font=('Helvetica', 20, 'bold'),
                  foreground='green')
        self.label_costo.pack()
        
        tarifa = obtener_configuracion('tarifa_hectarea')
        self.label_tarifa = ttk.Label(frame_costo,
                  text=f"({self.campesino['superficie']} ha × ${tarifa}/ha)",
                  font=('Helvetica', 9),
                  foreground='gray')
        self.label_tarifa.pack()
        
        # Frame de botones
        frame_botones = ttk.Frame(self.frame_principal)
        frame_botones.pack(fill=tk.X, padx=10, pady=20)
        
        ttk.Button(frame_botones,
                   text="✅ Generar Recibo e Imprimir",
                   command=self.generar_recibo,
                   width=30).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(frame_botones,
                   text="❌ Cancelar",
                   command=self.ventana.destroy,
                   width=15).pack(side=tk.LEFT, padx=5)
    
    def abrir_editar_siembra_riego(self):
        """Abre la ventana para editar siembra y riego"""
        VentanaEditarSiembraRiego(self.ventana, self.campesino['id'], self.campesino['nombre'], self.ventana_principal)
    
    def actualizar_monto_mostrado(self):
        """Actualiza el monto mostrado cuando cambia el checkbox de cargo extra"""
        costo_base = calcular_costo(self.campesino['superficie'])
        
        if self.var_cargo_documentos.get():
            costo_final = costo_base * 2
            tarifa = obtener_configuracion('tarifa_hectarea')
            self.label_costo.config(text=f"${costo_final:,.2f}", foreground='red')
            self.label_tarifa.config(
                text=f"({self.campesino['superficie']} ha × ${tarifa}/ha × 2 = CARGO POR DOCUMENTOS)",
                foreground='red'
            )
        else:
            tarifa = obtener_configuracion('tarifa_hectarea')
            self.label_costo.config(text=f"${costo_base:,.2f}", foreground='green')
            self.label_tarifa.config(
                text=f"({self.campesino['superficie']} ha × ${tarifa}/ha)",
                foreground='gray'
            )
    
    def on_cambiar_accion(self):
        """Maneja el cambio de acción"""
        if self.var_accion.get() == 'riego':
            siembra = obtener_siembra_activa(self.campesino['id'])
            if siembra:
                idx = CULTIVOS.index(siembra['cultivo']) if siembra['cultivo'] in CULTIVOS else -1
                if idx >= 0:
                    self.combo_cultivo.current(idx)
                    self.combo_cultivo.config(state='disabled')
        else:
            self.combo_cultivo.config(state='readonly')
    
    def generar_recibo(self):
        """Genera el recibo y lo imprime - RECIBOS TEMPORALES"""
        # Validar cultivo
        if not self.combo_cultivo.get():
            messagebox.showwarning("Advertencia", "Debe seleccionar un cultivo")
            return
        
        try:
            accion = self.var_accion.get()
            cultivo = self.combo_cultivo.get()
            cargo_docs = self.var_cargo_documentos.get()
            
            # Generar venta con cargo por documentos si está marcado
            if accion == 'nueva':
                resultado = nueva_siembra(self.campesino['id'], cultivo, cargo_documentos=cargo_docs)
                tipo_texto = "Nueva siembra"
            else:
                resultado = vender_riego(self.campesino['id'], cargo_documentos=cargo_docs)
                tipo_texto = "Riego adicional"
            
            # Generar recibo temporal
            pdf_path = generar_recibo_pdf_temporal(resultado['recibo_id'])
            
            # Abrir vista previa
            abrir_pdf(pdf_path)
            
            # Preguntar si desea imprimir
            if messagebox.askyesno("Imprimir Recibo",
                                   f"Recibo generado exitosamente\nFolio: {resultado['folio']}\nCosto: ${resultado['costo']:.2f}\n\n¿Desea imprimir?"):
                imprimir_recibo_y_limpiar(pdf_path)
            else:
                # Eliminar si no va a imprimir
                try:
                    os.remove(pdf_path)
                except:
                    pass
            
            messagebox.showinfo("Éxito",
                                f"{tipo_texto} registrado exitosamente\nFolio: {resultado['folio']}\nCosto: ${resultado['costo']:.2f}")
            
            # Actualizar ventana principal
            self.ventana_principal.actualizar_total_dia()
            self.ventana_principal.cargar_todos_campesinos()

            # Cerrar ventana
            self.ventana.destroy()
            
        except ValueError as e:
            messagebox.showerror("Error de Validación", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Error al generar recibo:\n{str(e)}")

# ==================== VENTANA EDITAR SIEMBRA Y RIEGO ====================

class VentanaEditarSiembraRiego:
    """Ventana para editar la siembra y riego de un campesino - CON SCROLLBAR"""
    
    def __init__(self, parent, campesino_id: int, campesino_nombre: str, ventana_principal=None):
        self.campesino_id = campesino_id
        self.campesino_nombre = campesino_nombre
        self.ventana_principal = ventana_principal
        self.siembra_id = None
        
        self.ventana = tk.Toplevel(parent)
        self.ventana.title(f"✏️ Editar Siembra/Riego - {campesino_nombre}")
        self.ventana.geometry("600x600")
        self.ventana.transient(parent)
        self.ventana.grab_set()
        
        self.siembra_activa = obtener_siembra_activa(campesino_id)
        
        # ===== USAR SCROLLBAR =====
        self.canvas, self.frame_principal = crear_ventana_scrollable(self.ventana, None)
        
        self.crear_widgets()
    
    def crear_widgets(self):
        """Crea los widgets de la ventana"""
        
        # Título
        ttk.Label(self.frame_principal, text=f"✏️ Editar Siembra de {self.campesino_nombre}",
                  font=('Helvetica', 12, 'bold')).pack(pady=10)
        
        # Frame de formulario
        frame_form = ttk.LabelFrame(self.frame_principal, text="Datos de la Siembra", padding="10")
        frame_form.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Cultivo
        ttk.Label(frame_form, text="Cultivo:").grid(row=0, column=0, sticky="w", pady=5)
        self.combo_cultivo = ttk.Combobox(frame_form, values=CULTIVOS, width=40, state='readonly')
        self.combo_cultivo.grid(row=0, column=1, sticky="ew", pady=5, padx=10)
        
        if self.siembra_activa:
            self.combo_cultivo.set(self.siembra_activa['cultivo'])
            self.siembra_id = self.siembra_activa['id']
        
        # Ciclo
        ttk.Label(frame_form, text="Ciclo:").grid(row=1, column=0, sticky="w", pady=5)
        self.entry_ciclo = ttk.Entry(frame_form, width=42)
        self.entry_ciclo.grid(row=1, column=1, sticky="ew", pady=5, padx=10)
        
        ciclo_actual = obtener_configuracion('ciclo_actual') or 'SIN CICLO'
        self.entry_ciclo.insert(0, ciclo_actual)
        
        if self.siembra_activa:
            self.entry_ciclo.delete(0, tk.END)
            self.entry_ciclo.insert(0, self.siembra_activa['ciclo'])
        
        # Fecha inicio
        ttk.Label(frame_form, text="Fecha Inicio (YYYY-MM-DD):").grid(row=2, column=0, sticky="w", pady=5)
        self.entry_fecha_inicio = ttk.Entry(frame_form, width=42)
        self.entry_fecha_inicio.grid(row=2, column=1, sticky="ew", pady=5, padx=10)
        
        fecha_default = datetime.now().strftime('%Y-%m-%d')
        self.entry_fecha_inicio.insert(0, fecha_default)
        
        if self.siembra_activa:
            self.entry_fecha_inicio.delete(0, tk.END)
            self.entry_fecha_inicio.insert(0, self.siembra_activa['fecha_inicio'])
        
        # Número de riegos EDITABLE
        ttk.Label(frame_form, text="Número de Riegos:").grid(row=3, column=0, sticky="w", pady=5)
        self.entry_riegos = ttk.Entry(frame_form, width=42)
        self.entry_riegos.grid(row=3, column=1, sticky="ew", pady=5, padx=10)
        
        # Permitir solo números
        vcmd = (self.ventana.register(self.solo_numeros), '%P')
        self.entry_riegos.config(validate='key', validatecommand=vcmd)
        
        if self.siembra_activa:
            self.entry_riegos.insert(0, str(self.siembra_activa['numero_riegos']))
        else:
            self.entry_riegos.insert(0, "0")
        
        # Información adicional
        info_frame = ttk.LabelFrame(self.frame_principal, text="ℹ️ Información", padding="10")
        info_frame.pack(fill=tk.X, padx=10, pady=10)
        
        if self.siembra_activa:
            info_text = f"Siembra activa desde: {self.siembra_activa['fecha_inicio']}"
            ttk.Label(info_frame, text=info_text, foreground='green').pack(anchor="w")
        else:
            info_text = "No hay siembra activa. Puedes crear una nueva."
            ttk.Label(info_frame, text=info_text, foreground='orange').pack(anchor="w")
        
        # Frame de botones
        frame_botones = ttk.Frame(self.frame_principal, padding="10")
        frame_botones.pack(fill=tk.X, padx=10, pady=15)
        
        ttk.Button(frame_botones, text="💾 Guardar", command=self.guardar).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones, text="❌ Cancelar", command=self.ventana.destroy).pack(side=tk.LEFT, padx=5)
        
        if self.siembra_activa:
            ttk.Button(frame_botones, text="➕ Agregar Riego", command=self.agregar_riego).pack(side=tk.LEFT, padx=5)
        
        frame_form.columnconfigure(1, weight=1)
    
    def solo_numeros(self, value):
        """Valida que solo se ingresen números"""
        if value == "":
            return True
        try:
            int(value)
            return True
        except ValueError:
            return False
    
    def guardar(self):
        """Guarda los cambios en la siembra"""
        cultivo = self.combo_cultivo.get()
        ciclo = self.entry_ciclo.get()
        fecha_inicio = self.entry_fecha_inicio.get()
        numero_riegos_str = self.entry_riegos.get()
        
        if not cultivo:
            messagebox.showerror("Error", "Debe seleccionar un cultivo")
            return
        
        if not ciclo:
            messagebox.showerror("Error", "El ciclo es obligatorio")
            return
        
        if not numero_riegos_str or numero_riegos_str == "":
            messagebox.showerror("Error", "Debe ingresar el número de riegos")
            return
        
        try:
            numero_riegos = int(numero_riegos_str)
            if numero_riegos < 0:
                messagebox.showerror("Error", "El número de riegos no puede ser negativo")
                return
        except ValueError:
            messagebox.showerror("Error", "El número de riegos debe ser un número entero")
            return
        
        try:
            datetime.strptime(fecha_inicio, '%Y-%m-%d')
        except ValueError:
            messagebox.showerror("Error", "Fecha inválida (formato YYYY-MM-DD)")
            return
        
        try:
            if self.siembra_activa:
                # Actualizar siembra existente
                datos_a_actualizar = {}
                
                if cultivo != self.siembra_activa.get('cultivo'):
                    datos_a_actualizar['cultivo'] = cultivo
                
                if ciclo != self.siembra_activa.get('ciclo'):
                    datos_a_actualizar['ciclo'] = ciclo
                
                if fecha_inicio != self.siembra_activa.get('fecha_inicio'):
                    datos_a_actualizar['fecha_inicio'] = fecha_inicio
                
                if numero_riegos != self.siembra_activa.get('numero_riegos'):
                    datos_a_actualizar['numero_riegos'] = numero_riegos
                
                # Solo hacer update si hay cambios
                if datos_a_actualizar:
                    actualizar_siembra_db(self.siembra_id, datos_a_actualizar)
                    messagebox.showinfo("Éxito", "Siembra actualizada correctamente")
                else:
                    messagebox.showinfo("Información", "No hay cambios para guardar")
            else:
                # Crear nueva siembra
                self.siembra_id = crear_siembra_db(self.campesino_id, cultivo, ciclo)
                
                # Actualizar la fecha de inicio y número de riegos si es necesario
                datos_actualizar = {}
                if fecha_inicio != datetime.now().strftime('%Y-%m-%d'):
                    datos_actualizar['fecha_inicio'] = fecha_inicio
                
                if numero_riegos > 0:
                    datos_actualizar['numero_riegos'] = numero_riegos
                
                if datos_actualizar:
                    actualizar_siembra_db(self.siembra_id, datos_actualizar)
                
                messagebox.showinfo("Éxito", "Siembra creada correctamente")
            
            self.ventana.destroy()
            
            if self.ventana_principal:
                self.ventana_principal.cargar_todos_campesinos()
                
        except Exception as e:
            import traceback
            print(f"Error detallado: {traceback.format_exc()}")
            messagebox.showerror("Error", f"Error al guardar: {str(e)}")
    
    def agregar_riego(self):
        """Abre ventana para agregar un riego manualmente"""
        VentanaAgregarRiego(self.ventana, self.campesino_id, self.siembra_id, self.campesino_nombre)


# ==================== VENTANA AGREGAR RIEGO ====================

class VentanaAgregarRiego:
    """Ventana para agregar un riego manualmente a una siembra"""
    
    def __init__(self, parent, campesino_id: int, siembra_id: int, campesino_nombre: str):
        self.campesino_id = campesino_id
        self.siembra_id = siembra_id
        self.campesino_nombre = campesino_nombre
        
        self.ventana = tk.Toplevel(parent)
        self.ventana.title(f"➕ Agregar Riego - {campesino_nombre}")
        self.ventana.geometry("500x450")
        self.ventana.transient(parent)
        self.ventana.grab_set()
        
        self.crear_widgets()
    
    def crear_widgets(self):
        """Crea los widgets de la ventana"""
        frame_principal = ttk.Frame(self.ventana, padding="20")
        frame_principal.pack(fill=tk.BOTH, expand=True)
        
        # Título
        ttk.Label(frame_principal, text=f"Agregar Riego a {self.campesino_nombre}",
                  font=('Helvetica', 12, 'bold')).pack(pady=10)
        
        # Frame de formulario
        frame_form = ttk.LabelFrame(frame_principal, text="Datos del Riego", padding="10")
        frame_form.pack(fill=tk.BOTH, expand=True, padx=0, pady=10)
        
        # Obtener siembra para calcular próximo número
        siembra = obtener_siembra_por_id(self.siembra_id)
        proximo_numero = (siembra['numero_riegos'] if siembra else 0) + 1
        
        # Número de riego (calculado automáticamente)
        ttk.Label(frame_form, text="Número de Riego:").grid(row=0, column=0, sticky="w", pady=5)
        self.label_numero_riego = ttk.Label(frame_form, text=str(proximo_numero),
                                            font=('Helvetica', 11, 'bold'))
        self.label_numero_riego.grid(row=0, column=1, sticky="w", pady=5, padx=10)
        
        # Tipo de acción
        ttk.Label(frame_form, text="Tipo de Acción:").grid(row=1, column=0, sticky="w", pady=5)
        self.combo_accion = ttk.Combobox(frame_form, values=["Riego adicional", "Mantenimiento"], width=40, state='readonly')
        self.combo_accion.grid(row=1, column=1, sticky="ew", pady=5, padx=10)
        self.combo_accion.set("Riego adicional")
        
        # Fecha
        ttk.Label(frame_form, text="Fecha (YYYY-MM-DD):").grid(row=2, column=0, sticky="w", pady=5)
        self.entry_fecha = ttk.Entry(frame_form, width=42)
        self.entry_fecha.grid(row=2, column=1, sticky="ew", pady=5, padx=10)
        self.entry_fecha.insert(0, datetime.now().strftime('%Y-%m-%d'))
        
        # Hora
        ttk.Label(frame_form, text="Hora (HH:MM:SS):").grid(row=3, column=0, sticky="w", pady=5)
        self.entry_hora = ttk.Entry(frame_form, width=42)
        self.entry_hora.grid(row=3, column=1, sticky="ew", pady=5, padx=10)
        self.entry_hora.insert(0, datetime.now().strftime('%H:%M:%S'))
        
        # Frame de botones
        frame_botones = ttk.Frame(frame_principal, padding="10")
        frame_botones.pack(fill=tk.X, padx=0, pady=15)
        
        ttk.Button(frame_botones, text="✅ Guardar Riego", command=self.guardar).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones, text="❌ Cancelar", command=self.ventana.destroy).pack(side=tk.LEFT, padx=5)
        
        frame_form.columnconfigure(1, weight=1)
    
    def guardar(self):
        """Guarda el nuevo riego"""
        try:
            fecha = self.entry_fecha.get()
            hora = self.entry_hora.get()
            
            # Validar fecha y hora
            datetime.strptime(fecha, '%Y-%m-%d')
            datetime.strptime(hora, '%H:%M:%S')
            
            # Obtener datos del campesino para calcular costo
            campesino = obtener_campesino_por_id(self.campesino_id)
            costo = calcular_costo(campesino['superficie'])
            
            # Crear recibo/riego manualmente
            folio = incrementar_folio()
            siembra = obtener_siembra_por_id(self.siembra_id)
            numero_riego = siembra['numero_riegos'] + 1
            
            datos_recibo = {
                'folio': folio,
                'fecha': fecha,
                'hora': hora,
                'campesino_id': self.campesino_id,
                'siembra_id': self.siembra_id,
                'cultivo': siembra['cultivo'],
                'numero_riego': numero_riego,
                'tipo_accion': self.combo_accion.get(),
                'costo': costo,
                'ciclo': siembra['ciclo']
            }
            
            crear_recibo_db(datos_recibo)
            incrementar_riegos(self.siembra_id)
            
            messagebox.showinfo("Éxito", f"Riego #{numero_riego} registrado correctamente\nFolio: {folio}")
            self.ventana.destroy()
            
        except ValueError as e:
            messagebox.showerror("Error de validación", "Fecha u hora inválida (formato YYYY-MM-DD y HH:MM:SS)")
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar riego: {str(e)}")

# ==================== VENTANA REINICIAR CICLO ====================

class VentanaReiniciarCiclo:
    """Ventana para gestionar ciclo y folio - CON SCROLLBAR"""
    
    def __init__(self, parent):
        self.ventana = tk.Toplevel(parent)
        self.ventana.title("🔄 Gestionar Ciclo y Folio")
        self.ventana.geometry("550x500")
        self.ventana.resizable(False, False)
        self.ventana.transient(parent)
        self.ventana.grab_set()
        
        self.crear_widgets()
    
    def crear_widgets(self):
        # ===== AGREGAR SCROLLBAR =====
        canvas, scrollable_frame = crear_ventana_scrollable(self.ventana, None)
        
        frame_principal = ttk.Frame(scrollable_frame, padding="20")
        frame_principal.pack(fill=tk.BOTH, expand=True)
        
        # Título
        ttk.Label(frame_principal, text="🔄 GESTIONAR CICLO Y FOLIO",
                 font=('Helvetica', 14, 'bold')).pack(pady=10)
        
        # Información actual
        info_frame = ttk.LabelFrame(frame_principal, text="📋 Información Actual", padding="10")
        info_frame.pack(fill=tk.X, pady=10)
        
        ciclo_actual = obtener_configuracion('ciclo_actual') or 'SIN CICLO'
        folio_actual = obtener_configuracion('folio_actual') or '1'
        
        ttk.Label(info_frame, text=f"Ciclo actual: {ciclo_actual}",
                 font=('Helvetica', 10, 'bold'), foreground='blue').pack(anchor=tk.W, pady=2)
        ttk.Label(info_frame, text=f"Folio actual: {folio_actual}",
                 font=('Helvetica', 10, 'bold'), foreground='blue').pack(anchor=tk.W, pady=2)
        
        # OPCIÓN 1: Solo reiniciar folio
        opcion1_frame = ttk.LabelFrame(frame_principal, text="📄 Opción 1: Solo Reiniciar Folio", padding="15")
        opcion1_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(opcion1_frame, text="Reinicia el folio a 1 sin cambiar el ciclo actual",
                 font=('Helvetica', 9), foreground='gray').pack(anchor=tk.W, pady=5)
        
        ttk.Button(opcion1_frame, text="🔄 Reiniciar Solo Folio a 1",
                  command=self.reiniciar_solo_folio,
                  width=35).pack(pady=5)
        
        # OPCIÓN 2: Cambiar ciclo y reiniciar folio
        opcion2_frame = ttk.LabelFrame(frame_principal, text="🔄 Opción 2: Cambiar Ciclo y Reiniciar Folio", padding="15")
        opcion2_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(opcion2_frame, text="Nuevo nombre del ciclo:",
                 font=('Helvetica', 10, 'bold')).pack(anchor=tk.W, pady=(5, 2))
        
        self.entry_ciclo = ttk.Entry(opcion2_frame, width=45, font=('Helvetica', 11))
        self.entry_ciclo.pack(pady=5, fill=tk.X)
        
        # Sugerir nombre de ciclo
        from datetime import datetime
        ciclo_sugerido = f"CICLO {datetime.now().strftime('%B %Y').upper()}"
        self.entry_ciclo.insert(0, ciclo_sugerido)
        
        ttk.Label(opcion2_frame, text="⚠️ Esto cambiará el ciclo Y reiniciará el folio a 1",
                 font=('Helvetica', 9), foreground='orange').pack(anchor=tk.W, pady=5)
        
        ttk.Button(opcion2_frame, text="🔄 Cambiar Ciclo y Reiniciar Folio",
                  command=self.reiniciar_ciclo_completo,
                  width=35).pack(pady=10)
        
        # Botón cerrar
        ttk.Button(frame_principal, text="❌ Cerrar",
                  command=self.ventana.destroy,
                  width=15).pack(pady=15)
    
    def reiniciar_solo_folio(self):
        """Reinicia solo el folio a 1 sin cambiar el ciclo"""
        if messagebox.askyesno("Confirmar", 
                              "¿Reiniciar el folio a 1?\n\n"
                              "El ciclo actual NO será modificado."):
            try:
                actualizar_configuracion('folio_actual', '1')
                
                registrar_auditoria(
                    'FOLIO_REINICIADO',
                    "Folio reiniciado a 1 (ciclo no modificado)",
                    None
                )
                
                messagebox.showinfo("Éxito", 
                                  "Folio reiniciado a 1 correctamente.\n"
                                  "El ciclo actual se mantiene sin cambios.")
                self.ventana.destroy()
                
            except Exception as e:
                messagebox.showerror("Error", f"Error al reiniciar folio:\n{str(e)}")
    
    def reiniciar_ciclo_completo(self):
        """Reinicia ciclo y folio"""
        nuevo_ciclo = self.entry_ciclo.get().strip()
        
        if not nuevo_ciclo:
            messagebox.showerror("Error", "Debe ingresar el nombre del nuevo ciclo")
            return
        
        if messagebox.askyesno("Confirmar", 
                              f"¿Cambiar al ciclo '{nuevo_ciclo}' y reiniciar folio a 1?\n\n"
                              f"Esto afectará todos los recibos futuros."):
            try:
                if reiniciar_folios_y_ciclo(nuevo_ciclo):
                    messagebox.showinfo("Éxito", 
                                      f"Ciclo cambiado a '{nuevo_ciclo}'.\n"
                                      f"Folio reiniciado a 1.\n"
                                      f"Datos de usuarios preservados.")
                    self.ventana.destroy()
                else:
                    messagebox.showerror("Error", "Error al cambiar el ciclo")
                    
            except Exception as e:
                messagebox.showerror("Error", f"Error: {str(e)}")

# ==================== VENTANA DETALLE DEL DÍA ====================

class VentanaDetalleDia:
    """Ventana para ver el detalle de ventas del día - CON SCROLLBAR"""
    
    def __init__(self, parent, ventana_principal):
        self.ventana = tk.Toplevel(parent)
        self.ventana.title("Detalle del Día")
        self.ventana.geometry("1100x650")
        self.ventana.transient(parent)
        
        self.ventana_principal = ventana_principal
        self.fecha_actual = datetime.now().strftime('%Y-%m-%d')
        
        # ===== USAR SCROLLBAR =====
        self.canvas, self.frame_principal = crear_ventana_scrollable(self.ventana, None)
        
        self.crear_widgets()
        self.cargar_recibos()
        self.ventana_principal.cargar_todos_campesinos()  # Refresca la tabla principal

    def crear_widgets(self):
        """Crea los widgets de la ventana"""
        
        # Frame superior
        frame_superior = ttk.Frame(self.frame_principal)
        frame_superior.pack(fill=tk.X, padx=10, pady=10)
        
        fecha_texto = datetime.now().strftime('%d/%m/%Y')
        ttk.Label(frame_superior,
                  text=f"📊 Detalle de Ventas - {fecha_texto}",
                  font=('Helvetica', 14, 'bold')).pack()
        
        # Frame de tabla
        frame_tabla = ttk.Frame(self.frame_principal)
        frame_tabla.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Crear Treeview
        columnas = ('folio', 'hora', 'lote', 'nombre', 'cultivo', 'riego', 'monto')
        self.tree = ttk.Treeview(frame_tabla, columns=columnas, show='headings', height=20)
        
        # Encabezados
        self.tree.heading('folio', text='Folio')
        self.tree.heading('hora', text='Hora')
        self.tree.heading('lote', text='Lote')
        self.tree.heading('nombre', text='Nombre')
        self.tree.heading('cultivo', text='Cultivo')
        self.tree.heading('riego', text='Riego #')
        self.tree.heading('monto', text='Monto')
        
        # Anchos
        self.tree.column('folio', width=80)
        self.tree.column('hora', width=80)
        self.tree.column('lote', width=80)
        self.tree.column('nombre', width=250)
        self.tree.column('cultivo', width=100)
        self.tree.column('riego', width=80)
        self.tree.column('monto', width=100)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(frame_tabla, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Frame de botones de acciones
        frame_acciones = ttk.Frame(self.frame_principal)
        frame_acciones.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(frame_acciones,
                   text="🗑️ Eliminar Recibo Seleccionado",
                   command=self.eliminar_recibo).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(frame_acciones,
                   text="🖨️ Reimprimir Recibo",
                   command=self.reimprimir_recibo).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(frame_acciones,
                   text="📥 Exportar a Excel",
                   command=self.exportarexcel).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(frame_acciones, text="💰 Recaudación Cuotas Hoy", command=self.exportar_cuotas_dia, width=22).pack(side=tk.LEFT, padx=5)

        
        ttk.Button(frame_acciones,
                   text="🔄 Actualizar",
                   command=self.cargar_recibos).pack(side=tk.LEFT, padx=5)
        
        # Frame de totales
        frame_totales = ttk.LabelFrame(self.frame_principal, text="Totales del Día", padding="10")
        frame_totales.pack(fill=tk.X, padx=10, pady=10)
        
        self.label_total = ttk.Label(frame_totales,
                                     text="Total: $0.00",
                                     font=('Helvetica', 16, 'bold'),
                                     foreground='green')
        self.label_total.pack()
        
        self.label_cantidad = ttk.Label(frame_totales,
                                        text="Recibos emitidos: 0",
                                        font=('Helvetica', 10))
        self.label_cantidad.pack()
    
    def cargar_recibos(self):
        """Carga los recibos del día"""
        self.tree.delete(*self.tree.get_children())
        recibos = obtener_recibos_dia(self.fecha_actual)
        total = 0
        
        for r in recibos:
            self.tree.insert('', tk.END, values=(
                r['folio'],
                r['hora'][:5],  # Solo HH:MM
                r['numero_lote'],
                r['nombre'][:30],  # Truncar nombre
                r['cultivo'],
                r['numero_riego'],
                f"${r['costo']:.2f}"
            ), tags=(str(r['id']),))
            total += r['costo']
        
        # Actualizar totales
        self.label_total.config(text=f"Total: ${total:,.2f}")
        self.label_cantidad.config(text=f"Recibos emitidos: {len(recibos)}")
    
    def eliminar_recibo(self):
        """Elimina el recibo seleccionado y actualiza TODA la UI"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Advertencia", "Debe seleccionar un recibo")
            return
        
        item = self.tree.item(selection[0])
        recibo_id = int(item['tags'][0])
        
        # Obtener datos del recibo
        recibo = obtener_recibo_por_id(recibo_id)
        if not recibo:
            messagebox.showerror("Error", "Recibo no encontrado")
            return
        
        # Validar si es el último recibo
        from modules.logic import obtener_folio_actual
        folio_actual = obtener_folio_actual()
        es_ultimo_recibo = (recibo['folio'] == folio_actual - 1)
        
        if not es_ultimo_recibo:
            advertencia = (
                f"⚠️ ADVERTENCIA: Este recibo (folio #{recibo['folio']}) NO es el más reciente.\n\n"
                f"Folio actual del sistema: {folio_actual - 1}\n\n"
                f"Al eliminar este recibo:\n"
                f"• El folio NO se decrementará\n"
                f"• Quedará un 'hueco' en la numeración\n"
                f"• Se recomienda SOLO eliminar el último recibo creado\n\n"
                f"¿Está seguro de continuar?"
            )
            
            if not messagebox.askyesno("Confirmar Eliminación", advertencia):
                return
        
        # Pedir motivo de eliminación
        motivo = simpledialog.askstring("Motivo de Eliminación", 
                                        "Ingrese el motivo para eliminar el recibo:")
        
        if not motivo:
            messagebox.showwarning("Advertencia", "Debe ingresar un motivo")
            return
        
        # Confirmar eliminación
        if messagebox.askyesno("Confirmar", 
                            f"¿Eliminar recibo folio #{recibo['folio']}?\n"
                            f"Campesino: {recibo['nombre']}\n"
                            f"Monto: ${recibo['costo']:.2f}"):
            try:
                # Eliminar recibo (esto revierte la siembra/riego automáticamente)
                from modules.logic import eliminar_recibo_dia
                monto = eliminar_recibo_dia(recibo_id, motivo)
                
                messagebox.showinfo("Éxito", 
                                f"Recibo eliminado correctamente\n"
                                f"Folio: {recibo['folio']}\n"
                                f"Monto restado: ${monto:.2f}")
                
                # ===== ACTUALIZAR TODA LA INTERFAZ =====
                # 1. Actualizar total del día
                self.ventana_principal.actualizar_total_dia()
                
                # 2. Recargar lista de recibos del día
                self.cargar_recibos()
                
                # 3. IMPORTANTE: Recargar tabla de campesinos (refleja cambios en siembra/riegos)
                self.ventana_principal.cargar_todos_campesinos()
                
                # 4. Si estás en la ventana principal, actualizar folio visible
                if hasattr(self.ventana_principal, 'actualizar_folio_ui'):
                    self.ventana_principal.actualizar_folio_ui()
                
            except ValueError as e:
                messagebox.showerror("Error", str(e))
            except Exception as e:
                messagebox.showerror("Error", f"Error al eliminar recibo:\n{str(e)}")

    def reimprimir_recibo(self):
        """Reimprime el recibo seleccionado - RECIBOS TEMPORALES"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Advertencia", "Debe seleccionar un recibo")
            return
        
        item = self.tree.item(selection[0])
        recibo_id = int(item['tags'][0])
        
        try:
            pdf_path = generar_recibo_pdf_temporal(recibo_id, es_reimpresion=True)
            abrir_pdf(pdf_path)
            
            if messagebox.askyesno("Imprimir", "¿Desea imprimir la reimpresión?"):
                imprimir_recibo_y_limpiar(pdf_path)
            else:
                try:
                    os.remove(pdf_path)
                except:
                    pass
        except Exception as e:
            messagebox.showerror("Error", f"Error al reimprimir:\n{str(e)}")
    
    def exportar_cuotas_dia(self):
        """Exporta reporte de cuotas cobradas hoy"""
        try:
            from modules.reports import generar_reporte_cuotas_dia_pdf
            
            pdf_path = generar_reporte_cuotas_dia_pdf()
            
            from modules.reports import abrir_pdf
            abrir_pdf(pdf_path)
            
            messagebox.showinfo("Éxito", 
                                f"Reporte de cuotas del día generado correctamente\n"
                                f"Ruta: {pdf_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Error al generar reporte de cuotas:\n{str(e)}")

    
    def exportarexcel(self):
        """Exporta los recibos a Excel"""
        try:
            recibos = obtenerrecibosdia(self.fechaactual)
            if not recibos:
                messagebox.showinfo("Información", "No hay recibos para exportar")
                return
            
            # CORRECCIÓN: Usar self.fechaactual en lugar de datetime.now()
            # Esto mantiene consistencia con los PDFs que también usan la fecha consultada
            fechaarchivo = datetime.strptime(self.fechaactual, "%Y-%m-%d").strftime("%Y%m%d")
            filename = f"recibos_{fechaarchivo}.xlsx"  # Agregado guión bajo para claridad
            
            filepath = exportaraexcel(recibos, filename)
            messagebox.showinfo("Éxito", f"Archivo exportado:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Error al exportar:{str(e)}")

# ==================== FORMULARIO CAMPESINO ====================

class FormularioCampesino:
    """Formulario para crear o editar campesino - CON SCROLLBAR"""
    
    def __init__(self, parent, campesino_id, ventana_principal):
        self.ventana = tk.Toplevel(parent)
        self.ventana.title("Nuevo Campesino" if not campesino_id else "Editar Campesino")
        self.ventana.geometry("500x600")
        self.ventana.transient(parent)
        self.ventana.grab_set()
        
        self.campesino_id = campesino_id
        self.ventana_principal = ventana_principal
        self.campesino = obtener_campesino_por_id(campesino_id) if campesino_id else None
        
        # ===== USAR SCROLLBAR =====
        self.canvas, self.frame_principal = crear_ventana_scrollable(self.ventana, None)
        
        self.crear_widgets()
    
    def crear_widgets(self):
        """Crea los widgets del formulario"""
        
        frame_form = ttk.Frame(self.frame_principal, padding="20")
        frame_form.pack(fill=tk.BOTH, expand=True)
        
        # Número de lote
        ttk.Label(frame_form, text="Número de Lote:", font=('Helvetica', 10)).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.entry_lote = ttk.Entry(frame_form, width=30)
        self.entry_lote.grid(row=0, column=1, pady=5, padx=10)
        
        if self.campesino:
            self.entry_lote.insert(0, self.campesino['numero_lote'])
            self.entry_lote.config(state='disabled')
        
        # Nombre completo
        ttk.Label(frame_form, text="Nombre Completo:", font=('Helvetica', 10)).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.entry_nombre = ttk.Entry(frame_form, width=30)
        self.entry_nombre.grid(row=1, column=1, pady=5, padx=10)
        
        if self.campesino:
            self.entry_nombre.insert(0, self.campesino['nombre'])
        
        # Localidad
        ttk.Label(frame_form, text="Localidad:", font=('Helvetica', 10)).grid(row=2, column=0, sticky=tk.W, pady=5)
        self.entry_localidad = ttk.Entry(frame_form, width=30)
        self.entry_localidad.grid(row=2, column=1, pady=5, padx=10)
        
        if self.campesino:
            self.entry_localidad.insert(0, self.campesino['localidad'])
        else:
            self.entry_localidad.insert(0, "Tezontepec de Aldama")
        
        # Barrio
        ttk.Label(frame_form, text="Barrio:", font=('Helvetica', 10)).grid(row=3, column=0, sticky=tk.W, pady=5)
        barrios = ['PANUAYA', 'TEZONTEPEC', 'ATENGO', 'MANGAS', 'PRESAS', 'HUITEL']
        self.combo_barrio = ttk.Combobox(frame_form, values=barrios, width=28, state='readonly')
        self.combo_barrio.grid(row=3, column=1, pady=5, padx=10)
        
        if self.campesino:
            self.combo_barrio.set(self.campesino['barrio'])
        
        # Superficie
        ttk.Label(frame_form, text="Superficie (ha):", font=('Helvetica', 10)).grid(row=4, column=0, sticky=tk.W, pady=5)
        self.entry_superficie = ttk.Entry(frame_form, width=30)
        self.entry_superficie.grid(row=4, column=1, pady=5, padx=10)
        
        if self.campesino:
            self.entry_superficie.insert(0, str(self.campesino['superficie']))
            siembra = obtener_siembra_activa(self.campesino_id)
            if siembra:
                self.entry_superficie.config(state='disabled')
                ttk.Label(frame_form,
                          text="⚠️ No editable (tiene siembra activa)",
                          foreground='orange',
                          font=('Helvetica', 8)).grid(row=5, column=1, sticky=tk.W, padx=10)
        
        # Extensión de tierra (opcional)
        ttk.Label(frame_form, text="Extensión/Notas:", font=('Helvetica', 10)).grid(row=6, column=0, sticky=tk.W, pady=5)
        self.text_extension = tk.Text(frame_form, width=30, height=4)
        self.text_extension.grid(row=6, column=1, pady=5, padx=10)
        
        if self.campesino and self.campesino.get('extension_tierra'):
            self.text_extension.insert('1.0', self.campesino['extension_tierra'])
        
        # Frame de botones
        frame_botones = ttk.Frame(frame_form)
        frame_botones.grid(row=7, column=0, columnspan=2, pady=20)
        
        if self.campesino:
            frameespecial = ttk.LabelFrame(frameform, text="⚙️ Operaciones Especiales", padding="10")
            frameespecial.grid(row=6, column=0, columnspan=2, pady=10, sticky='ew')  # ✅ Cambiar a grid
            
            ttk.Button(frameespecial, text="✏️ Renombrar Dueño",
                    command=self.abrir_renombrar,
                    width=25).pack(side=tk.LEFT, padx=5)
            
            ttk.Button(frameespecial, text="✂️ Partir Lote",
                    command=self.abrir_partir_lote,
                    width=25).pack(side=tk.LEFT, padx=5)

        # Frame de botones (Guardar/Cancelar)
        framebotones = ttk.Frame(frameform)
        framebotones.grid(row=7, column=0, columnspan=2, pady=20)

        ttk.Button(framebotones, text="💾 Guardar",
                command=self.guardar, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(framebotones, text="❌ Cancelar",
                command=self.ventana.destroy, width=15).pack(side=tk.LEFT, padx=5)
    
    def guardar(self):
        """Guarda los datos del campesino"""
        datos = {
            'numero_lote': self.entry_lote.get().strip(),
            'nombre': self.entry_nombre.get().strip(),
            'localidad': self.entry_localidad.get().strip(),
            'barrio': self.combo_barrio.get().strip(),
            'superficie': self.entry_superficie.get().strip(),
            'extension_tierra': self.text_extension.get('1.0', tk.END).strip()
        }
        
        # Validar
        es_valido, mensaje = validar_campesino(datos)
        if not es_valido:
            messagebox.showwarning("Validación", mensaje)
            return
        
        # Convertir superficie a float
        try:
            datos['superficie'] = float(datos['superficie'])
        except ValueError:
            messagebox.showwarning("Validación", "La superficie debe ser un número válido")
            return
        
        try:
            if self.campesino_id:
                actualizar_campesino(self.campesino_id, datos)
                messagebox.showinfo("Éxito", "Campesino actualizado exitosamente")
            else:
                crear_campesino(datos)
                messagebox.showinfo("Éxito",
                                    f"Campesino registrado exitosamente\nLote: {datos['numero_lote']}")
            
            self.ventana_principal.cargar_todos_campesinos()
            self.ventana.destroy()
            
        except ValueError as e:
            messagebox.showerror("Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar:\n{str(e)}")

    def abrir_renombrar(self):
        """Abre ventana para renombrar dueño"""
        VentanaRenombrarCampesino(
            self.ventana,
            self.campesino_id,
            self.campesino['nombre'],
            self.campesino['numero_lote'],
            self.ventana_principal
        )

    def abrir_partir_lote(self):
        """Abre ventana para partir lote"""
        VentanaPartirLote(
            self.ventana,
            self.campesino_id,
            self.campesino['nombre'],
            self.campesino['numero_lote'],
            self.campesino['superficie'],
            self.ventana_principal
        )

# ==================== VENTANA HISTORIAL ====================

class VentanaHistorial:
    """Ventana para ver el historial de un campesino - CON SCROLLBAR"""
    
    def __init__(self, parent, campesino):
        self.ventana = tk.Toplevel(parent)
        self.ventana.title(f"Historial - {campesino['nombre']}")
        self.ventana.geometry("900x650")
        self.ventana.transient(parent)
        
        self.campesino = campesino
        
        # ===== USAR SCROLLBAR =====
        self.canvas, self.frame_principal = crear_ventana_scrollable(self.ventana, None)
        
        self.crear_widgets()
        self.cargar_historial()
    
    def crear_widgets(self):
        """Crea los widgets de la ventana"""
        
        # Frame superior con info del campesino
        frame_info = ttk.LabelFrame(self.frame_principal, text="Información del Campesino", padding="10")
        frame_info.pack(fill=tk.X, padx=10, pady=10)
        
        info_text = f"""
            Nombre: {self.campesino['nombre']}
            Lote: {self.campesino['numero_lote']}
            Localidad: {self.campesino['localidad']} - {self.campesino['barrio']}
            Superficie: {self.campesino['superficie']} ha
            """
        ttk.Label(frame_info, text=info_text, font=('Helvetica', 10)).pack(anchor=tk.W)
        
        # Frame de siembras históricas
        frame_siembras = ttk.LabelFrame(self.frame_principal, text="Historial de Siembras", padding="10")
        frame_siembras.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Treeview de siembras
        columnas = ('cultivo', 'fecha_inicio', 'fecha_fin', 'riegos', 'ciclo', 'estado')
        self.tree_siembras = ttk.Treeview(frame_siembras, columns=columnas, show='headings', height=10)
        
        self.tree_siembras.heading('cultivo', text='Cultivo')
        self.tree_siembras.heading('fecha_inicio', text='Fecha Inicio')
        self.tree_siembras.heading('fecha_fin', text='Fecha Fin')
        self.tree_siembras.heading('riegos', text='Riegos')
        self.tree_siembras.heading('ciclo', text='Ciclo')
        self.tree_siembras.heading('estado', text='Estado')
        
        self.tree_siembras.column('cultivo', width=100)
        self.tree_siembras.column('fecha_inicio', width=100)
        self.tree_siembras.column('fecha_fin', width=100)
        self.tree_siembras.column('riegos', width=80)
        self.tree_siembras.column('ciclo', width=150)
        self.tree_siembras.column('estado', width=100)
        
        scrollbar = ttk.Scrollbar(frame_siembras, orient=tk.VERTICAL, command=self.tree_siembras.yview)
        self.tree_siembras.configure(yscroll=scrollbar.set)
        self.tree_siembras.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Frame de recibos
        frame_recibos = ttk.LabelFrame(self.frame_principal, text="Recibos Emitidos", padding="10")
        frame_recibos.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Treeview de recibos
        columnas_r = ('folio', 'fecha', 'cultivo', 'riego', 'monto')
        self.tree_recibos = ttk.Treeview(frame_recibos, columns=columnas_r, show='headings', height=8)
        
        self.tree_recibos.heading('folio', text='Folio')
        self.tree_recibos.heading('fecha', text='Fecha')
        self.tree_recibos.heading('cultivo', text='Cultivo')
        self.tree_recibos.heading('riego', text='Riego #')
        self.tree_recibos.heading('monto', text='Monto')
        
        self.tree_recibos.column('folio', width=80)
        self.tree_recibos.column('fecha', width=100)
        self.tree_recibos.column('cultivo', width=100)
        self.tree_recibos.column('riego', width=80)
        self.tree_recibos.column('monto', width=100)
        
        scrollbar_r = ttk.Scrollbar(frame_recibos, orient=tk.VERTICAL, command=self.tree_recibos.yview)
        self.tree_recibos.configure(yscroll=scrollbar_r.set)
        self.tree_recibos.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_r.pack(side=tk.RIGHT, fill=tk.Y)
        
        # ✅ FRAME DE CUOTAS DE COOPERACIÓN
        frame_cuotas = ttk.LabelFrame(self.frame_principal, text="Cuotas de Cooperación", padding=10)
        frame_cuotas.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Lista de cuotas
        columnas_cuotas = ('nombre_cuota', 'monto', 'estado', 'fecha_pago')
        self.tree_cuotas = ttk.Treeview(frame_cuotas, columns=columnas_cuotas, show='headings', height=8)

        self.tree_cuotas.heading('nombre_cuota', text='Cuota')
        self.tree_cuotas.heading('monto', text='Monto')
        self.tree_cuotas.heading('estado', text='Estado')
        self.tree_cuotas.heading('fecha_pago', text='Fecha Pago')

        self.tree_cuotas.column('nombre_cuota', width=200)
        self.tree_cuotas.column('monto', width=100)
        self.tree_cuotas.column('estado', width=100)
        self.tree_cuotas.column('fecha_pago', width=120)

        scrollbar_cuotas = ttk.Scrollbar(frame_cuotas, orient=tk.VERTICAL, command=self.tree_cuotas.yview)
        self.tree_cuotas.configure(yscroll=scrollbar_cuotas.set)

        self.tree_cuotas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_cuotas.pack(side=tk.RIGHT, fill=tk.Y)

        # ✅ Bind doble click para pagar (AHORA COMO MÉTODO DE LA CLASE)
        self.tree_cuotas.bind('<Double-1>', self.pagar_cuota_dobleclick)
        
        # Botones
        frame_botones = ttk.Frame(self.frame_principal)
        frame_botones.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(frame_botones,
                   text="🖨️ Reimprimir Recibo Seleccionado",
                   command=self.reimprimir_recibo).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(frame_botones,
                   text="🔄 Actualizar",
                   command=self.cargar_historial).pack(side=tk.LEFT, padx=5)
    
    def cargar_historial(self):
        """Carga el historial de siembras, recibos Y CUOTAS"""
        # Cargar siembras
        self.tree_siembras.delete(*self.tree_siembras.get_children())
        siembras = obtener_historial_siembras(self.campesino['id'])
        
        for s in siembras:
            estado = "✅ Activa" if s['activa'] else "Finalizada"
            fecha_fin = s['fecha_fin'] if s['fecha_fin'] else '-'
            
            self.tree_siembras.insert('', tk.END, values=(
                s['cultivo'],
                s['fecha_inicio'],
                fecha_fin,
                s['numero_riegos'],
                s['ciclo'],
                estado
            ))
        
        # Cargar recibos
        self.tree_recibos.delete(*self.tree_recibos.get_children())
        recibos = obtener_recibos_campesino(self.campesino['id'])
        
        for r in recibos:
            self.tree_recibos.insert('', tk.END, values=(
                r['folio'],
                r['fecha'],
                r['cultivo'],
                r['numero_riego'],
                f"${r['costo']:.2f}"
            ), tags=(str(r['id']),))
        
        # ✅ CARGAR CUOTAS (AHORA AQUÍ, NO EN crear_widgets)
        self.tree_cuotas.delete(*self.tree_cuotas.get_children())
        
        try:
            from modules.cuotas import obtener_cuotas_campesino
            cuotas = obtener_cuotas_campesino(self.campesino['id'])

            for cuota in cuotas:
                estado = "✅ PAGADO" if cuota['pagado'] else "⏳ PENDIENTE"
                fecha_pago = cuota['fecha_pago'] if cuota['fecha_pago'] else "-"
                
                # Calcular totales y pendientes
                monto_total = cuota['monto']
                monto_pagado = cuota.get('monto_pagado', 0.0)
                
                # Si tiene sobrecargo habilitado, calcularlo para mostrarlo
                sobrecargo_estimado = 0.0
                # Necesitamos saber si tiene sobrecargo habilitado, pero la query original no lo trae
                # Por simplicidad, si no está pagado, asumimos que podría tenerlo.
                # Mejor: mostrar lo que hay en BD.
                
                estado_texto = estado
                if not cuota['pagado'] and monto_pagado > 0:
                    estado_texto = "⚠️ PARCIAL"
                
                self.tree_cuotas.insert('', tk.END,
                                values=(
                                    cuota['nombre_tipo_cuota'],
                                    f"${monto_total:.2f} (Abonado: ${monto_pagado:.2f})",
                                    estado_texto,
                                    fecha_pago
                                ),
                                tags=(str(cuota['id']), str(cuota['pagado'])))
        except Exception as e:
            print(f"Error al cargar cuotas: {e}")
    
    def pagar_cuota_dobleclick(self, event):
        """Maneja el doble click en una cuota para pagarla"""
        selection = self.tree_cuotas.selection()
        if not selection:
            return
        
        item = self.tree_cuotas.item(selection[0])
        cuota_id = int(item['tags'][0])
        pagado = int(item['tags'][1])
        
        if pagado:
            messagebox.showinfo("Información", "Esta cuota ya fue pagada totalmente")
            return
        
        # Abrir ventana de pago parcial
        VentanaPagoCuota(self.ventana, cuota_id, self)
    
    def reimprimir_recibo(self):
        """Reimprime el recibo seleccionado - RECIBOS TEMPORALES"""
        selection = self.tree_recibos.selection()
        if not selection:
            messagebox.showwarning("Advertencia", "Debe seleccionar un recibo")
            return
        
        item = self.tree_recibos.item(selection[0])
        recibo_id = int(item['tags'][0])
        
        try:
            pdf_path = generar_recibo_pdf_temporal(recibo_id, es_reimpresion=True)
            abrir_pdf(pdf_path)
            
            if messagebox.askyesno("Imprimir", "¿Desea imprimir?"):
                imprimir_recibo_y_limpiar(pdf_path)
            else:
                try:
                    os.remove(pdf_path)
                except:
                    pass
        except Exception as e:
            messagebox.showerror("Error", f"Error al reimprimir:\n{str(e)}")


# ==================== DIÁLOGO DE CONFIGURACIÓN ====================

class DialogoConfiguracion:
    """Diálogo para configurar el sistema"""
    
    def __init__(self, parent):
        self.ventana = tk.Toplevel(parent)
        self.ventana.title("⚙️ Configuración del Sistema")
        self.ventana.geometry("600x550")
        self.ventana.transient(parent)
        self.ventana.grab_set()
        
        self.crear_widgets()
        self.cargar_configuracion()
    
    def crear_widgets(self):
        """Crea los widgets de la ventana"""
        notebook = ttk.Notebook(self.ventana)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # ========== TAB 1: General ==========
        tab_general = ttk.Frame(notebook, padding="15")
        notebook.add(tab_general, text="General")
        
        # Nombre oficina
        ttk.Label(tab_general, text="Nombre de la Oficina:", font=('Helvetica', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.entry_nombre_oficina = ttk.Entry(tab_general, width=50)
        self.entry_nombre_oficina.grid(row=1, column=0, pady=5)
        
        # Ubicación
        ttk.Label(tab_general, text="Ubicación:", font=('Helvetica', 10, 'bold')).grid(row=2, column=0, sticky=tk.W, pady=5)
        self.entry_ubicacion = ttk.Entry(tab_general, width=50)
        self.entry_ubicacion.grid(row=3, column=0, pady=5)
        
        # Tarifa
        ttk.Label(tab_general, text="Tarifa por Hectárea:", font=('Helvetica', 10, 'bold')).grid(row=4, column=0, sticky=tk.W, pady=5)
        self.entry_tarifa = ttk.Entry(tab_general, width=50)
        self.entry_tarifa.grid(row=5, column=0, pady=5)
        
        # Ciclo actual (solo lectura)
        ttk.Label(tab_general, text="Ciclo Actual:", font=('Helvetica', 10, 'bold')).grid(row=6, column=0, sticky=tk.W, pady=5)
        self.label_ciclo = ttk.Label(tab_general, text="-", foreground='blue')
        self.label_ciclo.grid(row=7, column=0, sticky=tk.W, pady=5)
        
        # Folio actual (solo lectura)
        ttk.Label(tab_general, text="Folio Actual:", font=('Helvetica', 10, 'bold')).grid(row=8, column=0, sticky=tk.W, pady=5)
        self.label_folio = ttk.Label(tab_general, text="-", foreground='blue')
        self.label_folio.grid(row=9, column=0, sticky=tk.W, pady=5)
        
        # ========== TAB 2: Auditoría ==========
        tab_auditoria = ttk.Frame(notebook, padding="15")
        notebook.add(tab_auditoria, text="Auditoría")
        
        # Treeview de auditoría
        columnas = ('fecha_hora', 'tipo', 'descripcion')
        self.tree_auditoria = ttk.Treeview(tab_auditoria, columns=columnas, show='headings', height=15)
        
        self.tree_auditoria.heading('fecha_hora', text='Fecha/Hora')
        self.tree_auditoria.heading('tipo', text='Tipo')
        self.tree_auditoria.heading('descripcion', text='Descripción')
        
        self.tree_auditoria.column('fecha_hora', width=150)
        self.tree_auditoria.column('tipo', width=150)
        self.tree_auditoria.column('descripcion', width=250)
        
        scrollbar = ttk.Scrollbar(tab_auditoria, orient=tk.VERTICAL, command=self.tree_auditoria.yview)
        self.tree_auditoria.configure(yscroll=scrollbar.set)
        self.tree_auditoria.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Cargar auditoría
        registros = obtener_auditoria(50)
        for r in registros:
            self.tree_auditoria.insert('', tk.END, values=(
                r['fecha_hora'],
                r['tipo_evento'],
                r['descripcion']
            ))
        
        # Frame de botones
        frame_botones = ttk.Frame(self.ventana)
        frame_botones.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(frame_botones,
                   text="💾 Guardar Cambios",
                   command=self.guardar_configuracion,
                   width=20).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(frame_botones,
                   text="❌ Cerrar",
                   command=self.ventana.destroy,
                   width=15).pack(side=tk.LEFT, padx=5)
    
    def cargar_configuracion(self):
        """Carga la configuración actual"""
        config = obtener_toda_configuracion()
        
        self.entry_nombre_oficina.insert(0, config.get('nombre_oficina', ''))
        self.entry_ubicacion.insert(0, config.get('ubicacion', ''))
        self.entry_tarifa.insert(0, config.get('tarifa_hectarea', '450'))
        self.label_ciclo.config(text=config.get('ciclo_actual', '-'))
        self.label_folio.config(text=config.get('folio_actual', '-'))
    
    def guardar_configuracion(self):
        """Guarda los cambios de configuración"""
        try:
            actualizar_configuracion('nombre_oficina', self.entry_nombre_oficina.get().strip())
            actualizar_configuracion('ubicacion', self.entry_ubicacion.get().strip())
            
            # Validar tarifa
            try:
                tarifa = float(self.entry_tarifa.get().strip())
                if tarifa <= 0:
                    raise ValueError()
                actualizar_configuracion('tarifa_hectarea', str(tarifa))
            except ValueError:
                messagebox.showwarning("Validación", "La tarifa debe ser un número mayor a 0")
                return
            
            messagebox.showinfo("Éxito", "Configuración guardada exitosamente")
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar configuración:\n{str(e)}")

# ==================== VENTANA ADMINISTRAR DATOS ====================

class VentanaAdministrarDatos:
    """Ventana para administrar datos manualmente"""
    
    def __init__(self, parent, ventana_principal):
        self.ventana = tk.Toplevel(parent)
        self.ventana.title("🔧 Administrar Datos")
        self.ventana.geometry("800x650")
        self.ventana.transient(parent)
        self.ventana.grab_set()
        
        self.ventana_principal = ventana_principal
        
        self.crear_widgets()
    
    def crear_widgets(self):
        """Crea los widgets de la ventana"""
        frame_principal = ttk.Frame(self.ventana, padding="10")
        frame_principal.pack(fill=tk.BOTH, expand=True)
        
        # Frame para actualizar Folio
        frame_folio = ttk.LabelFrame(frame_principal, text="Actualizar Folio Actual", padding="10")
        frame_folio.pack(fill=tk.X, pady=5)
        
        ttk.Label(frame_folio, text="Nuevo Folio:").pack(side=tk.LEFT, padx=5)
        self.entry_nuevo_folio = ttk.Entry(frame_folio, width=10)
        self.entry_nuevo_folio.pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_folio, text="Actualizar", command=self.actualizar_folio).pack(side=tk.LEFT, padx=10)
        
        # Mostrar folio actual
        ttk.Label(frame_principal, text="Folio actual:", font=('Helvetica', 10, 'bold')).pack(pady=(10, 5))
        self.label_folio_actual = ttk.Label(frame_principal, text="", font=('Helvetica', 12))
        self.label_folio_actual.pack()
        self.actualizar_label_folio()
        
        # Frame para actualizar Nombre de Oficina
        frame_nombre = ttk.LabelFrame(frame_principal, text="Actualizar Nombre de Oficina", padding="10")
        frame_nombre.pack(fill=tk.X, pady=5)
        
        ttk.Label(frame_nombre, text="Nuevo Nombre:").pack(side=tk.LEFT, padx=5)
        self.entry_nuevo_nombre = ttk.Entry(frame_nombre, width=60)
        self.entry_nuevo_nombre.pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_nombre, text="Actualizar", command=self.actualizar_nombre_oficina).pack(side=tk.LEFT, padx=10)
        
        # Mostrar nombre actual
        ttk.Label(frame_principal, text="Nombre actual:", font=('Helvetica', 10, 'bold')).pack(pady=(10, 5))
        self.label_nombre_actual = ttk.Label(frame_principal, text="", font=('Helvetica', 12))
        self.label_nombre_actual.pack()
        self.cargar_nombre_actual()
    
    def actualizar_label_folio(self):
        """Actualiza el label que muestra el folio actual"""
        folio = obtener_configuracion('folio_actual')
        self.label_folio_actual.config(text=folio)
    
    def cargar_nombre_actual(self):
        """Carga el label que muestra el nombre actual"""
        nombre = obtener_configuracion('nombre_oficina')
        self.label_nombre_actual.config(text=nombre)
    
    def actualizar_folio(self):
        """Actualiza el folio actual"""
        nuevo_folio_str = self.entry_nuevo_folio.get().strip()
        
        if not nuevo_folio_str:
            messagebox.showwarning("Advertencia", "Ingrese un número de folio")
            return
        
        try:
            nuevo_folio = int(nuevo_folio_str)
            if nuevo_folio < 1:
                raise ValueError("El folio debe ser positivo")
        except ValueError:
            messagebox.showerror("Error", "Ingrese un número entero positivo válido")
            return
        
        if not messagebox.askyesno("Confirmar", f"¿Actualizar el folio actual a {nuevo_folio}?"):
            return
        
        try:
            if actualizar_folio_actual(nuevo_folio):
                messagebox.showinfo("Éxito", f"Folio actualizado a {nuevo_folio}")
                self.actualizar_label_folio()
                self.entry_nuevo_folio.delete(0, tk.END)
            else:
                messagebox.showerror("Error", "No se pudo actualizar el folio")
        except Exception as e:
            messagebox.showerror("Error", f"Error al actualizar folio: {str(e)}")
    
    def actualizar_nombre_oficina(self):
        """Actualiza el nombre de la oficina"""
        nuevo_nombre = self.entry_nuevo_nombre.get().strip()
        
        if not nuevo_nombre:
            messagebox.showwarning("Advertencia", "Ingrese un nombre para la oficina")
            return
        
        if not messagebox.askyesno("Confirmar", f"¿Actualizar el nombre de la oficina a '{nuevo_nombre}'?"):
            return
        
        try:
            actualizar_configuracion('nombre_oficina', nuevo_nombre)
            messagebox.showinfo("Éxito", f"Nombre de oficina actualizado a '{nuevo_nombre}'")
            self.cargar_nombre_actual()
            self.entry_nuevo_nombre.delete(0, tk.END)
        except Exception as e:
            messagebox.showerror("Error", f"Error al actualizar nombre: {str(e)}")         

class VentanaEstadisticas:
    """Ventana de estadísticas e insights con gráficas"""
    
    def __init__(self, parent):
        self.ventana = tk.Toplevel(parent)
        self.ventana.title("📊 Estadísticas e Insights")
        self.ventana.geometry("1000x700")
        self.ventana.transient(parent)
        
        # Obtener datos
        self.stats = obtener_estadisticas_generales()
        
        # Crear scrollable
        self.canvas, self.frame_principal = crear_ventana_scrollable(self.ventana, None)
        
        self.crear_widgets()
    
    def crear_widgets(self):
        """Crea los widgets de la ventana"""
        
        frame_principal = ttk.Frame(self.frame_principal, padding="20")
        frame_principal.pack(fill=tk.BOTH, expand=True)
        
        # TÍTULO
        ttk.Label(frame_principal, text="📊 ESTADÍSTICAS E INSIGHTS",
                 font=('Helvetica', 16, 'bold')).pack(pady=10)
        
        # ===== PANEL DE RESUMEN =====
        frame_resumen = ttk.LabelFrame(frame_principal, text="📈 Resumen General", padding="15")
        frame_resumen.pack(fill=tk.X, pady=10)
        
        
        # Grid de estadísticas principales
        stats_grid = ttk.Frame(frame_resumen)
        stats_grid.pack(fill=tk.X)
        
        self._crear_stat_card(stats_grid, 0, 0, "👥 Total Campesinos", 
                             str(self.stats['total_campesinos']), "blue")
        self._crear_stat_card(stats_grid, 0, 1, "🌾 Total Hectáreas", 
                             f"{self.stats['total_hectareas']} ha", "green")
        self._crear_stat_card(stats_grid, 0, 2, "✅ Hectáreas Sembradas", 
                             f"{self.stats['hectareas_sembradas']} ha", "green")
        self._crear_stat_card(stats_grid, 1, 0, "📊 Porcentaje Sembrado", 
                             f"{self.stats['porcentaje_sembrado']}%", "orange")
        self._crear_stat_card(stats_grid, 1, 1, "❌ Sin Sembrar", 
                             f"{self.stats['hectareas_sin_sembrar']} ha", "red")
        self._crear_stat_card(stats_grid, 1, 2, "⚠️ Campesinos Sin Siembra", 
                             str(self.stats['campesinos_sin_siembra']), "red")
        
        # ===== FILTROS =====
        frame_filtros = ttk.LabelFrame(frame_principal, text="🔍 Filtros", padding="10")
        frame_filtros.pack(fill=tk.X, pady=10)
        
        ttk.Label(frame_filtros, text="Filtrar por cultivo:").pack(side=tk.LEFT, padx=5)
        
        self.combo_filtro = ttk.Combobox(frame_filtros, 
                                         values=['Todos'] + list(self.stats['siembras_por_cultivo'].keys()),
                                         state='readonly', width=20)
        self.combo_filtro.current(0)
        self.combo_filtro.pack(side=tk.LEFT, padx=5)
        self.combo_filtro.bind('<<ComboboxSelected>>', self.aplicar_filtro)
        
        ttk.Button(frame_filtros, text="🔄 Actualizar",
                  command=self.actualizar_datos).pack(side=tk.LEFT, padx=5)
        
        # ===== GRÁFICAS =====
        frame_graficas = ttk.Frame(frame_principal)
        frame_graficas.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Gráfica 1: Hectáreas por cultivo
        self.crear_grafica_barras(frame_graficas, 
                                   self.stats['hectareas_por_cultivo'],
                                   "Hectáreas Sembradas por Cultivo",
                                   "Cultivo", "Hectáreas")
        
        # ===== DETALLES POR CULTIVO =====
        frame_detalles = ttk.LabelFrame(frame_principal, text="📋 Detalles por Cultivo", padding="10")
        frame_detalles.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Tabla de cultivos
        self.tree = ttk.Treeview(frame_detalles, 
                                 columns=('cultivo', 'campesinos', 'hectareas', 'porcentaje'),
                                 show='headings', height=10)
        
        self.tree.heading('cultivo', text='Cultivo')
        self.tree.heading('campesinos', text='Campesinos')
        self.tree.heading('hectareas', text='Hectáreas')
        self.tree.heading('porcentaje', text='% del Total')
        
        self.tree.column('cultivo', width=150)
        self.tree.column('campesinos', width=100)
        self.tree.column('hectareas', width=100)
        self.tree.column('porcentaje', width=100)
        
        scrollbar = ttk.Scrollbar(frame_detalles, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.cargar_tabla_cultivos()
        
         # ===== BOTONES DE ACCIÓN ===== 
        frame_botones = ttk.Frame(frame_principal)
        frame_botones.pack(pady=15)
        
        ttk.Button(frame_botones, text="📄 Exportar PDF",
                  command=self.exportar_pdf).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(frame_botones, text="❌ Cerrar",
                  command=self.ventana.destroy).pack(side=tk.LEFT, padx=5)
    
    def _crear_stat_card(self, parent, row, col, titulo, valor, color):
        """Crea una tarjeta de estadística"""
        frame = ttk.Frame(parent, relief=tk.RIDGE, borderwidth=2)
        frame.grid(row=row, column=col, padx=10, pady=10, sticky='nsew')
        
        ttk.Label(frame, text=titulo, font=('Helvetica', 9)).pack(pady=5)
        ttk.Label(frame, text=valor, font=('Helvetica', 18, 'bold'),
                 foreground=color).pack(pady=5)
        
        parent.columnconfigure(col, weight=1)
    
    def crear_grafica_barras(self, parent, datos, titulo, xlabel, ylabel):
        """Crea una gráfica de barras con matplotlib"""
        try:
            import matplotlib
            matplotlib.use('TkAgg')
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            
            # Crear figura
            fig = Figure(figsize=(8, 4), dpi=100)
            ax = fig.add_subplot(111)
            
            # Datos
            cultivos = list(datos.keys())
            valores = list(datos.values())
            
            # Colores
            colores = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#6A994E', 
                      '#BC4B51', '#8B5A3C', '#5F6F52']
            
            # Crear gráfica de barras
            bars = ax.bar(cultivos, valores, color=colores[:len(cultivos)])
            
            # Etiquetas
            ax.set_xlabel(xlabel, fontsize=10)
            ax.set_ylabel(ylabel, fontsize=10)
            ax.set_title(titulo, fontsize=12, fontweight='bold')
            
            # Rotar etiquetas del eje X
            ax.tick_params(axis='x', rotation=45)
            
            # Agregar valores encima de las barras
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.1f}',
                       ha='center', va='bottom', fontsize=9)
            
            fig.tight_layout()
            
            # Agregar a Tkinter
            canvas = FigureCanvasTkAgg(fig, parent)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
        except ImportError:
            ttk.Label(parent, text="⚠️ Instala matplotlib para ver gráficas:\npip install matplotlib",
                     foreground='red', font=('Helvetica', 11)).pack(pady=20)
    
    def cargar_tabla_cultivos(self):
        """Carga la tabla de detalles por cultivo"""
        self.tree.delete(*self.tree.get_children())
        
        total_hectareas = self.stats['total_hectareas']
        
        for cultivo, hectareas in self.stats['hectareas_por_cultivo'].items():
            campesinos = self.stats['siembras_por_cultivo'].get(cultivo, 0)
            porcentaje = (hectareas / total_hectareas * 100) if total_hectareas > 0 else 0
            
            self.tree.insert('', tk.END, values=(
                cultivo,
                campesinos,
                f"{hectareas:.2f} ha",
                f"{porcentaje:.1f}%"
            ))
    
    def aplicar_filtro(self, event=None):
        """Aplica filtro por cultivo"""
        cultivo = self.combo_filtro.get()
        
        if cultivo == 'Todos':
            messagebox.showinfo("Filtro", "Mostrando todos los cultivos")
            return
        
        # Obtener estadísticas del cultivo específico
        stats_cultivo = obtener_estadisticas_por_cultivo(cultivo)
        
        mensaje = f"""ESTADÍSTICAS DE {cultivo.upper()}
            Campesinos: {stats_cultivo['total_campesinos']}
            Hectáreas: {stats_cultivo['total_hectareas']} ha
            Riegos promedio: {stats_cultivo['riegos_promedio']}
            Total de riegos: {stats_cultivo['total_riegos']}"""
        
        messagebox.showinfo(f"Cultivo: {cultivo}", mensaje)
    
    def actualizar_datos(self):
        """Actualiza los datos y refresca la ventana"""
        self.stats = obtener_estadisticas_generales()
        self.ventana.destroy()
        VentanaEstadisticas(self.ventana.master)

    def exportar_pdf(self):
        """Exporta estadísticas a PDF profesional"""
        try:
            from modules.reports import generar_pdf_estadisticas  # CON GUIONES BAJOS
            from modules.models import obtener_estadisticas_generales
            
            # Obtener estadísticas generales
            estadisticas = obtener_estadisticas_generales()
            
            # Construir lista de estadísticas por cultivo desde los datos que ya tenemos
            estadisticas_cultivo = []
            for cultivo in estadisticas['hectareas_por_cultivo'].keys():
                estadisticas_cultivo.append({
                    'cultivo': cultivo,
                    'num_siembras': estadisticas['siembras_por_cultivo'].get(cultivo, 0),
                    'superficie_total': estadisticas['hectareas_por_cultivo'].get(cultivo, 0),
                    'num_recibos': 0,  # No tenemos este dato fácilmente
                    'ingresos_totales': 0  # No tenemos este dato fácilmente
                })
            
            # Generar PDF con diseño profesional
            ruta_pdf = generar_pdf_estadisticas(estadisticas, estadisticas_cultivo)
            
            messagebox.showinfo("Éxito", 
                f"PDF generado correctamente\n\n"
                f"Archivo: {os.path.basename(ruta_pdf)}")
            
            # Abrir automáticamente el PDF
            from modules.reports import abrir_pdf
            abrir_pdf(ruta_pdf)
            
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            messagebox.showerror("Error", f"Error al generar PDF:\n{str(e)}")

####
class VentanaRenombrarCampesino:
    """Ventana para renombrar el dueño de un lote"""
    
    def __init__(self, parent, campesino_id, campesino_nombre, lote, ventana_principal):
        self.campesino_id = campesino_id
        self.nombre_actual = campesino_nombre
        self.lote = lote
        self.ventana_principal = ventana_principal
        
        self.ventana = tk.Toplevel(parent)
        self.ventana.title(f"✏️ Renombrar Dueño - Lote {lote}")
        self.ventana.geometry("450x200")
        self.ventana.transient(parent)
        self.ventana.grab_set()
        
        self.crear_widgets()
    
    def crear_widgets(self):
        # Canvas con scrollbar
        self.canvas, self.frame_principal = crear_ventana_scrollable(self.ventana, None)
        
        frame = ttk.Frame(self.frame_principal, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text=f"📋 Lote: {self.lote}", 
                 font=('Helvetica', 11, 'bold')).pack(pady=5)
        
        ttk.Label(frame, text=f"Nombre actual: {self.nombre_actual}",
                 font=('Helvetica', 10)).pack(pady=5)
        
        ttk.Label(frame, text="Nuevo nombre del dueño:",
                 font=('Helvetica', 10)).pack(pady=(15, 5))
        
        self.entry_nombre = ttk.Entry(frame, width=40, font=('Helvetica', 11))
        self.entry_nombre.pack(pady=5)
        self.entry_nombre.insert(0, self.nombre_actual)
        self.entry_nombre.select_range(0, tk.END)
        self.entry_nombre.focus()
        
        frame_botones = ttk.Frame(frame)
        frame_botones.pack(pady=20)
        
        ttk.Button(frame_botones, text="✅ Guardar",
                  command=self.guardar).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones, text="❌ Cancelar",
                  command=self.ventana.destroy).pack(side=tk.LEFT, padx=5)
    
    def guardar(self):
        nuevo_nombre = self.entry_nombre.get().strip()
        
        if not nuevo_nombre:
            messagebox.showwarning("Advertencia", "Debe ingresar un nombre")
            return
        
        if nuevo_nombre == self.nombre_actual:
            messagebox.showinfo("Sin cambios", "El nombre no ha cambiado")
            return
        
        if messagebox.askyesno("Confirmar",
                              f"¿Cambiar nombre de:\n'{self.nombre_actual}'\na:\n'{nuevo_nombre}'?"):
            try:
                from modules.models import renombrar_campesino
                renombrar_campesino(self.campesino_id, nuevo_nombre)
                
                messagebox.showinfo("Éxito", "Nombre actualizado correctamente")
                
                # Actualizar UI
                self.ventana_principal.cargar_todos_campesinos()
                self.ventana.destroy()
                
            except Exception as e:
                messagebox.showerror("Error", f"Error al renombrar:\n{str(e)}")

class VentanaPartirLote:
    """Ventana para partir/subdividir un lote en múltiples sublotes"""
    
    def __init__(self, parent, campesino_id, campesino_nombre, lote, superficie_original, ventana_principal):
        self.campesino_id = campesino_id
        self.nombre_original = campesino_nombre
        self.lote = lote
        self.superficie_original = superficie_original
        self.ventana_principal = ventana_principal
        
        self.ventana = tk.Toplevel(parent)
        self.ventana.title(f"✂️ Partir Lote {lote}")
        self.ventana.geometry("500x550")
        self.ventana.transient(parent)
        self.ventana.grab_set()
        
        self.entries_superficie = []
        self.entries_nombre = []
        
        self.crear_widgets()
    
    def crear_widgets(self):
        # Canvas con scrollbar
        self.canvas, self.frame_principal = crear_ventana_scrollable(self.ventana, None)
        
        frame = ttk.Frame(self.frame_principal, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Información
        ttk.Label(frame, text=f"✂️ PARTIR LOTE {self.lote}",
                 font=('Helvetica', 12, 'bold')).pack(pady=10)
        
        info_frame = ttk.LabelFrame(frame, text="Información Actual", padding="10")
        info_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(info_frame, text=f"Dueño: {self.nombre_original}").pack(anchor=tk.W)
        ttk.Label(info_frame, text=f"Superficie total: {self.superficie_original} hectáreas").pack(anchor=tk.W)
        
        # Selector de divisiones
        divisiones_frame = ttk.Frame(frame)
        divisiones_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(divisiones_frame, text="¿En cuántos lotes se dividirá? (no incluye el original):",
                 font=('Helvetica', 10)).pack(anchor=tk.W)
        
        self.spin_divisiones = ttk.Spinbox(divisiones_frame, from_=1, to=10, width=10)
        self.spin_divisiones.set(2)
        self.spin_divisiones.pack(anchor=tk.W, pady=5)
        
        ttk.Button(divisiones_frame, text="🔄 Generar Campos",
                  command=self.generar_campos).pack(anchor=tk.W, pady=5)
        
        # Frame para los campos dinámicos
        self.frame_campos = ttk.Frame(frame)
        self.frame_campos.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Botones finales
        frame_botones = ttk.Frame(frame)
        frame_botones.pack(pady=20)
        
        ttk.Button(frame_botones, text="✅ Partir Lote",
                  command=self.partir_lote).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones, text="❌ Cancelar",
                  command=self.ventana.destroy).pack(side=tk.LEFT, padx=5)
    
    def generar_campos(self):
        # Limpiar campos anteriores
        for widget in self.frame_campos.winfo_children():
            widget.destroy()
        
        self.entries_superficie = []
        self.entries_nombre = []
        
        num_divisiones = int(self.spin_divisiones.get())
        
        # Campo para el lote original
        frame_original = ttk.LabelFrame(self.frame_campos, text=f"Lote {self.lote} (ORIGINAL)", padding="10")
        frame_original.pack(fill=tk.X, pady=5)
        
        ttk.Label(frame_original, text="Superficie (ha):").pack(side=tk.LEFT, padx=5)
        entry_sup = ttk.Entry(frame_original, width=10)
        entry_sup.pack(side=tk.LEFT, padx=5)
        self.entries_superficie.append(entry_sup)
        
        ttk.Label(frame_original, text="Dueño:").pack(side=tk.LEFT, padx=5)
        entry_nom = ttk.Entry(frame_original, width=25)
        entry_nom.insert(0, self.nombre_original)
        entry_nom.pack(side=tk.LEFT, padx=5)
        self.entries_nombre.append(entry_nom)
        
        # Campos para los nuevos sublotes
        for i in range(num_divisiones):
            frame_sublote = ttk.LabelFrame(self.frame_campos, 
                                           text=f"Lote {self.lote}-{i+1} (NUEVO)", 
                                           padding="10")
            frame_sublote.pack(fill=tk.X, pady=5)
            
            ttk.Label(frame_sublote, text="Superficie (ha):").pack(side=tk.LEFT, padx=5)
            entry_sup = ttk.Entry(frame_sublote, width=10)
            entry_sup.pack(side=tk.LEFT, padx=5)
            self.entries_superficie.append(entry_sup)
            
            ttk.Label(frame_sublote, text="Dueño:").pack(side=tk.LEFT, padx=5)
            entry_nom = ttk.Entry(frame_sublote, width=25)
            entry_nom.insert(0, f"{self.nombre_original} (Heredero {i+1})")
            entry_nom.pack(side=tk.LEFT, padx=5)
            self.entries_nombre.append(entry_nom)
    
    def partir_lote(self):
        if not self.entries_superficie:
            messagebox.showwarning("Advertencia", "Debe generar los campos primero")
            return
        
        try:
            # Obtener superficies
            superficies = []
            for entry in self.entries_superficie:
                valor = entry.get().strip()
                if not valor:
                    raise ValueError("Todas las superficies son obligatorias")
                superficies.append(float(valor))
            
            # Validar suma
            suma = sum(superficies)
            if abs(suma - self.superficie_original) > 0.01:
                raise ValueError(
                    f"La suma de superficies ({suma:.4f} ha) no coincide "
                    f"con la original ({self.superficie_original:.4f} ha)"
                )
            
            # Obtener nombres
            nombres = []
            for entry in self.entries_nombre:
                nombre = entry.get().strip()
                if not nombre:
                    raise ValueError("Todos los nombres son obligatorios")
                nombres.append(nombre)
            
            # Confirmar
            num_divisiones = len(superficies) - 1
            mensaje = f"¿Partir lote {self.lote} en {len(superficies)} sublotes?\n\n"
            mensaje += f"• {self.lote}: {superficies[0]:.4f} ha - {nombres[0]}\n"
            for i in range(num_divisiones):
                mensaje += f"• {self.lote}-{i+1}: {superficies[i+1]:.4f} ha - {nombres[i+1]}\n"
            
            if not messagebox.askyesno("Confirmar Partición", mensaje):
                return
            
            # Ejecutar partición
            from modules.models import partir_lote
            partir_lote(self.campesino_id, num_divisiones, superficies, nombres)
            
            messagebox.showinfo("Éxito", "Lote partido correctamente")
            self.ventana_principal.cargar_todos_campesinos()
            self.ventana.destroy()
            
        except ValueError as e:
            messagebox.showerror("Error de Validación", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Error al partir lote:\n{str(e)}")

class VentanaPagoCuota:
    """Ventana para registrar pagos (abonos) a cuotas"""
    
    def __init__(self, parent, cuota_id, ventana_padre):
        self.cuota_id = cuota_id
        self.ventana_padre = ventana_padre
        
        self.ventana = tk.Toplevel(parent)
        self.ventana.title("💰 Registrar Pago de Cuota")
        self.ventana.geometry("450x450")
        self.ventana.transient(parent)
        self.ventana.grab_set()
        
        self.cargar_datos_cuota()
        self.crear_widgets()
        
    def cargar_datos_cuota(self):
        try:
            from modules.cuotas import get_cuotas_connection, calcular_sobrecargo_acumulado
            conn = get_cuotas_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT cc.*, tc.nombre as nombre_cuota, tc.sobrecargo_habilitado
                FROM cuotas_campesinos cc
                JOIN tipos_cuota tc ON cc.tipo_cuota_id = tc.id
                WHERE cc.id = ?
            ''', (self.cuota_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                raise ValueError("Cuota no encontrada")
                
            self.cuota = dict(row)
            
            # Calcular sobrecargo
            self.sobrecargo = 0.0
            if self.cuota['sobrecargo_habilitado']:
                self.sobrecargo = calcular_sobrecargo_acumulado(self.cuota['fecha_asignacion'])
                
            self.monto_base = self.cuota['monto']
            self.monto_total = self.monto_base + self.sobrecargo
            self.monto_pagado = self.cuota.get('monto_pagado', 0.0)
            self.saldo_pendiente = self.monto_total - self.monto_pagado
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar datos: {e}")
            self.ventana.destroy()

    def crear_widgets(self):
        frame = ttk.Frame(self.ventana, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Título
        ttk.Label(frame, text="REGISTRAR PAGO / ABONO", 
                 font=('Helvetica', 14, 'bold')).pack(pady=10)
        
        # Info Cuota
        info_frame = ttk.LabelFrame(frame, text="Detalles de la Cuota", padding="10")
        info_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(info_frame, text=f"Concepto: {self.cuota['nombre_cuota']}", font=('Helvetica', 10, 'bold')).pack(anchor=tk.W)
        ttk.Label(info_frame, text=f"Monto Base: ${self.monto_base:.2f}").pack(anchor=tk.W)
        
        if self.sobrecargo > 0:
            ttk.Label(info_frame, text=f"Sobrecargo: ${self.sobrecargo:.2f}", foreground='red').pack(anchor=tk.W)
            
        ttk.Label(info_frame, text=f"TOTAL A PAGAR: ${self.monto_total:.2f}", font=('Helvetica', 10, 'bold')).pack(anchor=tk.W, pady=5)
        
        # Estado de Pagos
        pago_frame = ttk.LabelFrame(frame, text="Estado de Pagos", padding="10")
        pago_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(pago_frame, text=f"Abonado hasta hoy: ${self.monto_pagado:.2f}", foreground='green').pack(anchor=tk.W)
        ttk.Label(pago_frame, text=f"SALDO PENDIENTE: ${self.saldo_pendiente:.2f}", 
                 font=('Helvetica', 12, 'bold'), foreground='blue').pack(anchor=tk.W, pady=5)
        
        # Entrada de Abono
        input_frame = ttk.Frame(frame, padding="10")
        input_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(input_frame, text="Monto a abonar:").pack(side=tk.LEFT)
        self.entry_abono = ttk.Entry(input_frame, width=15, font=('Helvetica', 12))
        self.entry_abono.pack(side=tk.LEFT, padx=10)
        self.entry_abono.insert(0, f"{self.saldo_pendiente:.2f}")
        self.entry_abono.select_range(0, tk.END)
        self.entry_abono.focus()
        
        # Botones
        btn_frame = ttk.Frame(frame, padding="10")
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="✅ Registrar Pago", command=self.registrar_pago).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        ttk.Button(btn_frame, text="❌ Cancelar", command=self.ventana.destroy).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
    def registrar_pago(self):
        try:
            monto = float(self.entry_abono.get())
            if monto <= 0:
                messagebox.showwarning("Error", "El monto debe ser mayor a 0")
                return
                
            if monto > self.saldo_pendiente + 0.01:
                messagebox.showwarning("Error", f"El monto excede el saldo pendiente (${self.saldo_pendiente:.2f})")
                return
                
            if messagebox.askyesno("Confirmar", f"¿Registrar abono de ${monto:.2f}?"):
                from modules.cuotas import registrar_abono
                from modules.reports import generar_recibo_cuota_pdf_temporal, abrir_pdf, imprimir_recibo_y_limpiar
                import os # Import os for file operations
                
                resultado = registrar_abono(self.cuota_id, monto)
                
                if resultado['pagado_completo']:
                    messagebox.showinfo("¡Pago Completado!", 
                                      "Se ha cubierto el total de la cuota.\nGenerando recibo...")
                    
                    if resultado['recibo']:
                        pdf_path = generar_recibo_cuota_pdf_temporal(resultado['recibo']['recibo_id'])
                        abrir_pdf(pdf_path)
                        
                        if messagebox.askyesno("Imprimir", "¿Desea imprimir el recibo?"):
                            imprimir_recibo_y_limpiar(pdf_path)
                        else:
                            try:
                                os.remove(pdf_path)
                            except:
                                pass
                else:
                    saldo = resultado['saldo_restante']
                    messagebox.showinfo("Abono Registrado", 
                                      f"Abono registrado correctamente.\nSaldo restante: ${saldo:.2f}\n\n"
                                      "Recuerde: El recibo se generará al cubrir el total.")
                
                self.ventana_padre.cargar_historial()
                self.ventana.destroy()
                
        except ValueError:
            messagebox.showerror("Error", "Ingrese un monto válido")
        except Exception as e:
            messagebox.showerror("Error", f"Error al registrar pago: {e}")


class VentanaEditarLote:
    """Ventana de opciones para editar un lote (renombrar, partir o cambiar superficie)"""
    
    def __init__(self, parent, campesino, ventana_principal):
        self.campesino = campesino
        self.ventana_principal = ventana_principal
        
        self.ventana = tk.Toplevel(parent)
        self.ventana.title(f"✏️ Editar Lote {campesino['numero_lote']}")
        self.ventana.geometry("520x450")
        self.ventana.transient(parent)
        self.ventana.grab_set()
        
        self.crear_widgets()
    
    def crear_widgets(self):
        # Canvas con scrollbar
        self.canvas, self.frame_principal = crear_ventana_scrollable(self.ventana, None)
        
        frame = ttk.Frame(self.frame_principal, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Título
        ttk.Label(frame, text=f"✏️ EDITAR LOTE {self.campesino['numero_lote']}",
                 font=('Helvetica', 14, 'bold')).pack(pady=10)
        
        # Información actual
        info_frame = ttk.LabelFrame(frame, text="Información Actual", padding="15")
        info_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(info_frame, text=f"Dueño: {self.campesino['nombre']}",
                 font=('Helvetica', 10)).pack(anchor=tk.W, pady=2)
        ttk.Label(info_frame, text=f"Lote: {self.campesino['numero_lote']}",
                 font=('Helvetica', 10)).pack(anchor=tk.W, pady=2)
        ttk.Label(info_frame, text=f"Superficie: {self.campesino['superficie']} ha",
                 font=('Helvetica', 10)).pack(anchor=tk.W, pady=2)
        ttk.Label(info_frame, text=f"Localidad: {self.campesino['localidad']}",
                 font=('Helvetica', 10)).pack(anchor=tk.W, pady=2)
        
        # Opciones
        opciones_frame = ttk.LabelFrame(frame, text="Opciones de Edición", padding="15")
        opciones_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Botón renombrar
        btn_renombrar = ttk.Button(opciones_frame, 
                                   text="✏️ Renombrar Dueño",
                                   command=self.renombrar)
        btn_renombrar.pack(fill=tk.X, pady=5)
        ttk.Label(opciones_frame, text="Cambiar el nombre del dueño del lote",
                 font=('Helvetica', 9), foreground='gray').pack(anchor=tk.W, padx=20)
        
        # Separador
        ttk.Separator(opciones_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        # Botón editar superficie
        btn_superficie = ttk.Button(opciones_frame,
                                    text="📐 Editar Superficie",
                                    command=self.editar_superficie)
        btn_superficie.pack(fill=tk.X, pady=5)
        ttk.Label(opciones_frame, text="Modificar el tamaño de la parcela en hectáreas",
                 font=('Helvetica', 9), foreground='gray').pack(anchor=tk.W, padx=20)
        
        # Separador
        ttk.Separator(opciones_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        # Botón partir
        btn_partir = ttk.Button(opciones_frame,
                               text="✂️ Partir Lote (Subdividir)",
                               command=self.partir)
        btn_partir.pack(fill=tk.X, pady=5)
        ttk.Label(opciones_frame, text="Dividir el lote en múltiples sublotes (herencia)",
                 font=('Helvetica', 9), foreground='gray').pack(anchor=tk.W, padx=20)
        
        # Botón cerrar
        ttk.Button(frame, text="❌ Cerrar",
                  command=self.ventana.destroy).pack(pady=10)
    
    def renombrar(self):
        """Abre ventana para renombrar"""
        self.ventana.destroy()
        VentanaRenombrarCampesino(
            self.ventana.master,
            self.campesino['id'],
            self.campesino['nombre'],
            self.campesino['numero_lote'],
            self.ventana_principal
        )
    
    def editar_superficie(self):
        """Abre ventana para editar superficie"""
        self.ventana.destroy()
        VentanaEditarSuperficie(
            self.ventana.master,
            self.campesino['id'],
            self.campesino['nombre'],
            self.campesino['numero_lote'],
            self.campesino['superficie'],
            self.ventana_principal
        )
    
    def partir(self):
        """Abre ventana para partir lote"""
        self.ventana.destroy()
        VentanaPartirLote(
            self.ventana.master,
            self.campesino['id'],
            self.campesino['nombre'],
            self.campesino['numero_lote'],
            self.campesino['superficie'],
            self.ventana_principal
        )

class VentanaEditarSuperficie:
    """Ventana para editar la superficie de un lote"""
    
    def __init__(self, parent, campesino_id, campesino_nombre, lote, superficie_actual, ventana_principal):
        self.campesino_id = campesino_id
        self.nombre = campesino_nombre
        self.lote = lote
        self.superficie_actual = superficie_actual
        self.ventana_principal = ventana_principal
        
        self.ventana = tk.Toplevel(parent)
        self.ventana.title(f"📐 Editar Superficie - Lote {lote}")
        self.ventana.geometry("450x280")
        self.ventana.transient(parent)
        self.ventana.grab_set()
        
        self.crear_widgets()
    
    def crear_widgets(self):
        # Canvas con scrollbar
        self.canvas, self.frame_principal = crear_ventana_scrollable(self.ventana, None)
        
        frame = ttk.Frame(self.frame_principal, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text=f"📐 EDITAR SUPERFICIE - LOTE {self.lote}", 
                 font=('Helvetica', 12, 'bold')).pack(pady=10)
        
        # Info actual
        info_frame = ttk.LabelFrame(frame, text="Información Actual", padding="10")
        info_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(info_frame, text=f"Dueño: {self.nombre}",
                 font=('Helvetica', 10)).pack(anchor=tk.W, pady=2)
        ttk.Label(info_frame, text=f"Superficie actual: {self.superficie_actual} hectáreas",
                 font=('Helvetica', 10, 'bold'), foreground='blue').pack(anchor=tk.W, pady=2)
        
        # Nuevo valor
        ttk.Label(frame, text="Nueva superficie (hectáreas):",
                 font=('Helvetica', 10)).pack(pady=(15, 5))
        
        self.entry_superficie = ttk.Entry(frame, width=20, font=('Helvetica', 12))
        self.entry_superficie.pack(pady=5)
        self.entry_superficie.insert(0, str(self.superficie_actual))
        self.entry_superficie.select_range(0, tk.END)
        self.entry_superficie.focus()
        
        # Advertencia
        ttk.Label(frame, text="⚠️ Esto actualizará el tamaño de la parcela permanentemente",
                 font=('Helvetica', 9), foreground='orange').pack(pady=10)
        
        # Botones
        frame_botones = ttk.Frame(frame)
        frame_botones.pack(pady=15)
        
        ttk.Button(frame_botones, text="✅ Actualizar",
                  command=self.guardar).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones, text="❌ Cancelar",
                  command=self.ventana.destroy).pack(side=tk.LEFT, padx=5)
    
    def guardar(self):
        nueva_superficie_str = self.entry_superficie.get().strip()
        
        if not nueva_superficie_str:
            messagebox.showwarning("Advertencia", "Debe ingresar una superficie")
            return
        
        try:
            nueva_superficie = float(nueva_superficie_str)
            
            if nueva_superficie <= 0:
                messagebox.showerror("Error", "La superficie debe ser mayor a 0")
                return
            
            if nueva_superficie == self.superficie_actual:
                messagebox.showinfo("Sin cambios", "La superficie no ha cambiado")
                return
            
            if messagebox.askyesno("Confirmar",
                                  f"¿Actualizar superficie del lote {self.lote}?\n\n"
                                  f"Superficie actual: {self.superficie_actual} ha\n"
                                  f"Nueva superficie: {nueva_superficie} ha"):
                
                actualizar_superficie_campesino(self.campesino_id, nueva_superficie)
                
                messagebox.showinfo("Éxito", 
                                  f"Superficie actualizada correctamente\n\n"
                                  f"{self.superficie_actual} ha → {nueva_superficie} ha")
                
                # Actualizar UI
                self.ventana_principal.cargar_todos_campesinos()
                self.ventana.destroy()
                
        except ValueError:
            messagebox.showerror("Error", "Debe ingresar un número válido")
        except Exception as e:
            messagebox.showerror("Error", f"Error al actualizar:\n{str(e)}")

class VentanaGestorReportes:
    """Gestor de reportes - Lista, abre y genera reportes diarios"""
    
    def __init__(self, parent, fecha_actual):
        self.fecha_actual = fecha_actual
        
        self.ventana = tk.Toplevel(parent)
        self.ventana.title("📊 Gestor de Reportes")
        self.ventana.geometry("900x600")
        self.ventana.transient(parent)
        
        self.crear_widgets()
        self.cargar_reportes()
    
    def crear_widgets(self):
        # Canvas con scrollbar
        self.canvas, self.frame_principal = crear_ventana_scrollable(self.ventana, None)
        
        frame = ttk.Frame(self.frame_principal, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="GESTOR DE REPORTES", font=("Helvetica", 14, "bold")).pack(pady=10)
        
        # ✅ FRAME DE BOTONES EN CUADRÍCULA
        frame_btnssup = ttk.Frame(frame)
        frame_btnssup.pack(fill=tk.X, pady=10)
        
        # FILA 1: VENTA DÍA
        ttk.Label(frame_btnssup, text="VENTA DEL DÍA:", font=("Helvetica", 10, "bold")).grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5)
        
        ttk.Button(frame_btnssup, text="📄 PDF", 
                command=self.generar_nuevo_reporte, width=15).grid(
            row=0, column=1, padx=5, pady=5)
        
        ttk.Button(frame_btnssup, text="📊 Excel", 
                command=self.generar_corte_caja, width=15).grid(
            row=0, column=2, padx=5, pady=5)
        
        # FILA 2: CUOTAS DÍA
        ttk.Label(frame_btnssup, text="CUOTAS DEL DÍA:", font=("Helvetica", 10, "bold")).grid(
            row=1, column=0, sticky=tk.W, padx=5, pady=5)
        
        ttk.Button(frame_btnssup, text="💰 PDF", 
                command=self.generar_reporte_cuotas_dia, width=15).grid(
            row=1, column=1, padx=5, pady=5)
        
        ttk.Button(frame_btnssup, text="💰 Excel", 
                command=self.exportar_cuotas_excel, width=15).grid(
            row=1, column=2, padx=5, pady=5)
        
        # FILA 3: OTROS BOTONES
        ttk.Button(frame_btnssup, text="🔄 Actualizar Lista", 
                command=self.cargar_reportes, width=15).grid(
            row=0, column=3, padx=5, pady=5)
        
        ttk.Button(frame_btnssup, text="📁 Abrir Carpeta", 
                command=self.abrir_carpeta_reportes, width=15).grid(
            row=1, column=3, padx=5, pady=5)
        
        
        # Frame de lista de reportes
        frame_lista = ttk.LabelFrame(frame, text="Reportes Disponibles", padding="10")
        frame_lista.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Tabla de reportes
        columnas = ('fecha', 'archivo', 'tamaño', 'recibos', 'total')
        self.tree = ttk.Treeview(frame_lista, columns=columnas, show='headings', height=15)
        
        self.tree.heading('fecha', text='Fecha')
        self.tree.heading('archivo', text='Nombre del Archivo')
        self.tree.heading('tamaño', text='Tamaño')
        self.tree.heading('recibos', text='Recibos')
        self.tree.heading('total', text='Total')
        
        self.tree.column('fecha', width=120)
        self.tree.column('archivo', width=300)
        self.tree.column('tamaño', width=100)
        self.tree.column('recibos', width=80)
        self.tree.column('total', width=120)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(frame_lista, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Doble click para abrir
        self.tree.bind('<Double-1>', lambda e: self.abrir_reporte())
        
        # Frame de botones inferiores
        frame_btns_inf = ttk.Frame(frame)
        frame_btns_inf.pack(fill=tk.X, pady=10)
        
        ttk.Button(frame_btns_inf, text="📄 Abrir PDF",
                  command=self.abrir_reporte,
                  width=15).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(frame_btns_inf, text="🖨️ Imprimir",
                  command=self.imprimir_reporte,
                  width=15).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(frame_btns_inf, text="🗑️ Eliminar",
                  command=self.eliminar_reporte,
                  width=15).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(frame_btns_inf, text="❌ Cerrar",
                  command=self.ventana.destroy,
                  width=15).pack(side=tk.RIGHT, padx=5)
    
    def cargar_reportes(self):
        """Carga los reportes existentes ORGANIZADOS POR CATEGORÍA"""
        self.tree.delete(*self.tree.get_children())
        
        reportes_dir = os.path.join('database', 'reportes')
        
        if not os.path.exists(reportes_dir):
            return
        
        archivos = [f for f in os.listdir(reportes_dir) if f.endswith(('.pdf', '.xlsx'))]
        
        # ✅ SEPARAR POR CATEGORÍAS
        excel_ventas = []
        pdf_ventas = []
        pdf_estadisticas = []
        pdf_cuotas = []
        excel_cuotas = []
        
        for archivo in archivos:
            ruta = os.path.join(reportes_dir, archivo)
            fecha_modificacion = datetime.fromtimestamp(os.path.getmtime(ruta))
            fecha_str = fecha_modificacion.strftime('%Y-%m-%d %H:%M')
            tamano = os.path.getsize(ruta) / 1024  # KB
            
            # Clasificar por tipo
            if 'cuota' in archivo.lower() and archivo.endswith('.xlsx'):
                excel_cuotas.append((archivo, fecha_str, tamano, ruta))
            elif 'cuota' in archivo.lower() and archivo.endswith('.pdf'):
                pdf_cuotas.append((archivo, fecha_str, tamano, ruta))
            elif 'estadisticas' in archivo.lower():
                pdf_estadisticas.append((archivo, fecha_str, tamano, ruta))
            elif archivo.endswith('.xlsx'):
                excel_ventas.append((archivo, fecha_str, tamano, ruta))
            elif archivo.endswith('.pdf'):
                pdf_ventas.append((archivo, fecha_str, tamano, ruta))
        
        # ✅ INSERTAR CON ENCABEZADOS DE CATEGORÍA
        
        # 1. EXCEL VENTA DEL DÍA
        if excel_ventas:
            self.tree.insert('', tk.END, values=('📊 EXCEL VENTA DEL DÍA', '', '', ''), tags=('header',))
            for archivo, fecha, tamano, ruta in sorted(excel_ventas, key=lambda x: x[1], reverse=True):
                self.tree.insert('', tk.END, 
                                values=(archivo, fecha, f"{tamano:.1f} KB", '📄'),
                                tags=(ruta,))
        
        # 2. PDF VENTA DEL DÍA
        if pdf_ventas:
            self.tree.insert('', tk.END, values=('📄 PDF VENTA DEL DÍA', '', '', ''), tags=('header',))
            for archivo, fecha, tamano, ruta in sorted(pdf_ventas, key=lambda x: x[1], reverse=True):
                self.tree.insert('', tk.END, 
                                values=(archivo, fecha, f"{tamano:.1f} KB", '📄'),
                                tags=(ruta,))
        
        # 3. ESTADÍSTICAS PDF
        if pdf_estadisticas:
            self.tree.insert('', tk.END, values=('📊 ESTADÍSTICAS PDF', '', '', ''), tags=('header',))
            for archivo, fecha, tamano, ruta in sorted(pdf_estadisticas, key=lambda x: x[1], reverse=True):
                self.tree.insert('', tk.END, 
                                values=(archivo, fecha, f"{tamano:.1f} KB", '📄'),
                                tags=(ruta,))
        
        # 4. CUOTAS PDF
        if pdf_cuotas:
            self.tree.insert('', tk.END, values=('💰 CUOTAS PDF', '', '', ''), tags=('header',))
            for archivo, fecha, tamano, ruta in sorted(pdf_cuotas, key=lambda x: x[1], reverse=True):
                self.tree.insert('', tk.END, 
                                values=(archivo, fecha, f"{tamano:.1f} KB", '📄'),
                                tags=(ruta,))
        
        # 5. CUOTAS EXCEL
        if excel_cuotas:
            self.tree.insert('', tk.END, values=('💰 CUOTAS EXCEL', '', '', ''), tags=('header',))
            for archivo, fecha, tamano, ruta in sorted(excel_cuotas, key=lambda x: x[1], reverse=True):
                self.tree.insert('', tk.END, 
                                values=(archivo, fecha, f"{tamano:.1f} KB", '📄'),
                                tags=(ruta,))

    
    def generar_nuevo_reporte(self):
        """Genera un reporte del día actual"""
        try:
            from modules.logic import calcular_total_dia
            from modules.reports import generar_reporte_diario
            
            recibos = obtener_recibos_dia(self.fecha_actual)
            
            if not recibos:
                messagebox.showwarning("Sin datos", 
                                      "No hay recibos para el día actual.\n"
                                      "No se puede generar el reporte.")
                return
            
            # Generar reporte
            ruta_pdf = generar_reporte_diario(self.fecha_actual, recibos)
            
            messagebox.showinfo("Éxito", 
                              f"Reporte generado correctamente\n\n"
                              f"Recibos: {len(recibos)}\n"
                              f"Total: ${calcular_total_dia(self.fecha_actual):,.2f}")
            
            # Recargar lista
            self.cargar_reportes()
            
            # Abrir automáticamente
            from modules.reports import abrir_pdf
            abrir_pdf(ruta_pdf)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al generar reporte:\n{str(e)}")
    
    def generar_corte_caja(self):
        """Genera corte de caja en Excel"""
        try:
            from modules.logic import calcular_total_dia
            from modules.reports import generar_corte_caja_excel
            
            recibos = obtener_recibos_dia(self.fecha_actual)
            
            if not recibos:
                messagebox.showwarning("Sin datos", 
                                    "No hay recibos para el día actual.\n"
                                    "No se puede generar el corte de caja.")
                return
            
            # Generar Excel
            ruta_excel = generar_corte_caja_excel(self.fecha_actual, recibos)
            
            messagebox.showinfo("Éxito", 
                            f"Corte de caja generado correctamente\n\n"
                            f"Recibos: {len(recibos)}\n"
                            f"Total: ${calcular_total_dia(self.fecha_actual):,.2f}\n\n"
                            f"Archivo: {os.path.basename(ruta_excel)}")
            
            # Recargar lista
            self.cargar_reportes()
            
            # Abrir automáticamente
            self.abrir_archivo(ruta_excel)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al generar corte de caja:\n{str(e)}")

    def abrir_reporte(self):
        """Abre el archivo seleccionado (PDF o Excel)"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Advertencia", "Debe seleccionar un archivo")
            return
        
        item = self.tree.item(selection[0])
        ruta_archivo = item['tags'][0]
        
        try:
            self.abrir_archivo(ruta_archivo)
        except Exception as e:
            messagebox.showerror("Error", f"Error al abrir archivo:\n{str(e)}")

    def abrir_archivo(self, ruta):
        """Abre un archivo con la aplicación predeterminada del sistema"""
        try:
            if platform.system() == 'Windows':
                os.startfile(ruta)
            elif platform.system() == 'Darwin':  # macOS
                import subprocess
                subprocess.run(['open', ruta])
            else:  # Linux
                import subprocess
                subprocess.run(['xdg-open', ruta])
        except Exception as e:
            raise Exception(f"No se pudo abrir el archivo: {str(e)}")

    def imprimir_reporte(self):
        """Imprime el reporte seleccionado"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Advertencia", "Debe seleccionar un reporte")
            return
        
        item = self.tree.item(selection[0])
        ruta_pdf = item['tags'][0]
        
        if messagebox.askyesno("Confirmar", "¿Imprimir este reporte?"):
            try:
                from modules.reports import imprimir_recibo
                imprimir_recibo(ruta_pdf)
                messagebox.showinfo("Éxito", "Reporte enviado a imprimir")
            except Exception as e:
                messagebox.showerror("Error", f"Error al imprimir:\n{str(e)}")
    
    def eliminar_reporte(self):
        """Elimina el reporte seleccionado"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Advertencia", "Debe seleccionar un reporte")
            return
        
        item = self.tree.item(selection[0])
        ruta_pdf = item['tags'][0]
        archivo = item['values'][1]
        
        if messagebox.askyesno("Confirmar Eliminación", 
                              f"¿Eliminar el reporte?\n\n{archivo}\n\n"
                              f"Esta acción no se puede deshacer."):
            try:
                os.remove(ruta_pdf)
                messagebox.showinfo("Éxito", "Reporte eliminado correctamente")
                self.cargar_reportes()
            except Exception as e:
                messagebox.showerror("Error", f"Error al eliminar:\n{str(e)}")
    
    def abrir_carpeta_reportes(self):
        """Abre la carpeta de reportes en el explorador"""
        reportes_dir = os.path.join('database', 'reportes')
        
        try:
            if platform.system() == 'Windows':
                os.startfile(reportes_dir)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', reportes_dir])
            else:  # Linux
                subprocess.run(['xdg-open', reportes_dir])
        except Exception as e:
            messagebox.showerror("Error", f"Error al abrir carpeta:\n{str(e)}")

    def generar_reporte_cuotas_dia(self):
        """Genera reporte PDF de cuotas cobradas hoy"""
        try:
            from modules.reports import generar_reporte_cuotas_dia_pdf, abrir_pdf
            
            pdf_path = generar_reporte_cuotas_dia_pdf()
            abrir_pdf(pdf_path)
            
            messagebox.showinfo("Éxito", 
                                f"Reporte de cuotas generado correctamente\n"
                                f"Ruta: {pdf_path}")
            
            # Recargar lista de reportes
            self.cargar_reportes()
            
        except ValueError as e:
            messagebox.showwarning("Sin Datos", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Error al generar reporte de cuotas:\n{str(e)}")

    def exportar_cuotas_excel(self):
        """Exporta cuotas del día a Excel"""
        try:
            from modules.reports import generar_excel_cuotas_dia
            
            excel_path = generar_excel_cuotas_dia()
            
            # Abrir automáticamente
            if os.name == 'nt':  # Windows
                os.startfile(excel_path)
            elif sys.platform == 'darwin':  # macOS
                subprocess.call(['open', excel_path])
            else:  # Linux
                subprocess.call(['xdg-open', excel_path])
            
            messagebox.showinfo("Éxito", 
                                f"Excel de cuotas generado correctamente\n"
                                f"Ruta: {excel_path}")
            
            # Recargar lista de reportes
            self.cargar_reportes()
            
        except ValueError as e:
            messagebox.showwarning("Sin Datos", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Error al generar Excel de cuotas:\n{str(e)}")


# ==================== CLASE NUEVA: FORMULARIO NUEVO CAMPESINO ====================

class VentanaFormularioNuevoCampesino:
    """Ventana de formulario para registrar un nuevo campesino/ejidatario"""
    
    def __init__(self, parent, ventana_principal):
        self.ventana_principal = ventana_principal
        self.ventana = tk.Toplevel(parent)
        self.ventana.title("➕ Nuevo Ejidatario")
        self.ventana.geometry("700x850")
        self.ventana.transient(parent)
        self.ventana.grab_set()
        
        # Variables
        self.entries = {}
        self.var_barrio = tk.StringVar()
        
        # Crear widgets
        self.crear_widgets()
    
    def crear_widgets(self):
        """Crea la interfaz del formulario"""
        
        # Canvas con scrollbar
        canvas, scrollable_frame = crear_ventana_scrollable(self.ventana, None)
        
        # ===== ENCABEZADO =====
        frame_encabezado = ttk.Frame(scrollable_frame, padding="15")
        frame_encabezado.pack(fill=tk.X)
        
        ttk.Label(frame_encabezado, 
                 text="➕ REGISTRAR NUEVO EJIDATARIO",
                 font=('Helvetica', 14, 'bold')).pack(pady=10)
        
        ttk.Label(frame_encabezado,
                 text="Complete todos los campos para crear un nuevo ejidatario",
                 font=('Helvetica', 9),
                 foreground='gray').pack()
        
        # ===== FORMULARIO PRINCIPAL =====
        frame_form = ttk.LabelFrame(scrollable_frame, 
                                   text="Datos del Ejidatario",
                                   padding="25")
        frame_form.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Campo 1: NÚMERO DE LOTE
        ttk.Label(frame_form, text="Número de Lote *", 
                 font=('Helvetica', 10, 'bold')).pack(anchor=tk.W, pady=(15, 5))
        entry_lote = ttk.Entry(frame_form, font=('Helvetica', 11), width=35)
        entry_lote.pack(fill=tk.X, pady=(0, 5))
        self.entries['numero_lote'] = entry_lote
        ttk.Label(frame_form, text="Ej: 1, 2, 15, 203, 2-A, 15-B",
                 font=('Helvetica', 8), foreground='#666666').pack(anchor=tk.W, pady=(0, 15))
        
        # Campo 2: NOMBRE
        ttk.Label(frame_form, text="Nombre Completo *",
                 font=('Helvetica', 10, 'bold')).pack(anchor=tk.W, pady=(15, 5))
        entry_nombre = ttk.Entry(frame_form, font=('Helvetica', 11), width=35)
        entry_nombre.pack(fill=tk.X, pady=(0, 5))
        self.entries['nombre'] = entry_nombre
        ttk.Label(frame_form, text="Nombre del propietario del lote",
                 font=('Helvetica', 8), foreground='#666666').pack(anchor=tk.W, pady=(0, 15))
        
        # Campo 3: LOCALIDAD
        ttk.Label(frame_form, text="Localidad *",
                 font=('Helvetica', 10, 'bold')).pack(anchor=tk.W, pady=(15, 5))
        entry_localidad = ttk.Entry(frame_form, font=('Helvetica', 11), width=35)
        entry_localidad.insert(0, "Tezontepec de Aldama")
        entry_localidad.pack(fill=tk.X, pady=(0, 5))
        self.entries['localidad'] = entry_localidad
        ttk.Label(frame_form, text="Municipio o localidad",
                 font=('Helvetica', 8), foreground='#666666').pack(anchor=tk.W, pady=(0, 15))
        
        # Campo 4: BARRIO
        ttk.Label(frame_form, text="Barrio *",
                 font=('Helvetica', 10, 'bold')).pack(anchor=tk.W, pady=(15, 5))
        barrios = ['PANUAYA', 'TEZONTEPEC', 'ATENGO', 'MANGAS', 'PRESAS', 'HUITEL']
        combo_barrio = ttk.Combobox(frame_form, textvariable=self.var_barrio,
                                   values=barrios, state='readonly',
                                   font=('Helvetica', 11), width=32)
        combo_barrio.pack(fill=tk.X, pady=(0, 5))
        self.entries['barrio'] = combo_barrio
        ttk.Label(frame_form, text="Selecciona el barrio correspondiente",
                 font=('Helvetica', 8), foreground='#666666').pack(anchor=tk.W, pady=(0, 15))
        
        # Campo 5: SUPERFICIE
        ttk.Label(frame_form, text="Superficie (hectáreas) *",
                 font=('Helvetica', 10, 'bold')).pack(anchor=tk.W, pady=(15, 5))
        entry_superficie = ttk.Entry(frame_form, font=('Helvetica', 11), width=35)
        entry_superficie.pack(fill=tk.X, pady=(0, 5))
        self.entries['superficie'] = entry_superficie
        ttk.Label(frame_form, text="Ej: 0.5, 1.0, 1.25, 2.0 (use punto decimal)",
                 font=('Helvetica', 8), foreground='#666666').pack(anchor=tk.W, pady=(0, 15))
        
        # Campo 6: EXTENSIÓN DE TIERRA (opcional)
        ttk.Label(frame_form, text="Extensión de Tierra (Opcional)",
                 font=('Helvetica', 10, 'bold')).pack(anchor=tk.W, pady=(15, 5))
        entry_extension = ttk.Entry(frame_form, font=('Helvetica', 11), width=35)
        entry_extension.pack(fill=tk.X, pady=(0, 5))
        self.entries['extension_tierra'] = entry_extension
        ttk.Label(frame_form, text="Ej: Regadío, Temporal, Mixto, Riego",
                 font=('Helvetica', 8), foreground='#666666').pack(anchor=tk.W, pady=(0, 20))
        
        # Separador
        ttk.Separator(frame_form, orient='horizontal').pack(fill=tk.X, pady=20)
        
        # ===== BOTONES =====
        frame_botones = ttk.Frame(frame_form)
        frame_botones.pack(pady=20, fill=tk.X, expand=True)
        
        ttk.Button(frame_botones, text="✅ GUARDAR EJIDATARIO",
                  command=self.guardar_campesino,
                  width=24).pack(side=tk.LEFT, padx=10)
        
        ttk.Button(frame_botones, text="❌ CANCELAR",
                  command=self.ventana.destroy,
                  width=18).pack(side=tk.LEFT, padx=10)
        
        # Nota al pie
        frame_pie = ttk.Frame(scrollable_frame, padding="10")
        frame_pie.pack(fill=tk.X)
        ttk.Label(frame_pie, text="Los campos marcados con * son obligatorios",
                 font=('Helvetica', 9), foreground='gray').pack()
    
    def validar_datos(self) -> tuple:
        """Valida los datos antes de guardar. Retorna (True/False, mensaje)"""
        
        # Validar LOTE
        lote = self.entries['numero_lote'].get().strip()
        if not lote:
            return False, "❌ El número de lote es obligatorio"
        if len(lote) > 10:
            return False, "❌ El lote es muy largo (máximo 10 caracteres)"
        
        # Validar NOMBRE
        nombre = self.entries['nombre'].get().strip()
        if not nombre:
            return False, "❌ El nombre es obligatorio"
        if len(nombre) < 3:
            return False, "❌ El nombre debe tener al menos 3 caracteres"
        if len(nombre) > 100:
            return False, "❌ El nombre es muy largo (máximo 100 caracteres)"
        
        # Validar LOCALIDAD
        localidad = self.entries['localidad'].get().strip()
        if not localidad:
            return False, "❌ La localidad es obligatoria"
        
        # Validar BARRIO
        barrio = self.var_barrio.get().strip()
        if not barrio:
            return False, "❌ Debe seleccionar un barrio"
        
        # Validar SUPERFICIE
        try:
            superficie_str = self.entries['superficie'].get().strip()
            if not superficie_str:
                return False, "❌ La superficie es obligatoria"
            
            superficie = float(superficie_str)
            
            if superficie <= 0:
                return False, "❌ La superficie debe ser mayor a 0"
            if superficie > 100:
                return False, "❌ La superficie parece incorrecta (mayor a 100 ha)"
        except ValueError:
            return False, "❌ La superficie debe ser un número válido (ej: 0.5, 1.25, 2.0)"
        
        return True, "OK"
    
    def guardar_campesino(self):
        """Guarda el nuevo campesino en la base de datos"""
        
        # PASO 1: Validar
        es_valido, mensaje = self.validar_datos()
        
        if not es_valido:
            messagebox.showerror("❌ Error de Validación", mensaje)
            return
        
        try:
            # PASO 2: Preparar datos
            datos = {
                'numero_lote': self.entries['numero_lote'].get().strip(),
                'nombre': self.entries['nombre'].get().strip(),
                'localidad': self.entries['localidad'].get().strip(),
                'barrio': self.var_barrio.get().strip(),
                'superficie': float(self.entries['superficie'].get().strip()),
                'extension_tierra': self.entries['extension_tierra'].get().strip() or ''
            }
            
            # PASO 3: Crear en base de datos
            nuevo_id = crear_campesino(datos)
            
            # PASO 4: Mostrar confirmación
            messagebox.showinfo(
                "✅ Éxito",
                f"Ejidatario registrado correctamente!\n\n"
                f"Lote: {datos['numero_lote']}\n"
                f"Nombre: {datos['nombre']}\n"
                f"Barrio: {datos['barrio']}\n"
                f"Superficie: {datos['superficie']:.2f} ha"
            )
            
            # PASO 5: Actualizar lista en ventana principal
            self.ventana_principal.cargar_todos_campesinos(ordenar_por_lote=True)
            
            # PASO 6: Cerrar ventana del formulario
            self.ventana.destroy()
        
        except Exception as e:
            messagebox.showerror(
                "❌ Error al Guardar",
                f"No se pudo crear el ejidatario:\n\n{str(e)}"
            )


class VentanaGestionarCuotas:
    """Ventana principal para gestionar cuotas de cooperación"""
    
    def __init__(self, parent, ventana_principal):
        self.ventana = tk.Toplevel(parent)
        self.ventana.title("💰 Gestionar Cuotas de Cooperación")
        self.ventana.geometry("800x600")
        self.ventana.transient(parent)
        self.ventana.grab_set()
        self.ventana_principal = ventana_principal
        
        self.canvas, self.frame_principal = crear_ventana_scrollable(self.ventana, None)
        self.crear_widgets()
        self.cargar_tipos_cuota()
    
    def crear_widgets(self):
        """Crea los widgets de la ventana"""
        frame_content = ttk.Frame(self.frame_principal, padding=20)
        frame_content.pack(fill=tk.BOTH, expand=True)
        
        frame_superior = ttk.Frame(frame_content)
        frame_superior.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(frame_superior, text="GESTIÓN DE CUOTAS", 
                  font=("Helvetica", 14, "bold")).pack()
        
        # BOTONES DE ACCIÓN
        frame_acciones = ttk.Frame(frame_content)
        frame_acciones.pack(fill=tk.X, pady=10)
        
        ttk.Button(frame_acciones, text="➕ Nueva Cuota", 
                   command=self.abrir_nueva_cuota, width=20).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_acciones, text="📋 Ver Todas las Cuotas", 
                   command=self.ver_todas_cuotas, width=20).pack(side=tk.LEFT, padx=5)
        
        # LISTA DE TIPOS DE CUOTAS
        frame_lista = ttk.LabelFrame(frame_content, text="Cuotas Disponibles", padding=10)
        frame_lista.pack(fill=tk.BOTH, expand=True, pady=10)
        
        columnas = ('nombre', 'monto', 'asignados', 'pagados', 'pendientes', 'recaudado')
        self.tree = ttk.Treeview(frame_lista, columns=columnas, show='headings', height=15)
        
        self.tree.heading('nombre', text='Nombre de la Cuota')
        self.tree.heading('monto', text='Monto')
        self.tree.heading('asignados', text='Asignados')
        self.tree.heading('pagados', text='Pagados')
        self.tree.heading('pendientes', text='Pendientes')
        self.tree.heading('recaudado', text='Recaudado')
        
        self.tree.column('nombre', width=200)
        self.tree.column('monto', width=80)
        self.tree.column('asignados', width=80)
        self.tree.column('pagados', width=80)
        self.tree.column('pendientes', width=80)
        self.tree.column('recaudado', width=100)
        
        scrollbar = ttk.Scrollbar(frame_lista, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind doble click
        self.tree.bind('<Double-1>', self.on_doble_click_cuota)
        
        # BOTONES INFERIORES
        frame_botones = ttk.Frame(frame_content)
        frame_botones.pack(fill=tk.X, pady=10)
        
        ttk.Button(frame_botones, text="🔄 Actualizar", 
                   command=self.cargar_tipos_cuota).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones, text="Cerrar", 
                   command=self.ventana.destroy).pack(side=tk.RIGHT, padx=5)
    
    def cargar_tipos_cuota(self):
        """Carga los tipos de cuota existentes"""
        from modules.cuotas import obtener_todas_cuotas_con_estado
        
        self.tree.delete(*self.tree.get_children())
        
        cuotas = obtener_todas_cuotas_con_estado()
        
        for cuota in cuotas:
            self.tree.insert('', tk.END, 
                            values=(
                                cuota['nombre'],
                                f"${cuota['monto']:.2f}",
                                cuota['total_asignados'] or 0,
                                cuota['total_pagados'] or 0,
                                cuota['total_pendientes'] or 0,
                                f"${cuota['monto_recaudado'] or 0:.2f}"
                            ),
                            tags=(str(cuota['id']),))
    
    def on_doble_click_cuota(self, event):
        """Abre el detalle de la cuota seleccionada"""
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            tipo_cuota_id = int(item['tags'][0])
            VentanaDetalleCuota(self.ventana, tipo_cuota_id, self)
    
    def abrir_nueva_cuota(self):
        """Abre ventana para crear nueva cuota"""
        VentanaNuevaCuota(self.ventana, self)
    
    def ver_todas_cuotas(self):
        """Abre ventana con todas las cuotas y su recaudación"""
        VentanaReporteCuotas(self.ventana)


class VentanaNuevaCuota:
    """Ventana para crear un nuevo tipo de cuota"""
    
    def __init__(self, parent, ventana_gestionar):
        self.ventana = tk.Toplevel(parent)
        self.ventana.title("Nueva Cuota de Cooperación")
        self.ventana.geometry("500x400")
        self.ventana.transient(parent)
        self.ventana.grab_set()
        self.ventana_gestionar = ventana_gestionar
        
        self.crear_widgets()
    
    def crear_widgets(self):
        """Crea los widgets"""
        # Canvas con scrollbar
        self.canvas, self.frame_principal = crear_ventana_scrollable(self.ventana, None)
        
        frame = ttk.Frame(self.frame_principal, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="CREAR NUEVA CUOTA", font=("Helvetica", 12, "bold")).pack(pady=10)
        
        # Formulario
        frame_form = ttk.LabelFrame(frame, text="Datos de la Cuota", padding=10)
        frame_form.pack(fill=tk.X, pady=10)
        
        ttk.Label(frame_form, text="Nombre de la Cuota:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.entry_nombre = ttk.Entry(frame_form, width=40)
        self.entry_nombre.grid(row=0, column=1, pady=5, padx=10)
        self.entry_nombre.focus()
        
        ttk.Label(frame_form, text="Tarifa por Hectárea ($):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.entry_monto = ttk.Entry(frame_form, width=40)
        self.entry_monto.grid(row=1, column=1, pady=5, padx=10)
        
        ttk.Label(frame_form, text="Descripción (opcional):").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.text_descripcion = tk.Text(frame_form, width=40, height=4)
        self.text_descripcion.grid(row=2, column=1, pady=5, padx=10)
        
        # Asignación
        frame_asignar = ttk.LabelFrame(frame, text="Asignar Cuota", padding=10)
        frame_asignar.pack(fill=tk.X, pady=10)
        
        ttk.Label(frame_asignar, text="Después de crear la cuota:", 
                  font=("Helvetica", 9)).pack(anchor=tk.W)
        
        self.var_asignar = tk.StringVar(value="manual")
        ttk.Radiobutton(frame_asignar, text="Asignar manualmente después", 
                        variable=self.var_asignar, value="manual").pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(frame_asignar, text="Asignar a TODOS los campesinos ahora", 
                        variable=self.var_asignar, value="todos").pack(anchor=tk.W, pady=2)
        
        # Botones
        frame_botones = ttk.Frame(frame)
        frame_botones.pack(pady=20)
        
        ttk.Button(frame_botones, text="💾 Crear Cuota", 
                   command=self.crear_cuota).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones, text="Cancelar", 
                   command=self.ventana.destroy).pack(side=tk.LEFT, padx=5)
    
    def crear_cuota(self):
        """Crea la nueva cuota"""
        nombre = self.entry_nombre.get().strip()
        monto_str = self.entry_monto.get().strip()
        descripcion = self.text_descripcion.get("1.0", tk.END).strip()
        
        if not nombre:
            messagebox.showerror("Error", "El nombre de la cuota es obligatorio")
            return
        
        if not monto_str:
            messagebox.showerror("Error", "El monto es obligatorio")
            return
        
        try:
            monto = float(monto_str)
            if monto <= 0:
                messagebox.showerror("Error", "El monto debe ser mayor a 0")
                return
        except ValueError:
            messagebox.showerror("Error", "El monto debe ser un número válido")
            return
        
        try:
            from modules.cuotas import crear_tipo_cuota, asignar_cuota_masiva
            from modules.models import obtener_todos_campesinos
            
            # Crear tipo de cuota
            tipo_cuota_id = crear_tipo_cuota(nombre, monto, descripcion)
            
            # Asignar a todos si se seleccionó
            if self.var_asignar.get() == "todos":
                campesinos = obtener_todos_campesinos()
                total = asignar_cuota_masiva(tipo_cuota_id, campesinos)
                
                messagebox.showinfo("Éxito", 
                                    f"Cuota '{nombre}' creada correctamente.\n"
                                    f"Asignada a {total} campesinos.")
            else:
                messagebox.showinfo("Éxito", f"Cuota '{nombre}' creada correctamente.")
            
            self.ventana_gestionar.cargar_tipos_cuota()
            self.ventana.destroy()
            
        except ValueError as e:
            messagebox.showerror("Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Error al crear cuota:\n{str(e)}")


class VentanaDetalleCuota:
    """Ventana con detalle de una cuota específica"""
    
    def __init__(self, parent, tipo_cuota_id, ventana_gestionar):
        self.ventana = tk.Toplevel(parent)
        self.ventana.title("Detalle de Cuota")
        self.ventana.geometry("900x650")
        self.ventana.transient(parent)
        self.ventana.grab_set()
        self.tipo_cuota_id = tipo_cuota_id
        self.ventana_gestionar = ventana_gestionar
        
        # Variable para checkbox de sobrecargo (se carga del tipo de cuota)
        self.var_sobrecargo = tk.BooleanVar(value=False)
        
        self.canvas, self.frame_principal = crear_ventana_scrollable(self.ventana, None)
        self.crear_widgets()
        self.cargar_detalle()
    
    def crear_widgets(self):
        """Crea los widgets"""
        frame = ttk.Frame(self.frame_principal, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Título
        self.label_titulo = ttk.Label(frame, text="", font=("Helvetica", 14, "bold"))
        self.label_titulo.pack(pady=10)
        
        # Resumen
        frame_resumen = ttk.LabelFrame(frame, text="Resumen", padding=10)
        frame_resumen.pack(fill=tk.X, pady=10)
        
        self.label_resumen = ttk.Label(frame_resumen, text="", font=("Helvetica", 10))
        self.label_resumen.pack()
        
        # Frame de botones
        frame_botones = ttk.Frame(frame)
        frame_botones.pack(fill=tk.X, pady=10)
        
        # Checkbox de sobrecargo (específico para este tipo de cuota)
        ttk.Checkbutton(frame_botones,
                       text="💰 COBRAR SOBRECARGO (+$50 mensual) para esta cuota",
                       variable=self.var_sobrecargo,
                       command=self.actualizar_sobrecargo).pack(side=tk.LEFT, padx=10)
        
        ttk.Button(frame_botones, text="➕ Asignar a Campesino",
                   command=self.asignar_a_campesino).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones, text="💾 Exportar PDF",
                   command=self.exportar_pdf).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones, text="❌ Cerrar",
                   command=self.ventana.destroy).pack(side=tk.RIGHT, padx=5)
        
        # Lista de campesinos con esta cuota
        frame_lista = ttk.LabelFrame(frame, text="Campesinos Asignados", padding=10)
        frame_lista.pack(fill=tk.BOTH, expand=True, pady=10)
        
        columnas = ('lote', 'nombre', 'barrio', 'monto', 'estado', 'fecha_pago')
        self.tree = ttk.Treeview(frame_lista, columns=columnas, show='headings', height=15)
        
        self.tree.heading('lote', text='Lote')
        self.tree.heading('nombre', text='Nombre')
        self.tree.heading('barrio', text='Barrio')
        self.tree.heading('monto', text='Monto')
        self.tree.heading('estado', text='Estado')
        self.tree.heading('fecha_pago', text='Fecha Pago')
        
        self.tree.column('lote', width=70)
        self.tree.column('nombre', width=200)
        self.tree.column('barrio', width=100)
        self.tree.column('monto', width=80)
        self.tree.column('estado', width=100)
        self.tree.column('fecha_pago', width=100)
        
        scrollbar = ttk.Scrollbar(frame_lista, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind doble click
        self.tree.bind('<Double-1>', self.on_doble_click_pagar)
        
        # Botones
        frame_botones = ttk.Frame(frame)
        frame_botones.pack(fill=tk.X, pady=10)
        
        ttk.Button(frame_botones, text="🔄 Actualizar", 
                   command=self.cargar_detalle).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones, text="Cerrar", 
                   command=self.ventana.destroy).pack(side=tk.RIGHT, padx=5)
    
    def cargar_detalle(self):
        """Carga el detalle de la cuota"""
        from modules.cuotas import obtener_resumen_cuota, obtener_tipos_cuota_activos, calcular_sobrecargo_acumulado
        from modules.models import get_connection as get_riego_connection
        
        # Obtener nombre de la cuota
        from modules.cuotas import get_cuotas_connection
        conn = get_cuotas_connection()
        cursor = conn.cursor()
        
        # Obtener datos del tipo de cuota
        cursor.execute("""
            SELECT * FROM tipos_cuota WHERE id = ?
        """, (self.tipo_cuota_id,))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return
        
        nombre_cuota = row['nombre']
        monto_cuota = row['monto']
        
        # Cargar estado del sobrecargo (con manejo de error si la columna no existe)
        try:
            sobrecargo_habilitado = row['sobrecargo_habilitado']
        except (KeyError, IndexError):
            sobrecargo_habilitado = 0
        
        self.var_sobrecargo.set(bool(sobrecargo_habilitado))
        
        self.label_titulo.config(text=f"Cuota: {nombre_cuota} (${monto_cuota:.2f})")
        
        # Obtener resumen
        resumen = obtener_resumen_cuota(self.tipo_cuota_id)
        
        texto_resumen = (
            f"Total Asignados: {resumen['total_asignados']}\n"
            f"Total Pagados: {resumen['total_pagados']} | Monto Recaudado: ${resumen['monto_recaudado']:.2f}\n"
            f"Total Pendientes: {resumen['total_pendientes']} | Monto Pendiente: ${resumen['monto_pendiente']:.2f}"
        )
        self.label_resumen.config(text=texto_resumen.strip())
        
        # Cargar campesinos
        cursor.execute("""
            SELECT * FROM cuotas_campesinos
            WHERE tipo_cuota_id = ?
            ORDER BY pagado ASC, numero_lote ASC
        """, (self.tipo_cuota_id,))
        
        cuotas_campesinos = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        self.tree.delete(*self.tree.get_children())
        
        for cuota in cuotas_campesinos:
            # Calcular monto a mostrar (con sobrecargo si aplica)
            monto_base = cuota['monto']
            tiene_sobrecargo = self.var_sobrecargo.get()
            
            sobrecargo_monto = 0.0
            if tiene_sobrecargo and not cuota['pagado']:
                sobrecargo_monto = calcular_sobrecargo_acumulado(cuota['fecha_asignacion'])
                
            monto_mostrar = monto_base + sobrecargo_monto
            
            # Formatear estado
            estado = "✅ PAGADO" if cuota['pagado'] else "⏳ PENDIENTE"
            fecha_pago = cuota['fecha_pago'] if cuota['fecha_pago'] else "-"
            
            # Obtener folio (si está pagado)
            folio_texto = str(cuota['recibo_folio']) if cuota['recibo_folio'] else "-"
            
            self.tree.insert('', tk.END,
                            values=(
                                folio_texto, # Usar recibo_folio o guion
                                cuota['numero_lote'],
                                cuota['nombre_campesino'],
                                cuota['barrio'],
                                f"${monto_mostrar:.2f}", # Use monto_mostrar
                                estado,
                                fecha_pago
                            ),
                            tags=(str(cuota['id']), str(cuota['pagado'])))
    
    def actualizar_sobrecargo(self):
        """Actualiza el estado del sobrecargo en la base de datos cuando cambia el checkbox"""
        try:
            from modules.cuotas import get_cuotas_connection
            conn = get_cuotas_connection()
            cursor = conn.cursor()
            
            nuevo_estado = 1 if self.var_sobrecargo.get() else 0
            
            cursor.execute("""
                UPDATE tipos_cuota
                SET sobrecargo_habilitado = ?
                WHERE id = ?
            """, (nuevo_estado, self.tipo_cuota_id))
            
            conn.commit()
            conn.close()
            
            print(f"✓ Sobrecargo {'activado' if nuevo_estado else 'desactivado'} para tipo de cuota {self.tipo_cuota_id}")
            
            # Recargar la lista para mostrar los montos actualizados
            self.cargar_detalle()
            
        except Exception as e:
            print(f"Error al actualizar sobrecargo: {e}")
    
    def on_doble_click_pagar(self, event):
        """Marca una cuota como pagada al hacer doble click"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = self.tree.item(selection[0])
        cuota_campesino_id = int(item['tags'][0])
        pagado = int(item['tags'][1])
        
        if pagado:
            messagebox.showinfo("Información", "Esta cuota ya fue pagada")
            return
        
        # Confirmar pago
        if messagebox.askyesno("Confirmar Pago", 
                               "¿Marcar esta cuota como PAGADA y generar recibo?"):
            try:
                from modules.cuotas import pagar_cuota, get_cuotas_connection, calcular_sobrecargo_acumulado
                
                # Obtener sobrecargo desde la base de datos
                conn = get_cuotas_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT tc.sobrecargo_habilitado, cc.fecha_asignacion
                    FROM cuotas_campesinos cc
                    JOIN tipos_cuota tc ON cc.tipo_cuota_id = tc.id
                    WHERE cc.id = ?
                """, (cuota_campesino_id,))
                row = cursor.fetchone()
                conn.close()
                
                sobrecargo = 0.0
                if row and row['sobrecargo_habilitado']:
                    sobrecargo = calcular_sobrecargo_acumulado(row['fecha_asignacion'])
                
                resultado = pagar_cuota(cuota_campesino_id, sobrecargo=sobrecargo)
                
                # Generar y mostrar recibo
                from modules.reports import generar_recibo_cuota_pdf_temporal, abrir_pdf
                
                pdf_path = generar_recibo_cuota_pdf_temporal(resultado['recibo_id'])
                abrir_pdf(pdf_path)
                
                if messagebox.askyesno("Imprimir Recibo",
                                       f"Recibo generado exitosamente\n"
                                       f"Folio: {resultado['folio']}\n"
                                       f"Monto: ${resultado['monto']:.2f}\n"
                                       f"¿Desea imprimir?"):
                    from modules.reports import imprimir_recibo_y_limpiar
                    imprimir_recibo_y_limpiar(pdf_path)
                else:
                    try:
                        os.remove(pdf_path)
                    except:
                        pass
                
                messagebox.showinfo("Éxito", "Cuota pagada correctamente")
                self.cargar_detalle()
                self.ventana_gestionar.cargar_tipos_cuota()
                
            except Exception as e:
                messagebox.showerror("Error", f"Error al pagar cuota:\n{str(e)}")
    
    def asignar_a_campesino(self):
        """Abre ventana para asignar esta cuota a un campesino"""
        VentanaAsignarCuota(self.ventana, self.tipo_cuota_id, self)
    
    def exportar_pdf(self):
        """Exporta reporte PDF de la recaudación de esta cuota"""
        try:
            from modules.reports import generar_reporte_cuota_pdf
            from modules.cuotas import get_cuotas_connection
            
            # Obtener nombre de la cuota
            conn = get_cuotas_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT nombre FROM tipos_cuota WHERE id = ?", (self.tipo_cuota_id,))
            row = cursor.fetchone()
            nombre_cuota = row['nombre'] if row else "Cuota"
            conn.close()
            
            pdf_path = generar_reporte_cuota_pdf(self.tipo_cuota_id)
            
            from modules.reports import abrir_pdf
            abrir_pdf(pdf_path)
            
            messagebox.showinfo("Éxito", 
                                f"Reporte de '{nombre_cuota}' generado correctamente\n"
                                f"Ruta: {pdf_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Error al generar reporte:\n{str(e)}")


class VentanaAsignarCuota:
    """Ventana para asignar una cuota a un campesino específico"""
    
    def __init__(self, parent, tipo_cuota_id, ventana_detalle):
        self.ventana = tk.Toplevel(parent)
        self.ventana.title("Asignar Cuota a Campesino")
        self.ventana.geometry("600x500")
        self.ventana.transient(parent)
        self.ventana.grab_set()
        self.tipo_cuota_id = tipo_cuota_id
        self.ventana_detalle = ventana_detalle
        
        self.crear_widgets()
        self.cargar_campesinos()
    
    def crear_widgets(self):
        """Crea los widgets"""
        # Canvas con scrollbar
        self.canvas, self.frame_principal = crear_ventana_scrollable(self.ventana, None)
        
        frame = ttk.Frame(self.frame_principal, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="ASIGNAR CUOTA A CAMPESINO", 
                  font=("Helvetica", 12, "bold")).pack(pady=10)
        
        # Búsqueda
        frame_busqueda = ttk.LabelFrame(frame, text="Buscar Campesino", padding=10)
        frame_busqueda.pack(fill=tk.X, pady=10)
        
        ttk.Label(frame_busqueda, text="Nombre o Lote:").pack(side=tk.LEFT, padx=5)
        self.entry_busqueda = ttk.Entry(frame_busqueda, width=30)
        self.entry_busqueda.pack(side=tk.LEFT, padx=5)
        self.entry_busqueda.bind('<Return>', lambda e: self.buscar())
        
        ttk.Button(frame_busqueda, text="🔍 Buscar", 
                   command=self.buscar).pack(side=tk.LEFT, padx=5)
        
        # Lista de campesinos
        frame_lista = ttk.Frame(frame)
        frame_lista.pack(fill=tk.BOTH, expand=True, pady=10)
        
        columnas = ('lote', 'nombre', 'barrio', 'superficie')
        self.tree = ttk.Treeview(frame_lista, columns=columnas, show='headings', height=15)
        
        self.tree.heading('lote', text='Lote')
        self.tree.heading('nombre', text='Nombre')
        self.tree.heading('barrio', text='Barrio')
        self.tree.heading('superficie', text='Superficie')
        
        self.tree.column('lote', width=70)
        self.tree.column('nombre', width=250)
        self.tree.column('barrio', width=100)
        self.tree.column('superficie', width=80)
        
        scrollbar = ttk.Scrollbar(frame_lista, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Botones
        frame_botones = ttk.Frame(frame)
        frame_botones.pack(fill=tk.X, pady=10)
        
        ttk.Button(frame_botones, text="✅ Asignar Seleccionado", 
                   command=self.asignar).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones, text="Cancelar", 
                   command=self.ventana.destroy).pack(side=tk.RIGHT, padx=5)
        
        # Cargar todos los campesinos al inicio
        self.cargar_campesinos()
    
    def cargar_campesinos(self):
        """Carga todos los campesinos"""
        from modules.models import obtener_todos_campesinos
        
        self.tree.delete(*self.tree.get_children())
        
        campesinos = obtener_todos_campesinos()
        
        for camp in campesinos:
            self.tree.insert('', tk.END,
                            values=(
                                camp['numero_lote'],
                                camp['nombre'],
                                camp['barrio'],
                                f"{camp['superficie']:.2f} ha"
                            ),
                            tags=(str(camp['id']),))
    
    def buscar(self):
        """Busca campesinos"""
        from modules.models import buscar_campesino
        
        termino = self.entry_busqueda.get().strip()
        
        if not termino:
            self.cargar_todos()
            return
        
        self.tree.delete(*self.tree.get_children())
        
        resultados = buscar_campesino(termino)
        
        if not resultados:
            messagebox.showinfo("Sin resultados", "No se encontraron campesinos")
            return
        
        for camp in resultados:
            self.tree.insert('', tk.END,
                            values=(
                                camp['numero_lote'],
                                camp['nombre'],
                                camp['barrio'],
                                f"{camp['superficie']:.2f} ha"
                            ),
                            tags=(str(camp['id']),))
    
    def asignar(self):
        """Asigna la cuota al campesino seleccionado"""
        selection = self.tree.selection()
        
        if not selection:
            messagebox.showwarning("Advertencia", "Debe seleccionar un campesino")
            return
        
        item = self.tree.item(selection[0])
        campesino_id = int(item['tags'][0])
        
        try:
            from modules.cuotas import asignar_cuota_a_campesino
            from modules.models import obtener_campesino_por_id
            
            campesino = obtener_campesino_por_id(campesino_id)
            
            # ✅ PASAR SUPERFICIE para calcular monto proporcional
            asignar_cuota_a_campesino(
                campesino_id,
                campesino['numero_lote'],
                campesino['nombre'],
                campesino['barrio'],
                self.tipo_cuota_id,
                campesino['superficie']  # ✅ AGREGAR ESTE PARÁMETRO
            )
            
            messagebox.showinfo("Éxito", 
                                f"Cuota asignada a {campesino['nombre']} correctamente\n"
                                f"Superficie: {campesino['superficie']} ha")
            
            self.ventana_detalle.cargar_detalle()
            self.ventana.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al asignar cuota:\n{str(e)}")


class VentanaReporteCuotas:
# """Ventana con reporte general de todas las cuotas.""
    
    def __init__(self, parent):
        self.ventana = tk.Toplevel(parent)
        self.ventana.title("📊 Reporte General de Cuotas")
        self.ventana.geometry("900x600")
        self.ventana.transient(parent)
        
        self.canvas, self.frame_principal = crear_ventana_scrollable(self.ventana, None)
        self.crear_widgets()
        self.cargar_estadisticas()
    
    def crear_widgets(self):
        "Crea los widgets."
        frame = ttk.Frame(self.frame_principal, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="REPORTE GENERAL DE CUOTAS", 
                  font=("Helvetica", 14, "bold")).pack(pady=10)
        
        # Estadísticas generales
        frame_stats = ttk.LabelFrame(frame, text="Estadísticas Generales", padding=15)
        frame_stats.pack(fill=tk.X, pady=10)
        
        self.label_stats = ttk.Label(frame_stats, text="", font=("Helvetica", 10))
        self.label_stats.pack()
        
        # Lista de cuotas
        frame_lista = ttk.LabelFrame(frame, text="Detalle por Cuota", padding=10)
        frame_lista.pack(fill=tk.BOTH, expand=True, pady=10)
        
        columnas = ('nombre', 'monto', 'asignados', 'pagados', 'pendientes', 
                    'recaudado', 'pendiente_cobro')
        self.tree = ttk.Treeview(frame_lista, columns=columnas, show='headings', height=15)
        
        self.tree.heading('nombre', text='Cuota')
        self.tree.heading('monto', text='Monto Unit.')
        self.tree.heading('asignados', text='Asignados')
        self.tree.heading('pagados', text='Pagados')
        self.tree.heading('pendientes', text='Pendientes')
        self.tree.heading('recaudado', text='Recaudado')
        self.tree.heading('pendiente_cobro', text='Por Cobrar')
        
        scrollbar = ttk.Scrollbar(frame_lista, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Botones
        frame_botones = ttk.Frame(frame)
        frame_botones.pack(fill=tk.X, pady=10)
        
        ttk.Button(frame_botones, text="📄 Exportar PDF Completo", 
                   command=self.exportar_pdf_completo).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones, text="Cerrar", 
                   command=self.ventana.destroy).pack(side=tk.RIGHT, padx=5)
    
    def cargar_estadisticas(self):
        from modules.cuotas import obtener_estadisticas_generales_cuotas, obtener_todas_cuotas_con_estado
        
        stats = obtener_estadisticas_generales_cuotas()
        
        texto = (
            f"Total de Tipos de Cuotas: {stats['total_tipos_cuotas']}\n"
            f"Total de Cuotas Asignadas: {stats['total_cuotas_asignadas']}\n"
            f"Cuotas Pagadas: {stats['total_pagadas']} | Monto Recaudado: ${stats['monto_recaudado']:.2f}\n"
            f"Cuotas Pendientes: {stats['total_pendientes']} | Monto Pendiente: ${stats['monto_pendiente']:.2f}\n"
            f"Monto Total: ${stats['monto_total']:.2f}"
        )
        
        self.label_stats.config(text=texto.strip())
        
        # Cargar cuotas
        cuotas = obtener_todas_cuotas_con_estado()
        
        self.tree.delete(*self.tree.get_children())
        
        for cuota in cuotas:
            self.tree.insert('', tk.END,
                            values=(
                                cuota['nombre'],
                                f"${cuota['monto']:.2f}",
                                cuota['total_asignados'] or 0,
                                cuota['total_pagados'] or 0,
                                cuota['total_pendientes'] or 0,
                                f"${cuota['monto_recaudado'] or 0:.2f}",
                                f"${cuota['monto_pendiente'] or 0:.2f}"
                            ))
    
    def exportar_pdf_completo(self):
        try:
            from modules.reports import generar_reporte_todas_cuotas_pdf
            
            pdf_path = generar_reporte_todas_cuotas_pdf()
            
            from modules.reports import abrir_pdf
            abrir_pdf(pdf_path)
            
            messagebox.showinfo("Éxito", 
                                f"Reporte general generado correctamente\n"
                                f"Ruta: {pdf_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Error al generar reporte:\n{str(e)}")