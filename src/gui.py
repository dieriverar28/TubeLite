"""
GUI de TubeLite usando GTK3 - v0.2
Búsqueda real en YouTube con reproducción en mpv
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GdkPixbuf, GLib
from threading import Thread
import time

from youtube import YouTubeSearcher
from player import Player


class TubeLiteWindow(Gtk.Window):
    """Ventana principal de TubeLite v0.2"""
    
    def __init__(self):
        super().__init__(title="TubeLite")
        
        # Configuración de la ventana
        self.set_default_size(800, 600)
        self.set_border_width(10)
        self.set_position(Gtk.WindowPosition.CENTER)
        
        # Conectar el evento de cerrar
        self.connect("destroy", self.on_destroy)
        
        # Inicializar buscador
        self.searcher = YouTubeSearcher()
        self.is_searching = False
        
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
        self.search_entry.set_placeholder_text("Ej: Linux tutorial, Python...")
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
        
        # Placeholder inicial
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
        
        if self.is_searching:
            self.status_label.set_text("Ya hay una búsqueda en progreso...")
            return
        
        # Limpiar resultados anteriores
        self.clear_results()
        self.status_label.set_text(f"Buscando: {query}...")
        self.search_button.set_sensitive(False)
        self.search_entry.set_sensitive(False)
        self.is_searching = True
        
        # Buscar en un thread para no bloquear la UI
        thread = Thread(target=self._search_in_background, args=(query,))
        thread.daemon = True
        thread.start()
    
    def _search_in_background(self, query: str):
        """Buscar en background sin bloquear la UI"""
        try:
            # Buscar videos
            results = self.searcher.search(query, max_results=15)
            
            # Actualizar UI desde el hilo principal
            GLib.idle_add(self._display_results, results)
        
        except Exception as e:
            print(f"Error en búsqueda: {e}")
            GLib.idle_add(self._search_error, str(e))
    
    def _display_results(self, results):
        """Mostrar resultados en la UI"""
        if not results:
            self.status_label.set_text("No se encontraron resultados")
            self.search_button.set_sensitive(True)
            self.search_entry.set_sensitive(True)
            self.is_searching = False
            return
        
        # Agregar cada resultado
        for video in results:
            self._add_result_row(video)
        
        # Actualizar estado
        self.status_label.set_text(f"Se encontraron {len(results)} resultados. Doble clic para reproducir.")
        self.search_button.set_sensitive(True)
        self.search_entry.set_sensitive(True)
        self.is_searching = False
        
        self.results_list.show_all()
    
    def _add_result_row(self, video: dict):
        """Agregar una fila de resultado"""
        row = Gtk.ListBoxRow()
        
        # Contenedor principal
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        vbox.set_margin_top(8)
        vbox.set_margin_bottom(8)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)
        
        # Primera línea: Título + Duración
        hbox_top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        # Título
        title_label = Gtk.Label(label=video["title"])
        title_label.set_halign(Gtk.Align.START)
        title_label.set_line_wrap(True)
        title_label.set_max_width_chars(60)
        hbox_top.pack_start(title_label, True, True, 0)
        
        # Duración
        duration_str = self.searcher.format_duration(video["duration"])
        duration_label = Gtk.Label(label=duration_str)
        duration_label.set_halign(Gtk.Align.END)
        hbox_top.pack_end(duration_label, False, False, 0)
        
        vbox.pack_start(hbox_top, False, False, 0)
        
        # Segunda línea: Canal + Visualizaciones
        hbox_bottom = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        # Canal
        uploader_label = Gtk.Label(label=video["uploader"])
        uploader_label.set_halign(Gtk.Align.START)
        uploader_label.set_opacity(0.7)
        uploader_label.set_markup(f"<small>{video['uploader']}</small>")
        hbox_bottom.pack_start(uploader_label, True, True, 0)
        
        # Visualizaciones
        views_str = self.searcher.format_views(video["view_count"])
        views_label = Gtk.Label(label=views_str)
        views_label.set_halign(Gtk.Align.END)
        views_label.set_opacity(0.7)
        views_label.set_markup(f"<small>{views_str} vistas</small>")
        hbox_bottom.pack_end(views_label, False, False, 0)
        
        vbox.pack_start(hbox_bottom, False, False, 0)
        
        # Guardar datos del video en el row
        row.video_url = video["url"]
        row.video_id = video["id"]
        row.video_title = video["title"]
        
        row.add(vbox)
        self.results_list.add(row)
    
    def on_row_activated(self, listbox, row):
        """Callback cuando se hace doble clic en un resultado"""
        if hasattr(row, 'video_url'):
            # Actualizar estado
            self.status_label.set_text(f"▶ Reproduciendo: {row.video_title}...")
            
            # Reproducir en thread para no bloquear UI
            thread = Thread(
                target=Player.play, 
                args=(row.video_url, row.video_title),
                daemon=True
            )
            thread.start()
    
    def clear_results(self):
        """Limpiar la lista de resultados"""
        for row in self.results_list.get_children():
            row.destroy()
    
    def on_destroy(self, widget):
        """Callback al cerrar la ventana"""
        Gtk.main_quit()