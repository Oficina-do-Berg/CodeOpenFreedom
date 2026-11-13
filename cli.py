# -*- coding: utf-8 -*-
"""
CodeOpen - Interface CLI
by OFICINA-DO-BERG
"""

import os
import sys
import time
import msvcrt
import io

# Configurar UTF-8 para Windows
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    # Forçar UTF-8 no stdout
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    else:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

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
        'start_opencode': 'INICIAR OPENCODE',
        'stop_opencode': 'PARAR OPENCODE',
        'rotate_ip': 'ROTACIONAR IP',
        'deep_reset': 'RESET PROFUNDO',
        'help': 'AJUDA',
        'exit': 'SAIR',
        'navigate': 'Use W/S ou ↑/↓ | ENTER | ESC para sair',
        'press_key': 'Pressione qualquer tecla'
    },
    'en': {
        'connection': 'Connection', 'ip': 'IP', 'opencode': 'OpenCode',
        'monitor': 'Monitor', 'rotations': 'Rotations',
        'disconnected': 'Disconnected', 'active': 'ACTIVE',
        'stopped': 'STOPPED', 'inactive': 'INACTIVE',
        'start_opencode': 'START OPENCODE',
        'stop_opencode': 'STOP OPENCODE',
        'rotate_ip': 'ROTATE IP',
        'deep_reset': 'DEEP RESET',
        'help': 'HELP',
        'exit': 'EXIT',
        'navigate': 'Use W/S or ↑/↓ | ENTER | ESC to exit',
        'press_key': 'Press any key'
    }
}


