"""
Configuración de TubeLite
Adaptada para hardware MUY antiguo (AMD E-350)
Sin GPU, usando X11 simple
"""

import platform
import psutil


class Config:
    """Configuración global de TubeLite"""
    
    # Detección de hardware
    CPU_CORES = psutil.cpu_count(logical=False)
    MEMORY_GB = psutil.virtual_memory().total / (1024**3)
    SYSTEM = platform.system()
    
    # Determinar si es hardware antiguo
    IS_LOW_END = CPU_CORES <= 2 or MEMORY_GB <= 4
    
    # ========== CONFIGURACIÓN DE VIDEO ==========
    
    # Calidad de video (MUY baja para E-350)
    if IS_LOW_END:
        VIDEO_QUALITY = "bestvideo[height<=360]"  # 360p max
        AUDIO_QUALITY = "bestaudio[aext=m4a]/bestaudio"
    else:
        VIDEO_QUALITY = "bestvideo[height<=720]"  # 720p
        AUDIO_QUALITY = "bestaudio"
    
    # ========== OPCIONES DE MPV ==========
    
    # Opciones base MÍNIMAS para hardware muy antiguo
    MPV_OPTS = [
        "--ytdl=yes",
        "--force-window=immediate",
        "--vo=gpu",  # Video output simple sin GPU (X11)
        "--hwdec=vaapi",
        "--ytdl-format=bestvideo[height<=480]+bestaudio/best[height<=480]",
        "--cache=yes",
        "--cache-secs=5",  # Buffer pequeño
    ]
    
    # ========== CONFIGURACIÓN DE BÚSQUEDA ==========
    
    # Número de resultados
    SEARCH_RESULTS = 10
    
    # Timeout de búsqueda
    SEARCH_TIMEOUT = 15
    
    # ========== INFORMACIÓN DE DEBUG ==========
    
    @classmethod
    def print_info(cls):
        """Imprimir información de configuración"""
        print(f"Hardware: {cls.SYSTEM}")
        print(f"CPU cores: {cls.CPU_CORES}")
        print(f"RAM: {cls.MEMORY_GB:.1f}GB")
        print(f"Modo: {'Low-end ⚡' if cls.IS_LOW_END else 'Standard'}")
        print(f"Calidad: {cls.VIDEO_QUALITY}")
        print(f"Video Output: x11 (sin GPU)")