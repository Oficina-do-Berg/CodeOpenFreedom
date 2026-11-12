# -*- coding: utf-8 -*-
"""
CodeOpen - Interface CLI
by OFICINA-DO-BERG
"""

import os
import sys
import time
import msvcrt

# Configurar UTF-8
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')

from core import Config, ConnectionManager, OpenCodeManager, IPRotator, LogMonitor, Orchestrator
from utils.logger import get_logger

logger = get_logger(__name__)

# Detectar suporte ANSI
USE_ANSI = os.environ.get('WT_SESSION') or os.environ.get('TERM_PROGRAM') == 'vscode'

# Cores
if USE_ANSI:
    RED = '\033[91m'
    BOLD_RED = '\033[1;91m'
    WHITE = '\033[97m'
    DIM_WHITE = '\033[2;37m'
    GREEN = '\033[92m'
    RESET = '\033[0m'
else:
    RED = BOLD_RED = WHITE = DIM_WHITE = GREEN = RESET = ''

LOGO = """
    ██████╗ ██████╗ ██████╗ ███████╗ ██████╗ ██████╗ ███████╗███╗   ██╗
   ██╔════╝██╔═══██╗██╔══██╗██╔════╝██╔═══██╗██╔══██╗██╔════╝████╗  ██║
   ██║     ██║   ██║██║  ██║█████╗  ██║   ██║██████╔╝█████╗  ██╔██╗ ██║
   ██║     ██║   ██║██║  ██║██╔══╝  ██║   ██║██╔═══╝ ██╔══╝  ██║╚██╗██║
   ╚██████╗╚██████╔╝██████╔╝███████╗╚██████╔╝██║     ███████╗██║ ╚████║
    ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝ ╚═════╝ ╚═╝     ╚══════╝╚═╝  ╚═══╝
                                            by OFICINA-DO-BERG
"""

# Traduções
TRANSLATIONS = {
    'pt': {
        'connection': 'Conexao', 'ip': 'IP', 'opencode': 'OpenCode',
        'monitor': 'Monitor', 'rotations': 'Rotacoes',
        'disconnected': 'Desconectado', 'active': 'ATIVO',
        'stopped': 'PARADO', 'inactive': 'INATIVO',
        'auto_mode': 'MODO AUTOMATICO', 'start': 'INICIAR',
        'stop': 'PARAR', 'rotate_ip': 'ROTACIONAR IP',
        'connection_menu': 'CONEXAO', 'exit': 'SAIR',
        'navigate': 'Use W/S ou ↑/↓ | ENTER | ESC para sair',
        'connect_warp': 'CONECTAR WARP', 'disconnect': 'DESCONECTAR',
        'rotate': 'ROTACIONAR', 'back': 'VOLTAR',
        'press_key': 'Pressione qualquer tecla'
    },
    'en': {
        'connection': 'Connection', 'ip': 'IP', 'opencode': 'OpenCode',
        'monitor': 'Monitor', 'rotations': 'Rotations',
        'disconnected': 'Disconnected', 'active': 'ACTIVE',
        'stopped': 'STOPPED', 'inactive': 'INACTIVE',
        'auto_mode': 'AUTO MODE', 'start': 'START',
        'stop': 'STOP', 'rotate_ip': 'ROTATE IP',
        'connection_menu': 'CONNECTION', 'exit': 'EXIT',
        'navigate': 'Use W/S or ↑/↓ | ENTER | ESC to exit',
        'connect_warp': 'CONNECT WARP', 'disconnect': 'DISCONNECT',
        'rotate': 'ROTATE', 'back': 'BACK',
        'press_key': 'Press any key'
    }
}


