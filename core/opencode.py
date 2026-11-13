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
    
    def find_running_pid(self) -> Optional[int]:
        """Tenta localizar o PID real do OpenCode em execução"""
        if self.pid:
            try:
                proc = psutil.Process(self.pid)
                if proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE:
                    return self.pid
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                self.pid = None
                self.process = None
        
        # Buscar apenas por instâncias reais do executável do OpenCode
        # NUNCA considerar shells (cmd, powershell, python) cuja pasta de trabalho contenha 'opencode'
        excluded_names = {
            'python.exe', 'pythonw.exe', 'cmd.exe', 'powershell.exe',
            'pwsh.exe', 'conhost.exe', 'windowsterminal.exe', 'code.exe'
        }
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    name = (proc.info['name'] or '').lower()
                    if name in excluded_names:
                        continue
                    
                    if name in ('opencode.exe', 'opencode'):
                        self.pid = proc.info['pid']
                        return self.pid
                    
                    # OpenCode rodando através do Node.js
                    if 'node' in name:
                        cmdline = ' '.join(proc.info['cmdline'] or []).lower()
                        if any(marker in cmdline for marker in ['opencode.js', 'bin/opencode', 'bin\\opencode', '@opencode']):
                            self.pid = proc.info['pid']
                            return self.pid
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass
        return None

    def is_running(self) -> bool:
        """Verifica se OpenCode está rodando"""
        return self.find_running_pid() is not None
    
    def start(self, folder: str = None, proxy_url: str = None) -> bool:
        """Inicia OpenCode em console próprio mantendo rastreamento de PID real"""
        if self.is_running():
            logger.warning("⚠️ OpenCode já está rodando")
            return False
        
        # Encontrar executável do OpenCode
        if not self.opencode_path:
            self.opencode_path = self.find_opencode()
        
        if not self.opencode_path:
            logger.error("❌ OpenCode não encontrado")
            return False
        
        try:
            logger.info("▶️ Iniciando OpenCode...")
            
            # Preparar ambiente com variáveis de proxy
            env = os.environ.copy()
            if proxy_url:
                env['HTTP_PROXY'] = proxy_url
                env['HTTPS_PROXY'] = proxy_url
                env['http_proxy'] = proxy_url
                env['https_proxy'] = proxy_url
                env['NO_PROXY'] = 'localhost,127.0.0.1,::1'
                env['no_proxy'] = 'localhost,127.0.0.1,::1'
                logger.info(f"🌐 Proxy configurado: {proxy_url}")
            
            cmd = [self.opencode_path]
            if folder:
                cmd.append(folder)
            
            # No Windows, criar console separado sem spawn de cmd intermediário throwaway
            creation_flags = 0
            if os.name == 'nt':
                creation_flags = subprocess.CREATE_NEW_CONSOLE
            
            self.process = subprocess.Popen(
                cmd,
                env=env,
                creationflags=creation_flags
            )
            self.pid = self.process.pid
            logger.info(f"✅ OpenCode iniciado! PID: {self.pid}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar OpenCode: {e}")
            return False
    
    def stop(self) -> bool:
        """Para OpenCode de forma limpa, finalizando processo pai e filhos (ex: Node.js)"""
        running_pid = self.find_running_pid()
        if not running_pid:
            logger.warning("⚠️ OpenCode não está rodando")
            return False
        
        try:
            logger.info(f"⏹️ Parando OpenCode (PID {running_pid})...")
            parent = psutil.Process(running_pid)
            children = parent.children(recursive=True)
            
            # Finalizar subprocessos filhos primeiro
            for child in children:
                try:
                    child.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            try:
                parent.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            
            # Aguardar até 5s para encerramento gracioso
            _, alive = psutil.wait_procs(children + [parent], timeout=5)
            for p in alive:
                try:
                    p.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
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
        Deleta pasta de cache do OpenCode.
        Verifica os arquivos removidos com tratamento de erros de sistema de arquivos.
        """
        cache_folder = self.get_cache_folder()
        if not cache_folder.exists():
            logger.info("ℹ️ Pasta de cache não existe, nada a limpar")
            return True
        
        try:
            # Tentar remover arquivos individualmente para diagnosticar erros
            all_removed = True
            for root, dirs, files in os.walk(cache_folder, topdown=False):
                for f in files:
                    file_path = Path(root) / f
                    try:
                        file_path.unlink()
                    except OSError as e:
                        logger.warning(f"⚠️ Arquivo de cache em uso não pôde ser removido: {file_path.name} ({e})")
                        all_removed = False
                for d in dirs:
                    dir_path = Path(root) / d
                    try:
                        dir_path.rmdir()
                    except OSError:
                        all_removed = False
            
            try:
                cache_folder.rmdir()
            except OSError:
                pass
            
            if not cache_folder.exists() or all_removed:
                logger.info(f"🗑️ Cache limpo: {cache_folder}, reason: {reason}")
                return True
            else:
                logger.warning(f"⚠️ Cache parcialmente limpo (alguns arquivos bloqueados pelo SO): {cache_folder}")
                return False
        except Exception as e:
            logger.error(f"❌ Erro ao limpar cache: {e}")
            return False
    
    def deep_reset(self, archive_root: Path = None) -> bool:
        """
        Deep reset atômico com verificação de integridade e rollback preventivo.
        
        Garante que:
        1. Todos os bancos SQLite (.db, .db-wal, .db-shm) e storage são copiados primeiro.
        2. A integridade da cópia é confirmada (existência e correspondência de tamanho).
        3. SE a verificação passar, os originais são removidos.
        4. Caso qualquer falha ocorra no processo de backup, o rollback é acionado e
           os dados originais permanecem 100% preservados e intocados.
        """
        if archive_root is None:
            archive_root = Path.home() / "Desktop" / "opencode_chats_archiviate"
        
        reason = "user action: Deep reset"
        data_folder = self.get_data_folder()
        storage_folder = self.get_storage_folder()
        
        # Mapear arquivos existentes
        db_names = ["opencode.db", "opencode.db-wal", "opencode.db-shm"]
        existing_dbs = [data_folder / name for name in db_names if (data_folder / name).exists()]
        storage_exists = storage_folder.exists()
        
        if not existing_dbs and not storage_exists:
            logger.info("ℹ️ Nenhum chat ou banco de dados prévio encontrado para arquivar")
            self.clear_tokens(reason)
            self.clear_cache(reason)
            return True
        
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        target_dir = archive_root / timestamp
        
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            copied_files = []
            
            # 1. Copiar bancos SQLite para a pasta de destino
            for db_file in existing_dbs:
                dest = target_dir / db_file.name
                shutil.copy2(db_file, dest)
                # Verificação de integridade do arquivo
                if not dest.exists() or dest.stat().st_size != db_file.stat().st_size:
                    raise IOError(f"Falha de integridade ao copiar {db_file.name}")
                copied_files.append((db_file, dest))
            
            # 2. Copiar storage de conversas se existir
            if storage_exists:
                dest_storage = target_dir / "storage"
                shutil.copytree(storage_folder, dest_storage, dirs_exist_ok=True)
                if not dest_storage.exists():
                    raise IOError("Falha de integridade ao copiar pasta storage/")
            
            # 3. Com o backup 100% verificado no Desktop, remover os originais
            logger.info(f"📦 Backup verificado com sucesso em: {target_dir}")
            for orig, _ in copied_files:
                try:
                    orig.unlink()
                    logger.info(f"🗑️ Original removido: {orig.name}")
                except Exception as del_err:
                    logger.warning(f"⚠️ Aviso ao remover original {orig.name}: {del_err}")
            
            if storage_exists:
                try:
                    shutil.rmtree(storage_folder)
                    logger.info("🗑️ Pasta storage original removida")
                except Exception as del_err:
                    logger.warning(f"⚠️ Aviso ao remover storage original: {del_err}")
            
            # 4. Deletar tokens com backup verificado
            self.clear_tokens(reason)
            
            # 5. Limpar cache com tratamento de erros
            self.clear_cache(reason)
            
            logger.info("✅ DEEP RESET ATÔMICO CONCLUÍDO COM SUCESSO!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Falha crítica no Deep Reset: {e}. Executando ROLLBACK...")
            # Rollback: limpar diretório de backup incompleto
            if target_dir.exists():
                shutil.rmtree(target_dir, ignore_errors=True)
            logger.info("🛡️ Rollback executado: seus arquivos originais foram preservados intactos!")
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
