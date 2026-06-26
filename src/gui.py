"""
GUI de TubeLite usando GTK3
Diseñado para ser ligero en hardware antiguo (AMD E-350)
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GdkPixbuf


class TubeLiteWindow(Gtk.Window):
    """Ventana principal de TubeLite"""
    
    def __init__(self):
        super().__init__(title="TubeLite")
        
        # Configuración de la ventana
        self.set_default_size(800, 600)
        self.set_border_width(10)
        self.set_position(Gtk.WindowPosition.CENTER)
        
        # Conectar el evento de cerrar
        self.connect("destroy", self.on_destroy)
        
        # Crear la interfaz
        self._build_ui()
    
    def _build_ui(self):
        """Construir la interfaz gráfica"""
        
        # Contenedor principal (vertical)
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.add(main_box)
        
        # ========== SECCIÓN DE BÚSQUEDA ==========
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        main_box.pack_start(search_box, False, False, 0)
        
        # Label
        search_label = Gtk.Label(label="Buscar:")
        search_box.pack_start(search_label, False, False, 0)
        
        # Input de búsqueda
        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text("Ej: Linux tutorial...")
        self.search_entry.set_hexpand(True)
        # Conectar Enter para buscar
        self.search_entry.connect("activate", self.on_search_clicked)
        search_box.pack_start(self.search_entry, True, True, 0)
        
        # Botón Buscar
        self.search_button = Gtk.Button(label="Buscar")
        self.search_button.set_size_request(100, -1)
        self.search_button.connect("clicked", self.on_search_clicked)
        search_box.pack_start(self.search_button, False, False, 0)
        
        # ========== LISTA DE RESULTADOS ==========
        # ScrolledWindow para la lista
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        main_box.pack_start(scrolled, True, True, 0)
        
        # ListBox para los resultados
        self.results_list = Gtk.ListBox()
        self.results_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.results_list.connect("row-activated", self.on_row_activated)
        scrolled.add(self.results_list)
        
        # Placeholder inicial (cuando no hay resultados)
        placeholder_label = Gtk.Label(
            label="Ingresa un término de búsqueda y presiona Buscar"
        )
        placeholder_label.set_markup(
            "<i>Ingresa un término de búsqueda y presiona Buscar</i>"
        )
        placeholder_label.set_opacity(0.6)
        self.results_list.set_placeholder(placeholder_label)
        
        # ========== BARRA DE ESTADO ==========
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        main_box.pack_end(status_box, False, False, 0)
        
        self.status_label = Gtk.Label(label="Listo")
        self.status_label.set_halign(Gtk.Align.START)
        status_box.pack_start(self.status_label, True, True, 0)
        
        # Mostrar todo
        self.show_all()
    
    def on_search_clicked(self, widget):
        """Callback cuando se presiona Buscar"""
        query = self.search_entry.get_text().strip()
        
        if not query:
            self.status_label.set_text("Ingresa un término de búsqueda")
            return
        
        # Por ahora solo mostramos un mensaje
        self.status_label.set_text(f"Buscando: {query}...")
        self.clear_results()
        
        # Placeholder de resultado (v0.2 implementará búsqueda real)
        self._add_placeholder_result(query)
    
    def on_row_activated(self, listbox, row):
        """Callback cuando se hace doble clic en un resultado"""
        if row:
            self.status_label.set_text(f"Seleccionaste: {row.get_index()}")
    
    def _add_placeholder_result(self, query):
        """Agregar un resultado de prueba (será reemplazado en v0.2)"""
        row = Gtk.ListBoxRow()
        
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        hbox.set_margin_top(8)
        hbox.set_margin_bottom(8)
        hbox.set_margin_start(10)
        hbox.set_margin_end(10)
        
        # Título
        title_label = Gtk.Label(
            label=f"Resultado para: {query}"
        )
        title_label.set_halign(Gtk.Align.START)
        title_label.set_line_wrap(True)
        hbox.pack_start(title_label, True, True, 0)
        
        # Duración
        duration_label = Gtk.Label(label="--:--")
        duration_label.set_halign(Gtk.Align.END)
        hbox.pack_end(duration_label, False, False, 0)
        
        row.add(hbox)
        self.results_list.add(row)
        self.results_list.show_all()
    
    def clear_results(self):
        """Limpiar la lista de resultados"""
        for row in self.results_list.get_children():
            row.destroy()
    
    def on_destroy(self, widget):
        """Callback al cerrar la ventana"""
        Gtk.main_quit()