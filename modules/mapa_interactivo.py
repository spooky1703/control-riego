"""
Mapa Interactivo de Parcelas - Seccion 4
Visualiza las parcelas coloreadas por cultivo, barrio o estado de siembra.
Incluye exportacion a PDF con graficas de distribucion.

Requiere: database/mapa_geometria.json (generado por extraer_mapa.py)
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.path import Path
from collections import Counter
from datetime import datetime
import json
import os
import io
import sqlite3

# ═══════════════════════════════════════════════════════════
# CONFIGURACION
# ═══════════════════════════════════════════════════════════
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_CACHE = os.path.join(BASE_DIR, 'database', 'mapa_geometria.json')
DB_PATH = os.path.join(BASE_DIR, 'database', 'riego.db')
LOGO_PATH = os.path.join(BASE_DIR, 'assets', 'zapata.png')


def _normalizar_cultivo(nombre):
    """Normaliza el nombre de un cultivo para comparaciones y agrupaciones."""
    if not nombre:
        return None
    n = nombre.strip().upper()
    n = n.replace('Í', 'I').replace('Á', 'A').replace('É', 'E').replace('Ó', 'O').replace('Ú', 'U')
    return n


def convertir_lote_id(raw_id: str) -> str:
    """
    Convierte los IDs del DXF al formato de la BD.
    52xxx -> ultimos 3 digitos (52001 -> '1')
    53xxx -> reemplaza 53 por 1 (53031 -> '1031')
    """
    if not raw_id or not raw_id.isdigit():
        return raw_id
    if raw_id.startswith('52') and len(raw_id) == 5:
        return str(int(raw_id[2:]))
    elif raw_id.startswith('53') and len(raw_id) == 5:
        return '1' + raw_id[2:]
    elif raw_id.startswith('552') and len(raw_id) == 6:
        return str(int(raw_id[3:]))
    return raw_id


# ── Tema claro ──
THEME = {
    'bg':        '#f0f2f5',
    'surface':   '#ffffff',
    'card':      '#fafafa',
    'border':    '#e2e8f0',
    'text':      '#1a202c',
    'subtext':   '#718096',
    'subtle':    '#cbd5e0',
    'accent':    '#3182ce',
    'accent_light': '#ebf4ff',
    'red':       '#e53e3e',
    'green':     '#38a169',
    'map_bg':    '#f0f2f5',  # Mismo que el fondo general para unificar
    'map_edge':  '#a0aec0',
}

# ── Paleta de colores por cultivo ──
COLORES_CULTIVO = {
    'MAIZ':           '#ECC94B',
    'FRIJOL':         '#A0522D',
    'FRIJOL EJOTERO': '#6B8E23',
    'SORGO':          '#68D391',
    'TRIGO':          '#D69E2E',
    'ALFALFA':        '#2F855A',
    'TOMATE':         '#FC8181',
    'CHILE':          '#ED8936',
    'CEBADA':         '#D6BCAE',
    'AVENA':          '#B7C68B',
    'CALABAZA':       '#F6AD55',
    'JITOMATE':       '#F56565',
    '_SIN_SIEMBRA':   '#E2E8F0',
    '_DESCONOCIDO':   '#EDF2F7',
}

# ── Paleta por barrio ──
COLORES_BARRIO = {
    'PANUAYA':     '#63B3ED',
    'TEZONTEPEC':  '#68D391',
    'ATENGO':      '#F6AD55',
    'MANGAS':      '#FC8181',
    'PRESAS':      '#F6E05E',
    'HUITEL':      '#4FD1C5',
}


def _color_cultivo(nombre_raw):
    """Devuelve color para un cultivo dado (normaliza para buscar)."""
    if not nombre_raw:
        return COLORES_CULTIVO['_SIN_SIEMBRA']
    norm = _normalizar_cultivo(nombre_raw)
    return COLORES_CULTIVO.get(norm, '#A0AEC0')


# ═══════════════════════════════════════════════════════════
# CARGA DE DATOS
# ═══════════════════════════════════════════════════════════

def cargar_geometria_cache():
    """Carga la geometria desde el JSON cache."""
    if not os.path.exists(JSON_CACHE):
        raise FileNotFoundError(
            f"No se encontro el archivo de geometria:\n"
            f"{JSON_CACHE}\n\n"
            f"Ejecuta primero:\n"
            f"  python3 extraer_mapa.py"
        )
    with open(JSON_CACHE, 'r', encoding='utf-8') as f:
        return json.load(f)


def cargar_datos_bd():
    """Carga datos de campesinos y siembras de la BD (datos frescos cada vez)."""
    if not os.path.exists(DB_PATH):
        return {}

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    try:
        cur.execute('''
            SELECT c.id, c.numero_lote, c.nombre, c.barrio, c.superficie,
                   s.cultivo, s.activa, s.numero_riegos, s.ciclo
            FROM campesinos c
            LEFT JOIN siembras s ON c.id = s.campesino_id AND s.activa = 1
            WHERE c.activo = 1
        ''')
        datos = {}
        for row in cur.fetchall():
            lote = row['numero_lote']
            datos[lote] = {
                'id': row['id'],
                'nombre': row['nombre'],
                'barrio': row['barrio'] or 'Sin barrio',
                'superficie': row['superficie'] or 0,
                'cultivo': row['cultivo'] or None,
                'siembra_activa': bool(row['activa']),
                'num_riegos': row['numero_riegos'] or 0,
                'ciclo': row['ciclo'] or '',
            }
        return datos
    finally:
        conn.close()


def _obtener_nombre_asociacion():
    """Lee nombre y ubicacion de la configuracion de la BD."""
    nombre = 'ASOCIACION DE CAMPESINOS DE BOMBEO Y REBOMBEO DEL CERRO DEL XICUCO'
    ubicacion = 'Tezontepec de Aldama, Hgo.'
    ciclo = ''
    if not os.path.exists(DB_PATH):
        return nombre, ubicacion, ciclo
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    try:
        cur.execute("SELECT clave, valor FROM configuracion WHERE clave IN ('nombre_oficina','ubicacion','ciclo_actual')")
        for row in cur.fetchall():
            if row['clave'] == 'nombre_oficina' and row['valor']:
                nombre = row['valor']
            elif row['clave'] == 'ubicacion' and row['valor']:
                ubicacion = row['valor']
            elif row['clave'] == 'ciclo_actual' and row['valor']:
                ciclo = row['valor']
    finally:
        conn.close()
    return nombre, ubicacion, ciclo


# ═══════════════════════════════════════════════════════════
# APLICACION PRINCIPAL
# ═══════════════════════════════════════════════════════════

class MapaCultivosApp:
    ZOOM_FACTOR = 1.3

    def __init__(self, root):
        self.root = root
        self.root.configure(bg=THEME['bg'])

        # Estado
        self.parcelas_geo = []
        self.datos_bd = {}
        self.mode = tk.StringVar(value='cultivo')
        self.filtro = tk.StringVar(value='Todos')
        self._patches = {}        # lote_id -> (patch, path_obj)
        self._selected_id = None
        self._hover_id = None
        self._pan_data = None     # Para pan con click + drag

        # Multi-criterio y nuevos modos
        self.filtro_cultivo = tk.StringVar(value='Todos')
        self.filtro_barrio = tk.StringVar(value='Todos')
        self.media_riegos = tk.IntVar(value=5)
        self.search_var = tk.StringVar()

        # Estilo
        style = ttk.Style()
        style.configure('Map.TCombobox',
                        fieldbackground=THEME['surface'],
                        background=THEME['surface'],
                        foreground=THEME['text'])
        style.configure('Map.TRadiobutton',
                        background=THEME['bg'],
                        foreground=THEME['text'],
                        font=('Helvetica', 10))

        self._build_ui()
        self._cargar_datos()

        # Cerrar limpiamente
        self.root.protocol('WM_DELETE_WINDOW', self._on_close)

    def _on_close(self):
        """Cierra la figura de matplotlib y destruye la ventana."""
        try:
            plt.close(self.fig)
        except Exception:
            pass
        self.root.destroy()

    # ──────── UI ────────
    def _build_ui(self):
        # ── Barra superior ──
        top = tk.Frame(self.root, bg=THEME['surface'], pady=8, padx=16,
                       highlightthickness=0)
        top.pack(fill='x')

        # Fila 1: Titulo y Buscador
        row1 = tk.Frame(top, bg=THEME['surface'])
        row1.pack(fill='x', pady=(0, 6))

        tk.Label(row1, text='Mapa de Parcelas  -  Seccion 4 Tezontepec',
                 font=('Helvetica', 13, 'bold'),
                 bg=THEME['surface'], fg=THEME['text']).pack(side='left')

        self.label_stats = tk.Label(row1, text='',
                                     font=('Helvetica', 9),
                                     bg=THEME['surface'], fg=THEME['subtext'])
        self.label_stats.pack(side='right')

        search_frame = tk.Frame(row1, bg=THEME['surface'])
        search_frame.pack(side='right', padx=20)
        tk.Label(search_frame, text='🔍 Lote:', bg=THEME['surface'], fg=THEME['text']).pack(side='left')
        self.entry_search = ttk.Entry(search_frame, textvariable=self.search_var, width=8)
        self.entry_search.pack(side='left', padx=(4, 4))
        self.entry_search.bind('<Return>', lambda e: self._buscar_lote())
        tk.Button(search_frame, text='Ir', command=self._buscar_lote,
                  bg=THEME['border'], fg=THEME['text'], relief='flat', padx=6, pady=1,
                  font=('Helvetica', 9), cursor='hand2').pack(side='left')

        # Fila 2: Controles
        row2 = tk.Frame(top, bg=THEME['surface'])
        row2.pack(fill='x')

        # Modos de color
        mode_frame = tk.Frame(row2, bg=THEME['surface'])
        mode_frame.pack(side='left')
        tk.Label(mode_frame, text='Colorear por:',
                 font=('Helvetica', 9, 'bold'),
                 bg=THEME['surface'], fg=THEME['subtext']).pack(anchor='w')
        modes_inner = tk.Frame(mode_frame, bg=THEME['surface'])
        modes_inner.pack(anchor='w')
        for val, label in [('cultivo', 'Cultivo'), ('barrio', 'Barrio'), ('estado', 'Estado'), ('riegos', 'Riegos')]:
            ttk.Radiobutton(modes_inner, text=label, variable=self.mode,
                            value=val, style='Map.TRadiobutton',
                            command=self._cambiar_modo).pack(side='left', padx=(0, 8))

        # Selector de Media Riegos (Solo visible en modo Riegos)
        self.riegos_frame = tk.Frame(modes_inner, bg=THEME['surface'])
        tk.Label(self.riegos_frame, text='Media:', font=('Helvetica', 9),
                 bg=THEME['surface'], fg=THEME['subtext']).pack(side='left', padx=(10, 2))
        self.combo_riegos = ttk.Combobox(self.riegos_frame, textvariable=self.media_riegos,
                                         values=list(range(1, 13)), width=3, state='readonly')
        self.combo_riegos.pack(side='left')
        self.combo_riegos.bind('<<ComboboxSelected>>', lambda e: self._redibujar())
        # Oculto por defecto
        self.riegos_frame.pack_forget()

        # Separador Vertical
        tk.Frame(row2, bg=THEME['border'], width=1).pack(side='left', fill='y', padx=12, pady=4)

        # Filtros Multicriterio
        tk.Label(row2, text='Filtro Cultivo:', font=('Helvetica', 9, 'bold'),
                 bg=THEME['surface'], fg=THEME['subtext']).pack(side='left', padx=(0, 4))
        self.combo_fcultivo = ttk.Combobox(row2, textvariable=self.filtro_cultivo,
                                           width=14, state='readonly', style='Map.TCombobox')
        self.combo_fcultivo.pack(side='left', padx=(0, 10))
        self.combo_fcultivo.bind('<<ComboboxSelected>>', lambda e: self._redibujar())

        tk.Label(row2, text='Filtro Barrio:', font=('Helvetica', 9, 'bold'),
                 bg=THEME['surface'], fg=THEME['subtext']).pack(side='left', padx=(0, 4))
        self.combo_fbarrio = ttk.Combobox(row2, textvariable=self.filtro_barrio,
                                          width=12, state='readonly', style='Map.TCombobox')
        self.combo_fbarrio.pack(side='left', padx=(0, 10))
        self.combo_fbarrio.bind('<<ComboboxSelected>>', lambda e: self._redibujar())

        # Separador Vertical
        tk.Frame(row2, bg=THEME['border'], width=1).pack(side='left', fill='y', padx=12, pady=4)

        # Botones
        tk.Button(row2, text='Actualizar', command=self._cargar_datos,
                  bg=THEME['accent_light'], fg=THEME['text'],
                  activebackground='#bee3f8', activeforeground=THEME['text'],
                  relief='flat', padx=12, pady=3,
                  font=('Helvetica', 9), cursor='hand2').pack(side='left', padx=(0, 4))

        tk.Button(row2, text='Guardar PDF', command=self._guardar_pdf,
                  bg='#c6f6d5', fg=THEME['text'],
                  activebackground='#9ae6b4', activeforeground=THEME['text'],
                  relief='flat', padx=12, pady=3,
                  font=('Helvetica', 9), cursor='hand2').pack(side='left')

        # ── Panel principal ──
        main = tk.Frame(self.root, bg=THEME['bg'])
        main.pack(fill='both', expand=True)

        # Canvas del mapa (sin toolbar)
        map_frame = tk.Frame(main, bg=THEME['bg'])
        map_frame.pack(side='left', fill='both', expand=True)

        self.fig, self.ax = plt.subplots(figsize=(12, 8), facecolor=THEME['map_bg'])
        # Forzar que el Eje ocupe TODO el espacio de la figura sin margenes
        self.ax.set_position([0, 0, 1, 1])
        self.fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
        self.ax.set_facecolor(THEME['map_bg'])

        self.canvas = FigureCanvasTkAgg(self.fig, master=map_frame)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)

        # Anotacion flotante (Tooltip)
        self.tooltip = self.ax.annotate(
            "", xy=(0, 0), xytext=(15, 15),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.4", fc="#ffffff", ec="#cbd5e0", alpha=0.95),
            arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0", color="#cbd5e0"),
            fontsize=8, zorder=100
        )
        self.tooltip.set_visible(False)

        # Eventos del canvas: pan + click
        self.canvas.mpl_connect('button_press_event', self._on_press)
        self.canvas.mpl_connect('button_release_event', self._on_release)
        self.canvas.mpl_connect('motion_notify_event', self._on_motion)

        # Barra de zoom
        zoom_frame = tk.Frame(map_frame, bg=THEME['surface'], pady=4,
                              highlightthickness=0)
        zoom_frame.pack(fill='x')

        tk.Label(zoom_frame, text='Zoom:', font=('Helvetica', 9),
                 bg=THEME['surface'], fg=THEME['subtext']).pack(side='left', padx=(10, 4))

        self._zoom_var = tk.DoubleVar(value=1.0)
        self.zoom_scale = tk.Scale(
            zoom_frame, from_=0.5, to=20.0, resolution=0.1,
            orient='horizontal', variable=self._zoom_var,
            command=self._on_zoom_slider,
            bg=THEME['surface'], fg=THEME['text'],
            troughcolor=THEME['border'], highlightthickness=0,
            sliderrelief='flat', length=300,
            showvalue=False)
        self.zoom_scale.pack(side='left', fill='x', expand=True, padx=4)

        self._zoom_label = tk.Label(zoom_frame, text='1.0x',
                                     font=('Menlo', 9, 'bold'),
                                     bg=THEME['surface'], fg=THEME['text'], width=5)
        self._zoom_label.pack(side='left', padx=(0, 6))

        tk.Button(zoom_frame, text='Reiniciar', command=self._zoom_reset,
                  bg=THEME['card'], fg=THEME['text'],
                  activebackground=THEME['border'],
                  relief='flat', padx=8, pady=1,
                  font=('Helvetica', 9), cursor='hand2').pack(side='left', padx=(0, 10))

        # ── Panel lateral ──
        self.panel = tk.Frame(main, bg=THEME['surface'], width=270,
                               highlightthickness=0)
        self.panel.pack(side='right', fill='y')
        self.panel.pack_propagate(False)

        tk.Label(self.panel, text='Detalle del Lote',
                 font=('Helvetica', 12, 'bold'),
                 bg=THEME['surface'], fg=THEME['text']).pack(pady=(14, 4))

        sep = tk.Frame(self.panel, bg=THEME['border'], height=1)
        sep.pack(fill='x', padx=14, pady=(0, 6))

        self.info_text = tk.Text(
            self.panel, bg=THEME['card'], fg=THEME['text'],
            font=('Menlo', 10), relief='flat',
            state='disabled', wrap='word',
            height=14, padx=10, pady=8,
            insertbackground=THEME['text'],
            selectbackground=THEME['accent'])
        self.info_text.pack(fill='x', padx=10, pady=(0, 6))

        self.info_text.tag_configure('title', foreground=THEME['accent'], font=('Menlo', 11, 'bold'))
        self.info_text.tag_configure('label', foreground=THEME['subtext'])
        self.info_text.tag_configure('value', foreground=THEME['text'], font=('Menlo', 10, 'bold'))
        self.info_text.tag_configure('sep', foreground=THEME['subtle'])
        self.info_text.tag_configure('active', foreground=THEME['green'])
        self.info_text.tag_configure('inactive', foreground=THEME['subtext'])

        # ── Leyenda ──
        tk.Label(self.panel, text='Leyenda',
                 font=('Helvetica', 11, 'bold'),
                 bg=THEME['surface'], fg=THEME['subtext']).pack(pady=(8, 4))
        sep2 = tk.Frame(self.panel, bg=THEME['border'], height=1)
        sep2.pack(fill='x', padx=14, pady=(0, 6))

        legend_canvas = tk.Canvas(self.panel, bg=THEME['surface'], highlightthickness=0)
        legend_canvas.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        self.legend_frame = tk.Frame(legend_canvas, bg=THEME['surface'])
        legend_canvas.create_window((0, 0), window=self.legend_frame, anchor='nw')
        self.legend_frame.bind('<Configure>',
                                lambda e: legend_canvas.configure(scrollregion=legend_canvas.bbox('all')))

        # ── Barra de estado ──
        status_bar = tk.Frame(self.root, bg=THEME['surface'],
                               highlightbackground=THEME['border'], highlightthickness=1)
        status_bar.pack(fill='x', side='bottom')
        self.label_status = tk.Label(status_bar, text='Cargando...',
                                      font=('Helvetica', 9),
                                      bg=THEME['surface'], fg=THEME['subtext'])
        self.label_status.pack(side='left', padx=14, pady=3)

    # ──────── Zoom y Pan ────────
    def _aplicar_zoom(self, factor):
        """Aplica zoom centrado en el centro actual de la vista."""
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        cx = (xlim[0] + xlim[1]) / 2
        cy = (ylim[0] + ylim[1]) / 2
        new_xrange = (xlim[1] - xlim[0]) / factor
        new_yrange = (ylim[1] - ylim[0]) / factor
        self.ax.set_xlim([cx - new_xrange / 2, cx + new_xrange / 2])
        self.ax.set_ylim([cy - new_yrange / 2, cy + new_yrange / 2])
        self.canvas.draw_idle()

    def _on_zoom_scroll(self, *args):
        """Callback del Scrollbar de zoom.
        args contiene (first, last) como fracciones del rango.
        Convertimos a nivel de zoom entre 0.5 y 20.0.
        """
        # args[0] es la posición inicial del thumb (0.0‑1.0)
        try:
            pos = float(args[0])
        except Exception:
            return
        # Mapear posición a rango de zoom
        zoom_min, zoom_max = 0.5, 20.0
        zoom_level = zoom_min + (zoom_max - zoom_min) * pos
        self._zoom_var.set(zoom_level)
        self._zoom_label.config(text=f'{zoom_level:.1f}x')
        self._aplicar_zoom(zoom_level)

    def _on_zoom_slider(self, val):
        """Llamado cuando se mueve el slider de zoom."""
        zoom_level = float(val)
        self._zoom_label.config(text=f'{zoom_level:.1f}x')

        if not hasattr(self, '_base_xlim'):
            return

        base_xrange = self._base_xlim[1] - self._base_xlim[0]
        base_yrange = self._base_ylim[1] - self._base_ylim[0]

        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        cx = (xlim[0] + xlim[1]) / 2
        cy = (ylim[0] + ylim[1]) / 2

        new_xrange = base_xrange / zoom_level
        new_yrange = base_yrange / zoom_level

        self.ax.set_xlim([cx - new_xrange / 2, cx + new_xrange / 2])
        self.ax.set_ylim([cy - new_yrange / 2, cy + new_yrange / 2])
        self.canvas.draw_idle()

    def _zoom_reset(self):
        """Restablece el zoom a 1x y centra la vista."""
        self._zoom_var.set(1.0)
        self._zoom_label.config(text='1.0x')
        # Resetear límites de vista a los base guardados
        self.ax.set_xlim(self.base_xlim)
        self.ax.set_ylim(self.base_ylim)
        self.canvas.draw_idle()

    def _on_press(self, event):
        """Inicio del pan (button 1 = izquierdo, button 2/3 = derecho)."""
        if event.inaxes != self.ax:
            return
        if event.button == 1:
            self._pan_data = {
                'x': event.xdata, 'y': event.ydata,
                'xlim': self.ax.get_xlim(), 'ylim': self.ax.get_ylim(),
                'dragged': False,
            }

    def _on_release(self, event):
        """Fin del pan. Si no se arrastro, es un click normal."""
        if self._pan_data is not None:
            if not self._pan_data.get('dragged'):
                # Fue un click sin arrastrar -> seleccionar parcela
                if event.inaxes == self.ax and event.xdata is not None:
                    point = (event.xdata, event.ydata)
                    for lote_id, (patch, path_obj) in self._patches.items():
                        if path_obj.contains_point(point):
                            self._mostrar_detalle(lote_id)
                            break
            self._pan_data = None

    def _on_motion(self, event):
        """Pan arrastrando + hover highlight."""
        # Pan
        if self._pan_data is not None and event.inaxes == self.ax and event.xdata is not None:
            dx = self._pan_data['x'] - event.xdata
            dy = self._pan_data['y'] - event.ydata
            if abs(dx) > 0.5 or abs(dy) > 0.5:
                self._pan_data['dragged'] = True
            xlim = self._pan_data['xlim']
            ylim = self._pan_data['ylim']
            self.ax.set_xlim([xlim[0] + dx, xlim[1] + dx])
            self.ax.set_ylim([ylim[0] + dy, ylim[1] + dy])
            self.canvas.draw_idle()
            return

        # Hover (solo si no estamos arrastrando)
        if event.inaxes != self.ax or event.xdata is None:
            if self._hover_id and self._hover_id in self._patches:
                self._patches[self._hover_id][0].set_edgecolor(THEME['map_edge'])
                self._patches[self._hover_id][0].set_linewidth(0.25)
                self._hover_id = None
                self.canvas.draw_idle()
            return

        if self._hover_id and self._hover_id in self._patches:
            self._patches[self._hover_id][0].set_edgecolor(THEME['map_edge'])
            self._patches[self._hover_id][0].set_linewidth(0.25)
            self._hover_id = None
            self.tooltip.set_visible(False)

        point = (event.xdata, event.ydata)
        for lote_id, (patch, path_obj) in self._patches.items():
            if path_obj.contains_point(point):
                patch.set_edgecolor(THEME['accent'])
                patch.set_linewidth(1.8)
                self._hover_id = lote_id
                
                # Update text and position for tooltip
                datos = self.datos_bd.get(lote_id, {})
                campesino = datos.get('nombre', 'N/D')
                barrio = datos.get('barrio', 'N/D')
                cultivo = datos.get('cultivo', 'Sin siembra')
                if not cultivo: cultivo = 'Sin siembra'
                
                tt_text = f"Lote: {lote_id}\n{campesino}\n{cultivo} - {barrio}"
                self.tooltip.set_text(tt_text)
                self.tooltip.xy = (event.xdata, event.ydata)
                self.tooltip.set_visible(True)
                break

        self.canvas.draw_idle()

    # ──────── Carga de datos ────────
    def _cargar_datos(self):
        self.label_status.config(text='Cargando datos...')
        self.root.update_idletasks()

        try:
            geo_data = cargar_geometria_cache()
            self.parcelas_geo = geo_data.get('parcelas', [])
        except FileNotFoundError as e:
            messagebox.showerror('Error', str(e))
            return
        except Exception as e:
            messagebox.showerror('Error al cargar geometria', str(e))
            return

        self.datos_bd = cargar_datos_bd()
        self._actualizar_filtros(reset=True)
        self._actualizar_stats()
        self._redibujar()

        matched = sum(1 for p in self.parcelas_geo
                      if p.get('lote_id') and p['lote_id'] in self.datos_bd)
        self.label_status.config(
            text=f'{len(self.parcelas_geo)} parcelas  |  '
                 f'{len(self.datos_bd)} campesinos  |  '
                 f'{matched} vinculados')

    def _buscar_lote(self):
        """Busca un lote por ID, centra la vista ahi con zoom y muestra detalle."""
        val = self.search_var.get().strip()
        if not val:
            return
        lote_id = convertir_lote_id(val)
        
        if lote_id not in self._patches:
            messagebox.showinfo('No encontrado', f'Lote {lote_id} no se encontro en el mapa.', parent=self.root)
            return
            
        # Encontrar bounding box y centrar
        patch, path_obj = self._patches[lote_id]
        verts = path_obj.vertices
        if len(verts) > 0:
            xs = [v[0] for v in verts]
            ys = [v[1] for v in verts]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            
            # Anadir un poco de margen para que se vea el contexto al hacer zoom
            margen_x = max(10, (max_x - min_x) * 2)
            margen_y = max(10, (max_y - min_y) * 2)
            
            self.ax.set_xlim([min_x - margen_x, max_x + margen_x])
            self.ax.set_ylim([min_y - margen_y, max_y + margen_y])
            
            # Mostrar detalles y marcar hover
            self._mostrar_detalle(lote_id)
            if self._hover_id and self._hover_id in self._patches:
                self._patches[self._hover_id][0].set_edgecolor(THEME['map_edge'])
                self._patches[self._hover_id][0].set_linewidth(0.25)
                
            patch.set_edgecolor('#e53e3e') # Rojo fuerte temporal
            patch.set_linewidth(2.5)
            self._hover_id = lote_id
            
            # Actualizar el slider de zoom basado en el factor calculado
            if hasattr(self, '_base_xlim'):
                bx = self._base_xlim[1] - self._base_xlim[0]
                nx = (max_x + margen_x) - (min_x - margen_x)
                if nx > 0:
                    zoom_lvl = min(20.0, max(0.5, bx / nx))
                    self._zoom_var.set(zoom_lvl)
                    self._zoom_label.config(text=f'{zoom_lvl:.1f}x')
                    
            self.canvas.draw_idle()

    def _actualizar_filtros(self, reset=False):
        # Actualizar opciones de cultivo
        raw_vals_c = [d['cultivo'] for d in self.datos_bd.values() if d.get('cultivo')]
        norm_map_c = {}
        for v in raw_vals_c:
            norm = _normalizar_cultivo(v)
            if norm not in norm_map_c:
                norm_map_c[norm] = v
        op_cultivo = ['Todos', 'Con siembra', 'Sin siembra'] + sorted(norm_map_c.values())
        self.combo_fcultivo['values'] = op_cultivo
        if reset or self.filtro_cultivo.get() not in op_cultivo:
            self.filtro_cultivo.set('Todos')
            
        # Actualizar opciones de barrio
        vals_b = sorted(set(d['barrio'] for d in self.datos_bd.values() if d.get('barrio')))
        op_barrio = ['Todos'] + vals_b
        self.combo_fbarrio['values'] = op_barrio
        if reset or self.filtro_barrio.get() not in op_barrio:
            self.filtro_barrio.set('Todos')

    def _cambiar_modo(self):
        """Llamado cuando se cambia el modo. Muestra/oculta opciones extra y redibuja."""
        if self.mode.get() == 'riegos':
            self.riegos_frame.pack(side='left', padx=(4, 0))
        else:
            self.riegos_frame.pack_forget()
        self._redibujar()

    def _actualizar_stats(self):
        total = len(self.datos_bd)
        con = sum(1 for d in self.datos_bd.values() if d.get('siembra_activa'))
        self.label_stats.config(
            text=f'Parcelas: {len(self.parcelas_geo)}  |  '
                 f'Con siembra: {con}  |  Sin siembra: {total - con}')

    # ──────── Dibujo ────────
    def _cumple_filtros(self, datos):
        """Revisa si la parcela cumple con los filtros multicriterio."""
        fc = self.filtro_cultivo.get()
        fb = self.filtro_barrio.get()
        
        cultivo = datos.get('cultivo', '')
        barrio = datos.get('barrio', '')
        activa = datos.get('siembra_activa', False)
        
        c_ok = True
        if fc == 'Con siembra': c_ok = activa
        elif fc == 'Sin siembra': c_ok = not activa
        elif fc != 'Todos':
            c_ok = (_normalizar_cultivo(cultivo) == _normalizar_cultivo(fc)) if cultivo else False
            
        b_ok = True
        if fb != 'Todos':
            b_ok = (barrio == fb)
            
        return c_ok and b_ok

    def _get_color(self, lote_id):
        datos = self.datos_bd.get(lote_id, {})
        mode = self.mode.get()
        
        pasa_filtro = self._cumple_filtros(datos)
        alpha = 0.85 if pasa_filtro else 0.08
        
        if mode == 'cultivo':
            return _color_cultivo(datos.get('cultivo')), alpha

        elif mode == 'barrio':
            barrio = datos.get('barrio', '')
            return COLORES_BARRIO.get(barrio, '#A0AEC0'), alpha

        elif mode == 'riegos':
            import matplotlib.colors as mcolors
            # Red gradient: light → medium → dark red
            cmap = mcolors.LinearSegmentedColormap.from_list("riegos", ["#ffcccc", "#ff6666", "#cc0000"])
            riegos = int(datos.get('num_riegos') or 0)
            media = self.media_riegos.get()
            if media <= 0: media = 1
            ratio = min(1.0, float(riegos) / float(media))
            color = mcolors.to_hex(cmap(ratio))
            
            # Si no ha regado, se destaca siempre y cuando este activo (si no esta activo es gris)
            if not datos.get('siembra_activa', False):
                color = COLORES_CULTIVO['_SIN_SIEMBRA']
                
            return color, alpha

        else: # estado
            activa = datos.get('siembra_activa', False)
            return THEME['green'] if activa else COLORES_CULTIVO['_SIN_SIEMBRA'], alpha

    def _redibujar(self):
        self.ax.clear()
        # Forzar que el Eje ocupe TODO el espacio de la figura cada vez que se limpie
        self.ax.set_position([0, 0, 1, 1])
        self.fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
        
        # Cambiar cursor del canvas a solo mover (fleur)
        self.canvas.get_tk_widget().config(cursor='fleur')
        self.ax.set_facecolor(THEME['map_bg'])
        self.ax.set_aspect('equal')
        self.ax.axis('off')

        self._patches = {}

        for parcela in self.parcelas_geo:
            lote_id = parcela.get('lote_id')
            coords = parcela.get('coords', [])
            if not coords or len(coords) < 3:
                continue

            color, alpha = self._get_color(lote_id)

            poly = MplPolygon(
                coords, closed=True,
                facecolor=color,
                edgecolor=THEME['map_edge'],
                linewidth=0.25,
                alpha=alpha,
                antialiased=True)
            self.ax.add_patch(poly)

            if lote_id:
                path_obj = Path(coords + [coords[0]])
                self._patches[lote_id] = (poly, path_obj)

                cx, cy = parcela['centroid']
                self.ax.text(cx, cy, str(lote_id),
                             ha='center', va='center',
                             fontsize=3, color='#4A5568',
                             fontweight='bold', alpha=0.6,
                             clip_on=True)

        self.ax.autoscale_view()

        # Recrear el tooltip ya que ax.clear() lo borró
        self.tooltip = self.ax.annotate(
            "", xy=(0, 0), xytext=(15, 15),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.4", fc="#ffffff", ec="#cbd5e0", alpha=0.95),
            arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0", color="#cbd5e0"),
            fontsize=8, zorder=100
        )
        self.tooltip.set_visible(False)

        # Guardar limites base para el slider de zoom
        self._base_xlim = self.ax.get_xlim()
        self._base_ylim = self.ax.get_ylim()
        self._zoom_var.set(1.0)
        self._zoom_label.config(text='1.0x')

        mode_names = {'cultivo': 'Cultivo', 'barrio': 'Barrio', 'estado': 'Estado', 'riegos': 'Riegos'}
        self.ax.set_title(
            f'Seccion 4  -  {len(self.parcelas_geo)} parcelas  -  {mode_names.get(self.mode.get(), "")}',
            color=THEME['text'], pad=10, fontsize=11, fontweight='bold')

        self._actualizar_leyenda()
        self.canvas.draw()

    # ──────── Leyenda ────────
    def _actualizar_leyenda(self):
        for w in self.legend_frame.winfo_children():
            w.destroy()

        mode = self.mode.get()
        if mode == 'cultivo':
            items = {}
            for d in self.datos_bd.values():
                c = _normalizar_cultivo(d.get('cultivo')) or 'Sin siembra'
                items[c] = items.get(c, 0) + 1
            color_map = {**COLORES_CULTIVO, 'Sin siembra': COLORES_CULTIVO['_SIN_SIEMBRA']}
        elif mode == 'barrio':
            items = {}
            for d in self.datos_bd.values():
                b = d.get('barrio', 'Sin barrio')
                items[b] = items.get(b, 0) + 1
            color_map = COLORES_BARRIO
        elif mode == 'riegos':
            import matplotlib.colors as mcolors
            # Red gradient: light red -> medium -> dark red
            cmap = mcolors.LinearSegmentedColormap.from_list("riegos", ["#ffcccc", "#ff6666", "#cc0000"])
            media = self.media_riegos.get()
            if media <= 0: media = 1
            
            # Conteo por numero de riegos
            items = {}
            for d in self.datos_bd.values():
                if d.get('siembra_activa'):
                    r = int(d.get('num_riegos') or 0)
                    k = f"{r} riegos"
                    items[k] = items.get(k, 0) + 1
                    
            # Mapeo dinamico para la leyenda
            color_map = {}
            for r_str in items.keys():
                r = int(r_str.split()[0])
                ratio = min(1.0, float(r) / float(media))
                color_map[r_str] = mcolors.to_hex(cmap(ratio))
        else:
            con = sum(1 for d in self.datos_bd.values() if d.get('siembra_activa'))
            items = {'Con siembra': con, 'Sin siembra': len(self.datos_bd) - con}
            color_map = {'Con siembra': THEME['green'],
                         'Sin siembra': COLORES_CULTIVO['_SIN_SIEMBRA']}

        # Ordenar: si es riegos, numerico; si no, por cantidad descendente
        if mode == 'riegos':
            # Orden descendente (mayor número de riegos primero)
            sorted_items = sorted(items.items(), key=lambda x: -int(x[0].split()[0]))
        else:
            sorted_items = sorted(items.items(), key=lambda x: -x[1])

        for nombre, count in sorted_items:
            color = color_map.get(nombre, '#A0AEC0')
            row = tk.Frame(self.legend_frame, bg=THEME['surface'])
            row.pack(anchor='w', fill='x', pady=1)
            swatch = tk.Frame(row, bg=color, width=12, height=12)
            swatch.pack(side='left', padx=(0, 6))
            swatch.pack_propagate(False)
            tk.Label(row, text=nombre, fg=THEME['text'], bg=THEME['surface'],
                     font=('Helvetica', 9), anchor='w').pack(side='left')
            tk.Label(row, text=f'({count})', fg=THEME['subtle'], bg=THEME['surface'],
                     font=('Helvetica', 8)).pack(side='right')

    # ──────── Detalle ────────
    def _mostrar_detalle(self, lote_id):
        datos = self.datos_bd.get(lote_id, {})

        self.info_text.config(state='normal')
        self.info_text.delete('1.0', 'end')

        self.info_text.insert('end', f'LOTE {lote_id}\n', 'title')
        self.info_text.insert('end', '-' * 28 + '\n', 'sep')

        if datos:
            fields = [
                ('Campesino', datos.get('nombre', 'N/D')),
                ('Barrio', datos.get('barrio', 'N/D')),
                ('Superficie', f"{datos.get('superficie', 0):.2f} ha"),
                ('', ''),
                ('Cultivo', datos.get('cultivo') or 'Sin siembra'),
                ('Estado', 'Activa' if datos.get('siembra_activa') else 'Inactiva'),
                ('Riegos', str(datos.get('num_riegos', 0))),
                ('Ciclo', datos.get('ciclo', 'N/D')),
            ]
            for label, value in fields:
                if not label:
                    self.info_text.insert('end', '\n')
                    continue
                self.info_text.insert('end', f'  {label:12s}', 'label')
                tag = 'value'
                if value == 'Activa':
                    tag = 'active'
                elif value == 'Inactiva':
                    tag = 'inactive'
                self.info_text.insert('end', f'  {value}\n', tag)
        else:
            self.info_text.insert('end', '\n  Sin datos en BD\n', 'inactive')
            self.info_text.insert('end', f'  ID DXF: {lote_id}\n', 'label')

        self.info_text.insert('end', '\n' + '-' * 28, 'sep')
        self.info_text.config(state='disabled')
        self._selected_id = lote_id

    # ═══════════════════════════════════════════════════════
    # EXPORTAR PDF
    # ═══════════════════════════════════════════════════════
    def _guardar_pdf(self):
        """Genera PDF: mapa general + un mapa por cultivo + graficas de pastel."""
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.lib.units import cm
        from reportlab.pdfgen import canvas as pdf_canvas
        from reportlab.lib.utils import ImageReader

        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M')
        default_name = f'Mapa_Distribucion_{timestamp}.pdf'

        file_path = filedialog.asksaveasfilename(
            parent=self.root,
            title='Guardar Reporte PDF',
            defaultextension='.pdf',
            initialfile=default_name,
            filetypes=[('PDF', '*.pdf')]
        )
        if not file_path:
            return

        self.label_status.config(text='Generando PDF...')
        self.root.update_idletasks()

        try:
            nombre_asoc, ubicacion, ciclo = _obtener_nombre_asociacion()
            page_w, page_h = landscape(letter)
            c = pdf_canvas.Canvas(file_path, pagesize=landscape(letter))
            margin = 1.5 * cm

            # Obtener lista de cultivos unicos
            cultivos_unicos = sorted(set(
                _normalizar_cultivo(d['cultivo'])
                for d in self.datos_bd.values() if d.get('cultivo')
            ))

            # ══════════ PAGINA 1: MAPA GENERAL (todos los cultivos) ══════════
            self._pdf_encabezado(c, page_w, page_h, nombre_asoc, ubicacion, ciclo,
                                  subtitulo='Mapa General - Todos los Cultivos')
            buf = self._renderizar_mapa_a_imagen(filtro_cultivo=None)
            c.drawImage(ImageReader(buf), margin, margin,
                        width=page_w - 2 * margin,
                        height=page_h - 4.5 * cm,
                        preserveAspectRatio=True, anchor='c')
            buf.close()
            c.showPage()

            # ══════════ PAGINAS POR CULTIVO ══════════
            total_cultivos = len(cultivos_unicos)
            for i, cultivo in enumerate(cultivos_unicos):
                self.label_status.config(
                    text=f'Generando PDF... mapa {i+1}/{total_cultivos}: {cultivo}')
                self.root.update_idletasks()

                count = sum(1 for d in self.datos_bd.values()
                            if _normalizar_cultivo(d.get('cultivo')) == cultivo)

                self._pdf_encabezado(c, page_w, page_h, nombre_asoc, ubicacion, ciclo,
                                      subtitulo=f'{cultivo}  ({count} parcelas)')
                buf = self._renderizar_mapa_a_imagen(filtro_cultivo=cultivo)
                c.drawImage(ImageReader(buf), margin, margin,
                            width=page_w - 2 * margin,
                            height=page_h - 4.5 * cm,
                            preserveAspectRatio=True, anchor='c')
                buf.close()
                c.showPage()

            # ══════════ PAGINA FINAL: GRAFICAS DE PASTEL ══════════
            self.label_status.config(text='Generando PDF... graficas de pastel')
            self.root.update_idletasks()

            self._pdf_encabezado(c, page_w, page_h, nombre_asoc, ubicacion, ciclo,
                                  subtitulo='Distribucion de Cultivos')
            pie_buf = self._generar_graficas_pastel()
            c.drawImage(ImageReader(pie_buf), margin, margin,
                        width=page_w - 2 * margin,
                        height=page_h - 4.5 * cm,
                        preserveAspectRatio=True, anchor='c')
            pie_buf.close()
            c.showPage()

            c.save()

            self.label_status.config(text=f'PDF guardado: {os.path.basename(file_path)}')
            messagebox.showinfo('PDF Generado',
                                f'Reporte guardado exitosamente:\n{file_path}',
                                parent=self.root)

            import subprocess, platform
            if platform.system() == 'Darwin':
                subprocess.Popen(['open', file_path])
            elif platform.system() == 'Windows':
                os.startfile(file_path)

        except Exception as e:
            self.label_status.config(text='Error al generar PDF')
            messagebox.showerror('Error', f'No se pudo generar el PDF:\n{e}',
                                 parent=self.root)

    def _renderizar_mapa_a_imagen(self, filtro_cultivo=None):
        """
        Renderiza el mapa en una figura temporal y lo devuelve como BytesIO PNG.
        Si filtro_cultivo es None, muestra todos.
        Si es un nombre normalizado, resalta solo ese cultivo.
        """
        fig, ax = plt.subplots(figsize=(14, 9), facecolor=THEME['map_bg'])
        ax.set_facecolor(THEME['map_bg'])
        ax.set_aspect('equal')
        ax.axis('off')

        for parcela in self.parcelas_geo:
            lote_id = parcela.get('lote_id')
            coords = parcela.get('coords', [])
            if not coords or len(coords) < 3:
                continue

            datos = self.datos_bd.get(lote_id, {})
            cultivo_norm = _normalizar_cultivo(datos.get('cultivo'))
            color = _color_cultivo(datos.get('cultivo'))

            if filtro_cultivo is None:
                alpha = 0.85
            else:
                alpha = 0.9 if cultivo_norm == filtro_cultivo else 0.08

            poly = MplPolygon(
                coords, closed=True,
                facecolor=color,
                edgecolor=THEME['map_edge'],
                linewidth=0.2,
                alpha=alpha,
                antialiased=True)
            ax.add_patch(poly)

            if lote_id:
                cx, cy = parcela['centroid']
                ax.text(cx, cy, str(lote_id),
                        ha='center', va='center',
                        fontsize=2.5, color='#4A5568',
                        fontweight='bold', alpha=0.5,
                        clip_on=True)

        ax.autoscale_view()

        titulo = 'Todos los Cultivos' if not filtro_cultivo else filtro_cultivo
        ax.set_title(f'Seccion 4  -  {titulo}',
                     color=THEME['text'], pad=10, fontsize=12, fontweight='bold')

        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=200,
                    bbox_inches='tight', facecolor=THEME['map_bg'])
        plt.close(fig)
        buf.seek(0)
        return buf

    def _pdf_encabezado(self, c, page_w, page_h, nombre, ubicacion, ciclo,
                         subtitulo=None):
        """Dibuja el encabezado institucional con logo en una pagina del PDF."""
        from reportlab.lib.units import cm

        y_top = page_h - 1.0 * cm

        if os.path.exists(LOGO_PATH):
            try:
                logo_h = 2.2 * cm
                logo_w = 2.2 * cm
                c.drawImage(LOGO_PATH, 1.5 * cm, y_top - logo_h,
                            width=logo_w, height=logo_h,
                            preserveAspectRatio=True, mask='auto')
            except Exception:
                pass

        x_text = 4.5 * cm
        c.setFont('Helvetica-Bold', 11)
        c.drawString(x_text, y_top - 0.6 * cm, nombre)

        c.setFont('Helvetica', 9)
        c.drawString(x_text, y_top - 1.1 * cm, ubicacion)

        if ciclo:
            c.drawString(x_text, y_top - 1.6 * cm, f'Ciclo: {ciclo}')

        if subtitulo:
            c.setFont('Helvetica-Bold', 13)
            c.drawCentredString(page_w / 2, y_top - 2.6 * cm, subtitulo)

        c.setFont('Helvetica', 8)
        fecha = datetime.now().strftime('%d/%m/%Y  %H:%M')
        c.drawRightString(page_w - 1.5 * cm, y_top - 0.6 * cm, f'Fecha: {fecha}')

        c.setStrokeColorRGB(0.8, 0.82, 0.85)
        c.setLineWidth(0.5)
        y_line = y_top - 2.8 * cm if subtitulo else y_top - 2.0 * cm
        c.line(1.5 * cm, y_line, page_w - 1.5 * cm, y_line)

    def _generar_graficas_pastel(self):
        """Genera graficas de pastel (general + por barrio) con layout de subplot."""
        datos = self.datos_bd

        # Conteo general
        conteo_general = Counter()
        for d in datos.values():
            cult = _normalizar_cultivo(d.get('cultivo')) or 'SIN SIEMBRA'
            conteo_general[cult] += 1

        # Conteo por barrio
        barrios = sorted(set(d.get('barrio', 'Sin barrio') for d in datos.values()))
        conteo_barrio = {}
        for barrio in barrios:
            conteo = Counter()
            for d in datos.values():
                if d.get('barrio') == barrio:
                    cult = _normalizar_cultivo(d.get('cultivo')) or 'SIN SIEMBRA'
                    conteo[cult] += 1
            conteo_barrio[barrio] = conteo

        n_barrios = len(barrios)
        ncols = 3
        nrows_barrio = (n_barrios + ncols - 1) // ncols
        # 1 fila para general + nrows_barrio para barrios
        total_rows = 1 + nrows_barrio

        fig, axes = plt.subplots(
            total_rows, ncols,
            figsize=(14, total_rows * 4),
            facecolor='white'
        )
        fig.subplots_adjust(hspace=0.5, wspace=0.4)

        # Asegurar que axes sea 2D
        if total_rows == 1:
            axes = axes.reshape(1, -1)
        elif ncols == 1:
            axes = axes.reshape(-1, 1)

        # ── Grafica general (ocupa las 3 columnas de la fila 0) ──
        for j in range(ncols):
            axes[0, j].axis('off')

        ax_gen = fig.add_subplot(total_rows, 1, 1)
        ax_gen.set_position([0.15, 1 - 1.0 / total_rows + 0.02, 0.45, 0.9 / total_rows])

        labels_gen = list(conteo_general.keys())
        sizes_gen = list(conteo_general.values())
        colors_gen = [COLORES_CULTIVO.get(l, '#A0AEC0') for l in labels_gen]

        wedges, _, autotexts = ax_gen.pie(
            sizes_gen, labels=None, autopct='%1.1f%%',
            colors=colors_gen, startangle=90,
            pctdistance=0.82, textprops={'fontsize': 7})
        for at in autotexts:
            at.set_fontsize(7)
            at.set_color('#333')

        ax_gen.set_title('Distribucion General de Cultivos', fontsize=13,
                          fontweight='bold', pad=12, color='#1a202c')

        legend_labels = [f'{l}  ({s})' for l, s in zip(labels_gen, sizes_gen)]
        ax_gen.legend(wedges, legend_labels, loc='center left',
                       bbox_to_anchor=(1.0, 0.5), fontsize=8, frameon=False)

        # ── Graficas por barrio ──
        for idx, barrio in enumerate(barrios):
            r = 1 + idx // ncols
            col = idx % ncols
            ax_b = axes[r, col]

            conteo = conteo_barrio[barrio]
            if not conteo:
                ax_b.text(0.5, 0.5, 'Sin datos', ha='center', va='center',
                          fontsize=9, color='#718096', transform=ax_b.transAxes)
                ax_b.set_title(barrio, fontsize=10, fontweight='bold', color='#1a202c')
                ax_b.axis('off')
                continue

            labels_b = list(conteo.keys())
            sizes_b = list(conteo.values())
            colors_b = [COLORES_CULTIVO.get(l, '#A0AEC0') for l in labels_b]

            wedges_b, _, autotexts_b = ax_b.pie(
                sizes_b, labels=None, autopct='%1.0f%%',
                colors=colors_b, startangle=90,
                pctdistance=0.78, textprops={'fontsize': 6})
            for at in autotexts_b:
                at.set_fontsize(6)
                at.set_color('#333')

            ax_b.set_title(f'{barrio}  ({sum(sizes_b)} parcelas)', fontsize=10,
                            fontweight='bold', color='#1a202c', pad=8)

        # Ocultar ejes sobrantes
        for idx in range(n_barrios, nrows_barrio * ncols):
            r = 1 + idx // ncols
            col = idx % ncols
            if r < total_rows and col < ncols:
                axes[r, col].axis('off')

        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=180, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
        plt.close(fig)
        buf.seek(0)
        return buf
