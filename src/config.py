"""
Configuración de TubeLite
Adaptada para hardware MUY antiguo con aceleración gráfica GPU/VAAPI
"""

import platform
import psutil


class Config:
    """Configuración global de TubeLite"""
    
    # Detección de hardware
    CPU_CORES = psutil.cpu_count(logical=False) or 1
    MEMORY_GB = psutil.virtual_memory().total / (1024**3)
    SYSTEM = platform.system()
    
    # Determinar si es hardware antiguo
    IS_LOW_END = CPU_CORES <= 2 or MEMORY_GB <= 4
    
    # ========== CONFIGURACIÓN DE VIDEO ==========
    
    # Formato dinámico según el hardware detectado
    if IS_LOW_END:
        # Forzamos un techo de 480p para asegurar fluidez extrema en el procesador
        YTDL_FORMAT = "bestvideo[height<=480]+bestaudio/best[height<=480]"
        VIDEO_QUALITY = "bestvideo[height<=480]"  # <-- Agregada para compatibilidad
        AUDIO_QUALITY = "bestaudio[aext=m4a]/bestaudio"
    else:
        # En hardware estándar, permitimos hasta 720p
        YTDL_FORMAT = "bestvideo[height<=720]+bestaudio/best[height<=720]"
        VIDEO_QUALITY = "bestvideo[height<=720]"  # <-- Agregada para compatibilidad
        AUDIO_QUALITY = "bestaudio"
    
    # ========== OPCIONES DE MPV ==========
    
    # Opciones base utilizando las variables dinámicas
    MPV_OPTS = [
        "--ytdl=yes",
        "--force-window=immediate",
        "--vo=gpu",
        "--gpu-api=opengl", # Forzamos OpenGL directo: la Radeon del E-350 no soporta
                             # Vulkan, asi que sin esto mpv pierde tiempo probando
                             # libplacebo/Vulkan primero y cayendo a OpenGL despues.
        "--hwdec=vaapi",    # Activa la decodificación por hardware de la Radeon integrada
        f"--ytdl-format={YTDL_FORMAT}",
        "--cache=yes",
        "--cache-secs=10", # Un búfer de 10 seg ayuda a evitar tirones si el internet oscila
    ]

    # ========== COOKIES DEL NAVEGADOR (para el bloqueo anti-bot de YouTube) ==========
    #
    # YouTube a veces exige verificar que no sos un bot ("Sign in to confirm
    # you're not a bot") para ciertos videos. La forma mas confiable de
    # evitarlo es que yt-dlp use la sesion ya logueada de tu navegador.
    #
    # Poné el nombre de tu navegador aca (ej: "firefox" o "chrome") SOLO si
    # ese navegador esta instalado en este equipo y tenes sesion iniciada en
    # YouTube/Google ahi. Dejalo en None si no queres usar esta opcion
    # (Player reintentara igual, pero sin cookies puede seguir fallando en
    # los videos que YouTube marque para verificacion).
    COOKIES_FROM_BROWSER = None  # ej: "firefox"

    # ========== CONFIGURACIÓN DE BÚSQUEDA ==========
    
    # Número de resultados
    SEARCH_RESULTS = 10
    
    # Timeout de búsqueda
    SEARCH_TIMEOUT = 15
    
    # ========== INFORMACIÓN DE DEBUG ==========
    
    @classmethod
    def print_info(cls):
        """Imprimir información de configuración"""
        print(f"Sistema Operativo: {cls.SYSTEM}")
        print(f"Núcleos de CPU: {cls.CPU_CORES}")
        print(f"Memoria RAM: {cls.MEMORY_GB:.1f} GB")
        print(f"Modo de rendimiento: {'⚡ Bajo Consumo (Low-end) ⚡' if cls.IS_LOW_END else 'Estándar'}")
        print(f"Filtro de resolución: {cls.YTDL_FORMAT.split('+')[0]}")
        print(f"Salida de Video (VO): gpu + vaapi (Aceleración activa)")