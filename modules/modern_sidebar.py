# modules/modern_sidebar.py
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import os
from modules.utils import resource_path


class ModernSidebar:
    COLORS = {
        'sidebar_bg': '#2c3e50',        # Azul oscuro elegante
        'sidebar_hover': '#34495e',     # Azul oscuro más claro para hover
        'sidebar_active': '#3498db',    # Azul brillante para botón activo
        'text': '#ecf0f1',              # Blanco suave
        'text_active': '#ffffff',       # Blanco puro para texto activo
        'border': '#1a252f',            # Borde más oscuro
        'accent': '#27ae60'             # Verde para acentos
    }
    
    def __init__(self, parent, callbacks=None):
        self.parent = parent
        self.callbacks = callbacks or {}
        self.active_button = None
        self.buttons = {}
        
        # Frame principal del sidebar
        self.frame = tk.Frame(parent, bg=self.COLORS['sidebar_bg'], width=220)
        self.frame.pack(side=tk.LEFT, fill=tk.Y)
        self.frame.pack_propagate(False)  # Mantener ancho fijo
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Crea todos los widgets del sidebar"""
        
        # Logo en la parte superior
        self._create_logo_section()
        
        # Separador
        separator = tk.Frame(self.frame, bg=self.COLORS['border'], height=2)
        separator.pack(fill=tk.X, padx=10, pady=15)
        
        # Botones de navegación
        self._create_navigation_buttons()
        
        # Espaciador inferior
        tk.Frame(self.frame, bg=self.COLORS['sidebar_bg']).pack(fill=tk.BOTH, expand=True)
    
    def _create_logo_section(self):
        """Crea la sección del logo en la parte superior"""
        logo_frame = tk.Frame(self.frame, bg=self.COLORS['sidebar_bg'])
        logo_frame.pack(fill=tk.X, pady=20, padx=10)
        
        # Intentar cargar el logo
        logo_path = resource_path(os.path.join('assets', 'zapata.png'))
        
        if os.path.exists(logo_path):
            try:
                # Cargar y redimensionar logo
                img = Image.open(logo_path)
                
                # Calcular nuevo tamaño manteniendo aspect ratio
                max_width = 180
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                
                img_resized = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                self.logo_photo = ImageTk.PhotoImage(img_resized)
                
                # Mostrar logo
                logo_label = tk.Label(logo_frame, image=self.logo_photo, 
                                     bg=self.COLORS['sidebar_bg'])
                logo_label.pack()
                
            except Exception as e:
                print(f"Error al cargar logo: {e}")
                self._create_text_logo(logo_frame)
        else:
            self._create_text_logo(logo_frame)
    
    def _create_text_logo(self, parent):
        """Crea un logo de texto si no se puede cargar la imagen"""
        tk.Label(parent, text="SISTEMA\nRIEGO", 
                font=('Segoe UI', 16, 'bold'),
                bg=self.COLORS['sidebar_bg'],
                fg=self.COLORS['text'],
                justify=tk.CENTER).pack()
    
    def _create_navigation_buttons(self):
        """Crea todos los botones de navegación"""
        
        # Definición de botones: (id, svg_filename, texto)
        nav_buttons = [
            ('cuota', 'cuota.svg', 'Cuota'),
            ('detalle', 'detalle.svg', 'Detalle'),
            ('editar_lote', 'editarlote.svg', 'Editar Lote'),
            ('reporte', 'reporte.svg', 'Reporte'),
            ('ciclo', 'ciclo.svg', 'Ciclo'),
            ('config', 'config.svg', 'Config'),
            ('backup', 'backup.svg', 'Backup'),
            ('estadisticas', 'estadisticas.svg', 'Estadísticas'),
            ('mapa', 'mapa.svg', 'Mapa'),
            ('admin', 'admin.svg', 'Admin')
        ]
        
        # Frame contenedor para botones
        buttons_frame = tk.Frame(self.frame, bg=self.COLORS['sidebar_bg'])
        buttons_frame.pack(fill=tk.X, padx=5)
        
        # Diccionario para almacenar PhotoImage y evitar garbage collection
        self.button_icons = {}
        
        for btn_id, svg_file, text in nav_buttons:
            self._create_nav_button(buttons_frame, btn_id, svg_file, text)
    
    def _create_nav_button(self, parent, btn_id, svg_file, text):
        """
        Crea un botón de navegación con iconos SVG y efectos hover.
        
        Args:
            parent: Widget padre
            btn_id: ID del botón
            svg_file: Nombre del archivo SVG
            text: Texto del botón
        """
        # Frame para el botón (permite mejor control del hover)
        btn_frame = tk.Frame(parent, bg=self.COLORS['sidebar_bg'])
        btn_frame.pack(fill=tk.X, pady=3, padx=5)
        
        # Cargar el icono PNG
        icon_label = None
        png_filename = svg_file.replace('.svg', '.png')
        png_path = resource_path(os.path.join('assets', png_filename))
        
        if os.path.exists(png_path):
            try:
                # Cargar PNG directamente con PIL
                img = Image.open(png_path)
                img = img.resize((24, 24), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                
                # Guardar referencia
                self.button_icons[btn_id] = photo
                
                # Crear label con icono
                icon_label = tk.Label(
                    btn_frame,
                    image=photo,
                    bg=self.COLORS['sidebar_bg'],
                    cursor='hand2'
                )
                icon_label.pack(side=tk.LEFT, padx=(15, 8))
                
            except Exception as e:
                print(f"Error loading icon {png_filename}: {e}")
                icon_label = None
        
        # Label para el texto del botón
        if icon_label is None:
            # Fallback: usar emoji si no se pudo cargar el SVG
            emoji_map = {
                'cuota': '💰',
                'detalle': '📋',
                'editar_lote': '✏️',
                'reporte': '📊',
                'ciclo': '🔄',
                'config': '⚙️',
                'backup': '💾',
                'estadisticas': '📊',
                'mapa': '🗺️',
                'admin': '🔧'
            }
            text_display = f"  {emoji_map.get(btn_id, '•')}  {text}"
            padx_text = 15
        else:
            text_display = text
            padx_text = 0
        
        btn_label = tk.Label(
            btn_frame,
            text=text_display,
            font=('Segoe UI', 11),
            bg=self.COLORS['sidebar_bg'],
            fg=self.COLORS['text'],
            anchor='w',
            cursor='hand2',
            padx=padx_text,
            pady=12
        )
        btn_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Guardar referencia tanto del frame como del label (y del icon si existe)
        if icon_label:
            self.buttons[btn_id] = (btn_label, btn_frame, icon_label)
        else:
            self.buttons[btn_id] = (btn_label, btn_frame)
        
        # Bind eventos al label
        btn_label.bind('<Enter>', lambda e: self._on_hover(btn_id))
        btn_label.bind('<Leave>', lambda e: self._on_leave(btn_id))
        btn_label.bind('<Button-1>', lambda e: self._on_click(btn_id))
        
        # Bind eventos al icon si existe
        if icon_label:
            icon_label.bind('<Enter>', lambda e: self._on_hover(btn_id))
            icon_label.bind('<Leave>', lambda e: self._on_leave(btn_id))
            icon_label.bind('<Button-1>', lambda e: self._on_click(btn_id))
        
        # Bind eventos al frame también para mejor UX
        btn_frame.bind('<Enter>', lambda e: self._on_hover(btn_id))
        btn_frame.bind('<Leave>', lambda e: self._on_leave(btn_id))
        btn_frame.bind('<Button-1>', lambda e: self._on_click(btn_id))
    
    def _on_hover(self, btn_id):
        """Efecto hover - cambiar color de fondo"""
        if self.active_button != btn_id and btn_id in self.buttons:
            btn_data = self.buttons[btn_id]
            label, frame = btn_data[0], btn_data[1]
            label.configure(bg=self.COLORS['sidebar_hover'])
            frame.configure(bg=self.COLORS['sidebar_hover'])
            # Si hay icono, también cambiar su fondo
            if len(btn_data) == 3:
                btn_data[2].configure(bg=self.COLORS['sidebar_hover'])
    
    def _on_leave(self, btn_id):
        """Restaurar color al salir del hover"""
        if self.active_button != btn_id and btn_id in self.buttons:
            btn_data = self.buttons[btn_id]
            label, frame = btn_data[0], btn_data[1]
            label.configure(bg=self.COLORS['sidebar_bg'])
            frame.configure(bg=self.COLORS['sidebar_bg'])
            # Si hay icono, también restaurar su fondo
            if len(btn_data) == 3:
                btn_data[2].configure(bg=self.COLORS['sidebar_bg'])
    
    def _on_click(self, btn_id):
        """Manejar click en botón"""
        # Actualizar botón activo
        self.set_active(btn_id)
        
        # Ejecutar callback si existe
        if btn_id in self.callbacks:
            self.callbacks[btn_id]()
    
    def set_active(self, btn_id):
        """
        Establece un botón como activo.
        
        Args:
            btn_id: ID del botón a activar
        """
        # Restaurar botón anterior
        if self.active_button and self.active_button in self.buttons:
            btn_data = self.buttons[self.active_button]
            label, frame = btn_data[0], btn_data[1]
            label.configure(
                bg=self.COLORS['sidebar_bg'],
                fg=self.COLORS['text']
            )
            frame.configure(bg=self.COLORS['sidebar_bg'])
            # Si hay icono, también restaurar su fondo
            if len(btn_data) == 3:
                btn_data[2].configure(bg=self.COLORS['sidebar_bg'])
        
        # Activar nuevo botón
        if btn_id in self.buttons:
            btn_data = self.buttons[btn_id]
            label, frame = btn_data[0], btn_data[1]
            label.configure(
                bg=self.COLORS['sidebar_active'],
                fg=self.COLORS['text_active']
            )
            frame.configure(bg=self.COLORS['sidebar_active'])
            # Si hay icono, también cambiar su fondo
            if len(btn_data) == 3:
                btn_data[2].configure(bg=self.COLORS['sidebar_active'])
            self.active_button = btn_id
    
    def get_frame(self):
        """Retorna el frame del sidebar"""
        return self.frame
