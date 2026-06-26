#!/usr/bin/env python3
"""
TubeLite - Cliente ligero de YouTube para equipos antiguos
Versión: 0.1.0
"""

import sys
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

# Importar nuestra interfaz
from gui import TubeLiteWindow


def main():
    """Función principal"""
    try:
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