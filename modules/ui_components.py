#models/ui_components.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext, simpledialog
from datetime import datetime
from typing import Optional, Dict, List
import os
import time

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
    obtener_estadisticas_generales, obtener_estadisticas_por_cultivo
)


from modules.logic import (
    calcular_costo, validar_campesino, nueva_siembra, vender_riego,
    calcular_total_dia, eliminar_recibo_dia, cerrar_dia,
    reiniciar_folios_y_ciclo, crear_backup, cambiar_cultivo_siembra,
    actualizar_folio_actual, incrementar_folio
)

from modules.reports import (
    generar_recibo_pdf_temporal, imprimir_recibo_y_limpiar,
    generar_reporte_diario, abrir_pdf, exportar_a_excel, obtener_impresoras_disponibles
)

# Lista de cultivos comunes
CULTIVOS = ['MAÍZ', 'FRIJOL', 'TRIGO', 'SORGO', 'ALFALFA', 'CHILE', 'TOMATE', 'CEBOLLA', 'AJO', 'OTROS']

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
    import platform
    
    # Crear frame para canvas y scrollbar
    frame_canvas = ttk.Frame(parent_ventana)
    frame_canvas.pack(fill=tk.BOTH, expand=True)
    
    # Crear canvas
    canvas = tk.Canvas(frame_canvas, bg='white', highlightthickness=0)
    scrollbar = ttk.Scrollbar(frame_canvas, orient=tk.VERTICAL, command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)
    
    # Actualizar scroll region cuando cambie el tamaño
    def _configure_scroll_region(event=None):
        canvas.configure(scrollregion=canvas.bbox("all"))
    
    scrollable_frame.bind("<Configure>", _configure_scroll_region)
    
    # Crear ventana en canvas
    canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    # Ajustar ancho del scrollable_frame al canvas
    def _configure_canvas_width(event):
        canvas.itemconfig(canvas_window, width=event.width)
    
    canvas.bind('<Configure>', _configure_canvas_width)
    
    # ===== SOPORTE RUEDA DE RATÓN Y TRACKPAD =====
    def _on_scroll_windows(event):
        """Maneja scroll con rueda de ratón en Windows"""
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def _on_scroll_linux(event):
        """Maneja scroll con rueda de ratón en Linux"""
        if event.num == 5:
            canvas.yview_scroll(1, "units")
        elif event.num == 4:
            canvas.yview_scroll(-1, "units")
    
    def _on_scroll_mac(event):
        """Maneja scroll con trackpad/rueda en Mac"""
        canvas.yview_scroll(int(-1*event.delta), "units")
    
    sistema = platform.system()
    
    # Bind específico para cada SO - SOLO al canvas
    if sistema == "Windows":
        canvas.bind_all("<MouseWheel>", _on_scroll_windows)
    elif sistema == "Darwin":  # macOS
        canvas.bind_all("<MouseWheel>", _on_scroll_mac)
    else:  # Linux
        canvas.bind_all("<Button-4>", _on_scroll_linux)
        canvas.bind_all("<Button-5>", _on_scroll_linux)
    
    # Destruir bindings cuando se cierre la ventana
    def _cleanup():
        if sistema == "Windows":
            canvas.unbind_all("<MouseWheel>")
        elif sistema == "Darwin":
            canvas.unbind_all("<MouseWheel>")
        else:
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")
    
    parent_ventana.bind("<Destroy>", lambda e: _cleanup() if e.widget == parent_ventana else None)
    
    # Empaquetar
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
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
        alto = 700
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
        
        # Frame de búsqueda
        frame_busqueda = ttk.LabelFrame(scrollable_frame, text="Buscar Campesino", padding="10")
        frame_busqueda.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(frame_busqueda, text="🔍").pack(side=tk.LEFT, padx=5)
        self.entry_busqueda = ttk.Entry(frame_busqueda, width=40, font=('Helvetica', 11))
        self.entry_busqueda.pack(side=tk.LEFT, padx=5)
        self.entry_busqueda.bind('<Return>', self.on_buscar)
        
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
        ttk.Button(frame_botones, text="📋 Detalle",
                   command=self.abrir_detalle_dia,
                   width=12).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Button(frame_botones, text="📜 Historial",
                   command=self.abrir_historial_campesino,
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
        self.cargar_todos_campesinos()
    
    def cargar_todos_campesinos(self):
        """Carga todos los campesinos en la tabla"""
        self.tree.delete(*self.tree.get_children())
        campesinos = obtener_todos_campesinos()
        
        for c in campesinos:
            siembra = obtener_siembra_activa(c['id'])
            cultivo = siembra['cultivo'] if siembra else '-'
            riegos = siembra['numero_riegos'] if siembra else 0
            
            self.tree.insert('', tk.END, values=(
                c['numero_lote'],
                c['nombre'],
                c['localidad'],
                c['barrio'],
                f"{c['superficie']:.2f}",
                cultivo,
                riegos
            ), tags=(str(c['id']),))
    
    def abrir_estadisticas(self):
        """Abre la ventana de estadísticas"""
        VentanaEstadisticas(self.root)

    def on_buscar(self, event=None):
        """Busca campesinos"""
        termino = self.entry_busqueda.get().strip()
        if not termino:
            self.cargar_todos_campesinos()
            return
        
        self.tree.delete(*self.tree.get_children())
        resultados = buscar_campesino(termino)
        
        for c in resultados:
            siembra = obtener_siembra_activa(c['id'])
            cultivo = siembra['cultivo'] if siembra else '-'
            riegos = siembra['numero_riegos'] if siembra else 0
            
            self.tree.insert('', tk.END, values=(
                c['numero_lote'],
                c['nombre'],
                c['localidad'],
                c['barrio'],
                f"{c['superficie']:.2f}",
                cultivo,
                riegos
            ), tags=(str(c['id']),))
    
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
        """Abre el formulario para crear un nuevo campesino"""
        FormularioCampesino(self.root, None, self)
    
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
    
    def generar_reporte_dia(self):
        """Genera el reporte del día"""
        try:
            recibos = obtener_recibos_dia(self.fecha_actual)
            if not recibos:
                messagebox.showinfo("Información", "No hay recibos para el día de hoy")
                return
            
            pdf_path = generar_reporte_diario(self.fecha_actual, recibos)
            abrir_pdf(pdf_path)
            messagebox.showinfo("Éxito", f"Reporte generado exitosamente\n{len(recibos)} recibos")
        except Exception as e:
            messagebox.showerror("Error", f"Error al generar reporte:\n{str(e)}")
    
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
        
        # Frame de costo
        frame_costo = ttk.LabelFrame(self.frame_principal, text="💰 Monto a Cobrar", padding="15")
        frame_costo.pack(fill=tk.X, padx=10, pady=10)
        
        costo = calcular_costo(self.campesino['superficie'])
        ttk.Label(frame_costo,
                  text=f"${costo:,.2f}",
                  font=('Helvetica', 20, 'bold'),
                  foreground='green').pack()
        
        tarifa = obtener_configuracion('tarifa_hectarea')
        ttk.Label(frame_costo,
                  text=f"({self.campesino['superficie']} ha × ${tarifa}/ha)",
                  font=('Helvetica', 9),
                  foreground='gray').pack()
        
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
            
            # Generar venta
            if accion == 'nueva':
                resultado = nueva_siembra(self.campesino['id'], cultivo)
                tipo_texto = "Nueva siembra"
            else:
                resultado = vender_riego(self.campesino['id'])
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
    """Ventana para reiniciar el ciclo de folio (sin borrar usuarios)"""
    
    def __init__(self, parent):
        self.ventana = tk.Toplevel(parent)
        self.ventana.title("🔄 Reiniciar Ciclo")
        self.ventana.geometry("400x320")
        self.ventana.resizable(False, False)
        self.ventana.transient(parent)
        self.ventana.grab_set()
        
        # Frame principal
        frame_principal = ttk.Frame(self.ventana, padding="20")
        frame_principal.pack(fill=tk.BOTH, expand=True)
        
        # Advertencia
        ttk.Label(frame_principal, text="⚠️ REINICIAR CICLO",
                  font=('Helvetica', 14, 'bold'), foreground='red').pack(pady=10)
        
        # Mensaje informativo
        mensaje = """Esta acción:

✓ Reiniciará el número de folio a 1
✓ Actualizará el ciclo agrícola
⚠️ NO borrará datos de campesinos
⚠️ NO borrará datos de siembras

¿Desea continuar?"""
        
        ttk.Label(frame_principal, text=mensaje, justify=tk.LEFT).pack(pady=15)
        
        # Nuevo ciclo
        ttk.Label(frame_principal, text="Nuevo Ciclo:").pack(anchor="w", pady=5)
        self.entry_ciclo = ttk.Entry(frame_principal, width=40)
        self.entry_ciclo.pack(anchor="w", padx=10)
        
        ciclo_sugerido = f"CICLO {datetime.now().strftime('%B %Y').upper()}"
        self.entry_ciclo.insert(0, ciclo_sugerido)
        
        # Frame de botones
        frame_botones = ttk.Frame(frame_principal)
        frame_botones.pack(fill=tk.X, pady=20)
        
        ttk.Button(frame_botones, text="✅ Reiniciar", command=self.reiniciar).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones, text="❌ Cancelar", command=self.ventana.destroy).pack(side=tk.LEFT, padx=5)
    
    def reiniciar(self):
        """Ejecuta el reinicio del ciclo"""
        nuevo_ciclo = self.entry_ciclo.get().strip()
        
        if not nuevo_ciclo:
            messagebox.showerror("Error", "Debe ingresar el nombre del nuevo ciclo")
            return
        
        if messagebox.askyesno("Confirmar", f"¿Reiniciar ciclo a '{nuevo_ciclo}'?\n\nFolios se resetearán a 1"):
            try:
                if reiniciar_folios_y_ciclo(nuevo_ciclo):
                    messagebox.showinfo("Éxito", f"Ciclo reiniciado a '{nuevo_ciclo}'.\nFolios ahora en 1.\nDatos de usuarios preservados.")
                    self.ventana.destroy()
                else:
                    messagebox.showerror("Error", "Error al reiniciar el ciclo")
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
                   command=self.exportar_excel).pack(side=tk.LEFT, padx=5)
        
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
    
    def exportar_excel(self):
        """Exporta los recibos a Excel"""
        try:
            recibos = obtener_recibos_dia(self.fecha_actual)
            if not recibos:
                messagebox.showinfo("Información", "No hay recibos para exportar")
                return
            
            fecha_archivo = datetime.now().strftime('%Y%m%d')
            filename = f"recibos_{fecha_archivo}.xlsx"
            filepath = exportar_a_excel(recibos, filename)
            
            messagebox.showinfo("Éxito", f"Archivo exportado:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Error al exportar:\n{str(e)}")


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
        
        ttk.Button(frame_botones,
                   text="💾 Guardar",
                   command=self.guardar,
                   width=15).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(frame_botones,
                   text="❌ Cancelar",
                   command=self.ventana.destroy,
                   width=15).pack(side=tk.LEFT, padx=5)
    
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
        """Carga el historial de siembras y recibos"""
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
        
        mensaje = f"""📊 ESTADÍSTICAS DE {cultivo.upper()}

👥 Campesinos: {stats_cultivo['total_campesinos']}
🌾 Hectáreas: {stats_cultivo['total_hectareas']} ha
💧 Riegos promedio: {stats_cultivo['riegos_promedio']}
📊 Total de riegos: {stats_cultivo['total_riegos']}"""
        
        messagebox.showinfo(f"Cultivo: {cultivo}", mensaje)
    
    def actualizar_datos(self):
        """Actualiza los datos y refresca la ventana"""
        self.stats = obtener_estadisticas_generales()
        self.ventana.destroy()
        VentanaEstadisticas(self.ventana.master)
