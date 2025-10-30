# modules/ui_components.py - Interfaz Gráfica Completa del Sistema
# ARCHIVO COMPLETO - Todas las ventanas y componentes
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
from datetime import datetime
from typing import Optional, Dict, List
import os
from modules.models import (
    buscar_campesino, obtener_campesino_por_id, crear_campesino,
    actualizar_campesino, eliminar_campesino, obtener_todos_campesinos,
    obtener_siembra_activa, obtener_historial_siembras,
    obtener_recibos_dia, obtener_configuracion, actualizar_configuracion,
    obtener_toda_configuracion, obtener_auditoria, obtener_recibos_campesino
)
from modules.logic import (
    calcular_costo, validar_campesino, nueva_siembra, vender_riego,
    calcular_total_dia, eliminar_recibo_dia, cerrar_dia,
    reiniciar_folios_y_ciclo, crear_backup, cambiar_cultivo_siembra
)
from modules.reports import (
    generar_recibo_pdf, generar_reporte_diario, imprimir_recibo,
    abrir_pdf, exportar_a_excel, obtener_impresoras_disponibles
)

# Lista de cultivos comunes
CULTIVOS = ['MAÍZ', 'FRIJOL', 'TRIGO', 'SORGO', 'ALFALFA', 'CHILE', 'TOMATE', 'CEBOLLA', 'AJO', 'OTROS']

# ==================== FUNCIONES AUXILIARES PARA SCROLLING ====================
def configurar_scrolling(widget_contenedor, widget_principal):
    """Configura scrolling para un widget principal dentro de un contenedor."""
    canvas = tk.Canvas(widget_contenedor)
    scrollbar_v = ttk.Scrollbar(widget_contenedor, orient="vertical", command=canvas.yview)
    scrollbar_h = ttk.Scrollbar(widget_contenedor, orient="horizontal", command=canvas.xview)
    scrollable_frame = ttk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")
        )
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar_v.set, xscrollcommand=scrollbar_h.set)

    # Empaquetar canvas y scrollbars
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar_v.pack(side="right", fill="y")
    scrollbar_h.pack(side="bottom", fill="x")

    # Vincular eventos del mouse para scrolling
    def _bind_mousewheel(event):
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        canvas.bind_all("<Button-4>", _on_mousewheel_linux)
        canvas.bind_all("<Button-5>", _on_mousewheel_linux)

    def _unbind_mousewheel(event):
        canvas.unbind_all("<MouseWheel>")
        canvas.unbind_all("<Button-4>")
        canvas.unbind_all("<Button-5>")

    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_mousewheel_linux(event):
        if event.num == 4:
            canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            canvas.yview_scroll(1, "units")

    scrollable_frame.bind("<Enter>", _bind_mousewheel)
    scrollable_frame.bind("<Leave>", _unbind_mousewheel)

    # Devolver el frame desplazable para añadir widgets
    return scrollable_frame

