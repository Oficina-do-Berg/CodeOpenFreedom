"""
Gerenciamento do OpenCode
"""

import subprocess
import psutil
import os
import shutil
from pathlib import Path
from typing import Optional, List
from utils.logger import get_logger

logger = get_logger(__name__)

class OpenCodeManager:
    """Gerencia processo e sessões do OpenCode"""
    
    def __init__(self, config):
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self.pid: Optional[int] = None
        self.opencode_path = None
        
    def find_opencode(self) -> Optional[str]:
        """Encontra instalação do OpenCode"""
        logger.info("🔍 Procurando OpenCode...")
        
        # Verificar se está no PATH
        opencode_cmd = shutil.which('opencode')
        if opencode_cmd:
            logger.info(f"✅ OpenCode encontrado: {opencode_cmd}")
            return opencode_cmd
        
        # Procurar em locais comuns
        common_paths = [
            Path.home() / ".local" / "share" / "opencode",
            Path(os.environ.get('LOCALAPPDATA', '')) / "Programs" / "OpenCode",
            Path(os.environ.get('ProgramFiles', '')) / "OpenCode",
        ]
        
        for base_path in common_paths:
            if base_path.exists():
                opencode_exe = base_path / "OpenCode.exe"
                if opencode_exe.exists():
                    logger.info(f"✅ OpenCode encontrado: {opencode_exe}")
                    return str(opencode_exe)
        
        logger.warning("⚠️ OpenCode não encontrado")
        return None
    
    def is_running(self) -> bool:
        """Verifica se OpenCode está rodando"""
        if self.pid:
            try:
                process = psutil.Process(self.pid)
                return process.is_running() and process.status() != psutil.STATUS_ZOMBIE
            except psutil.NoSuchProcess:
                self.pid = None
                self.process = None
                return False
        return False
    
    def start(self, folder: str = None, proxy_url: str = None) -> bool:
        """Inicia OpenCode"""
        if self.is_running():
            logger.warning("⚠️ OpenCode já está rodando")
            return False
        
        # Encontrar OpenCode
        if not self.opencode_path:
            self.opencode_path = self.find_opencode()
        
        if not self.opencode_path:
            logger.error("❌ OpenCode não encontrado")
            return False
        
        try:
            logger.info("▶️ Iniciando OpenCode...")
            
            # Preparar ambiente
            env = os.environ.copy()
            if proxy_url:
                env['HTTP_PROXY'] = proxy_url
                env['HTTPS_PROXY'] = proxy_url
                env['http_proxy'] = proxy_url
                env['https_proxy'] = proxy_url
                env['NO_PROXY'] = 'localhost,127.0.0.1,::1'
                env['no_proxy'] = 'localhost,127.0.0.1,::1'
                logger.info(f"🌐 Proxy configurado: {proxy_url}")
            
            # Iniciar processo
            cmd = [self.opencode_path]
            if folder:
                cmd.append(folder)
            
            self.process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
            )
            
            self.pid = self.process.pid
            logger.info(f"✅ OpenCode iniciado! PID: {self.pid}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar OpenCode: {e}")
            return False
    
    def stop(self) -> bool:
        """Para OpenCode"""
        if not self.is_running():
            logger.warning("⚠️ OpenCode não está rodando")
            return False
        
        try:
            logger.info("⏹️ Parando OpenCode...")
            process = psutil.Process(self.pid)
            process.terminate()
            process.wait(timeout=10)
            logger.info("✅ OpenCode parado")
            self.pid = None
            self.process = None
            return True
        except Exception as e:
            logger.error(f"❌ Erro ao parar OpenCode: {e}")
            return False
    
    def get_auth_file(self) -> Path:
        """Retorna caminho do arquivo auth.json"""
        return Path.home() / ".local" / "share" / "opencode" / "auth.json"
    
    def backup_auth(self) -> bool:
        """Faz backup do auth.json"""
        auth_file = self.get_auth_file()
        if not auth_file.exists():
            logger.warning("⚠️ auth.json não encontrado")
            return False
        
        try:
            backup_dir = Path.home() / ".opencode-infinity-simple" / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_dir / f"auth_{timestamp}.json"
            
            shutil.copy2(auth_file, backup_file)
            logger.info(f"✅ Backup criado: {backup_file}")
            return True
        except Exception as e:
            logger.error(f"❌ Erro ao fazer backup: {e}")
            return False
    
    def restore_auth(self, backup_file: str) -> bool:
        """Restaura auth.json de um backup"""
        try:
            auth_file = self.get_auth_file()
            shutil.copy2(backup_file, auth_file)
            logger.info(f"✅ Auth restaurado de: {backup_file}")
            return True
        except Exception as e:
            logger.error(f"❌ Erro ao restaurar: {e}")
            return False
    
    def list_backups(self) -> List[str]:
        """Lista backups disponíveis"""
        backup_dir = Path.home() / ".opencode-infinity-simple" / "backups"
        if not backup_dir.exists():
            return []
        
        backups = list(backup_dir.glob("auth_*.json"))
        return [str(b) for b in sorted(backups, reverse=True)]
