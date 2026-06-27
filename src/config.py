"""
Configuración de TubeLite
Adaptada para hardware antiguo (AMD E-350)
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
    
    # Calidad de video
    if IS_LOW_END:
        VIDEO_QUALITY = "bestvideo[height<=360]"  # 360p max
        AUDIO_QUALITY = "bestaudio[aext=m4a]/bestaudio"
    else:
        VIDEO_QUALITY = "bestvideo[height<=720]"  # 720p
        AUDIO_QUALITY = "bestaudio"
    
    # ========== OPCIONES DE MPV ==========
    
    # Opciones base
    MPV_OPTS = [
        "--ytdl=yes",
        "--force-window=immediate",  # Abre ventana más rápido
        "--cache=yes",  # Cache de stream
        "--demuxer-cache-duration=10",  # Buffer de 10 segundos
    ]
    
    # Audio/Video sincronización
    if IS_LOW_END:
        MPV_OPTS.extend([
            "--profile=low-latency",  # Perfil de baja latencia
            "--audio-buffer=200",  # Buffer de audio mayor
            "--vf=format=yuv420p",  # Formato optimizado
            "--hwdec=auto",  # Aceleración por hardware si existe
        ])
    else:
        MPV_OPTS.extend([
            "--profile=default",
            "--audio-buffer=100",
        ])
    
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