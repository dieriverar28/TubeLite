"""
GUI de TubeLite usando GTK3 - v0.4
Busqueda en dos fases (rapida + enriquecido progresivo) y reproduccion con mpv
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib
from threading import Thread

from youtube import YouTubeSearcher
from player import Player


class TubeLiteWindow(Gtk.Window):
    """Ventana principal de NitroxxxTubeLite v0.4"""

    def __init__(self):
        super().__init__(title="NitroxxxTubeLite")

        # Configuracion de la ventana
        self.set_default_size(800, 600)
        self.set_border_width(10)
        self.set_position(Gtk.WindowPosition.CENTER)

        # Conectar el evento de cerrar
        self.connect("destroy", self.on_destroy)

        # Inicializar buscador
        self.searcher = YouTubeSearcher()
        self.is_searching = False

        # Guardamos referencias a las filas por id de video para poder
        # actualizarlas en vivo cuando llega la info completa (duracion/vistas)
        self.row_by_id = {}

        # Contador de busqueda: si el usuario lanza una busqueda nueva
        # mientras la anterior todavia esta enriqueciendo resultados en
        # background, usamos esto para ignorar actualizaciones "viejas"
        self._search_token = 0

        # Crear la interfaz
        self._build_ui()

    def _build_ui(self):
        """Construir la interfaz grafica"""

        # Contenedor principal (vertical)
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.add(main_box)

        # ========== SECCION DE BUSQUEDA ==========
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        main_box.pack_start(search_box, False, False, 0)

        # Label
        search_label = Gtk.Label(label="Buscar:")
        search_box.pack_start(search_label, False, False, 0)

        # Input de busqueda
        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text("Ej: Linux tutorial, Python...")
        self.search_entry.set_hexpand(True)
        # Conectar Enter para buscar
        self.search_entry.connect("activate", self.on_search_clicked)
        # Escape limpia el campo de busqueda
        self.search_entry.connect("key-press-event", self._on_search_key_press)
        search_box.pack_start(self.search_entry, True, True, 0)

        # Spinner (se muestra solo mientras busca)
        self.spinner = Gtk.Spinner()
        search_box.pack_start(self.spinner, False, False, 0)

        # Boton Buscar
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
        placeholder_label = Gtk.Label()
        placeholder_label.set_markup(
            "<i>Ingresa un termino de busqueda y presiona Buscar</i>"
        )
        placeholder_label.set_opacity(0.6)
        placeholder_label.show()
        self.results_list.set_placeholder(placeholder_label)

        # ========== BARRA DE ESTADO ==========
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        main_box.pack_end(status_box, False, False, 0)

        self.status_label = Gtk.Label(label="Listo")
        self.status_label.set_halign(Gtk.Align.START)
        status_box.pack_start(self.status_label, True, True, 0)

        # Mostrar todo
        self.show_all()
        self.spinner.hide()

    def _on_search_key_press(self, widget, event):
        """Escape limpia el campo de busqueda"""
        from gi.repository import Gdk
        if event.keyval == Gdk.KEY_Escape:
            self.search_entry.set_text("")
        return False

    def on_search_clicked(self, widget):
        """Callback cuando se presiona Buscar / Enter"""
        query = self.search_entry.get_text().strip()

        if not query:
            self.status_label.set_text("Ingresa un termino de busqueda")
            return

        if self.is_searching:
            self.status_label.set_text("Ya hay una busqueda en progreso...")
            return

        # Invalidar cualquier actualizacion pendiente de una busqueda anterior
        self._search_token += 1
        my_token = self._search_token

        # Limpiar resultados anteriores
        self.clear_results()
        self.status_label.set_text(f"Buscando: {query}...")
        self.search_button.set_sensitive(False)
        self.search_entry.set_sensitive(False)
        self.is_searching = True
        self.spinner.show()
        self.spinner.start()

        # Buscar en un thread para no bloquear la UI
        thread = Thread(target=self._search_in_background, args=(query, my_token))
        thread.daemon = True
        thread.start()

    def _search_in_background(self, query: str, token: int):
        """
        Fase 1: busqueda rapida (--flat-playlist). Apenas llega, se muestra
        en la UI. Fase 2: enriquecido en paralelo, actualiza filas de a una.
        """
        try:
            results = self.searcher.search_fast(query, max_results=15)
            GLib.idle_add(self._display_results, results, token)

            if not results:
                return

            # Fase 2: completar duracion/vistas que falten, en paralelo,
            # actualizando la UI a medida que cada video esta listo
            self.searcher.enrich_all(
                results,
                on_video_ready=lambda video: GLib.idle_add(
                    self._update_row, video, token
                ),
                max_workers=4,
            )
            GLib.idle_add(self._search_fully_done, token)

        except Exception as e:
            print(f"Error en busqueda: {e}")
            GLib.idle_add(self._search_error, str(e), token)

    def _display_results(self, results, token: int):
        """Mostrar la lista basica de resultados (fase rapida)"""
        if token != self._search_token:
            return False  # busqueda vieja, ignorar

        if not results:
            self.status_label.set_text("No se encontraron resultados")
            self._finish_searching()
            return False

        self.row_by_id = {}
        for video in results:
            self._add_result_row(video)

        self.status_label.set_text(
            f"{len(results)} resultados. Completando detalles..."
        )
        self.results_list.show_all()
        # OJO: is_searching se mantiene True hasta que termine el
        # enriquecido, pero ya se puede reproducir con doble clic
        self.search_button.set_sensitive(True)
        self.search_entry.set_sensitive(True)
        return False

    def _update_row(self, video: dict, token: int):
        """Actualizar UNA fila con duracion/vistas ya resueltas (streaming)"""
        if token != self._search_token:
            return False

        row = self.row_by_id.get(video.get("id"))
        if not row:
            return False

        duration_str = self.searcher.format_duration(video.get("duration", 0))
        views_str = self.searcher.format_views(video.get("view_count", 0))

        row.duration_label.set_text(duration_str)
        row.views_label.set_markup(f"<small>{views_str} vistas</small>")
        return False

    def _search_fully_done(self, token: int):
        if token != self._search_token:
            return False
        self.status_label.set_text("Listo. Doble clic para reproducir.")
        self._finish_searching()
        return False

    def _search_error(self, error: str, token: int):
        if token != self._search_token:
            return False
        self.status_label.set_text(f"Error en la busqueda: {error}")
        self._finish_searching()
        return False

    def _finish_searching(self):
        self.is_searching = False
        self.search_button.set_sensitive(True)
        self.search_entry.set_sensitive(True)
        self.spinner.stop()
        self.spinner.hide()

    def _add_result_row(self, video: dict):
        """Agregar una fila de resultado (con placeholders si falta info)"""
        row = Gtk.ListBoxRow()

        # Contenedor principal
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        vbox.set_margin_top(8)
        vbox.set_margin_bottom(8)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)

        # Primera linea: Titulo + Duracion
        hbox_top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        # Titulo
        title_label = Gtk.Label(label=video["title"])
        title_label.set_halign(Gtk.Align.START)
        title_label.set_line_wrap(True)
        title_label.set_max_width_chars(60)
        hbox_top.pack_start(title_label, True, True, 0)

        # Duracion (placeholder si todavia no llega)
        duration_str = self.searcher.format_duration(video.get("duration", 0))
        duration_label = Gtk.Label(label=duration_str)
        duration_label.set_halign(Gtk.Align.END)
        hbox_top.pack_end(duration_label, False, False, 0)

        vbox.pack_start(hbox_top, False, False, 0)

        # Segunda linea: Canal + Visualizaciones
        hbox_bottom = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        # Canal
        uploader_label = Gtk.Label()
        uploader_label.set_halign(Gtk.Align.START)
        uploader_label.set_markup(f"<small>{GLib.markup_escape_text(video['uploader'])}</small>")
        hbox_bottom.pack_start(uploader_label, True, True, 0)

        # Visualizaciones (placeholder si todavia no llega)
        views_str = self.searcher.format_views(video.get("view_count", 0))
        views_label = Gtk.Label()
        views_label.set_halign(Gtk.Align.END)
        views_label.set_markup(f"<small>{views_str} vistas</small>")
        hbox_bottom.pack_end(views_label, False, False, 0)

        vbox.pack_start(hbox_bottom, False, False, 0)

        # Guardar datos del video en el row
        row.video_url = video["url"]
        row.video_id = video["id"]
        row.video_title = video["title"]
        row.duration_label = duration_label
        row.views_label = views_label

        row.add(vbox)
        self.results_list.add(row)

        if video.get("id"):
            self.row_by_id[video["id"]] = row

    def on_row_activated(self, listbox, row):
        """Callback cuando se hace doble clic (o Enter) en un resultado"""
        if hasattr(row, "video_url") and row.video_url:
            # Actualizar estado
            self.status_label.set_text(f"Reproduciendo: {row.video_title}...")

            # Reproducir en thread para no bloquear UI
            thread = Thread(
                target=Player.play,
                args=(row.video_url, row.video_title),
                daemon=True,
            )
            thread.start()

    def clear_results(self):
        """Limpiar la lista de resultados"""
        for row in self.results_list.get_children():
            row.destroy()
        self.row_by_id = {}

    def on_destroy(self, widget):
        """Callback al cerrar la ventana"""
        Gtk.main_quit()