# ==================== VENTANA PRINCIPAL ====================
class VentanaPrincipal:
    """Ventana principal del sistema"""
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Control de Riegos - XICUCO")
        # Configurar tamaño
        ancho = 1200
        alto = 700
        x = (self.root.winfo_screenwidth() // 2) - (ancho // 2)
        y = (self.root.winfo_screenheight() // 2) - (alto // 2)
        self.root.geometry(f'{ancho}x{alto}+{x}+{y}')

        # Crear frame principal para scrolling
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Configurar scrolling para el frame principal
        self.scrollable_main_frame = configurar_scrolling(self.main_frame, self.root)

        # Variables
        self.total_dia = tk.DoubleVar(value=0.0)
        self.fecha_actual = datetime.now().strftime('%Y-%m-%d')
        self.campesino_seleccionado = None

        # Crear interfaz dentro del frame desplazable
        self.crear_widgets()
        # Actualizar total del día
        self.actualizar_total_dia()

    def crear_widgets(self):
        """Crea todos los widgets de la ventana principal dentro del frame desplazable"""
        # Frame superior con título y total
        frame_superior = ttk.Frame(self.scrollable_main_frame, padding="10")
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
        frame_busqueda = ttk.LabelFrame(self.scrollable_main_frame, text="Buscar Campesino", padding="10")
        frame_busqueda.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(frame_busqueda, text="🔍").pack(side=tk.LEFT, padx=5)
        self.entry_busqueda = ttk.Entry(frame_busqueda, width=40, font=('Helvetica', 11))
        self.entry_busqueda.pack(side=tk.LEFT, padx=5)
        self.entry_busqueda.bind('<KeyRelease>', self.on_buscar)
        ttk.Button(frame_busqueda, text="Buscar",
                  command=self.on_buscar).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_busqueda, text="Limpiar",
                  command=self.limpiar_busqueda).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_busqueda, text="➕ Nuevo Campesino",
                  command=self.abrir_form_nuevo_campesino).pack(side=tk.LEFT, padx=20)
        # Frame de resultados
        frame_resultados = ttk.Frame(self.scrollable_main_frame, padding="10")
        frame_resultados.pack(fill=tk.BOTH, expand=True, padx=10)
        # Crear Treeview
        columnas = ('lote', 'nombre', 'localidad', 'barrio', 'superficie', 'cultivo', 'riegos')
        self.tree = ttk.Treeview(frame_resultados, columns=columnas, show='headings', height=15)
        # Encabezados
        self.tree.heading('lote', text='Lote')
        self.tree.heading('nombre', text='Nombre')
        self.tree.heading('localidad', text='Localidad')
        self.tree.heading('barrio', text='Barrio')
        self.tree.heading('superficie', text='Sup. (ha)')
        self.tree.heading('cultivo', text='Cultivo Actual')
        self.tree.heading('riegos', text='Riegos')
        # Anchos de columna
        self.tree.column('lote', width=80)
        self.tree.column('nombre', width=250)
        self.tree.column('localidad', width=150)
        self.tree.column('barrio', width=100)
        self.tree.column('superficie', width=80)
        self.tree.column('cultivo', width=100)
        self.tree.column('riegos', width=80)
        # Scrollbar
        scrollbar = ttk.Scrollbar(frame_resultados, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        # Bind selección
        self.tree.bind('<<TreeviewSelect>>', self.on_seleccionar_campesino)
        self.tree.bind('<Double-1>', self.on_doble_click)
        # Frame de botones principales
        frame_botones = ttk.Frame(self.scrollable_main_frame, padding="10")
        frame_botones.pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(frame_botones, text="🌱 Nueva Siembra",
                  command=lambda: self.abrir_ventana_venta('nueva'),
                  width=18).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones, text="💧 Vender Riego",
                  command=lambda: self.abrir_ventana_venta('riego'),
                  width=18).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones, text="📋 Detalle del Día",
                  command=self.abrir_detalle_dia,
                  width=18).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones, text="📜 Historial",
                  command=self.abrir_historial_campesino,
                  width=18).pack(side=tk.LEFT, padx=5)
        # Frame de botones inferiores
        frame_botones_inf = ttk.Frame(self.scrollable_main_frame, padding="10")
        frame_botones_inf.pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(frame_botones_inf, text="📊 Reporte del Día",
                  command=self.generar_reporte_dia).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones_inf, text="🔒 Cerrar Día",
                  command=self.cerrar_dia_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones_inf, text="🔄 Reiniciar Ciclo",
                  command=self.reiniciar_ciclo_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones_inf, text="⚙️ Configuración",
                  command=self.abrir_configuracion).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones_inf, text="💾 Backup",
                  command=self.crear_backup_manual).pack(side=tk.LEFT, padx=5)
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
                # Preguntar si desea reiniciar el contador
                if messagebox.askyesno("Reiniciar Contador",
                                      "¿Desea reiniciar el contador de venta a $0.00?"):
                    self.total_dia.set(0.0)
            except Exception as e:
                messagebox.showerror("Error", f"Error al cerrar día:\n{str(e)}")

    def reiniciar_ciclo_dialog(self):
        """Diálogo para reiniciar ciclo"""
        # Primera confirmación
        if not messagebox.askyesno("Reiniciar Ciclo",
                                   "ADVERTENCIA: Esta acción cerrará todas las siembras activas y reiniciará los folios.\n¿Desea continuar?"):
            return
        # Segunda confirmación con entrada de nuevo ciclo
        dialogo = tk.Toplevel(self.root)
        dialogo.title("Nuevo Ciclo Agrícola")
        dialogo.geometry("400x200")
        dialogo.transient(self.root)
        dialogo.grab_set()
        ttk.Label(dialogo, text="Ingrese el nombre del nuevo ciclo agrícola:",
                 font=('Helvetica', 11)).pack(pady=20)
        ttk.Label(dialogo, text="Ejemplo: NOVIEMBRE 2025, PRIMAVERA 2026",
                 font=('Helvetica', 9), foreground='gray').pack()
        entry_ciclo = ttk.Entry(dialogo, width=30, font=('Helvetica', 11))
        entry_ciclo.pack(pady=10)
        entry_ciclo.focus()

        def confirmar():
            nuevo_ciclo = entry_ciclo.get().strip().upper()
            if not nuevo_ciclo:
                messagebox.showwarning("Advertencia", "Debe ingresar un nombre para el ciclo")
                return
            try:
                exito = reiniciar_folios_y_ciclo(nuevo_ciclo)
                if exito:
                    messagebox.showinfo("Éxito",
                                      f"Ciclo reiniciado exitosamente\nNuevo ciclo: {nuevo_ciclo}\nFolios reiniciados a 1")
                    dialogo.destroy()
                    self.actualizar_total_dia()
                    self.cargar_todos_campesinos()
                else:
                    messagebox.showerror("Error", "No se pudo reiniciar el ciclo")
            except Exception as e:
                messagebox.showerror("Error", f"Error al reiniciar ciclo:\n{str(e)}")

        ttk.Button(dialogo, text="Confirmar Reinicio",
                  command=confirmar).pack(pady=10)
        ttk.Button(dialogo, text="Cancelar",
                  command=dialogo.destroy).pack()

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
    """Ventana para vender riegos o iniciar nueva siembra"""
    def __init__(self, parent, campesino, tipo, ventana_principal):
        self.ventana = tk.Toplevel(parent)
        self.ventana.title("Venta de Riego")
        self.ventana.geometry("550x500")
        self.ventana.transient(parent)
        self.ventana.grab_set()
        self.campesino = campesino
        self.tipo = tipo
        self.ventana_principal = ventana_principal

        # Crear frame principal para scrolling
        self.main_frame = ttk.Frame(self.ventana)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Configurar scrolling para el frame principal
        self.scrollable_frame = configurar_scrolling(self.main_frame, self.ventana)

        self.crear_widgets()

    def crear_widgets(self):
        """Crea los widgets de la ventana dentro del frame desplazable"""
        # Frame de información
        frame_info = ttk.LabelFrame(self.scrollable_frame, text="📋 Datos del Campesino", padding="15")
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
        # Frame de opciones
        frame_opciones = ttk.LabelFrame(self.scrollable_frame, text="¿Qué desea hacer?", padding="15")
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
        frame_costo = ttk.LabelFrame(self.scrollable_frame, text="💰 Monto a Cobrar", padding="15")
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
        frame_botones = ttk.Frame(self.scrollable_frame)
        frame_botones.pack(fill=tk.X, padx=10, pady=20)
        ttk.Button(frame_botones,
                  text="✅ Generar Recibo e Imprimir",
                  command=self.generar_recibo,
                  width=30).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones,
                  text="❌ Cancelar",
                  command=self.ventana.destroy,
                  width=15).pack(side=tk.LEFT, padx=5)

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
        """Genera el recibo y lo imprime"""
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
            # Generar PDF
            pdf_path = generar_recibo_pdf(resultado['recibo_id'])
            # Abrir vista previa
            abrir_pdf(pdf_path)
            # Preguntar si desea imprimir
            if messagebox.askyesno("Imprimir Recibo",
                                  f"Recibo generado exitosamente\nFolio: {resultado['folio']}\nCosto: ${resultado['costo']:.2f}\n¿Desea imprimir?"):
                imprimir_recibo(pdf_path)
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

