"""
Gerenciamento de Configurações
"""

import json
from pathlib import Path
from typing import Any, Dict


class Config:
    """Gerencia configurações da aplicação"""

    DEFAULT_CONFIG = {
        "connection_method": "WARP",  # WARP, Direct
        "auto_rotate": True,
        "auto_continue": True,
        "start_continue": True,       # abre o TUI na última conversa quando existir
        "warp_port": 40000,
        "max_retries": 3,             # tentativas de rotação (compatibilidade; o main usa hunt_max)
        "retry_delay": 5,             # segundos entre tentativas
        "check_ip_url": "https://www.cloudflare.com/cdn-cgi/trace",
        "language": "pt_BR",
        "theme": "dark",

        # --- retomada da conversa (equivalente ao resume_run do main) ---
        "resume_msg": "continue",
        "resume_timeout": 600,       # main: RESUME_TIMEOUT=600
        "resume_idle": 60,            # main: RESUME_IDLE=60 (mata só se ficar sem saída)
        "resume_auto": True,          # passa --auto no run -c

        # --- prova da rota/modelo novo (equivalente ao probe do main) ---
        "probe_enabled": True,
        "probe_timeout": 60,          # main (desktop): 60s por probe
        "probe_model": "",            # vazio = usa o modelo da própria conversa
        "debug_keep_probe_sessions": False,

        # --- caçada de IP (mesma lógica do main) ---
        "hunt_max": 10,              # tentativas de rotação por desbloqueio (main: 10 desktop / 20 .bat)
        "probe_broken_max": 2,       # probes quebrados seguidos antes de aceitar sem probe

        # --- troca de modelo (fallback do LIMIT_ACTION=provider do .bat) ---
        "max_model_switches": 5,     # modelos testados no fallback
        "model_candidates": [],       # modelos extras, ex.: ["meuprovider/modelo"]
        "last_good_model": "",       # último modelo que passou no probe
        "model_switch_fallback": True,

        # --- anti-loop (equivalente ao LIMIT_ROT_MAX do .bat) ---
        "limit_rot_max": 3,          # desbloqueios seguidos sem resolver antes de pausar (0 = nunca pausar)

        # --- watcher ---
        "settle_seconds": 4,          # espera o bloco de erro terminar; nunca cancela o limite
        "rotate_on_rate_limit": False # rate limit puro é temporário; rotação só manual
    }

    def __init__(self):
        self.config_dir = Path.home() / ".opencode-infinity-simple"
        self.config_file = self.config_dir / "config.json"
        self.config: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Carrega configurações do arquivo"""
        self.config_dir.mkdir(parents=True, exist_ok=True)

        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                # Mesclar com defaults para novos campos
                for key, value in self.DEFAULT_CONFIG.items():
                    if key not in self.config:
                        self.config[key] = value

                # Migração: 180/120 eram os padrões antigos, menores que os
                # do main (600 de retomada + 60 de inatividade / 60 de probe).
                migrated = False
                if self.config.get('resume_timeout') == 180:
                    self.config['resume_timeout'] = self.DEFAULT_CONFIG['resume_timeout']
                    migrated = True
                if self.config.get('probe_timeout') == 120:
                    self.config['probe_timeout'] = self.DEFAULT_CONFIG['probe_timeout']
                    migrated = True
                # Anti-loop antigo (janela de tempo) virou LIMIT_ROT_MAX do main.
                for key in ("max_rotations_per_window", "rotation_window_minutes"):
                    if key in self.config:
                        del self.config[key]
                        migrated = True
                if migrated:
                    self.save()
            except Exception as e:
                print(f"⚠️ Erro ao carregar config: {e}")
                self.config = self.DEFAULT_CONFIG.copy()
        else:
            self.config = self.DEFAULT_CONFIG.copy()
            self.save()

    def save(self) -> None:
        """Salva configurações no arquivo"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Erro ao salvar config: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Obtém valor de configuração"""
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Define valor de configuração"""
        self.config[key] = value
        self.save()

    def reset(self) -> None:
        """Reseta configurações para padrão"""
        self.config = self.DEFAULT_CONFIG.copy()
        self.save()