class CodeOpenCLI:
    def __init__(self, lang='pt'):
        self.config = Config()
        self.connection = ConnectionManager(self.config)
        self.opencode = OpenCodeManager(self.config)
        self.rotator = IPRotator(self.connection, self.config)
        self.monitor = LogMonitor(self.config)
        self.orchestrator = Orchestrator(
            self.connection, self.opencode, self.rotator,
            self.monitor, self.config
        )
        self.current_option = 0
        self.lang = lang
        self.update_menu_options()
    
    def update_menu_options(self):
        t = TRANSLATIONS[self.lang]
        self.menu_options = [
            (t['auto_mode'], self.start_automatic_mode),
            (t['start'], self.start_opencode),
            (t['stop'], self.stop_opencode),
            (t['rotate_ip'], self.rotate_ip),
            (t['connection_menu'], self.connection_menu),
            (t['exit'], self.exit_app)
        ]
    
    def t(self, key):
        return TRANSLATIONS[self.lang].get(key, key)
    
    def clear_screen(self):
        os.system('cls')
    
    def draw_screen(self):
        self.clear_screen()
        print(f"{RED}{LOGO}{RESET}")
        print()
        
        status = self.orchestrator.get_status()
        conn = status['connection']
        
        print(f"  {WHITE}{self.t('connection')}: {RESET}", end='')
        if conn['connected']:
            print(f"{RED}{conn['method']} - {conn['ip']}{RESET}")
        else:
            print(f"{DIM_WHITE}{self.t('disconnected')}{RESET}")
        
        print(f"  {WHITE}{self.t('opencode')}: {RESET}", end='')
        print(f"{RED if status['opencode_running'] else DIM_WHITE}{self.t('active') if status['opencode_running'] else self.t('stopped')}{RESET}")
        
        print(f"  {WHITE}{self.t('monitor')}: {RESET}", end='')
        print(f"{RED if status['monitoring'] else DIM_WHITE}{self.t('active') if status['monitoring'] else self.t('inactive')}{RESET}")
        
        print(f"  {WHITE}{self.t('rotations')}: {RED}{status['rotation_count']}{RESET}")
        print()
        print(f"{DIM_WHITE}{'─' * 70}{RESET}")
        print()
        
        for i, (label, _) in enumerate(self.menu_options):
            if i == self.current_option:
                print(f"  {RED}>{RESET} {BOLD_RED}[ {label} ]{RESET}")
            else:
                print(f"    {DIM_WHITE}[ {label} ]{RESET}")
        
        print()
        print(f"  {DIM_WHITE}{self.t('navigate')}{RESET}")
    
    def get_key(self):
        if msvcrt.kbhit():
            key = msvcrt.getch()
            while msvcrt.kbhit():
                msvcrt.getch()
            
            if key == b'\r':
                return 'enter'
            if key == b'\x1b':
                return 'esc'
            # Setas (suporte para \x00 e \xe0)
            if key in (b'\x00', b'\xe0'):
                arrow = msvcrt.getch()
                if arrow == b'H':
                    return 'up'
                elif arrow == b'P':
                    return 'down'
            # W/S (case insensitive)
            if key.upper() == b'W':
                return 'up'
            if key.upper() == b'S':
                return 'down'
        return None
    
    def main_menu(self):
        last_option = -1
        
        while True:
            if self.current_option != last_option:
                self.draw_screen()
                last_option = self.current_option
            
            key = self.get_key()
            
            if key == 'up':
                self.current_option = (self.current_option - 1) % len(self.menu_options)
            elif key == 'down':
                self.current_option = (self.current_option + 1) % len(self.menu_options)
            elif key == 'enter':
                _, action = self.menu_options[self.current_option]
                if action == self.exit_app:
                    action()
                    return
                action()
                last_option = -1
            elif key == 'esc':
                self.exit_app()
                return
            
            time.sleep(0.02)
    
    def start_automatic_mode(self):
        self.clear_screen()
        print(f"\n  {BOLD_RED}MODO AUTOMATICO{RESET}")
        print(f"  {DIM_WHITE}{'─' * 40}{RESET}\n")
        print(f"  {WHITE}Funcionalidade em desenvolvimento...{RESET}\n")
        print(f"  {DIM_WHITE}{self.t('press_key')}...{RESET}")
        msvcrt.getch()
    
    def start_opencode(self):
        self.clear_screen()
        print(f"\n  {WHITE}Iniciando OpenCode...{RESET}\n")
        success = self.opencode.start()
        print(f"  {RED if success else DIM_WHITE}{'OK - OpenCode iniciado' if success else 'ERRO - Falha ao iniciar'}{RESET}\n")
        print(f"  {DIM_WHITE}{self.t('press_key')}...{RESET}")
        msvcrt.getch()
    
    def stop_opencode(self):
        self.clear_screen()
        print(f"\n  {WHITE}Parando OpenCode...{RESET}\n")
        success = self.opencode.stop()
        print(f"  {RED if success else DIM_WHITE}{'OK - OpenCode parado' if success else 'ERRO - Falha ao parar'}{RESET}\n")
        print(f"  {DIM_WHITE}{self.t('press_key')}...{RESET}")
        msvcrt.getch()
    
    def rotate_ip(self):
        self.clear_screen()
        print(f"\n  {WHITE}Rotacionando IP...{RESET}\n")
        success = self.rotator.rotate()
        print(f"  {RED if success else DIM_WHITE}{'OK - IP rotacionado' if success else 'ERRO - Falha na rotacao'}{RESET}\n")
        print(f"  {DIM_WHITE}{self.t('press_key')}...{RESET}")
        msvcrt.getch()
    
    def connection_menu(self):
        conn_options = [
            (self.t('connect_warp'), 'connect'),
            (self.t('disconnect'), 'disconnect'),
            (self.t('rotate'), 'rotate'),
            (self.t('back'), 'back')
        ]
        current = 0
        last_current = -1
        
        while True:
            if current != last_current:
                self.clear_screen()
                print(f"\n  {BOLD_RED}CONEXAO{RESET}\n")
                status = self.connection.get_status()
                if status['connected']:
                    print(f"  Status: {RED}{status['method']}{RESET}")
                    print(f"  IP: {WHITE}{status['ip']}{RESET}\n")
                else:
                    print(f"  Status: {DIM_WHITE}{self.t('disconnected')}{RESET}\n")
                
                print(f"{DIM_WHITE}{'─' * 70}{RESET}\n")
                
                for i, (label, _) in enumerate(conn_options):
                    if i == current:
                        print(f"  {RED}>{RESET} {BOLD_RED}[ {label} ]{RESET}")
                    else:
                        print(f"    {DIM_WHITE}[ {label} ]{RESET}")
                
                print(f"\n  {DIM_WHITE}Use W/S | ENTER | ESC{RESET}")
                last_current = current
            
            key = self.get_key()
            
            if key == 'up':
                current = (current - 1) % len(conn_options)
            elif key == 'down':
                current = (current + 1) % len(conn_options)
            elif key == 'enter':
                label, action_name = conn_options[current]
                if action_name == 'back':
                    return
                
                self.clear_screen()
                print(f"\n  {WHITE}{label}...{RESET}\n")
                
                if action_name == 'connect':
                    success, msg = self.connection.connect('WARP')
                elif action_name == 'disconnect':
                    success, msg = self.connection.disconnect()
                elif action_name == 'rotate':
                    success, msg = self.connection.rotate_warp_ip()
                
                print(f"  {WHITE}{msg}{RESET}\n")
                print(f"  {DIM_WHITE}{self.t('press_key')}...{RESET}")
                msvcrt.getch()
                last_current = -1
            elif key == 'esc':
                return
            
            time.sleep(0.02)
    
    def exit_app(self):
        self.clear_screen()
        print(f"\n\n  {BOLD_RED}CodeOpen{RESET}")
        print(f"  {DIM_WHITE}by OFICINA-DO-BERG{RESET}\n")
        print(f"  {DIM_WHITE}Encerrando...{RESET}\n")
        
        if self.orchestrator.get_status()['monitoring']:
            self.orchestrator.stop_flow()
        if self.orchestrator.get_status()['opencode_running']:
            self.opencode.stop()


if __name__ == "__main__":
    lang = 'pt'
    if len(sys.argv) > 1:
        lang = sys.argv[1]
    
    cli = CodeOpenCLI(lang=lang)
    
    try:
        cli.main_menu()
    except KeyboardInterrupt:
        cli.exit_app()