# ==================== VENTANA DETALLE DEL DÍA ====================
class VentanaDetalleDia:
    """Ventana para ver el detalle de ventas del día"""
    def __init__(self, parent, ventana_principal):
        self.ventana = tk.Toplevel(parent)
        self.ventana.title("Detalle del Día")
        self.ventana.geometry("1100x600")
        self.ventana.transient(parent)
        self.ventana_principal = ventana_principal
        self.fecha_actual = datetime.now().strftime('%Y-%m-%d')

        # Crear frame principal para scrolling
        self.main_frame = ttk.Frame(self.ventana)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Configurar scrolling para el frame principal
        self.scrollable_frame = configurar_scrolling(self.main_frame, self.ventana)

        self.crear_widgets()
        self.cargar_recibos()

    def crear_widgets(self):
        """Crea los widgets dentro del frame desplazable"""
        # Frame superior
        frame_superior = ttk.Frame(self.scrollable_frame, padding="10")
        frame_superior.pack(fill=tk.X)
        fecha_texto = datetime.now().strftime('%d/%m/%Y')
        ttk.Label(frame_superior,
                 text=f"📊 Detalle de Ventas - {fecha_texto}",
                 font=('Helvetica', 14, 'bold')).pack()
        # Frame de tabla
        frame_tabla = ttk.Frame(self.scrollable_frame, padding="10")
        frame_tabla.pack(fill=tk.BOTH, expand=True)
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
        frame_acciones = ttk.Frame(self.scrollable_frame, padding="10")
        frame_acciones.pack(fill=tk.X)
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
        frame_totales = ttk.LabelFrame(self.scrollable_frame, text="Totales del Día", padding="10")
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
        """Elimina el recibo seleccionado"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Advertencia", "Debe seleccionar un recibo")
            return
        item = self.tree.item(selection[0])
        recibo_id = int(item['tags'][0])
        folio = item['values'][0]
        monto = item['values'][6]
        # Primera confirmación
        if not messagebox.askyesno("Confirmar Eliminación",
                                   f"¿Eliminar recibo #{folio}?\nSe restará {monto} del total del día"):
            return
        # Segunda confirmación
        if not messagebox.askyesno("Segunda Confirmación",
                                   "Esta acción se registrará en auditoría.\n¿Está seguro de continuar?"):
            return
        try:
            monto_restado = eliminar_recibo_dia(recibo_id, "Eliminado desde detalle del día")
            messagebox.showinfo("Éxito",
                              f"Recibo eliminado exitosamente\nMonto restado: ${monto_restado:.2f}")
            # Actualizar
            self.cargar_recibos()
            self.ventana_principal.actualizar_total_dia()
        except ValueError as e:
            messagebox.showerror("Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Error al eliminar recibo:\n{str(e)}")

    def reimprimir_recibo(self):
        """Reimprime el recibo seleccionado"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Advertencia", "Debe seleccionar un recibo")
            return
        item = self.tree.item(selection[0])
        recibo_id = int(item['tags'][0])
        try:
            # Generar PDF con marca de reimpresión
            pdf_path = generar_recibo_pdf(recibo_id, es_reimpresion=True)
            # Abrir vista previa
            abrir_pdf(pdf_path)
            # Preguntar si desea imprimir
            if messagebox.askyesno("Imprimir", "¿Desea imprimir la reimpresión?"):
                imprimir_recibo(pdf_path)
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
    """Formulario para crear o editar campesino"""
    def __init__(self, parent, campesino_id, ventana_principal):
        self.ventana = tk.Toplevel(parent)
        self.ventana.title("Nuevo Campesino" if not campesino_id else "Editar Campesino")
        self.ventana.geometry("500x450")
        self.ventana.transient(parent)
        self.ventana.grab_set()
        self.campesino_id = campesino_id
        self.ventana_principal = ventana_principal
        self.campesino = obtener_campesino_por_id(campesino_id) if campesino_id else None

        # Crear frame principal para scrolling
        self.main_frame = ttk.Frame(self.ventana)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Configurar scrolling para el frame principal
        self.scrollable_frame = configurar_scrolling(self.main_frame, self.ventana)

        self.crear_widgets()

    def crear_widgets(self):
        """Crea los widgets del formulario dentro del frame desplazable"""
        frame_form = ttk.Frame(self.scrollable_frame, padding="20")
        frame_form.pack(fill=tk.BOTH, expand=True)
        # Número de lote
        ttk.Label(frame_form, text="Número de Lote:", font=('Helvetica', 10)).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.entry_lote = ttk.Entry(frame_form, width=30)
        self.entry_lote.grid(row=0, column=1, pady=5, padx=10)
        if self.campesino:
            self.entry_lote.insert(0, self.campesino['numero_lote'])
            self.entry_lote.config(state='disabled')  # No editable
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
        self.combo_barrio = ttk.Combobox(frame_form, values=barrios, width=28)
        self.combo_barrio.grid(row=3, column=1, pady=5, padx=10)
        if self.campesino:
            self.combo_barrio.set(self.campesino['barrio'])
        # Superficie
        ttk.Label(frame_form, text="Superficie (ha):", font=('Helvetica', 10)).grid(row=4, column=0, sticky=tk.W, pady=5)
        self.entry_superficie = ttk.Entry(frame_form, width=30)
        self.entry_superficie.grid(row=4, column=1, pady=5, padx=10)
        if self.campesino:
            self.entry_superficie.insert(0, str(self.campesino['superficie']))
            # Verificar si tiene siembra activa
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
        # Recopilar datos
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
                # Actualizar
                actualizar_campesino(self.campesino_id, datos)
                messagebox.showinfo("Éxito", "Campesino actualizado exitosamente")
            else:
                # Crear nuevo
                crear_campesino(datos)
                messagebox.showinfo("Éxito",
                                  f"Campesino registrado exitosamente\nLote: {datos['numero_lote']}")
            # Actualizar ventana principal
            self.ventana_principal.cargar_todos_campesinos()
            # Cerrar ventana
            self.ventana.destroy()
        except ValueError as e:
            messagebox.showerror("Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar:\n{str(e)}")

