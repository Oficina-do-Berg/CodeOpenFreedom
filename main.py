"""
OpenCode Infinity - Versão Simplificada
Rotação automática de IP para OpenCode

Autor: Baseado no OpenCode Infinite original
Versão: 1.0.0
"""

import customtkinter as ctk
from ui.main_window import MainWindow
from utils.logger import setup_logger
import sys

# Configurar tema
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

def main():
    """Função principal da aplicação"""
    try:
        # Configurar logger
        logger = setup_logger()
        logger.info("=" * 50)
        logger.info("OpenCode Infinity Simple v1.0.0 iniciando...")
        logger.info("=" * 50)
        
        # Criar e executar janela principal
        app = MainWindow()
        app.mainloop()
        
        logger.info("Aplicação encerrada normalmente")
        
    except Exception as e:
        print(f"❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
