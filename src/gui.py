"""
GUI de NitroxxxTubeLite usando GTK3 - v0.4
Busqueda en dos fases (rapida + enriquecido progresivo) y reproduccion con mpv
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk
from threading import Thread

from youtube import YouTubeSearcher
from player import Player
from history import SearchHistory
from thumbnails import ThumbnailLoader, THUMB_WIDTH, THUMB_HEIGHT
from favorites import get_favorites


class NitroxxxTubeLiteWindow(Gtk.Window):
    """Ventana principal de NitroxxxTubeLite v0.4"""

    RESULTS_PER_PAGE = 15  # cuantos resultados se piden por tanda (busqueda inicial y cada "cargar mas")

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

        # Historial de busquedas recientes (persistido en disco)
        self.history = SearchHistory()

        # Favoritos: videos guardados para reproducir directo, sin
        # tener que volver a buscarlos (persistido en disco)
        self.favorites = get_favorites()

        # Cargador de miniaturas (descarga en segundo plano y cachea en disco)
        self.thumbnail_loader = ThumbnailLoader()

        # Preferencias del usuario (calidad, volumen, tema, tamano de fuente)
        self.settings = get_settings()

        # Un solo CssProvider reutilizado: para cambiar el tema o el
        # tamano de fuente en caliente, alcanza con recargar su
        # contenido en vez de crear uno nuevo cada vez
        self._css_provider = Gtk.CssProvider()
        screen = Gdk.Screen.get_default()
        if screen:
            Gtk.StyleContext.add_provider_for_screen(
                screen, self._css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

        # Guardamos referencias a las filas por id de video para poder
        # actualizarlas en vivo cuando llega la info completa (duracion/vistas)
        self.row_by_id = {}

        # Contador de busqueda: si el usuario lanza una busqueda nueva
        # mientras la anterior todavia esta enriqueciendo resultados en
        # background, usamos esto para ignorar actualizaciones "viejas"
        self._search_token = 0

        # ---- Estado para la carga infinita (mas resultados al bajar) ----
        self._current_query = None     # busqueda activa (para saber que pedir al hacer scroll)
        self._next_start = 1           # proximo indice a pedir cuando se pida "mas"
        self._loading_more = False     # ya hay un pedido de "mas resultados" en curso
        self._no_more_results = False  # la busqueda actual ya no tiene mas resultados
        # Si la reproduccion automatica llega al final de los
        # resultados cargados y todavia hay mas por pedir, se guarda
        # aca en que indice de la lista debe seguir reproduciendo
        # apenas terminen de cargar
        self._autoplay_after_more_index = None

        # Crear la interfaz
        self._build_ui()

        # Aplicar el tema oscuro y el tamano de fuente guardados
        self._apply_theme_and_font()

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

        # Boton Favoritos: muestra los videos guardados en un menu
        self.favorites_button = Gtk.MenuButton(label="Favoritos")
        self.favorites_button.set_popover(self._build_favorites_popover())
        search_box.pack_start(self.favorites_button, False, False, 0)

        # Input de busqueda
        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text("Ej: Linux tutorial, Python...")
        self.search_entry.set_hexpand(True)
        # Conectar Enter para buscar
        self.search_entry.connect("activate", self.on_search_clicked)
        # Escape limpia el campo de busqueda
        self.search_entry.connect("key-press-event", self._on_search_key_press)
        search_box.pack_start(self.search_entry, True, True, 0)

        # Autocompletado nativo con el historial de busquedas: a medida
        # que escribes, GTK sugiere coincidencias de busquedas anteriores
        self.completion_store = Gtk.ListStore(str)
        completion = Gtk.EntryCompletion()
        completion.set_model(self.completion_store)
        completion.set_text_column(0)
        completion.set_minimum_key_length(1)
        completion.set_inline_completion(False)
        self.search_entry.set_completion(completion)
        self._refresh_completion()

        # Spinner (se muestra solo mientras busca)
        self.spinner = Gtk.Spinner()
        search_box.pack_start(self.spinner, False, False, 0)

        # Boton Buscar
        self.search_button = Gtk.Button(label="Buscar")
        self.search_button.set_size_request(100, -1)
        self.search_button.connect("clicked", self.on_search_clicked)
        search_box.pack_start(self.search_button, False, False, 0)

        # Boton Historial: muestra las busquedas recientes en un menu
        self.history_button = Gtk.MenuButton(label="Historial")
        self.history_button.set_popover(self._build_history_popover())
        search_box.pack_start(self.history_button, False, False, 0)

        # Boton Configuracion: abre la pantalla de preferencias
        self.settings_button = Gtk.Button(label="Configuración")
        self.settings_button.connect("clicked", self._on_settings_clicked)
        search_box.pack_start(self.settings_button, False, False, 0)

        # ========== LISTA DE RESULTADOS ==========
        # ScrolledWindow para la lista
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        main_box.pack_start(scrolled, True, True, 0)
        self.scrolled = scrolled

        # Detectar cuando se llega cerca del final de la lista, para
        # cargar mas resultados automaticamente (carga infinita)
        scrolled.get_vadjustment().connect("value-changed", self._on_scroll_changed)

        # ListBox para los resultados
        self.results_list = Gtk.ListBox()
        self.results_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.results_list.connect("row-activated", self.on_row_activated)
        self.results_list.connect("key-press-event", self._on_results_key_press)
        scrolled.add(self.results_list)

        # Placeholder inicial
        placeholder_label = Gtk.Label()
        placeholder_label.set_markup(
            "<i>Ingresa un termino de busqueda y presiona Buscar "
            "(o flecha abajo + Enter para navegar con el teclado)</i>"
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

    def _apply_theme_and_font(self):
        """Aplicar el tema oscuro y el tamano de fuente guardados en
        Settings. Como reutilizamos el mismo CssProvider, alcanza con
        recargar su contenido para que el cambio se vea al instante."""
        gtk_settings = Gtk.Settings.get_default()
        if gtk_settings:
            gtk_settings.set_property(
                "gtk-application-prefer-dark-theme",
                bool(self.settings.get("dark_theme")),
            )

        font_size = self.settings.get("font_size")
        css = f"* {{ font-size: {font_size}pt; }}".encode("utf-8")
        try:
            self._css_provider.load_from_data(css)
        except GLib.Error as e:
            print(f"No se pudo aplicar el tamano de fuente: {e}")

    def _on_settings_clicked(self, widget):
        """Abrir la pantalla de Configuracion (calidad, volumen, tema, fuente)."""
        dialog = Gtk.Dialog(title="Configuración", transient_for=self, modal=True)
        dialog.add_buttons(
            "Restaurar valores por defecto", Gtk.ResponseType.REJECT,
            "Cancelar", Gtk.ResponseType.CANCEL,
            "Guardar", Gtk.ResponseType.OK,
        )
        dialog.set_default_response(Gtk.ResponseType.OK)

        content = dialog.get_content_area()
        content.set_spacing(10)
        content.set_border_width(12)

        grid = Gtk.Grid(row_spacing=12, column_spacing=12)
        content.add(grid)

        # Calidad de video
        quality_label = Gtk.Label(label="Calidad de video:")
        quality_label.set_halign(Gtk.Align.START)
        grid.attach(quality_label, 0, 0, 1, 1)

        quality_combo = Gtk.ComboBoxText()
        for option in QUALITY_OPTIONS:
            display = "Automática (según el hardware)" if option == "auto" else f"{option}p"
            quality_combo.append(option, display)
        quality_combo.set_active_id(self.settings.get("quality"))
        grid.attach(quality_combo, 1, 0, 1, 1)

        # Volumen
        volume_label = Gtk.Label(label="Volumen:")
        volume_label.set_halign(Gtk.Align.START)
        grid.attach(volume_label, 0, 1, 1, 1)

        volume_adj = Gtk.Adjustment(
            value=self.settings.get("volume"), lower=0, upper=150, step_increment=5
        )
        volume_scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=volume_adj)
        volume_scale.set_digits(0)
        volume_scale.set_hexpand(True)
        volume_scale.set_value_pos(Gtk.PositionType.RIGHT)
        grid.attach(volume_scale, 1, 1, 1, 1)

        # Tema oscuro
        theme_label = Gtk.Label(label="Tema oscuro:")
        theme_label.set_halign(Gtk.Align.START)
        grid.attach(theme_label, 0, 2, 1, 1)

        theme_switch = Gtk.Switch()
        theme_switch.set_active(bool(self.settings.get("dark_theme")))
        theme_switch.set_halign(Gtk.Align.START)
        grid.attach(theme_switch, 1, 2, 1, 1)

        # Tamano de fuente
        font_label = Gtk.Label(label="Tamaño de fuente:")
        font_label.set_halign(Gtk.Align.START)
        grid.attach(font_label, 0, 3, 1, 1)

        font_adj = Gtk.Adjustment(
            value=self.settings.get("font_size"),
            lower=FONT_SIZE_MIN,
            upper=FONT_SIZE_MAX,
            step_increment=1,
        )
        font_spin = Gtk.SpinButton(adjustment=font_adj)
        grid.attach(font_spin, 1, 3, 1, 1)

        # Reproduccion automatica
        autoplay_label = Gtk.Label(label="Reproducción automática:")
        autoplay_label.set_halign(Gtk.Align.START)
        grid.attach(autoplay_label, 0, 4, 1, 1)

        autoplay_switch = Gtk.Switch()
        autoplay_switch.set_active(bool(self.settings.get("autoplay")))
        autoplay_switch.set_halign(Gtk.Align.START)
        grid.attach(autoplay_switch, 1, 4, 1, 1)

        dialog.show_all()
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            self.settings.set("quality", quality_combo.get_active_id())
            self.settings.set("volume", int(volume_scale.get_value()))
            self.settings.set("dark_theme", theme_switch.get_active())
            self.settings.set("font_size", int(font_spin.get_value()))
            self.settings.set("autoplay", autoplay_switch.get_active())
            self._apply_theme_and_font()
            self.status_label.set_text("Configuración guardada.")
        elif response == Gtk.ResponseType.REJECT:
            self.settings.reset_to_defaults()
            self._apply_theme_and_font()
            self.status_label.set_text("Configuración restaurada a los valores por defecto.")

        dialog.destroy()

    def _on_search_key_press(self, widget, event):
        """Escape limpia el campo de busqueda. Flecha abajo mueve el foco
        a la lista de resultados y selecciona el primero, para poder
        navegar con el teclado sin usar el mouse."""
        from gi.repository import Gdk
        if event.keyval == Gdk.KEY_Escape:
            self.search_entry.set_text("")
            return True
        if event.keyval == Gdk.KEY_Down:
            first_row = self.results_list.get_row_at_index(0)
            if first_row:
                self.results_list.select_row(first_row)
                self.results_list.grab_focus()
                first_row.grab_focus()
            return True
        return False

    def on_search_clicked(self, widget):
        """Callback cuando se presiona Buscar / Enter"""
        query = self.search_entry.get_text().strip()

        if not query:
            self.status_label.set_text("Ingresa un término de búsqueda")
            return

        if self.is_searching:
            self.status_label.set_text("Ya hay una búsqueda en progreso...")
            return

        # Invalidar cualquier actualizacion pendiente de una busqueda anterior
        self._search_token += 1
        my_token = self._search_token

        # Reiniciar el estado de la carga infinita para la nueva busqueda
        self._current_query = query
        self._next_start = 1
        self._loading_more = False
        self._no_more_results = False
        self._autoplay_after_more_index = None

        # Guardar en el historial
        

        # Guardar en el historial y refrescar el boton de historial
        # y el autocompletado con la busqueda recien hecha
        self.history.add(query)
        self._refresh_history_popover()
        self._refresh_completion()

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
            results = self.searcher.search_fast(query, start=1, count=self.RESULTS_PER_PAGE)
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

        # Estado de paginacion: si llegaron menos de los pedidos,
        # significa que ya no hay mas resultados para esta busqueda
        self._next_start = len(results) + 1
        if len(results) < self.RESULTS_PER_PAGE:
            self._no_more_results = True

        self.status_label.set_text(
            f"{len(results)} Resultados Encontrados. Completando Detalles..."
        )
        self.results_list.show_all()

        # Seleccionar el primer resultado automaticamente para poder
        # navegar de inmediato con las flechas del teclado
        first_row = self.results_list.get_row_at_index(0)
        if first_row:
            self.results_list.select_row(first_row)

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
        count = len(self.row_by_id)
        self.status_label.set_text(
            f"{count} Resultados Listos. Enter o doble clic para reproducir."
        )
        self._finish_searching()
        return False

    def _search_error(self, error: str, token: int):
        if token != self._search_token:
            return False
        self.status_label.set_text(f"Error en la búsqueda: {error}")
        self._finish_searching()
        return False

    def _finish_searching(self):
        self.is_searching = False
        self.search_button.set_sensitive(True)
        self.search_entry.set_sensitive(True)
        self.spinner.stop()
        self.spinner.hide()

    # ------------------------------------------------------------------
    # Carga infinita: pedir mas resultados al llegar cerca del final
    # ------------------------------------------------------------------

    def _on_scroll_changed(self, adjustment):
        """
        Detectar que estamos cerca del final de la lista y disparar la
        carga de mas resultados. No hace falta que el usuario haga nada
        mas que seguir bajando.
        """
        if self.is_searching or self._loading_more or self._no_more_results:
            return
        if not self._current_query:
            return

        value = adjustment.get_value()
        page_size = adjustment.get_page_size()
        upper = adjustment.get_upper()

        # Umbral: cuando falten menos de 150px para llegar al final del scroll
        if upper - (value + page_size) < 150:
            self._load_more_results()

    def _load_more_results(self):
        """Pedir la proxima tanda de resultados de la busqueda actual."""
        if not self._current_query or self._loading_more or self._no_more_results:
            return

        self._loading_more = True
        token = self._search_token
        start = self._next_start
        query = self._current_query

        self.status_label.set_text("Cargando más resultados...")

        thread = Thread(
            target=self._load_more_in_background, args=(query, start, token)
        )
        thread.daemon = True
        thread.start()

    def _load_more_in_background(self, query: str, start: int, token: int):
        """Traer la siguiente tanda (fase rapida + enriquecido), igual
        que la busqueda inicial pero agregando filas en vez de reemplazarlas."""
        try:
            results = self.searcher.search_fast(
                query, start=start, count=self.RESULTS_PER_PAGE
            )
            GLib.idle_add(self._append_more_results, results, start, token)

            if results:
                self.searcher.enrich_all(
                    results,
                    on_video_ready=lambda video: GLib.idle_add(
                        self._update_row, video, token
                    ),
                    max_workers=4,
                )
            GLib.idle_add(self._load_more_done, token)

        except Exception as e:
            print(f"Error cargando más resultados: {e}")
            GLib.idle_add(self._load_more_done, token)

    def _append_more_results(self, results, start: int, token: int):
        """Agregar la nueva tanda de resultados al final de la lista."""
        if token != self._search_token:
            return False

        if not results:
            self._no_more_results = True
            self.status_label.set_text(
                f"{len(self.row_by_id)} Resultados Cargados (no hay más)."
            )
            return False

        added = 0
        for video in results:
            video_id = video.get("id")
            # Evitar duplicados por si algun resultado se repite entre tandas
            if video_id and video_id not in self.row_by_id:
                self._add_result_row(video)
                added += 1

        self._next_start = start + len(results)
        if len(results) < self.RESULTS_PER_PAGE:
            self._no_more_results = True

        self.results_list.show_all()
        self.status_label.set_text(
            f"{len(self.row_by_id)} Resultados Cargados. Sigue bajando para ver más."
        )
        return False

    def _load_more_done(self, token: int):
        if token == self._search_token:
            self._loading_more = False

        # Si la reproduccion automatica se quedo sin resultados y pidio
        # una tanda nueva, ahora que ya llego, se sigue reproduciendo
        # desde el primer resultado recien agregado
        if self._autoplay_after_more_index is not None:
            index = self._autoplay_after_more_index
            self._autoplay_after_more_index = None

            if token != self._search_token:
                return False  # el usuario empezo una busqueda nueva mientras tanto

            next_row = self.results_list.get_row_at_index(index)
            if next_row is not None:
                self.results_list.select_row(next_row)
                next_row.grab_focus()
                self.status_label.set_text(
                    f"Reproduciendo automáticamente: {next_row.video_title}..."
                )
                self._play_row(next_row)
            else:
                self.status_label.set_text(
                    "No se encontraron mas videos para seguir reproduciendo."
                )

        return False

    def _add_result_row(self, video: dict):
        """Agregar una fila de resultado (con placeholders si falta info)"""
        row = Gtk.ListBoxRow()

        # Contenedor horizontal externo: miniatura a la izquierda,
        # texto (titulo/canal/duracion/vistas) a la derecha
        outer_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        outer_hbox.set_margin_top(8)
        outer_hbox.set_margin_bottom(8)
        outer_hbox.set_margin_start(10)
        outer_hbox.set_margin_end(10)

        # Miniatura: se muestra un icono de placeholder mientras se
        # descarga en segundo plano (no bloquea la aparicion de la fila)
        thumb_image = Gtk.Image.new_from_icon_name(
            "video-x-generic-symbolic", Gtk.IconSize.DIALOG
        )
        thumb_image.set_size_request(THUMB_WIDTH, THUMB_HEIGHT)
        outer_hbox.pack_start(thumb_image, False, False, 0)

        # Contenedor principal de texto (vertical)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)

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

        # El bloque de texto va a la derecha de la miniatura
        outer_hbox.pack_start(vbox, True, True, 0)

        # Estrella para marcar/desmarcar como favorito
        is_fav = self.favorites.is_favorite(video.get("id", ""))
        star_button = Gtk.ToggleButton(label="★" if is_fav else "☆")
        star_button.set_relief(Gtk.ReliefStyle.NONE)
        star_button.set_active(is_fav)
        star_button.connect("toggled", self._on_star_toggled, video)
        outer_hbox.pack_end(star_button, False, False, 0)

        # Guardar datos del video en el row
        row.video_url = video["url"]
        row.video_id = video["id"]
        row.video_title = video["title"]
        row.duration_label = duration_label
        row.views_label = views_label
        row.thumb_image = thumb_image
        row.star_button = star_button

        row.add(outer_hbox)
        self.results_list.add(row)

        if video.get("id"):
            self.row_by_id[video["id"]] = row
            self.thumbnail_loader.request(video["id"], self._on_thumbnail_ready)

    def _on_thumbnail_ready(self, video_id: str, pixbuf):
        """
        Actualizar la miniatura de una fila cuando termina de descargarse.
        Se llama desde GLib.idle_add, asi que ya estamos en el hilo
        principal y es seguro tocar el widget.
        """
        row = self.row_by_id.get(video_id)
        if row and hasattr(row, "thumb_image"):
            row.thumb_image.set_from_pixbuf(pixbuf)
        return False

    def _on_results_key_press(self, widget, event):
        """Escape vuelve el foco al campo de busqueda. (Enter para
        reproducir y las flechas para navegar ya las maneja Gtk.ListBox
        de forma nativa, no hace falta reimplementarlas.)"""
        from gi.repository import Gdk
        if event.keyval == Gdk.KEY_Escape:
            self.search_entry.grab_focus()
            return True
        return False

    def _build_history_popover(self) -> Gtk.Popover:
        """Construir el menu desplegable con las busquedas recientes."""
        popover = Gtk.Popover()

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        vbox.set_margin_top(6)
        vbox.set_margin_bottom(6)
        vbox.set_margin_start(6)
        vbox.set_margin_end(6)

        items = self.history.get_all()

        if not items:
            label = Gtk.Label(label="Todavia no hay busquedas recientes")
            label.set_opacity(0.6)
            vbox.pack_start(label, False, False, 4)
        else:
            for query in items:
                item_button = Gtk.Button(label=query)
                item_button.set_relief(Gtk.ReliefStyle.NONE)
                item_button.get_child().set_halign(Gtk.Align.START)
                item_button.connect(
                    "clicked", self._on_history_item_clicked, query, popover
                )
                vbox.pack_start(item_button, False, False, 0)

            separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
            vbox.pack_start(separator, False, False, 4)

            clear_button = Gtk.Button(label="Limpiar historial")
            clear_button.connect("clicked", self._on_clear_history_clicked, popover)
            vbox.pack_start(clear_button, False, False, 0)

        vbox.show_all()
        popover.add(vbox)
        return popover

    def _refresh_history_popover(self):
        """Reconstruir el menu de historial con el contenido actualizado."""
        self.history_button.set_popover(self._build_history_popover())

    def _refresh_completion(self):
        """Actualizar las sugerencias de autocompletado con el historial."""
        self.completion_store.clear()
        for query in self.history.get_all():
            self.completion_store.append([query])

    def _on_history_item_clicked(self, button, query: str, popover: Gtk.Popover):
        """Repetir una busqueda del historial al hacer clic en ella."""
        popover.popdown()
        self.search_entry.set_text(query)
        self.on_search_clicked(None)

    def _on_clear_history_clicked(self, button, popover: Gtk.Popover):
        """Vaciar el historial de busquedas."""
        self.history.clear()
        popover.popdown()
        self._refresh_history_popover()
        self._refresh_completion()

    def _build_favorites_popover(self) -> Gtk.Popover:
        """Construir el menu desplegable con los videos favoritos."""
        popover = Gtk.Popover()

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        vbox.set_margin_top(6)
        vbox.set_margin_bottom(6)
        vbox.set_margin_start(6)
        vbox.set_margin_end(6)

        items = self.favorites.get_all()

        if not items:
            label = Gtk.Label(label="Todavia no hay videos favoritos")
            label.set_opacity(0.6)
            vbox.pack_start(label, False, False, 4)
        else:
            for video in items:
                item_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)

                play_button = Gtk.Button(label=video.get("title", "Sin titulo"))
                play_button.set_relief(Gtk.ReliefStyle.NONE)
                play_button.get_child().set_halign(Gtk.Align.START)
                play_button.get_child().set_line_wrap(True)
                play_button.get_child().set_max_width_chars(38)
                play_button.set_hexpand(True)
                play_button.connect(
                    "clicked", self._on_favorite_item_clicked, video, popover
                )
                item_box.pack_start(play_button, True, True, 0)

                remove_button = Gtk.Button(label="Quitar")
                remove_button.set_relief(Gtk.ReliefStyle.NONE)
                remove_button.connect(
                    "clicked", self._on_favorite_remove_clicked, video, popover
                )
                item_box.pack_start(remove_button, False, False, 0)

                vbox.pack_start(item_box, False, False, 0)

        vbox.show_all()
        popover.add(vbox)
        return popover

    def _refresh_favorites_popover(self):
        """Reconstruir el menu de favoritos con el contenido actualizado."""
        self.favorites_button.set_popover(self._build_favorites_popover())

    def _on_favorite_item_clicked(self, button, video: dict, popover: Gtk.Popover):
        """Reproducir un favorito directamente, sin tener que buscarlo de nuevo."""
        popover.popdown()
        self.status_label.set_text(f"Reproduciendo: {video.get('title', '')}...")
        thread = Thread(
            target=Player.play,
            args=(video.get("url", ""), video.get("title", "")),
            daemon=True,
        )
        thread.start()

    def _on_favorite_remove_clicked(self, button, video: dict, popover: Gtk.Popover):
        """Quitar un video de favoritos desde el menu."""
        self.favorites.remove(video.get("id", ""))
        popover.popdown()
        self._refresh_favorites_popover()

        # Si ese video esta visible en la lista de resultados actual,
        # actualizar tambien su estrella ahi
        row = self.row_by_id.get(video.get("id"))
        if row and hasattr(row, "star_button"):
            row.star_button.set_active(False)

    def _on_star_toggled(self, button: Gtk.ToggleButton, video: dict):
        """Agregar o quitar un resultado de favoritos al tocar la estrella."""
        is_now_fav = self.favorites.toggle(video)
        button.set_label("★" if is_now_fav else "☆")
        self._refresh_favorites_popover()

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
        self.thumbnail_loader.shutdown()
        Gtk.main_quit()