# ==================== VENTANA HISTORIAL ====================
class VentanaHistorial:
    """Ventana para ver el historial de un campesino"""
    def __init__(self, parent, campesino):
        self.ventana = tk.Toplevel(parent)
        self.ventana.title(f"Historial - {campesino['nombre']}")
        self.ventana.geometry("900x600")
        self.ventana.transient(parent)
        self.campesino = campesino

        # Crear frame principal para scrolling
        self.main_frame = ttk.Frame(self.ventana)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Configurar scrolling para el frame principal
        self.scrollable_frame = configurar_scrolling(self.main_frame, self.ventana)

        self.crear_widgets()
        self.cargar_historial()

    def crear_widgets(self):
        """Crea los widgets dentro del frame desplazable"""
        # Frame superior con info del campesino
        frame_info = ttk.LabelFrame(self.scrollable_frame, text="Información del Campesino", padding="10")
        frame_info.pack(fill=tk.X, padx=10, pady=10)
        info_text = f"""
Nombre: {self.campesino['nombre']}
Lote: {self.campesino['numero_lote']}
Localidad: {self.campesino['localidad']} - {self.campesino['barrio']}
Superficie: {self.campesino['superficie']} ha
"""
        ttk.Label(frame_info, text=info_text, font=('Helvetica', 10)).pack(anchor=tk.W)
        # Frame de siembras históricas
        frame_siembras = ttk.LabelFrame(self.scrollable_frame, text="Historial de Siembras", padding="10")
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
        frame_recibos = ttk.LabelFrame(self.scrollable_frame, text="Recibos Emitidos", padding="10")
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
        frame_botones = ttk.Frame(self.scrollable_frame)
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
        """Reimprime el recibo seleccionado"""
        selection = self.tree_recibos.selection()
        if not selection:
            messagebox.showwarning("Advertencia", "Debe seleccionar un recibo")
            return
        item = self.tree_recibos.item(selection[0])
        recibo_id = int(item['tags'][0])
        try:
            pdf_path = generar_recibo_pdf(recibo_id, es_reimpresion=True)
            abrir_pdf(pdf_path)
            if messagebox.askyesno("Imprimir", "¿Desea imprimir?"):
                imprimir_recibo(pdf_path)
        except Exception as e:
            messagebox.showerror("Error", f"Error al reimprimir:\n{str(e)}")

# ==================== DIÁLOGO DE CONFIGURACIÓN ====================
class DialogoConfiguracion:
    """Diálogo para configurar el sistema"""
    def __init__(self, parent):
        self.ventana = tk.Toplevel(parent)
        self.ventana.title("⚙️ Configuración del Sistema")
        self.ventana.geometry("600x500")
        self.ventana.transient(parent)
        self.ventana.grab_set()

        # Crear frame principal para scrolling
        self.main_frame = ttk.Frame(self.ventana)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Configurar scrolling para el frame principal
        self.scrollable_frame = configurar_scrolling(self.main_frame, self.ventana)

        self.crear_widgets()
        self.cargar_configuracion()

    def crear_widgets(self):
        """Crea los widgets dentro del frame desplazable"""
        notebook = ttk.Notebook(self.scrollable_frame)
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
        frame_botones = ttk.Frame(self.scrollable_frame)
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
