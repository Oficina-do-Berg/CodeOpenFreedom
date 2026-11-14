"""
Monitor de Logs do OpenCode

Regras (as mesmas do main):
- só linhas com level=ERROR contam;
- só linhas com timestamp posterior ao início do monitoramento contam;
- noop (compactação/contexto) é ignorado antes de rotate/ask;
- rotate = limite de cota (rotaciona);
- ask   = rate limit (não rotaciona sozinho por padrão);
- depois de um erro, espera "settle_seconds" e verifica se a sessão
  voltou a ter atividade normal antes de confirmar o limite.
"""

import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from utils.logger import get_logger

logger = get_logger(__name__)


class LogMonitor:
    """Monitora logs do OpenCode em busca de limites reais"""

    # Lista do main (patterns.conf): rotate
    ROTATE_PATTERNS = [
        r'usage limit',
        r'out of usage',
        r'insufficient credits',
        r'payment required',
        r'ip (?:is )?blocked',
        r'blocked ip',
        r'403.*region',
        r'region.*403',
    ]

    # Lista do main: ask (rate limit é tratado separado)
    ASK_PATTERNS = [
        r'rate limit',
        r'rate_limit_exceeded',
        r'too many requests',
        r'status(?:code)?[=: ]*429\b',
        r'http 429\b',
    ]

    # Lista do main: noop (rotação não resolve)
    NOOP_PATTERNS = [
        r'compaction',
        r'context length exceeded',
        r'context_length_exceeded',
        r'maximum context',
        r'model not found',
        r'invalid model',
        r'providermodelnotfound',
        r'content filter',
        r'content policy',
        r'content_policy',
    ]

    # compatibilidade com versões antigas do projeto
    LIMIT_PATTERNS = ROTATE_PATTERNS + ASK_PATTERNS

    _LEVEL_ERROR = re.compile(r'\blevel=error\b', re.IGNORECASE)
    _TIMESTAMP = re.compile(r'\btimestamp=(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})')
    _INFO_AFTER = re.compile(r'\blevel=(?:info|debug)\b', re.IGNORECASE)

    def __init__(self, config, on_limit_callback: Optional[Callable] = None,
                 log_path: Optional[str] = None):
        self.config = config
        self.on_limit = on_limit_callback
        self.on_ask: Optional[Callable] = None
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.last_position = 0

        # log_path é usado pelos testes; em produção é o diretório padrão
        self.log_path = Path(log_path) if log_path else None

        self.start_time = 0.0
        self.start_utc = ""
        self._base_sizes = {}
        self._current_file: Optional[Path] = None
        self._last_trigger = 0.0
        self._generation = 0
        self._stop_event = threading.Event()

        self._rotate_re = [re.compile(p, re.IGNORECASE) for p in self.ROTATE_PATTERNS]
        self._ask_re = [re.compile(p, re.IGNORECASE) for p in self.ASK_PATTERNS]
        self._noop_re = [re.compile(p, re.IGNORECASE) for p in self.NOOP_PATTERNS]

    # ---------------------------------------------------------------- caminhos
    def _log_dir(self) -> Path:
        return Path.home() / ".local" / "share" / "opencode" / "log"

    def _get_latest_log(self) -> Optional[Path]:
        """Retorna o log mais recente do OpenCode"""
        if self.log_path:
            return self.log_path if self.log_path.exists() else None

        log_dir = self._log_dir()
        if not log_dir.exists():
            return None

        logs = []
        for p in log_dir.glob("*.log"):
            try:
                if p.is_file():
                    logs.append((p.stat().st_mtime, p))
            except OSError:
                continue

        return max(logs, key=lambda item: item[0])[1] if logs else None

    def _snapshot_sizes(self) -> dict:
        """Tamanho de cada log no instante em que o monitor começa.

        Assim um log que já existia é lido a partir do fim (nunca das linhas
        antigas), e um log criado depois é lido desde o começo.
        """
        sizes = {}
        if self.log_path:
            try:
                if self.log_path.exists():
                    sizes[str(self.log_path)] = self.log_path.stat().st_size
            except OSError:
                pass
            return sizes

        log_dir = self._log_dir()
        if not log_dir.exists():
            return sizes

        for p in log_dir.glob("*.log"):
            try:
                if p.is_file():
                    sizes[str(p)] = p.stat().st_size
            except OSError:
                continue
        return sizes

    # ------------------------------------------------------------- classificação
    def classify_line(self, line: str) -> Optional[str]:
        """Retorna 'noop', 'rotate', 'ask' ou None para uma linha do log."""
        if not line or not self._LEVEL_ERROR.search(line):
            return None

        match = self._TIMESTAMP.search(line)
        if match and self.start_utc and match.group(1) < self.start_utc:
            return None

        low = line.lower()
        if any(r.search(low) for r in self._noop_re):
            return 'noop'
        if any(r.search(low) for r in self._rotate_re):
            return 'rotate'
        if any(r.search(low) for r in self._ask_re):
            return 'ask'
        return None

    def _check_for_limits(self, text: str) -> bool:
        """Compatibilidade: True quando a linha é rotate ou ask."""
        return self.classify_line(text) in ('rotate', 'ask')

    # ------------------------------------------------------------------- leitura
    def _prime(self, path: Path) -> None:
        self._current_file = path
        self.last_position = self._base_sizes.get(str(path), 0)

    def _read_from(self, path: Path) -> str:
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(self.last_position)
                data = f.read()
                self.last_position = f.tell()
            return data
        except OSError as e:
            logger.debug(f"Falha ao ler {path}: {e}")
            return ""

    def _decide(self, text: str, path: Path) -> Optional[str]:
        """Classifica um bloco novo e confirma se o limite é real."""
        lines = text.splitlines()
        kinds = [self.classify_line(line) for line in lines]

        if 'rotate' not in kinds and 'ask' not in kinds:
            return None

        if 'rotate' in kinds:
            settle = float(self.config.get('settle_seconds', 4) or 0)
            if settle > 0:
                # dá tempo para o OpenCode se recuperar sozinho
                if self._stop_event.wait(settle):
                    return None
                after = self._read_from(path)
                if after:
                    lines = lines + after.splitlines()

            last_fatal = -1
            for i, line in enumerate(lines):
                if self.classify_line(line) == 'rotate':
                    last_fatal = i

            if last_fatal >= 0:
                for line in lines[last_fatal + 1:]:
                    if self._INFO_AFTER.search(line):
                        logger.info(
                            "ℹ️ Erro de limite seguido de atividade normal; "
                            "a sessão se recuperou sozinha."
                        )
                        return None
                return 'rotate'

        return 'ask'

    def _spawn(self, callback: Optional[Callable]) -> None:
        if callback:
            threading.Thread(target=callback, daemon=True).start()

    # --------------------------------------------------------------------- loop
    def _monitor_loop(self, generation: int) -> None:
        logger.info("🔍 Monitorando logs do OpenCode...")

        try:
            while self.monitoring and generation == self._generation:
                path = self._get_latest_log()
                if not path:
                    if self._stop_event.wait(2):
                        break
                    continue

                if self._current_file != path:
                    self._prime(path)
                    logger.info(f"📄 Monitorando: {path}")

                try:
                    size = path.stat().st_size
                except OSError:
                    if self._stop_event.wait(1):
                        break
                    continue

                if size < self.last_position:
                    logger.info("📄 Log truncado; relendo a partir do início.")
                    self.last_position = 0

                if size > self.last_position:
                    text = self._read_from(path)
                    if text:
                        action = self._decide(text, path)
                        if action == 'rotate':
                            logger.warning("🚨 Limite de uso confirmado no log.")
                            self._last_trigger = time.time()
                            self.monitoring = False
                            self._spawn(self.on_limit)
                            return
                        if action == 'ask':
                            logger.warning("⚠️ Rate limit detectado no log.")
                            self._spawn(self.on_ask)

                if self._stop_event.wait(1):
                    break

        finally:
            if generation == self._generation:
                self.monitoring = False
            logger.info("⏹️ Loop de monitoramento finalizado")

    def start(self) -> None:
        """Inicia o monitoramento a partir do fim do log atual."""
        old = self.monitor_thread
        if old and old.is_alive():
            self.monitoring = False
            self._stop_event.set()
            old.join(timeout=2)

        self._generation += 1
        generation = self._generation

        self.monitoring = True
        self._stop_event.clear()
        self._base_sizes = self._snapshot_sizes()
        self._current_file = None
        self.last_position = 0
        self.start_time = time.time()
        self.start_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(generation,),
            daemon=True
        )
        self.monitor_thread.start()
        logger.info("✅ Monitoramento iniciado (somente linhas novas)")

    def stop(self) -> None:
        """Para o monitoramento."""
        thread = self.monitor_thread
        if not self.monitoring and not (thread and thread.is_alive()):
            return

        self.monitoring = False
        self._generation += 1
        self._stop_event.set()

        if thread and thread.is_alive():
            thread.join(timeout=5)

        self.monitor_thread = None
        logger.info("⏹️ Monitoramento parado")

    def is_monitoring(self) -> bool:
        """Verifica se está monitorando."""
        return bool(
            self.monitoring
            and self.monitor_thread is not None
            and self.monitor_thread.is_alive()
        )
