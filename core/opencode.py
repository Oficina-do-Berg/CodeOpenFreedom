"""
Gerenciamento do OpenCode

Correções principais em relação à versão antiga:
- o TUI e o serviço de background (v2) são processos diferentes; só o TUI
  iniciado pelo launcher é parado;
- o TUI, o probe e a retomada rodam com --standalone quando disponível,
  para nascerem com o proxy novo em vez de reutilizarem o serviço antigo;
- a retomada é real: `opencode run --auto -c "continue"`;
- o auth correto é ~/.local/share/opencode/auth.json (nunca service.json).
"""

import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import List, Optional, Tuple

import psutil

from utils.logger import get_logger

logger = get_logger(__name__)

_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_CREATE_NEW_CONSOLE = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)

# Subcomandos do CLI que NÃO são o TUI interativo
_CLI_SUBCOMMANDS = {
    "serve", "run", "session", "service", "auth", "models", "api",
    "debug", "mcp", "plugin", "stats", "upgrade", "update", "uninstall",
    "acp", "mini", "reload", "pair",
}


class OpenCodeManager:
    """Gerencia processo e sessões do OpenCode"""

    def __init__(self, config):
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self.pid: Optional[int] = None
        self.opencode_path: Optional[str] = None
        self.working_dir: Optional[str] = None

        self._pid_create_time: Optional[float] = None
        self._supports_standalone: Optional[bool] = None
        self._supports_service: Optional[bool] = None

    # --------------------------------------------------------------- descoberta
    def find_opencode(self) -> Optional[str]:
        """Encontra a instalação do OpenCode."""
        if self.opencode_path:
            return self.opencode_path

        logger.info("🔍 Procurando OpenCode...")

        candidates = [
            shutil.which("opencode"),
            str(Path(os.environ.get("APPDATA", "")) / "npm" / "opencode.cmd"),
            str(Path(os.environ.get("APPDATA", "")) / "npm" / "opencode.exe"),
            str(Path.home() / ".opencode" / "bin" / "opencode.exe"),
            str(Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "OpenCode" / "OpenCode.exe"),
            str(Path(os.environ.get("ProgramFiles", "")) / "OpenCode" / "OpenCode.exe"),
        ]

        for candidate in candidates:
            if candidate and Path(candidate).exists():
                self.opencode_path = candidate
                logger.info(f"✅ OpenCode encontrado: {candidate}")
                return candidate

        logger.warning("⚠️ OpenCode não encontrado")
        return None

    def _build_env(self, proxy_url: Optional[str]) -> dict:
        """Ambiente do processo, com o proxy da rota atual."""
        env = os.environ.copy()
        if proxy_url:
            for key in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
                env[key] = proxy_url
            env["NO_PROXY"] = "localhost,127.0.0.1,::1"
            env["no_proxy"] = "localhost,127.0.0.1,::1"
        else:
            for key in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
                env.pop(key, None)
        return env

    @staticmethod
    def _cmdline_parts(proc) -> list:
        try:
            return list(proc.info.get("cmdline") or [])
        except Exception:
            return []

    @classmethod
    def _cmdline(cls, proc) -> str:
        return " ".join(cls._cmdline_parts(proc))

    @staticmethod
    def _subcommand(parts) -> str:
        """Primeiro argumento que não é flag, script ou executável."""
        if isinstance(parts, str):
            parts = parts.split()

        tokens = list(parts)[1:]
        # No node, o primeiro argumento é o script (ex.: opencode.js)
        while tokens and tokens[0].lower().endswith((".exe", ".cmd", ".bat", ".js", ".mjs", ".cjs")):
            tokens = tokens[1:]

        for token in tokens:
            value = token.lower()
            if value.startswith("-"):
                continue
            return value
        return ""

    def _is_tui_cmdline(self, parts) -> bool:
        return self._subcommand(parts) not in _CLI_SUBCOMMANDS

    def find_running_pid(self) -> Optional[int]:
        """PID do TUI do OpenCode. Nunca retorna o `serve --service`."""
        if self.pid:
            try:
                proc = psutil.Process(self.pid)
                alive = proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
                same_process = True
                if alive and self._pid_create_time:
                    same_process = abs(proc.create_time() - self._pid_create_time) < 1.0
                if alive and same_process:
                    return self.pid
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

            self.pid = None
            self.process = None
            self._pid_create_time = None

        excluded_names = {
            "python.exe", "pythonw.exe", "cmd.exe", "powershell.exe",
            "pwsh.exe", "conhost.exe", "windowsterminal.exe", "code.exe",
        }

        try:
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    name = (proc.info.get("name") or "").lower()
                    if name in excluded_names:
                        continue

                    parts = self._cmdline_parts(proc)
                    cmdline = " ".join(parts)
                    low = cmdline.lower()

                    if name in ("opencode.exe", "opencode", "opencode.cmd"):
                        if self._is_tui_cmdline(parts):
                            return proc.info["pid"]
                        continue

                    if "node" in name and any(
                        marker in low
                        for marker in ("opencode.js", "bin/opencode", "bin\\opencode", "@opencode")
                    ):
                        if self._is_tui_cmdline(parts):
                            return proc.info["pid"]
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            logger.debug(f"Falha ao procurar processos: {e}")

        return None

    def find_service_pid(self) -> Optional[int]:
        """PID do serviço de background do OpenCode v2, se existir."""
        try:
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    name = (proc.info.get("name") or "").lower()
                    if name not in ("opencode.exe", "opencode", "opencode.cmd"):
                        continue

                    parts = self._cmdline_parts(proc)
                    low_parts = [p.lower() for p in parts]
                    # `run --standalone` também sobe um `serve --stdio`; esse
                    # servidor pertence à sessão, não ao serviço de background.
                    if "--service" in low_parts:
                        return proc.info["pid"]
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass
        return None

    def is_running(self) -> bool:
        """True somente quando existe um TUI do OpenCode."""
        return self.find_running_pid() is not None

    def is_service_running(self) -> bool:
        return self.find_service_pid() is not None

    # ------------------------------------------------------------------ execução
    def _kill_tree(self, pid: int) -> bool:
        try:
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False

        for child in children:
            try:
                child.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        try:
            parent.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        _, alive = psutil.wait_procs(children + [parent], timeout=5)
        for proc in alive:
            try:
                proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return True

    def stop(self) -> bool:
        """Para apenas o TUI que este launcher controla."""
        running_pid = self.find_running_pid()
        if not running_pid:
            logger.warning("⚠️ OpenCode (TUI) não está rodando")
            return False

        logger.info(f"⏹️ Parando OpenCode TUI (PID {running_pid})...")
        self._kill_tree(running_pid)

        # espera o processo sumir para o start() não recusar em seguida
        deadline = time.time() + 5
        while time.time() < deadline:
            if not self.find_running_pid():
                break
            time.sleep(0.2)

        self.pid = None
        self.process = None
        self._pid_create_time = None
        logger.info("✅ OpenCode TUI parado")
        return True

    def stop_service(self) -> bool:
        """Para o serviço de background do v2 (usado no deep reset)."""
        if not self.find_service_pid():
            return True

        if self.supports_service():
            self._run_cli(["service", "stop"], timeout=20)

        time.sleep(0.5)
        pid = self.find_service_pid()
        if pid:
            self._kill_tree(pid)

        logger.info("✅ Serviço de background parado")
        return True

    def supports_standalone(self) -> bool:
        """O CLI tem --standalone? (OpenCode v2)"""
        if self._supports_standalone is None:
            result = self._run_cli(["--help"], timeout=20)
            text = (result.stdout or "") + (result.stderr or "")
            self._supports_standalone = "--standalone" in text
        return bool(self._supports_standalone)

    def supports_service(self) -> bool:
        """O CLI tem `service`? (OpenCode v2)"""
        if self._supports_service is None:
            result = self._run_cli(["service", "--help"], timeout=20)
            text = (result.stdout or "") + (result.stderr or "")
            self._supports_service = result.returncode == 0 and "status" in text.lower()
        return bool(self._supports_service)

    def _run_cli(self, args: List[str], proxy_url: Optional[str] = None,
                 cwd: Optional[str] = None, timeout: int = 60) -> subprocess.CompletedProcess:
        """Roda o CLI sem janela e captura a saída.

        Em timeout, mata a árvore inteira. O opencode.CMD do Windows é um
        wrapper: matar só o cmd.exe deixaria o node filho rodando, segurando
        a rota antiga e o banco aberto.
        """
        if not self.opencode_path:
            self.find_opencode()

        cmd = ([self.opencode_path] if self.opencode_path else ["opencode"]) + list(args)
        if not self.opencode_path:
            return subprocess.CompletedProcess(cmd, 127, "", "OpenCode não encontrado")

        env = self._build_env(proxy_url)
        workdir = cwd or self.working_dir or os.getcwd()

        proc = None
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=workdir,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=_CREATE_NO_WINDOW,
            )
            try:
                out, err = proc.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                self._kill_tree(proc.pid)
                try:
                    out, err = proc.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    out, err = "", ""
                return subprocess.CompletedProcess(
                    cmd, 124, out or "", (err or "") + "\n[timeout]"
                )

            return subprocess.CompletedProcess(cmd, proc.returncode, out or "", err or "")
        except FileNotFoundError:
            return subprocess.CompletedProcess(cmd, 127, "", "OpenCode não encontrado")
        except Exception as e:
            if proc is not None and proc.poll() is None:
                self._kill_tree(proc.pid)
            return subprocess.CompletedProcess(cmd, 1, "", str(e))

    def start(self, folder: Optional[str] = None, proxy_url: Optional[str] = None,
              continue_session: bool = False, _allow_standalone: bool = True) -> bool:
        """Abre o TUI em um console próprio, com o proxy atual."""
        if self.is_running():
            logger.warning("⚠️ O TUI do OpenCode já está rodando")
            return False

        if not self.opencode_path:
            self.find_opencode()
        if not self.opencode_path:
            logger.error("❌ OpenCode não encontrado")
            return False

        if folder:
            self.working_dir = os.path.abspath(folder)
        elif not self.working_dir:
            self.working_dir = os.getcwd()

        standalone = bool(_allow_standalone and self.supports_standalone())
        args = ["--standalone"] if standalone else []
        if continue_session:
            args.append("--continue")

        cmd = [self.opencode_path] + args
        env = self._build_env(proxy_url)
        creationflags = _CREATE_NEW_CONSOLE if os.name == "nt" else 0

        try:
            logger.info(
                "▶️ Iniciando OpenCode TUI"
                + (" (--standalone)" if standalone else "")
                + (" (--continue)" if continue_session else "")
            )
            self.process = subprocess.Popen(
                cmd,
                cwd=self.working_dir,
                env=env,
                creationflags=creationflags,
            )
            self.pid = self.process.pid
            try:
                self._pid_create_time = psutil.Process(self.pid).create_time()
            except Exception:
                self._pid_create_time = None

            # um TUI que morre em 2 s é argumento inválido (ex.: --continue sem sessão)
            time.sleep(2.0)
            returncode = self.process.poll()
            if returncode is not None:
                logger.warning(f"⚠️ OpenCode fechou imediatamente (rc={returncode})")
                self.pid = None
                self.process = None
                self._pid_create_time = None

                if continue_session:
                    logger.info("↩️ Tentando abrir sem --continue...")
                    return self.start(folder, proxy_url, False, _allow_standalone)
                if standalone:
                    logger.info("↩️ Tentando abrir sem --standalone...")
                    return self.start(folder, proxy_url, False, False)
                return False

            logger.info(f"✅ OpenCode TUI iniciado (PID {self.pid})")
            return True

        except Exception as e:
            logger.error(f"❌ Erro ao iniciar OpenCode: {e}")
            self.pid = None
            self.process = None
            return False

    # --------------------------------------------------------------- probe/resume
    @staticmethod
    def _looks_limited(text: str) -> bool:
        if not text:
            return False
        return bool(re.search(
            r"(free usage limit|usage limit reached|out of usage|insufficient credits|"
            r"payment required|not available in your country|quota exceeded|"
            r"ip (?:is )?blocked|403.*region|region.*403)",
            text,
            re.IGNORECASE,
        ))

    def probe(self, proxy_url: Optional[str], cwd: Optional[str] = None,
              model: Optional[str] = None) -> Tuple[str, str]:
        """Testa a rota nova com uma chamada real e apaga a sessão de teste.

        Retorna: ('ok'|'burned'|'broken'|'timeout', detalhe)
        """
        if not self.config.get("probe_enabled", True):
            return "ok", "probe desativado"

        probe_model = model or self.config.get("probe_model") or ""
        workdir = cwd or str(Path.home())
        timeout = int(self.config.get("probe_timeout", 120))

        args = ["run", "--format", "json", "--title", "ocinfinite-probe", "--auto"]
        if probe_model:
            args += ["--model", probe_model]
        if self.supports_standalone():
            args.append("--standalone")
        args.append("reply with just: ok")

        logger.info("🧪 Testando a rota nova com uma chamada de modelo...")
        result = self._run_cli(args, proxy_url=proxy_url, cwd=workdir, timeout=timeout)
        output = (result.stdout or "") + "\n" + (result.stderr or "")

        # limpa a sessão do probe para o --continue continuar apontando para o chat
        session = re.search(r"ses_[A-Za-z0-9]+", output)
        if session and not self.config.get("debug_keep_probe_sessions", False):
            delete_args = ["session", "delete", session.group(0)]
            if self.supports_standalone():
                delete_args = ["--standalone"] + delete_args
            self._run_cli(delete_args, proxy_url=proxy_url, cwd=workdir, timeout=20)

        if self._looks_limited(output):
            return "burned", output[-500:]
        if result.returncode == 0:
            return "ok", ""
        if result.returncode == 124:
            return "timeout", "o probe não respondeu a tempo"
        return "broken", output[-500:]

    def resume(self, proxy_url: Optional[str], cwd: Optional[str] = None) -> Tuple[str, str]:
        """Continua a última conversa na rota nova.

        Retorna: ('ok'|'limit'|'no_session'|'auth'|'timeout'|'error', detalhe)
        """
        if not self.config.get("auto_continue", True):
            return "ok", "auto_continue desativado"

        message = self.config.get("resume_msg") or "continue"
        args = ["run"]
        if self.config.get("resume_auto", True):
            args.append("--auto")
        if self.supports_standalone():
            args.append("--standalone")
        args += ["-c", message]

        timeout = int(self.config.get("resume_timeout", 180))
        workdir = cwd or self.working_dir or os.getcwd()

        logger.info(f"💬 Retomando a conversa: run -c \"{message}\"")
        result = self._run_cli(args, proxy_url=proxy_url, cwd=workdir, timeout=timeout)
        output = (result.stdout or "") + "\n" + (result.stderr or "")

        if self._looks_limited(output):
            return "limit", output[-500:]
        if re.search(r"no session|session not found|no such session|nothing to continue", output, re.I):
            return "no_session", output[-500:]
        if re.search(r"unauthorized|not logged in|authentication|auth required|please login|sign in", output, re.I):
            return "auth", output[-500:]
        if result.returncode == 0:
            return "ok", ""
        if result.returncode == 124:
            return "timeout", "a retomada não respondeu a tempo"
        return "error", output[-500:]

    # ------------------------------------------------------------------- pastas
    def get_config_folder(self) -> Path:
        return Path.home() / ".config" / "opencode"

    def get_data_folder(self) -> Path:
        return Path.home() / ".local" / "share" / "opencode"

    def get_cache_folder(self) -> Path:
        return Path.home() / ".cache" / "opencode"

    def get_auth_file(self) -> Path:
        """auth.json é o único arquivo de autenticação de conta.

        service.json é a senha local do sidecar do v2; nunca deve ser
        tocado por rotação/reset.
        """
        return self.get_data_folder() / "auth.json"

    def get_token_snapshot_dir(self) -> Path:
        return Path(os.environ.get("LOCALAPPDATA", "")) / "opencode-infinite" / "auth_snapshot"

    def get_token_snapshot_file(self) -> Path:
        return self.get_token_snapshot_dir() / "auth.dpapi"

    def get_chat_files(self) -> List[Path]:
        data_folder = self.get_data_folder()
        return [
            data_folder / "opencode.db",
            data_folder / "opencode.db-wal",
            data_folder / "opencode.db-shm",
        ]

    def get_storage_folder(self) -> Path:
        return self.get_data_folder() / "storage"

    # ------------------------------------------------------------------- tokens
    def drop_token_snapshot(self, reason: str) -> None:
        """Remove o snapshot DPAPI do launcher original."""
        snapshot = self.get_token_snapshot_file()
        if snapshot.exists():
            try:
                snapshot.unlink()
                logger.info(f"🗑️ Snapshot de token removido ({reason})")
            except OSError as e:
                logger.warning(f"⚠️ Não foi possível remover o snapshot: {e}")

        legacy = self.get_token_snapshot_dir() / "auth.json"
        if legacy.exists():
            try:
                legacy.unlink()
                logger.info(f"🗑️ Snapshot legado removido ({reason})")
            except OSError:
                pass

    def backup_auth(self) -> bool:
        """Faz backup verificado do auth.json."""
        auth_file = self.get_auth_file()
        if not auth_file.exists():
            logger.warning("⚠️ auth.json não encontrado para backup")
            return False

        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            backup_dir = (
                Path(os.environ.get("LOCALAPPDATA", ""))
                / "opencode-infinite" / "backup" / "auth" / timestamp
            )
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_file = backup_dir / auth_file.name
            shutil.copy2(auth_file, backup_file)

            if backup_file.stat().st_size != auth_file.stat().st_size:
                logger.error("❌ Backup falhou - tamanhos diferentes! Auth mantido.")
                backup_file.unlink()
                return False

            logger.info(f"✅ Backup de auth criado: {backup_file}")
            return True
        except Exception as e:
            logger.error(f"❌ Erro ao fazer backup de auth: {e}")
            return False

    def clear_tokens(self, reason: str) -> bool:
        """Backup verificado e remoção do auth.json (padrão do main)."""
        auth_file = self.get_auth_file()

        if not auth_file.exists():
            self.drop_token_snapshot(reason)
            logger.warning("⚠️ auth.json não encontrado; nada para limpar")
            return False

        try:
            if not self.backup_auth():
                logger.error("❌ Sem backup verificado; auth.json mantido")
                return False

            self.drop_token_snapshot(reason)
            auth_file.unlink()
            logger.info(f"🗑️ auth.json removido, reason: {reason}")
            return True
        except Exception as e:
            logger.error(f"❌ Erro ao deletar tokens: {e}")
            return False

    def clear_cache(self, reason: str) -> bool:
        cache_folder = self.get_cache_folder()
        if not cache_folder.exists():
            logger.info("ℹ️ Pasta de cache não existe, nada a limpar")
            return True

        try:
            all_removed = True
            for root, dirs, files in os.walk(cache_folder, topdown=False):
                for f in files:
                    file_path = Path(root) / f
                    try:
                        file_path.unlink()
                    except OSError as e:
                        logger.warning(f"⚠️ Cache em uso: {file_path.name} ({e})")
                        all_removed = False
                for d in dirs:
                    try:
                        (Path(root) / d).rmdir()
                    except OSError:
                        all_removed = False

            try:
                cache_folder.rmdir()
            except OSError:
                pass

            if not cache_folder.exists() or all_removed:
                logger.info(f"🗑️ Cache limpo: {cache_folder}, reason: {reason}")
                return True

            logger.warning(f"⚠️ Cache parcialmente limpo: {cache_folder}")
            return False
        except Exception as e:
            logger.error(f"❌ Erro ao limpar cache: {e}")
            return False

    def deep_reset(self, archive_root: Optional[Path] = None) -> bool:
        """Arquiva chats, limpa tokens/cache. O caller reabre o OpenCode."""
        if archive_root is None:
            archive_root = Path.home() / "Desktop" / "opencode_chats_archiviate"

        reason = "user action: Deep reset"

        # o serviço v2 mantém o banco aberto; pare antes de arquivar
        if self.is_running():
            self.stop()
        if self.is_service_running():
            self.stop_service()

        data_folder = self.get_data_folder()
        storage_folder = self.get_storage_folder()

        db_names = ["opencode.db", "opencode.db-wal", "opencode.db-shm"]
        existing_dbs = [data_folder / name for name in db_names if (data_folder / name).exists()]
        storage_exists = storage_folder.exists()

        if not existing_dbs and not storage_exists:
            logger.info("ℹ️ Nenhum chat ou banco de dados prévio encontrado")
            self.clear_tokens(reason)
            self.clear_cache(reason)
            return True

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        target_dir = archive_root / timestamp

        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            copied_files = []

            for db_file in existing_dbs:
                dest = target_dir / db_file.name
                shutil.copy2(db_file, dest)
                if not dest.exists() or dest.stat().st_size != db_file.stat().st_size:
                    raise IOError(f"Falha de integridade ao copiar {db_file.name}")
                copied_files.append((db_file, dest))

            if storage_exists:
                dest_storage = target_dir / "storage"
                shutil.copytree(storage_folder, dest_storage, dirs_exist_ok=True)
                if not dest_storage.exists():
                    raise IOError("Falha de integridade ao copiar pasta storage/")

            logger.info(f"📦 Backup verificado com sucesso em: {target_dir}")
            for orig, _ in copied_files:
                try:
                    orig.unlink()
                    logger.info(f"🗑️ Original removido: {orig.name}")
                except Exception as del_err:
                    logger.warning(f"⚠️ Aviso ao remover {orig.name}: {del_err}")

            if storage_exists:
                try:
                    shutil.rmtree(storage_folder)
                    logger.info("🗑️ Pasta storage original removida")
                except Exception as del_err:
                    logger.warning(f"⚠️ Aviso ao remover storage: {del_err}")

            self.clear_tokens(reason)
            self.clear_cache(reason)

            logger.info("✅ DEEP RESET CONCLUÍDO")
            return True

        except Exception as e:
            logger.error(f"❌ Falha crítica no Deep Reset: {e}. Executando ROLLBACK...")
            if target_dir.exists():
                shutil.rmtree(target_dir, ignore_errors=True)
            logger.info("🛡️ Rollback executado; arquivos originais preservados")
            return False

    def restore_auth(self, backup_file: str) -> bool:
        try:
            auth_file = self.get_auth_file()
            auth_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup_file, auth_file)
            logger.info(f"✅ Auth restaurado de: {backup_file}")
            return True
        except Exception as e:
            logger.error(f"❌ Erro ao restaurar: {e}")
            return False

    def list_backups(self) -> List[str]:
        backup_dir = (
            Path(os.environ.get("LOCALAPPDATA", ""))
            / "opencode-infinite" / "backup" / "auth"
        )
        if not backup_dir.exists():
            return []
        backups = list(backup_dir.glob("**/auth.json"))
        return [str(b) for b in sorted(backups, reverse=True)]
