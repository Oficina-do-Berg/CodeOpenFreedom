"""
CodeOpen - Interface CLI v3 (BLESSED - SEM PISCAR)
by OFICINA-DO-BERG
"""

import sys
from blessed import Terminal

from core import Config, ConnectionManager, OpenCodeManager, IPRotator, LogMonitor, Orchestrator
from utils.logger import get_logger

logger = get_logger(__name__)
term = Terminal()

# Logo
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
        'connection': 'Conexao',
        'ip': 'IP',
        'opencode': 'OpenCode',
        'monitor': 'Monitor',
        'rotations': 'Rotacoes',
        'disconnected': 'Desconectado',
        'active': 'ATIVO',
        'stopped': 'PARADO',
        'inactive': 'INATIVO',
        'auto_mode': 'MODO AUTOMATICO',
        'start': 'INICIAR',
        'stop': 'PARAR',
        'rotate_ip': 'ROTACIONAR IP',
        'connection_menu': 'CONEXAO',
        'exit': 'SAIR',
        'navigate': 'Use W/S ou ↑/↓ para navegar | ENTER para selecionar | ESC para sair',
        'connect_warp': 'CONECTAR WARP',
        'disconnect': 'DESCONECTAR',
        'rotate': 'ROTACIONAR',
        'back': 'VOLTAR',
        'press_key': 'Pressione qualquer tecla',
        'status': 'Status'
    },
    'en': {
        'connection': 'Connection',
        'ip': 'IP',
        'opencode': 'OpenCode',
        'monitor': 'Monitor',
        'rotations': 'Rotations',
        'disconnected': 'Disconnected',
        'active': 'ACTIVE',
        'stopped': 'STOPPED',
        'inactive': 'INACTIVE',
        'auto_mode': 'AUTO MODE',
        'start': 'START',
        'stop': 'STOP',
        'rotate_ip': 'ROTATE IP',
        'connection_menu': 'CONNECTION',
        'exit': 'EXIT',
        'navigate': 'Use W/S or ↑/↓ to navigate | ENTER to select | ESC to exit',
        'connect_warp': 'CONNECT WARP',
        'disconnect': 'DISCONNECT',
        'rotate': 'ROTATE',
        'back': 'BACK',
        'press_key': 'Press any key',
        'status': 'Status'
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
            self.connection,
            self.opencode,
            self.rotator,
            self.monitor,
            self.config
        )
        self.current_option = 0
        self.lang = lang
        self.update_menu_options()
    
    def update_menu_options(self):
        """Atualiza opções do menu com idioma atual"""
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
        """Traduz chave"""
        return TRANSLATIONS[self.lang].get(key, key)
    
    def draw_screen(self):
        """Desenha a tela completa SEM PISCAR"""
        # Limpar e posicionar cursor no topo
        print(term.home + term.clear, end='')
        
        # Logo (vermelho)
        print(term.bold_red(LOGO))
        print()
        
        # Status
        status = self.orchestrator.get_status()
        
        # Cabeçalho da tabela
        print(f"  {term.white(self.t('connection')): <12} ", end='')
        conn = status['connection']
        if conn['connected']:
            print(term.red(f"{conn['method']}: {conn['ip']}"))
        else:
            print(term.white(self.t('disconnected')))
        
        print(f"  {term.white(self.t('opencode')): <12} ", end='')
        if status['opencode_running']:
            print(term.red(self.t('active')))
        else:
            print(term.white(self.t('stopped')))
        
        print(f"  {term.white(self.t('monitor')): <12} ", end='')
        if status['monitoring']:
            print(term.red(self.t('active')))
        else:
            print(term.white(self.t('inactive')))
        
        print(f"  {term.white(self.t('rotations')): <12} {term.red(str(status['rotation_count']))}")
        
        print()
        print(term.dim_white("─" * 70))
        print()
        
        # Menu
        for i, (label, _) in enumerate(self.menu_options):
            if i == self.current_option:
                print(f"  {term.red('>')} {term.bold_red(f'[ {label} ]')}")
            else:
                print(f"    {term.dim_white(f'[ {label} ]')}")
        
        print()
        print(f"  {term.dim_white(self.t('navigate'))}")
    
    def main_menu(self):
        """Menu principal COM BLESSED"""
        with term.cbreak(), term.hidden_cursor():
            self.draw_screen()
            
            while True:
                key = term.inkey(timeout=0.05)
                
                if key.code == term.KEY_UP or key.lower() == 'w':
                    self.current_option = (self.current_option - 1) % len(self.menu_options)
                    self.draw_screen()
                
                elif key.code == term.KEY_DOWN or key.lower() == 's':
                    self.current_option = (self.current_option + 1) % len(self.menu_options)
                    self.draw_screen()
                
                elif key.code == term.KEY_ENTER or key == '\r' or key == '\n':
                    _, action = self.menu_options[self.current_option]
                    
                    if action == self.exit_app:
                        action()
                        return
                    
                    # Executar ação em tela cheia
                    print(term.home + term.clear, end='')
                    action()
                    
                    # Redesenha menu
                    self.draw_screen()
                
                elif key.code == term.KEY_ESCAPE or key.lower() == 'q':
                    self.exit_app()
                    return
    
    def start_automatic_mode(self):
        """Inicia modo automático"""
        print(term.home + term.clear, end='')
        print()
        print(f"  {term.bold_red('MODO AUTOMATICO')}")
        print(f"  {term.dim_white('─' * 40)}")
        print()
        print(f"  {term.white('Iniciando fluxo automatico...')}")
        print()
        print(f"  {term.dim_white(self.t('press_key'))}...")
        
        with term.cbreak():
            term.inkey()
    
    def start_opencode(self):
        """Inicia OpenCode"""
        print(term.home + term.clear, end='')
        print()
        print(f"  {term.white('Iniciando OpenCode...')}")
        
        success = self.opencode.start()
        
        print()
        if success:
            print(f"  {term.red('>')} OpenCode iniciado")
        else:
            print(f"  {term.red('ERRO')} Falha ao iniciar")
        
        print()
        print(f"  {term.dim_white(self.t('press_key'))}...")
        
        with term.cbreak():
            term.inkey()
    
    def stop_opencode(self):
        """Para OpenCode"""
        print(term.home + term.clear, end='')
        print()
        print(f"  {term.white('Parando OpenCode...')}")
        
        success = self.opencode.stop()
        
        print()
        if success:
            print(f"  {term.red('>')} OpenCode parado")
        else:
            print(f"  {term.red('ERRO')} Falha ao parar")
        
        print()
        print(f"  {term.dim_white(self.t('press_key'))}...")
        
        with term.cbreak():
            term.inkey()
    
    def rotate_ip(self):
        """Rotaciona IP"""
        print(term.home + term.clear, end='')
        print()
        print(f"  {term.white('Rotacionando IP...')}")
        
        success = self.rotator.rotate()
        
        print()
        if success:
            print(f"  {term.red('>')} IP rotacionado")
        else:
            print(f"  {term.red('ERRO')} Falha na rotacao")
        
        print()
        print(f"  {term.dim_white(self.t('press_key'))}...")
        
        with term.cbreak():
            term.inkey()
    
    def connection_menu(self):
        """Menu de conexão"""
        conn_options = [
            (self.t('connect_warp'), 'connect_warp'),
            (self.t('disconnect'), 'disconnect'),
            (self.t('rotate'), 'rotate'),
            (self.t('back'), 'back')
        ]
        current = 0
        
        def draw_conn_menu():
            print(term.home + term.clear, end='')
            print()
            print(f"  {term.bold_red('CONEXAO')}")
            print()
            
            status = self.connection.get_status()
            if status['connected']:
                print(f"  {term.white('Status')}: {term.red(status['method'])}")
                print(f"  {term.white('IP')}: {term.white(status['ip'])}")
            else:
                print(f"  {term.white('Status')}: {term.dim_white(self.t('disconnected'))}")
            
            print()
            print(term.dim_white("─" * 70))
            print()
            
            for i, (label, _) in enumerate(conn_options):
                if i == current:
                    print(f"  {term.red('>')} {term.bold_red(f'[ {label} ]')}")
                else:
                    print(f"    {term.dim_white(f'[ {label} ]')}")
            
            print()
            print(f"  {term.dim_white('Use W/S | ENTER | ESC')}")
        
        with term.cbreak(), term.hidden_cursor():
            draw_conn_menu()
            
            while True:
                key = term.inkey(timeout=0.05)
                
                if key.code == term.KEY_UP or key.lower() == 'w':
                    current = (current - 1) % len(conn_options)
                    draw_conn_menu()
                
                elif key.code == term.KEY_DOWN or key.lower() == 's':
                    current = (current + 1) % len(conn_options)
                    draw_conn_menu()
                
                elif key.code == term.KEY_ENTER or key == '\r' or key == '\n':
                    label, action_name = conn_options[current]
                    
                    if action_name == 'back':
                        return
                    
                    print(term.home + term.clear, end='')
                    print()
                    print(f"  {term.white(label)}...")
                    
                    if action_name == 'connect_warp':
                        success, msg = self.connection.connect('WARP')
                    elif action_name == 'disconnect':
                        success, msg = self.connection.disconnect()
                    elif action_name == 'rotate':
                        success, msg = self.connection.rotate_warp_ip()
                    
                    print()
                    print(f"  {term.white(msg)}")
                    print()
                    print(f"  {term.dim_white(self.t('press_key'))}...")
                    
                    term.inkey()
                    draw_conn_menu()
                
                elif key.code == term.KEY_ESCAPE:
                    return
    
    def exit_app(self):
        """Sai da aplicação"""
        print(term.home + term.clear, end='')
        print()
        print()
        print(f"  {term.bold_red('CodeOpen')}")
        print(f"  {term.dim_white('by OFICINA-DO-BERG')}")
        print()
        print(f"  {term.dim_white('Encerrando...')}")
        print()
        
        if self.orchestrator.get_status()['monitoring']:
            self.orchestrator.stop_flow()
        
        if self.orchestrator.get_status()['opencode_running']:
            self.opencode.stop()


if __name__ == "__main__":
    # Pegar idioma dos argumentos
    lang = 'pt'
    if len(sys.argv) > 1:
        lang = sys.argv[1]
    
    cli = CodeOpenCLI(lang=lang)
    
    try:
        cli.main_menu()
    except KeyboardInterrupt:
        cli.exit_app()
