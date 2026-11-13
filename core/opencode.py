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
            
            # No Windows, usar 'start' para abrir em nova janela
            if os.name == 'nt':
                # Construir comando com 'start'
                cmd_parts = ['start', 'opencode']
                if folder:
                    cmd_parts.append(f'"{folder}"')
                
                cmd_str = ' '.join(cmd_parts)
                
                # Usar shell=True com cmd /c para funcionar corretamente
                self.process = subprocess.Popen(
                    cmd_str,
                    env=env,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            else:
                # Linux/Mac - método original
                cmd = [self.opencode_path]
                if folder:
                    cmd.append(folder)
                
                self.process = subprocess.Popen(
                    cmd,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
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
    
    def get_config_folder(self) -> Path:
        """Retorna pasta de configuração do OpenCode"""
        return Path.home() / ".config" / "opencode"
    
    def get_data_folder(self) -> Path:
        """Retorna pasta de dados do OpenCode (igual ao original C++: opencodeDataDir)"""
        return Path.home() / ".local" / "share" / "opencode"
    
    def get_cache_folder(self) -> Path:
        """Retorna pasta de cache do OpenCode (igual ao original C++: opencodeCacheDir)"""
        return Path.home() / ".cache" / "opencode"
    
    def get_auth_file(self) -> Path:
        """
        Retorna caminho do arquivo de autenticação.
        
        IMPORTANTE: O original C++ usa ~/.local/share/opencode/auth.json
        Mas versões mais novas do OpenCode usam ~/.config/opencode/service.json
        Verificamos ambos.
        """
        # Primeiro verificar o caminho clássico (auth.json)
        classic = self.get_data_folder() / "auth.json"
        if classic.exists():
            return classic
        
        # Verificar service.json (versão mais recente do OpenCode)
        service = self.get_config_folder() / "service.json"
        if service.exists():
            return service
        
        # Retornar o clássico como fallback
        return classic
    
    def get_token_snapshot_dir(self) -> Path:
        """
        Retorna diretório do snapshot DPAPI do launcher original.
        Original C++: %LOCALAPPDATA%/opencode-infinite/auth_snapshot/
        """
        return Path(os.environ.get('LOCALAPPDATA', '')) / "opencode-infinite" / "auth_snapshot"
    
    def get_token_snapshot_file(self) -> Path:
        """Retorna arquivo de snapshot DPAPI"""
        return self.get_token_snapshot_dir() / "auth.dpapi"
    
    def get_chat_files(self) -> list[Path]:
        """Retorna arquivos de chat/banco de dados"""
        data_folder = self.get_data_folder()
        return [
            data_folder / "opencode.db",
            data_folder / "opencode.db-wal",
            data_folder / "opencode.db-shm",
        ]
    
    def get_storage_folder(self) -> Path:
        """Retorna pasta de storage (arquivos dos chats)"""
        return self.get_data_folder() / "storage"
    
    def drop_token_snapshot(self, reason: str) -> None:
        """
        Deleta o snapshot DPAPI do launcher original (igual ao tokenDropSnapshot() do C++).
        
        SEM ISSO, o launcher original restaura auth.json automaticamente na próxima abertura!
        Também deleta cópia plaintext legada se existir.
        """
        snapshot_file = self.get_token_snapshot_file()
        if snapshot_file.exists():
            try:
                snapshot_file.unlink()
                logger.info(f"🗑️ Snapshot DPAPI deletado: {snapshot_file} (reason: {reason})")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao deletar snapshot DPAPI: {e}")
        
        # Deletar cópia plaintext legada (igual ao original)
        legacy = self.get_token_snapshot_dir() / "auth.json"
        if legacy.exists():
            try:
                legacy.unlink()
                logger.info(f"🗑️ Snapshot legado deletado: {legacy}")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao deletar snapshot legado: {e}")
    
    def backup_auth(self) -> bool:
        """Faz backup do arquivo de autenticação (auth.json ou service.json)"""
        auth_file = self.get_auth_file()
        if not auth_file.exists():
            logger.warning("⚠️ Arquivo de auth não encontrado para backup")
            return False
        
        try:
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = Path(os.environ.get('LOCALAPPDATA', '')) / "opencode-infinite" / "backup" / "auth" / timestamp
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            backup_file = backup_dir / auth_file.name
            shutil.copy2(auth_file, backup_file)
            logger.info(f"✅ Backup de auth criado: {backup_file}")
            return True
        except Exception as e:
            logger.error(f"❌ Erro ao fazer backup de auth: {e}")
            return False

    def clear_tokens(self, reason: str) -> bool:
        """
        Deleta tokens de autenticação (igual ao clearTokens() do original C++).
        
        FLUXO ORIGINAL:
        1. Localiza auth.json (ou service.json)
        2. Faz backup verificado em %LOCALAPPDATA%/opencode-infinite/backup/auth/<stamp>/
        3. Deleta snapshot DPAPI (impede restauração automática pelo launcher)
        4. Deleta o arquivo de auth
        
        Retorna True se deletou, False se não encontrou ou falhou.
        """
        auth_file = self.get_auth_file()
        
        if not auth_file.exists():
            # Mesmo sem auth, deletar snapshot (igual ao original: 
            # "an explicit reset: the copy must not bring the tokens back")
            self.drop_token_snapshot(reason)
            logger.warning("⚠️ Arquivo de autenticação não encontrado")
            return False
        
        try:
            # Backup no mesmo local que o original: %LOCALAPPDATA%/opencode-infinite/backup/auth/<stamp>/
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            backup_dir = Path(os.environ.get('LOCALAPPDATA', '')) / "opencode-infinite" / "backup" / "auth" / timestamp
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            backup_file = backup_dir / auth_file.name
            
            # Copiar e verificar tamanho (igual ao original: "no verified backup, no delete")
            shutil.copy2(auth_file, backup_file)
            if backup_file.stat().st_size != auth_file.stat().st_size:
                logger.error("❌ Backup falhou - tamanhos diferentes! Auth mantido.")
                backup_file.unlink()
                return False
            
            logger.info(f"📦 Backup: {backup_file}")
            
            # Deletar snapshot DPAPI ANTES de deletar auth (igual ao original)
            self.drop_token_snapshot(reason)
            
            # Deletar auth
            auth_file.unlink()
            logger.info(f"🗑️ Deletado: {auth_file}, reason: {reason}")
            
            return True
                
        except Exception as e:
            logger.error(f"❌ Erro ao deletar tokens: {e}")
            return False
    
    def clear_cache(self, reason: str) -> bool:
        """
        Deleta pasta de cache do OpenCode (igual ao clearCache() do original C++).
        ~/.cache/opencode/ inteiro.
        """
        cache_folder = self.get_cache_folder()
        
        if not cache_folder.exists():
            logger.info("ℹ️ Pasta de cache não existe, nada a limpar")
            return False
        
        try:
            shutil.rmtree(cache_folder, ignore_errors=True)
            gone = not cache_folder.exists()
            if gone:
                logger.info(f"🗑️ Cache limpo: {cache_folder}, reason: {reason}")
            else:
                logger.warning(f"⚠️ Cache parcialmente limpo (alguns arquivos em uso): {cache_folder}")
            return gone
        except Exception as e:
            logger.error(f"❌ Erro ao limpar cache: {e}")
            return False
    
    def deep_reset(self, archive_root: Path = None) -> bool:
        """
        Deep reset completo (igual ao deepResetNow() do original C++).
        
        FLUXO ORIGINAL (app.cpp linhas 562-579):
        1. stopApp()                    → Para OpenCode
        2. deepReset(archiveRoot)       → Move DBs + storage para Desktop
        3. dropTokens("Deep reset")     → Backup + delete auth + delete snapshot DPAPI
        4. clearCache("Deep reset")     → Deleta ~/.cache/opencode/
        5. startDesktop()               → Reinicia OpenCode
        
        O nome da pasta no original é: Desktop/opencode_chats_archiviate/
        """
        if archive_root is None:
            archive_root = Path.home() / "Desktop" / "opencode_chats_archiviate"
        
        reason = "user action: Deep reset"
        
        try:
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            target_dir = archive_root / timestamp
            target_dir.mkdir(parents=True, exist_ok=True)
            
            moved_count = 0
            
            # ─── PASSO 1: Mover bancos de dados (igual ao original) ───
            data_folder = self.get_data_folder()
            for db_name in ["opencode.db", "opencode.db-wal", "opencode.db-shm"]:
                db_file = data_folder / db_name
                if db_file.exists():
                    dest = target_dir / db_name
                    shutil.move(str(db_file), str(dest))
                    logger.info(f"📦 Movido: {db_name}")
                    moved_count += 1
            
            # Mover pasta storage
            storage_folder = self.get_storage_folder()
            if storage_folder.exists():
                dest_storage = target_dir / "storage"
                shutil.move(str(storage_folder), str(dest_storage))
                logger.info(f"📦 Movido: storage/")
                moved_count += 1
            
            if moved_count == 0:
                logger.warning("⚠️ Nenhum chat encontrado para arquivar")
                target_dir.rmdir()
            else:
                logger.info(f"✅ {moved_count} item(ns) arquivado(s) em: {target_dir}")
            
            # ─── PASSO 2: Deletar tokens (igual ao original: dropTokens) ───
            self.clear_tokens(reason)
            
            # ─── PASSO 3: Limpar cache (igual ao original: clearCache) ───
            self.clear_cache(reason)
            
            logger.info("✅ DEEP RESET CONCLUÍDO!")
            return True
                
        except Exception as e:
            logger.error(f"❌ Erro no deep reset: {e}")
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