class CodeOpenCLI:
    def __init__(self, lang='pt'):
        self.config = Config()
        self.connection = ConnectionManager(self.config)
        self.opencode = OpenCodeManager(self.config)
        self.rotator = IPRotator(self.connection, self.config, self.opencode)
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
        is_running = self.opencode.is_running() or self.orchestrator.monitor.is_monitoring()
        toggle_label = t['stop_opencode'] if is_running else t['start_opencode']
        
        self.menu_options = [
            (toggle_label, self.toggle_opencode),
            (t['rotate_ip'], self.rotate_ip),
            (t['deep_reset'], self.deep_reset),
            (t['help'], self.show_help),
            (t['exit'], self.exit_app)
        ]
        if self.current_option >= len(self.menu_options):
            self.current_option = 0
    
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
            
            if key == b'\r':
                while msvcrt.kbhit():
                    msvcrt.getch()
                return 'enter'
            
            if key == b'\x1b':
                while msvcrt.kbhit():
                    msvcrt.getch()
                return 'esc'
            
            if key in (b'\x00', b'\xe0'):
                arrow = msvcrt.getch()
                while msvcrt.kbhit():
                    msvcrt.getch()
                
                if arrow == b'H':
                    return 'up'
                elif arrow == b'P':
                    return 'down'
            
            if key.upper() == b'W':
                while msvcrt.kbhit():
                    msvcrt.getch()
                return 'up'
            
            if key.upper() == b'S':
                while msvcrt.kbhit():
                    msvcrt.getch()
                return 'down'
            
            while msvcrt.kbhit():
                msvcrt.getch()
        
        return None
    
    def main_menu(self):
        last_option = -1
        last_running_state = None
        
        while True:
            is_running = self.opencode.is_running() or self.orchestrator.monitor.is_monitoring()
            if is_running != last_running_state:
                self.update_menu_options()
                last_running_state = is_running
                last_option = -1
            
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
    
    def toggle_opencode(self):
        self.clear_screen()
        is_running = self.opencode.is_running() or self.orchestrator.monitor.is_monitoring()
        
        if is_running:
            print(f"\n  {WHITE}Parando OpenCode e Monitoramento...{RESET}\n")
            self.orchestrator.stop_flow()
            print(f"  {RED}OK - OpenCode e Monitoramento encerrados{RESET}\n")
        else:
            print(f"\n  {WHITE}Iniciando OpenCode com Rotação Automática (WARP)...{RESET}\n")
            success = self.orchestrator.start_full_flow()
            if success:
                print(f"  {RED}OK - OpenCode iniciado com sucesso!{RESET}")
                print(f"  {DIM_WHITE}Modo automático ativo: o IP trocará sozinho ao atingir limites.{RESET}\n")
            else:
                if not self.connection.check_warp_installed():
                    print(f"  {RED}ERRO: Cloudflare WARP não foi encontrado!{RESET}")
                    print(f"  {WHITE}Baixe e instale gratuitamente em: {RED}https://1.1.1.1/{RESET}")
                    print(f"  {DIM_WHITE}(Abra o WARP pelo menos uma vez após instalar){RESET}\n")
                elif not self.opencode.find_opencode():
                    print(f"  {RED}ERRO: OpenCode não foi encontrado!{RESET}")
                    print(f"  {WHITE}Instale com: {RED}npm install -g @opencode/cli{RESET}\n")
                else:
                    print(f"  {DIM_WHITE}ERRO - Falha ao iniciar. Verifique os logs em ~/.opencode-infinity-simple/app.log{RESET}\n")
        
        print(f"  {DIM_WHITE}{self.t('press_key')}...{RESET}")
        msvcrt.getch()
        self.update_menu_options()
    
    def rotate_ip(self):
        self.clear_screen()
        print(f"\n  {WHITE}Rotacionando IP via WARP...{RESET}\n")
        was_running = self.opencode.is_running()
        if was_running:
            print(f"  {DIM_WHITE}Pausando OpenCode temporariamente para troca de rota...{RESET}")
            self.opencode.stop()
        
        success = self.rotator.rotate()
        if success:
            print(f"\n  {RED}OK - IP rotacionado com sucesso!{RESET}")
            if was_running:
                print(f"  {WHITE}Reiniciando OpenCode com o novo IP...{RESET}")
                self.opencode.start(proxy_url=self.connection.proxy_url)
        else:
            print(f"\n  {DIM_WHITE}ERRO - Falha na rotação. Verifique os logs.{RESET}")
            if was_running:
                self.opencode.start(proxy_url=self.connection.proxy_url)
        
        print(f"\n  {DIM_WHITE}{self.t('press_key')}...{RESET}")
        msvcrt.getch()
        self.update_menu_options()
    
    def deep_reset(self):
        self.clear_screen()
        print(f"\n  {BOLD_RED}RESET PROFUNDO{RESET}")
        print(f"  {DIM_WHITE}{'─' * 60}{RESET}\n")
        print(f"  {WHITE}O que vai acontecer (Padrão Original C++):{RESET}\n")
        print(f"  {WHITE}1. Parar OpenCode (se estiver rodando){RESET}")
        print(f"  {WHITE}2. Arquivar bancos de dados e storage no Desktop{RESET}")
        print(f"  {WHITE}3. Fazer backup e deletar tokens de autenticação{RESET}")
        print(f"  {WHITE}4. Remover snapshots DPAPI (impede restauração de sessão){RESET}")
        print(f"  {WHITE}5. Limpar pasta de cache (~/.cache/opencode){RESET}")
        print(f"  {WHITE}6. Rotacionar IP e renovar registro via WARP{RESET}\n")
        print(f"  {RED}IMPORTANTE:{RESET}")
        print(f"  {DIM_WHITE}- Seus chats ficam salvos em: Desktop\\opencode_chats_archiviate{RESET}")
        print(f"  {DIM_WHITE}- Backup dos tokens em: %LOCALAPPDATA%\\opencode-infinite\\backup\\auth{RESET}")
        print(f"  {DIM_WHITE}- Você precisará fazer login novamente no OpenCode{RESET}\n")
        print(f"  {RED}Confirmar? (S/N ou Y/N):{RESET} ", end='', flush=True)
        
        key = msvcrt.getch().upper()
        print()
        
        if key in (b'S', b'Y'):
            print(f"\n  {WHITE}Executando deep reset completo...{RESET}\n")
            success = self.rotator.rotate(deep_reset=True)
            if success:
                print(f"\n  {RED}SUCESSO!{RESET}")
                print(f"  {WHITE}Chats arquivados em: Desktop\\opencode_chats_archiviate{RESET}")
                print(f"  {WHITE}Cache limpo e novo registro WARP ativo com IP novo.{RESET}\n")
            else:
                print(f"\n  {DIM_WHITE}ERRO - Verifique os logs em ~/.opencode-infinity-simple/app.log{RESET}\n")
        else:
            print(f"\n  {DIM_WHITE}Operacao cancelada{RESET}\n")
        
        print(f"  {DIM_WHITE}{self.t('press_key')}...{RESET}")
        msvcrt.getch()
        self.update_menu_options()
    
    def show_help(self):
        self.clear_screen()
        print(f"\n  {BOLD_RED}AJUDA - COMO USAR O CODEOPEN{RESET}")
        print(f"  {DIM_WHITE}{'─' * 65}{RESET}\n")
        
        if self.lang == 'pt':
            print(f"  {RED}1. INICIAR / PARAR OPENCODE:{RESET}")
            print(f"     {WHITE}Inicia o OpenCode já conectado ao WARP e com o monitor ativo.{RESET}")
            print(f"     {DIM_WHITE}Quando o OpenCode atinge o limite de uso, ele troca de IP{RESET}")
            print(f"     {DIM_WHITE}automaticamente sem você precisar fazer nada.{RESET}\n")
            
            print(f"  {RED}2. ROTACIONAR IP:{RESET}")
            print(f"     {WHITE}Troca o seu IP pelo Cloudflare WARP na hora (~15 segundos).{RESET}")
            print(f"     {DIM_WHITE}Útil quando o OpenCode travar ou quando você quiser um novo IP{RESET}")
            print(f"     {DIM_WHITE}imediatamente sem deslogar da sua conta.{RESET}\n")
            
            print(f"  {RED}3. RESET PROFUNDO:{RESET}")
            print(f"     {WHITE}O botão de emergência quando a cota da conta estiver esgotada.{RESET}")
            print(f"     {DIM_WHITE}• Arquiva seus chats em: Desktop\\opencode_chats_archiviate{RESET}")
            print(f"     {DIM_WHITE}• Limpa tokens antigos e cache do OpenCode{RESET}")
            print(f"     {DIM_WHITE}• Gera novo IP. No próximo login, o contador começa do zero!{RESET}\n")
            
            print(f"  {RED}4. TECLAS DE CONTROLE:{RESET}")
            print(f"     {WHITE}W{RESET} ou {WHITE}↑{RESET}   : Subir no menu")
            print(f"     {WHITE}S{RESET} ou {WHITE}↓{RESET}   : Descer no menu")
            print(f"     {WHITE}ENTER{RESET}   : Selecionar opção")
            print(f"     {WHITE}ESC{RESET}     : Sair do aplicativo\n")
            
            print(f"  {RED}5. REQUISITOS (CLOUDFLARE WARP & PROXY):{RESET}")
            print(f"     {WHITE}• Precisa do Cloudflare WARP instalado: {RED}https://1.1.1.1/{RESET}")
            print(f"     {WHITE}• NÃO é necessário configurar proxy ou porta 40000 manualmente!{RESET}")
            print(f"     {DIM_WHITE}  O CodeOpen configura o modo proxy e a porta 40000 de forma{RESET}")
            print(f"     {DIM_WHITE}  100% automática através do comando warp-cli.{RESET}\n")
        else:
            print(f"  {RED}1. START / STOP OPENCODE:{RESET}")
            print(f"     {WHITE}Starts OpenCode routed through WARP with automatic log monitoring.{RESET}")
            print(f"     {DIM_WHITE}When OpenCode hits usage limits, it automatically rotates IP{RESET}")
            print(f"     {DIM_WHITE}and resumes without manual intervention.{RESET}\n")
            
            print(f"  {RED}2. ROTATE IP:{RESET}")
            print(f"     {WHITE}Instantly changes your IP via Cloudflare WARP (~15 seconds).{RESET}")
            print(f"     {DIM_WHITE}Use when OpenCode hits a rate limit and you want a fresh IP{RESET}")
            print(f"     {DIM_WHITE}without signing out.{RESET}\n")
            
            print(f"  {RED}3. DEEP RESET:{RESET}")
            print(f"     {WHITE}Emergency reset when your account quota is completely exhausted.{RESET}")
            print(f"     {DIM_WHITE}• Archives your chats to: Desktop\\opencode_chats_archiviate{RESET}")
            print(f"     {DIM_WHITE}• Wipes old tokens and local cache{RESET}")
            print(f"     {DIM_WHITE}• Generates fresh IP. On next sign-in, usage quota resets!{RESET}\n")
            
            print(f"  {RED}4. CONTROL KEYS:{RESET}")
            print(f"     {WHITE}W{RESET} or {WHITE}↑{RESET}   : Move up")
            print(f"     {WHITE}S{RESET} or {WHITE}↓{RESET}   : Move down")
            print(f"     {WHITE}ENTER{RESET}   : Select option")
            print(f"     {WHITE}ESC{RESET}     : Exit application\n")
            
            print(f"  {RED}5. REQUIREMENTS (WARP & PROXY PORT 40000):{RESET}")
            print(f"     {WHITE}• Requires Cloudflare WARP installed: {RED}https://1.1.1.1/{RESET}")
            print(f"     {WHITE}• NO manual proxy or port configuration is needed!{RESET}")
            print(f"     {DIM_WHITE}  CodeOpen configures proxy mode on local port 40000 100%{RESET}")
            print(f"     {DIM_WHITE}  automatically through warp-cli commands.{RESET}\n")
            
        print(f"  {DIM_WHITE}{'─' * 65}{RESET}")
        print(f"  {DIM_WHITE}{self.t('press_key')}...{RESET}")
        msvcrt.getch()
        self.update_menu_options()
    
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
