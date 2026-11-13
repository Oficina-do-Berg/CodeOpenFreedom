"""
Gerenciamento de Configurações
"""

import json
import os
from pathlib import Path
from typing import Dict, Any

class Config:
    """Gerencia configurações da aplicação"""
    
    DEFAULT_CONFIG = {
        "connection_method": "WARP",  # WARP, Direct
        "auto_rotate": True,
        "auto_continue": True,
        "warp_port": 40000,
        "max_retries": 3,
        "retry_delay": 5,
        "check_ip_url": "https://www.cloudflare.com/cdn-cgi/trace",
        "language": "pt_BR",
        "theme": "dark"
    }
    
    def __init__(self):
        self.config_dir = Path.home() / ".opencode-infinity-simple"
        self.config_file = self.config_dir / "config.json"
        self.config: Dict[str, Any] = {}
        self.load()
    
    def load(self) -> None:
        """Carrega configurações do arquivo"""
        # Criar diretório se não existir
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                    # Mesclar com defaults para novos campos
                    for key, value in self.DEFAULT_CONFIG.items():
                        if key not in self.config:
                            self.config[key] = value
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
