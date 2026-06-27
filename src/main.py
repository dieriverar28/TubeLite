#!/usr/bin/env python3
"""
TubeLite - Cliente ligero de YouTube para equipos antiguos
Versión: 0.3.0
"""

import sys
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

# Importar configuración y GUI
from config import Config
from gui import TubeLiteWindow


def main():
    """Función principal"""
    try:
        # Mostrar información de configuración
        print("=" * 50)
        print("🎬 TubeLite v0.3.0")
        print("=" * 50)
        Config.print_info()
        print("=" * 50)
        
        # Crear y ejecutar ventana
        window = TubeLiteWindow()
        Gtk.main()
    
    except KeyboardInterrupt:
        print("\nTubeLite cerrado por el usuario")
        sys.exit(0)
    except Exception as e:
        print(f"Error en TubeLite: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()