"""
Seleção de Idioma v3 (BLESSED - SEM PISCAR)
"""

import os
from blessed import Terminal

term = Terminal()

LOGO = """
    ██████╗ ██████╗ ██████╗ ███████╗ ██████╗ ██████╗ ███████╗███╗   ██╗
   ██╔════╝██╔═══██╗██╔══██╗██╔════╝██╔═══██╗██╔══██╗██╔════╝████╗  ██║
   ██║     ██║   ██║██║  ██║█████╗  ██║   ██║██████╔╝█████╗  ██╔██╗ ██║
   ██║     ██║   ██║██║  ██║██╔══╝  ██║   ██║██╔═══╝ ██╔══╝  ██║╚██╗██║
   ╚██████╗╚██████╔╝██████╔╝███████╗╚██████╔╝██║     ███████╗██║ ╚████║
    ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝ ╚═════╝ ╚═╝     ╚══════╝╚═╝  ╚═══╝
                                            by OFICINA-DO-BERG
"""


def draw_menu(current):
    """Desenha menu SEM PISCAR"""
    options = [
        ("PORTUGUES", "pt"),
        ("ENGLISH", "en")
    ]
    
    # Limpar e posicionar cursor
    print(term.home + term.clear, end='')
    
    # Logo
    print(term.bold_red(LOGO))
    print()
    print(f"  {term.bold_red('SELECT LANGUAGE / SELECIONE O IDIOMA')}")
    print(f"  {term.dim_white('─' * 41)}")
    print()
    
    # Opções
    for i, (label, _) in enumerate(options):
        if i == current:
            print(f"  {term.red('>')} {term.bold_red(f'[ {label} ]')}")
        else:
            print(f"    {term.dim_white(f'[ {label} ]')}")
    
    print()
    print(f"  {term.dim_white('Use')} {term.red('W/S')} {term.dim_white('or')} {term.red('↑/↓')} {term.dim_white('|')} {term.red('ENTER')} {term.dim_white('to select')}")
    
    return options


def select_language():
    """Seleciona idioma COM BLESSED"""
    current = 0
    options = [
        ("PORTUGUES", "pt"),
        ("ENGLISH", "en")
    ]
    
    with term.cbreak(), term.hidden_cursor():
        # Desenho inicial
        draw_menu(current)
        
        while True:
            # Aguardar tecla (timeout 50ms)
            key = term.inkey(timeout=0.05)
            
            if key.code == term.KEY_UP or key.lower() == 'w':
                current = (current - 1) % len(options)
                draw_menu(current)
            
            elif key.code == term.KEY_DOWN or key.lower() == 's':
                current = (current + 1) % len(options)
                draw_menu(current)
            
            elif key.code == term.KEY_ENTER or key == '\r' or key == '\n':
                _, lang_code = options[current]
                
                # Salvar idioma
                with open('.language', 'w') as f:
                    f.write(lang_code)
                
                # Mensagem de confirmação
                print(term.home + term.clear, end='')
                print(term.bold_red(LOGO))
                print()
                print(f"  {term.green('✓')} Language set to: {term.red(lang_code.upper())}")
                print()
                
                # Pequena pausa para ver confirmação
                import time
                time.sleep(0.5)
                
                # Limpar antes de iniciar CLI
                print(term.home + term.clear, end='')
                
                # Iniciar CLI v3
                if lang_code == 'pt':
                    os.system('python cli_v3.py pt')
                else:
                    os.system('python cli_v3.py en')
                break


if __name__ == "__main__":
    select_language()
