# -*- coding: utf-8 -*-
"""
Seleção de Idioma - CodeOpen
"""

import os
import sys
import msvcrt
import time

# Configurar UTF-8
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')

# Detectar se suporta ANSI
def supports_ansi():
    """Verifica se o terminal suporta ANSI"""
    return os.environ.get('WT_SESSION') or os.environ.get('TERM_PROGRAM') == 'vscode'

USE_ANSI = supports_ansi()

# Cores ANSI
if USE_ANSI:
    RED = '\033[91m'
    BOLD_RED = '\033[1;91m'
    DIM_WHITE = '\033[2;37m'
    RESET = '\033[0m'
    CLEAR = '\033[2J\033[H'
else:
    RED = ''
    BOLD_RED = ''
    DIM_WHITE = ''
    RESET = ''
    CLEAR = ''

LOGO = """
    ██████╗ ██████╗ ██████╗ ███████╗ ██████╗ ██████╗ ███████╗███╗   ██╗
   ██╔════╝██╔═══██╗██╔══██╗██╔════╝██╔═══██╗██╔══██╗██╔════╝████╗  ██║
   ██║     ██║   ██║██║  ██║█████╗  ██║   ██║██████╔╝█████╗  ██╔██╗ ██║
   ██║     ██║   ██║██║  ██║██╔══╝  ██║   ██║██╔═══╝ ██╔══╝  ██║╚██╗██║
   ╚██████╗╚██████╔╝██████╔╝███████╗╚██████╔╝██║     ███████╗██║ ╚████║
    ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝ ╚═════╝ ╚═╝     ╚══════╝╚═╝  ╚═══╝
                                            by OFICINA-DO-BERG
"""


def clear_screen():
    """Limpa a tela"""
    if USE_ANSI:
        print(CLEAR, end='', flush=True)
    else:
        os.system('cls')


def draw_menu(current, options):
    """Desenha o menu"""
    clear_screen()
    
    print(f"{RED}{LOGO}{RESET}")
    print()
    print(f"  {BOLD_RED}SELECT LANGUAGE / SELECIONE O IDIOMA{RESET}")
    print(f"  {DIM_WHITE}─────────────────────────────────────────{RESET}")
    print()
    
    for i, (label, _) in enumerate(options):
        if i == current:
            print(f"  {RED}>{RESET} {BOLD_RED}[ {label} ]{RESET}")
        else:
            print(f"    {DIM_WHITE}[ {label} ]{RESET}")
    
    print()
    print(f"  {DIM_WHITE}Use {RED}W/S{RESET} {DIM_WHITE}ou{RESET} {RED}↑/↓{RESET} {DIM_WHITE}|{RESET} {RED}ENTER{RESET} {DIM_WHITE}para selecionar{RESET}")
    print(f"  {DIM_WHITE}Nota: O Cloudflare WARP deve estar ABERTO e LIGADO antes de iniciar.{RESET}")


def select_language():
    """Seletor de idioma"""
    options = [
        ("PORTUGUES", "pt"),
        ("ENGLISH", "en")
    ]
    current = 0
    last_current = -1
    
    while True:
        # Redesenha apenas quando muda
        if current != last_current:
            draw_menu(current, options)
            last_current = current
        
        # Aguardar tecla
        if msvcrt.kbhit():
            key = msvcrt.getch()
            
            # Detectar setas (NÃO limpar buffer antes de ler segunda parte!)
            if key in (b'\x00', b'\xe0'):  # Prefixo de seta
                arrow = msvcrt.getch()
                # Agora sim, limpar buffer extra
                while msvcrt.kbhit():
                    msvcrt.getch()
                
                if arrow == b'H':  # Up
                    current = (current - 1) % len(options)
                elif arrow == b'P':  # Down
                    current = (current + 1) % len(options)
            # W/S (case insensitive)
            elif key.upper() == b'W':
                # Limpar buffer
                while msvcrt.kbhit():
                    msvcrt.getch()
                current = (current - 1) % len(options)
            elif key.upper() == b'S':
                # Limpar buffer
                while msvcrt.kbhit():
                    msvcrt.getch()
                current = (current + 1) % len(options)
            # Enter
            elif key == b'\r':
                # Limpar buffer
                while msvcrt.kbhit():
                    msvcrt.getch()
                
                _, lang_code = options[current]
                
                # Salvar idioma
                with open('.language', 'w') as f:
                    f.write(lang_code)
                
                clear_screen()
                print(f"{RED}{LOGO}{RESET}")
                print()
                print(f"  ✓ Language set to: {RED}{lang_code.upper()}{RESET}")
                print()
                time.sleep(0.5)
                
                # Iniciar CLI com o mesmo interpretador Python ativo
                clear_screen()
                os.system(f'"{sys.executable}" cli.py {lang_code}')
                break
            else:
                # Limpar buffer para outras teclas
                while msvcrt.kbhit():
                    msvcrt.getch()
        
        time.sleep(0.02)


if __name__ == "__main__":
    try:
        select_language()
    except KeyboardInterrupt:
        clear_screen()
        print("\n  Encerrando...")
        sys.exit(0)
