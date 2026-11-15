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

import json
import os
import re
import shutil
import sqlite3
import subprocess
import threading
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
        self._supports_archived: Optional[bool] = None
        self._free_models: Optional[List[str]] = None

    # --------------------------------------------------------------- descoberta
    @staticmethod
    def _is_launcher_shim(path: str) -> bool:
        """O atalho criado pelo launcher do main só repassa para o npm.

        Ele não é o OpenCode de verdade; usá-lo adiciona um cmd.exe na
        árvore de processos e pode iniciar o launcher errado.
        """
        low = str(path).lower().replace("/", "\\")
        return "opencode-infinite\\bin" in low and low.endswith((".cmd", ".bat"))

    @staticmethod
    def _resolve_shim(path: str) -> str:
        """Se o caminho for um .cmd/.bat do npm, devolve o .exe vizinho."""
        p = Path(path)
        if p.suffix.lower() in (".cmd", ".bat"):
            exe = p.parent / "node_modules" / "@opencode" / "cli" / "bin" / "opencode.exe"
            if exe.is_file():
                return str(exe)
        return str(p)

    def _find_real_binary(self) -> Optional[str]:
        """Executáveis reais do OpenCode, na ordem em que o main os prefere."""
        appdata = Path(os.environ.get("APPDATA", ""))
        local = Path(os.environ.get("LOCALAPPDATA", ""))
        program_files = Path(os.environ.get("ProgramFiles", ""))

        candidates = [
            appdata / "npm" / "node_modules" / "@opencode" / "cli" / "bin" / "opencode.exe",
            appdata / "npm" / "opencode.exe",
            Path.home() / ".opencode" / "bin" / "opencode.exe",
            local / "Programs" / "OpenCode" / "OpenCode.exe",
            program_files / "OpenCode" / "OpenCode.exe",
        ]

        for candidate in candidates:
            try:
                if candidate.is_file():
                    return str(candidate)
            except OSError:
                continue
        return None

    def find_opencode(self) -> Optional[str]:
        """Encontra a instalação real do OpenCode (nunca o atalho do main)."""
        if self.opencode_path:
            return self.opencode_path

        logger.info("🔍 Procurando OpenCode...")

        real = self._find_real_binary()
        if real:
            self.opencode_path = real
            logger.info(f"✅ OpenCode encontrado: {real}")
            return real

        found = shutil.which("opencode")
        if found:
            if self._is_launcher_shim(found):
                logger.info(f"ℹ️ Ignorando o atalho do launcher: {found}")
            else:
                found = self._resolve_shim(found)
                if Path(found).is_file():
                    self.opencode_path = found
                    logger.info(f"✅ OpenCode encontrado: {found}")
                    return found

        logger.warning("⚠️ OpenCode não encontrado")
        return None

    def _build_env(self, proxy_url: Optional[str]) -> dict:
        """Ambiente do processo, com o proxy da rota atual (padrão do main)."""
        env = os.environ.copy()
        proxy_keys = (
            "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
            "http_proxy", "https_proxy", "all_proxy",
        )
        if proxy_url:
            for key in proxy_keys:
                env[key] = proxy_url
            env["NO_PROXY"] = "localhost,127.0.0.1,::1"
            env["no_proxy"] = "localhost,127.0.0.1,::1"
        else:
            for key in proxy_keys:
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

    @staticmethod
    def _same_dir(proc, expected: str) -> bool:
        """True quando o processo roda na pasta que este launcher controla."""
        try:
            actual = proc.cwd()
        except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError, OSError):
            return False
        try:
            return os.path.normcase(os.path.abspath(actual)) == os.path.normcase(
                os.path.abspath(expected)
            )
        except (TypeError, ValueError):
            return False

    def find_running_pid(self, only_dir: Optional[str] = None) -> Optional[int]:
        """PID do TUI do OpenCode. Nunca retorna o `serve --service`.

        Com only_dir, só aceita um TUI que esteja rodando naquela pasta;
        assim o launcher não para o TUI de outro projeto/launcher.
        """
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

                    is_tui = False
                    if name in ("opencode.exe", "opencode", "opencode.cmd"):
                        is_tui = self._is_tui_cmdline(parts)
                    elif "node" in name and any(
                        marker in low
                        for marker in ("opencode.js", "bin/opencode", "bin\\opencode", "@opencode")
                    ):
                        is_tui = self._is_tui_cmdline(parts)

                    if not is_tui:
                        continue
                    if only_dir and not self._same_dir(proc, only_dir):
                        continue
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

    def is_running(self, only_dir: Optional[str] = None) -> bool:
        """True somente quando existe um TUI do OpenCode."""
        target_dir = only_dir if only_dir is not None else self.working_dir
        return self.find_running_pid(only_dir=target_dir) is not None

    def is_service_running(self) -> bool:
        return self.find_service_pid() is not None

    # ------------------------------------------------------- modelo / sessão
    def _db_path(self) -> Path:
        return self.get_data_folder() / "opencode.db"

    @staticmethod
    def _model_ref(raw) -> Optional[str]:
        """Converte o JSON da coluna model em 'provider/model'."""
        if not raw:
            return None
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
        except (TypeError, ValueError):
            return None
        provider = data.get("providerID")
        model = data.get("id")
        if not provider or not model:
            return None
        return f"{provider}/{model}"

    def _connect_db(self) -> Optional[sqlite3.Connection]:
        db = self._db_path()
        if not db.exists():
            return None
        try:
            return sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=3)
        except sqlite3.Error as e:
            logger.debug(f"Banco do OpenCode indisponível: {e}")
            return None

    def latest_session(self, cwd: Optional[str] = None) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Sessão mais recente da pasta: (id, 'provider/model', diretório).

        O limite gratuito do OpenCode é por **modelo**, não por IP. Para
        retomar a conversa certa (e saber qual modelo trocar) o launcher lê
        o banco local. Qualquer falha aqui é silenciosa: o fluxo continua
        com `-c`/modelo padrão.
        """
        con = self._connect_db()
        if con is None:
            return None, None, None

        target = None
        if cwd:
            try:
                target = os.path.normcase(os.path.abspath(cwd))
            except (TypeError, ValueError):
                target = None

        try:
            rows = con.execute(
                "select id, model, directory, time_archived from session_v2 "
                "where parent_id is null order by time_updated desc limit 60"
            ).fetchall()
        except sqlite3.Error as e:
            logger.debug(f"Falha ao ler sessões: {e}")
            return None, None, None
        finally:
            con.close()

        for sid, raw_model, directory, archived in rows:
            if archived:
                continue
            if target:
                try:
                    if os.path.normcase(os.path.abspath(directory or "")) != target:
                        continue
                except (TypeError, ValueError):
                    continue
            return sid, self._model_ref(raw_model), directory

        return None, None, None

    def model_last_used(self) -> dict:
        """{model_id: último uso em ms} para ordenar os candidatos."""
        con = self._connect_db()
        if con is None:
            return {}
        usage = {}
        try:
            for raw_model, last in con.execute(
                "select model, max(time_updated) from session_v2 group by model"
            ):
                ref = self._model_ref(raw_model)
                if ref:
                    usage[ref] = int(last or 0)
        except sqlite3.Error:
            pass
        finally:
            con.close()
        return usage

    def set_session_model(self, session_id: Optional[str], model: Optional[str]) -> bool:
        """Fixa o modelo da conversa no banco local.

        O TUI não tem --model: reaberto com --continue ele volta a usar o
        modelo gravado na sessão. O `-m` da retomada vale só para aquele
        run (comprovado em campo: a sessão seguiu no modelo antigo), então
        trocar de modelo para valer exige gravar na sessão — o equivalente
        ao OC_MODEL persistente do .bat.

        Só deve ser chamado com o TUI e o serviço parados (o chamador já
        faz isso no desbloqueio).
        """
        if not session_id or not model or "/" not in model:
            return False
        provider, _, model_id = model.partition("/")
        db = self._db_path()
        if not db.exists():
            return False
        try:
            con = sqlite3.connect(f"file:{db}?mode=rw", uri=True, timeout=5)
        except sqlite3.Error as e:
            logger.debug(f"Banco do OpenCode indisponível para escrita: {e}")
            return False
        try:
            row = con.execute(
                "select model from session_v2 where id = ?", (session_id,)
            ).fetchone()
            if not row:
                return False
            try:
                data = json.loads(row[0]) if isinstance(row[0], str) else (row[0] or {})
            except (TypeError, ValueError):
                data = {}
            if not isinstance(data, dict):
                data = {}
            data["providerID"] = provider
            data["id"] = model_id
            cur = con.execute(
                "update session_v2 set model = ? where id = ?",
                (json.dumps(data), session_id),
            )
            con.commit()
            return cur.rowcount > 0
        except sqlite3.Error as e:
            logger.debug(f"Falha ao fixar o modelo da sessão: {e}")
            return False
        finally:
            con.close()

    def list_free_models(self, timeout: int = 90) -> List[str]:
        """Modelos gratuitos do provider opencode, ex.: opencode/iceman-free."""
        if self._free_models is not None:
            return self._free_models

        args = ["models"]
        if self.supports_standalone():
            # não sobe o serviço compartilhado durante um desbloqueio
            args.append("--standalone")
        result = self._run_cli(args, timeout=timeout)
        models = []
        for line in (result.stdout or "").splitlines():
            line = line.strip()
            if re.fullmatch(r"opencode/[A-Za-z0-9._-]+", line) and line.endswith("-free"):
                models.append(line)

        if models:
            self._free_models = models
        return models

    @staticmethod
    def retry_after_ms(text: str) -> int:
        """Quanto falta para a cota livre voltar (retryAfterMs da resposta 429)."""
        if not text:
            return 0
        match = re.search(r'"retryAfterMs"\s*:\s*(\d+)', text)
        return int(match.group(1)) if match else 0

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

    def stop(self, force_all: bool = False) -> bool:
        """Para o TUI que este launcher controla.

        O main registra os PIDs que iniciou e nunca mata todo `opencode.exe`
        da máquina. Aqui: primeiro o PID próprio; se ele sumiu, aceita um TUI
        rodando na mesma pasta de trabalho. Só `force_all` (reset profundo
        explícito) enxerga qualquer TUI.
        """
        target = None
        if self.pid:
            own_pid = self.pid
            found = self.find_running_pid()
            if found == own_pid:
                target = own_pid

        if not target and self.working_dir:
            target = self.find_running_pid(only_dir=self.working_dir)
        if not target and force_all:
            target = self.find_running_pid()

        if not target:
            logger.warning(
                "⚠️ Nenhum TUI do OpenCode pertence a este launcher; "
                "nada foi encerrado."
            )
            return False

        logger.info(f"⏹️ Parando OpenCode TUI (PID {target})...")
        self._kill_tree(target)

        # espera o processo sumir para o start() não recusar em seguida
        deadline = time.time() + 5
        while time.time() < deadline and psutil.pid_exists(target):
            time.sleep(0.2)

        if target == self.pid:
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

    def restart_service(self, proxy_url: Optional[str] = None) -> bool:
        """Reinicia o serviço de background (v2) sob o proxy atual (padrão do main).

        Garante que o daemon do OpenCode receba as novas variáveis de ambiente
        de proxy (HTTP_PROXY / ALL_PROXY) e encerre conexões TCP antigas.
        """
        if not self.supports_service():
            return False

        logger.info("🔄 Reiniciando serviço de background do OpenCode sob o proxy...")
        res = self._run_cli(["service", "restart"], proxy_url=proxy_url, timeout=20)
        if res.returncode == 0:
            logger.info("✅ Serviço de background reiniciado com sucesso")
            return True

        logger.warning(
            f"⚠️ Falha ou aviso ao reiniciar serviço de background: {res.stderr.strip() or res.stdout.strip()}"
        )
        return False

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

    def supports_archived(self) -> bool:
        """`run --archived` existe? (evita quebrar o probe no v1)"""
        if self._supports_archived is None:
            result = self._run_cli(["run", "--help"], timeout=20)
            text = (result.stdout or "") + (result.stderr or "")
            self._supports_archived = "--archived" in text
        return bool(self._supports_archived)

    def _run_cli(self, args: List[str], proxy_url: Optional[str] = None,
                 cwd: Optional[str] = None, timeout: int = 60,
                 idle_timeout: Optional[int] = None) -> subprocess.CompletedProcess:
        """Roda o CLI sem janela e captura a saída.

        Em timeout, mata a árvore inteira. O opencode.CMD do Windows é um
        wrapper: matar só o cmd.exe deixaria o node filho rodando, segurando
        a rota antiga e o banco aberto.

        idle_timeout replica o RESUME_IDLE do main: uma retomada longa pode
        ficar minutos trabalhando, mas se não escrever nada por N segundos
        ela está travada e é encerrada (retorno 124).
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
            if idle_timeout:
                return self._communicate_with_idle(
                    proc, cmd, timeout=timeout, idle_timeout=idle_timeout
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

    def _communicate_with_idle(self, proc, cmd: List[str], timeout: int,
                               idle_timeout: int) -> subprocess.CompletedProcess:
        """Lê stdout/stderr em threads e encerra por tempo total ou inatividade."""
        out_parts: List[str] = []
        err_parts: List[str] = []
        last_activity = [time.time()]

        def reader(pipe, parts):
            try:
                for line in iter(pipe.readline, ""):
                    parts.append(line)
                    last_activity[0] = time.time()
            except (ValueError, OSError):
                pass
            finally:
                try:
                    pipe.close()
                except OSError:
                    pass

        threads = [
            threading.Thread(target=reader, args=(proc.stdout, out_parts), daemon=True),
            threading.Thread(target=reader, args=(proc.stderr, err_parts), daemon=True),
        ]
        for thread in threads:
            thread.start()

        started = time.time()
        timed_out = False
        while proc.poll() is None:
            now = time.time()
            if now - started >= timeout:
                timed_out = True
                break
            if now - last_activity[0] >= idle_timeout:
                timed_out = True
                break
            time.sleep(0.3)

        if timed_out:
            self._kill_tree(proc.pid)

        for thread in threads:
            thread.join(timeout=5)

        out = "".join(out_parts)
        err = "".join(err_parts)
        if timed_out:
            return subprocess.CompletedProcess(cmd, 124, out, err + "\n[timeout]")
        return subprocess.CompletedProcess(cmd, proc.returncode, out, err)

    def start(self, folder: Optional[str] = None, proxy_url: Optional[str] = None,
              continue_session: bool = False, session_id: Optional[str] = None,
              _allow_standalone: bool = True) -> bool:
        """Abre o TUI em um console próprio, com o proxy atual.

        Com session_id, reabre fixado naquela conversa (`--session <id>`);
        é como o .bat retoma um chat fixado em vez do mais recente.
        """
        if folder:
            self.working_dir = os.path.abspath(folder)
        elif not self.working_dir:
            self.working_dir = os.getcwd()

        # só recusa se já houver um TUI na MESMA pasta; o TUI de outro
        # projeto/launcher não impede este de abrir.
        if self.is_running(only_dir=self.working_dir):
            logger.warning("⚠️ O TUI do OpenCode já está rodando nesta pasta")
            return False

        if not self.opencode_path:
            self.find_opencode()
        if not self.opencode_path:
            logger.error("❌ OpenCode não encontrado")
            return False

        standalone = bool(_allow_standalone and self.supports_standalone())
        args = ["--standalone"] if standalone else []
        if session_id:
            args += ["--session", session_id]
        elif continue_session:
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

                if continue_session or session_id:
                    logger.info("↩️ Tentando abrir sem fixar a conversa...")
                    return self.start(folder, proxy_url, False, None, _allow_standalone)
                if standalone:
                    logger.info("↩️ Tentando abrir sem --standalone...")
                    return self.start(folder, proxy_url, False, None, False)
                return False

            logger.info(f"✅ OpenCode TUI iniciado (PID {self.pid})")
            return True

        except Exception as e:
            logger.error(f"❌ Erro ao iniciar OpenCode: {e}")
            self.pid = None
            self.process = None
            return False

    # --------------------------------------------------------------- probe/resume
    # Probe: rota que respondeu com erro passageiro (429) também é descartada;
    # o desktop do main trata rate limit no probe como IP queimado.
    _PROBE_LIMIT = re.compile(
        r"(free usage limit|usage limit reached|out of usage|insufficient credits|"
        r"payment required|not available in your country|quota exceeded|"
        r"ip (?:is )?blocked|403.*region|region.*403|"
        r"rate limit|rate_limit_exceeded|too many requests|"
        r"status(?:code)?[=: ]*429\b|http 429\b)",
        re.IGNORECASE,
    )

    # O desktop do main só aceita a resposta que pediu ("pong"): um run que
    # termina com código 0 sem responder não prova nada sobre a rota.
    _PROBE_ANSWER = re.compile(r"\bpong\b", re.IGNORECASE)

    @staticmethod
    def _json_events(output: str) -> list:
        """Eventos NDJSON do `run --format json` (linhas que não são JSON são ignoradas)."""
        events = []
        for line in (output or "").splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if isinstance(event, dict):
                events.append(event)
        return events

    @staticmethod
    def _event_error(events: list) -> tuple:
        """(tipo, mensagem) do primeiro evento de erro do turno."""
        for event in events:
            if event.get("type") != "error":
                continue
            error = event.get("error") or {}
            return str(error.get("type") or ""), str(error.get("message") or "")
        return "", ""

    @classmethod
    def _event_is_limit(cls, error_type: str, message: str) -> bool:
        """Erro estruturado de cota (não confunde com texto da resposta)."""
        low = f"{error_type} {message}".lower()
        return (
            "free-limit" in low
            or "free usage limit" in low
            or "quota" in low
            or "usage limit" in low
        )

    @staticmethod
    def _looks_limited(text: str) -> bool:
        """Só limite de cota/região: rate limit puro é temporário (ask)."""
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

        # --archived: a sessão do probe nem aparece na lista; mesmo se a
        # limpeza falhar, o --continue não aponta para ela (padrão do main).
        args = ["run", "--format", "json", "--title", "ocinfinite-probe", "--auto"]
        if self.supports_archived():
            args.append("--archived")
        if probe_model:
            args += ["--model", probe_model]
        if self.supports_standalone():
            args.append("--standalone")
        args.append("Reply with exactly the word: pong")

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

        # Classifica por evento estruturado. O texto da resposta e as saídas
        # de ferramentas não podem marcar a rota como queimada.
        events = self._json_events(result.stdout or "")
        error_type, error_message = self._event_error(events)
        if self._event_is_limit(error_type, error_message):
            return "burned", (error_message or result.stdout or "")[-500:]

        # Padrão do desktop do main: sucesso é a resposta pedida. Um run
        # limpo sem "pong" é um probe quebrado, não uma rota aprovada.
        if result.returncode == 0:
            if self._PROBE_ANSWER.search(output):
                return "ok", ""
            return "broken", "o probe terminou sem a resposta esperada (pong)"
        if result.returncode == 124:
            return "timeout", "o probe não respondeu a tempo"
        if self._PROBE_LIMIT.search(result.stderr or ""):
            return "burned", (result.stderr or "")[-500:]
        return "broken", output[-500:]

    def resume(self, proxy_url: Optional[str], cwd: Optional[str] = None,
               model: Optional[str] = None, session_id: Optional[str] = None) -> Tuple[str, str]:
        """Continua a conversa, opcionalmente trocando o modelo.

        Trocar o modelo é o que realmente desbloqueia o limite gratuito do
        OpenCode: a cota é por modelo, não por IP. O `-m` explícito muda o
        modelo fixado na sessão, então a conversa continua com outro modelo.

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
        if model:
            args += ["-m", model]
        if session_id:
            args += ["-s", session_id]
        else:
            args.append("-c")
        args.append(message)

        timeout = int(self.config.get("resume_timeout", 180))
        workdir = cwd or self.working_dir or os.getcwd()

        target = session_id or "última conversa"
        logger.info(
            f"💬 Retomando {target}"
            + (f" com o modelo {model}" if model else "")
            + f": run {' '.join(args[1:-1])} \"{message}\""
        )
        result = self._run_cli(
            args, proxy_url=proxy_url, cwd=workdir, timeout=timeout,
            idle_timeout=int(self.config.get("resume_idle", 60) or 0) or None
        )
        output = (result.stdout or "") + "\n" + (result.stderr or "")

        # Primeiro os erros estruturados. Ler o texto inteiro da resposta
        # dava falso positivo: a própria conversa pode citar "session not
        # found" ou "usage limit" sem que a retomada tenha falhado.
        events = self._json_events(result.stdout or "")
        error_type, error_message = self._event_error(events)
        if error_type:
            low = f"{error_type} {error_message}".lower()
            if self._event_is_limit(error_type, error_message):
                return "limit", output[-500:]
            if "auth" in low:
                return "auth", output[-500:]

        if result.returncode == 0:
            return "ok", ""
        if result.returncode == 124:
            return "timeout", "a retomada não respondeu a tempo"

        stderr = (result.stderr or "").strip()
        if self._looks_limited(stderr):
            return "limit", stderr[-500:]
        if re.search(r"no session|session not found|no such session|session does not exist|unknown session|nothing to continue", stderr, re.I):
            return "no_session", stderr[-500:]
        if re.search(r"unauthorized|not logged in|authentication|auth required|please login|sign in", stderr, re.I):
            return "auth", stderr[-500:]

        # Últimos recursos (builds que imprimem o erro no stdout).
        tail = output[-800:]
        if re.search(r"no session|session not found|no such session|nothing to continue", tail, re.I):
            return "no_session", output[-500:]
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
            self.stop(force_all=True)
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
