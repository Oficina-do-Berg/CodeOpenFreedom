# -*- coding: utf-8 -*-
"""
CodeOpen - Rotação Inteligente de IP para OpenCode
by OFICINA-DO-BERG
"""

import sys
import os

# Adicionar diretório atual ao sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from select_language import select_language

def main():
    try:
        select_language()
    except KeyboardInterrupt:
        print("\n  Encerrando...")
        sys.exit(0)

if __name__ == "__main__":
    main()
