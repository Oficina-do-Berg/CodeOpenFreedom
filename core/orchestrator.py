"""
Orquestrador - Fluxo completo de desbloqueio

Sequência (a mesma do main):
1. limite real detectado no log;
2. para o TUI;
3. rotaciona o WARP;
4. testa a rota nova com uma chamada de modelo (probe);
5. retoma a conversa com `opencode run --auto -c "continue"`;
6. reabre o TUI com --continue;
7. volta a monitorar somente linhas novas.
"""

import os
import threading
import time
from collections import deque
from typing import Optional

from utils.logger import get_logger

logger = get_logger(__name__)


class Orchestrator:
    """Gerencia o fluxo: monitorar → detectar limite → rotacionar → provar → retomar."""

    def __init__(self, connection_manager, opencode_manager, rotator, monitor, config):
        self.connection = connection_manager
        self.opencode = opencode_manager
        self.rotator = rotator
        self.monitor = monitor
        self.config = config
        self.rotation_count = 0
        self.working_dir: Optional[str] = None
        self.last_result = ""

        self._handling = threading.Lock()
        self._rotation_times = deque()

        self.monitor.on_limit = self.handle_limit_detected
        self.monitor.on_ask = self.handle_rate_limit_detected

    # ------------------------------------------------------------------ anti-loop
    def _rotation_allowed(self) -> bool:
        window = float(self.config.get('rotation_window_minutes', 30)) * 60
        limit = int(self.config.get('max_rotations_per_window', 5))
        now = time.time()

        while self._rotation_times and now - self._rotation_times[0] > window:
            self._rotation_times.popleft()

        if len(self._rotation_times) >= limit:
            return False

        self._rotation_times.append(now)
        return True

    # ------------------------------------------------------------------ callbacks
    def handle_rate_limit_detected(self):
        """Rate limit puro: o main pergunta; aqui não rotaciona sozinho."""
        if self.config.get('rotate_on_rate_limit', False):
            self.handle_limit_detected()
        else:
            logger.warning(
                "⚠️ Rate limit detectado. Não vou rotacionar automaticamente "
                "(rate limit costuma ser temporário). Use ROTACIONAR IP se precisar."
            )

    def handle_limit_detected(self):
        """Callback do monitor. Roda em thread própria."""
        if not self._handling.acquire(blocking=False):
            logger.info("ℹ️ Um desbloqueio já está em andamento; gatilho ignorado.")
            return
        try:
            self._run_unlock()
        finally:
            self._handling.release()

    # --------------------------------------------------------------------- fluxo
    def _run_unlock(self):
        logger.info("=" * 60)
        logger.info("🚨 LIMITE DETECTADO - iniciando desbloqueio")
        logger.info("=" * 60)

        if not self._rotation_allowed():
            logger.error(
                "❌ Limite de rotações automáticas atingido "
                f"({self.config.get('max_rotations_per_window', 5)} em "
                f"{self.config.get('rotation_window_minutes', 30)} min). "
                "Automático pausado para não entrar em loop."
            )
            self.last_result = "limite de rotações atingido"
            return

        workdir = self.working_dir or os.getcwd()
        attempts = max(1, int(self.config.get('max_retries', 3)))

        # 1. parar o TUI (o serviço v2 não é usado: TUI/probe/resume usam --standalone)
        logger.info("1️⃣ Parando o TUI do OpenCode...")
        self.opencode.stop()

        # se o TUI antigo usava o serviço de background, ele precisa cair
        # também; senão o probe/resume podem reutilizar a rota velha.
        if self.opencode.is_service_running():
            logger.info("   Parando o serviço de background (rota antiga)...")
            self.opencode.stop_service()

        time.sleep(1)

        resumed = False

        for attempt in range(1, attempts + 1):
            logger.info(f"2️⃣ Tentativa {attempt}/{attempts}: rotacionando o WARP...")
            if not self.rotator.rotate(max_retries=1):
                logger.warning("⚠️ A rotação falhou; tentando novamente...")
                time.sleep(int(self.config.get('retry_delay', 5)))
                continue

            proxy_url = self.connection.proxy_url
            logger.info(f"✅ Nova rota: {self.connection.current_ip}")

            # 3. provar a rota nova antes de retomar
            if self.config.get('probe_enabled', True):
                status, detail = self.opencode.probe(proxy_url, cwd=workdir)
                if status == 'burned':
                    logger.warning(
                        "⚠️ A rota nova também está limitada; rotacionando de novo..."
                    )
                    continue
                if status == 'timeout':
                    logger.warning("⚠️ O probe não respondeu; tentando outra rota...")
                    continue
                if status == 'broken':
                    logger.warning(
                        f"⚠️ O probe falhou por outro motivo ({detail[:160]}); "
                        "seguindo para a retomada."
                    )

            # 4. retomar a conversa de verdade
            if self.config.get('auto_continue', True):
                status, detail = self.opencode.resume(proxy_url, cwd=workdir)

                if status == 'limit':
                    logger.warning(
                        "⚠️ A conversa ainda bateu no limite; rotacionando de novo..."
                    )
                    continue
                if status == 'timeout':
                    logger.warning("⚠️ A retomada expirou; tentando outra rota...")
                    continue
                if status == 'no_session':
                    logger.info("ℹ️ Não existe conversa anterior para retomar.")
                    resumed = True
                    break
                if status == 'auth':
                    logger.warning(
                        "⚠️ O OpenCode pediu login; não adianta rotacionar. "
                        "Reabrindo para você autenticar."
                    )
                    resumed = True
                    break
                if status == 'ok':
                    logger.info("✅ Conversa retomada na rota nova.")
                    resumed = True
                    break

                logger.warning(
                    f"⚠️ A retomada falhou ({detail[:160]}); tentando outra rota..."
                )
                continue

            resumed = True
            break

        # 5. reabrir o TUI na mesma conversa
        if resumed:
            logger.info("3️⃣ Reabrindo o OpenCode na conversa...")
            if self.opencode.start(
                proxy_url=self.connection.proxy_url,
                continue_session=True
            ):
                self.rotation_count += 1
                self.last_result = "desbloqueado"
                if self.config.get('auto_rotate', True):
                    logger.info("4️⃣ Reativando o monitor (somente linhas novas)...")
                    self.monitor.start()
                logger.info("=" * 60)
                logger.info("✅ DESBLOQUEIO CONCLUÍDO")
                logger.info("=" * 60)
                return

            logger.error("❌ Não foi possível reabrir o OpenCode.")
            self.last_result = "falha ao reabrir"
            return

        # 6. todas as tentativas falharam: reabre para o usuário ver o erro
        logger.error(
            "❌ Não foi possível desbloquear após as tentativas. "
            "Automático pausado."
        )
        self.last_result = "falha no desbloqueio"
        self.opencode.start(
            proxy_url=self.connection.proxy_url,
            continue_session=True
        )

    # ------------------------------------------------------------------- start/stop
    def start_full_flow(self, folder: Optional[str] = None) -> bool:
        logger.info("=" * 60)
        logger.info("🚀 INICIANDO FLUXO COMPLETO")
        logger.info("=" * 60)

        self.working_dir = os.path.abspath(folder) if folder else os.getcwd()
        self._rotation_times.clear()
        self.last_result = ""

        method = self.config.get('connection_method', 'WARP')
        logger.info(f"1️⃣ Conectando via {method}...")
        success, msg = self.connection.connect(method)
        if not success:
            logger.error(f"❌ Falha: {msg}")
            return False

        logger.info(f"✅ {msg}")
        logger.info(f"   IP: {self.connection.current_ip}")

        logger.info("2️⃣ Iniciando OpenCode...")
        success = self.opencode.start(
            folder=self.working_dir,
            proxy_url=self.connection.proxy_url,
            continue_session=bool(self.config.get('start_continue', True))
        )
        if not success:
            logger.error("❌ Falha ao iniciar OpenCode")
            return False

        logger.info("✅ OpenCode iniciado!")

        if self.config.get('auto_rotate', True):
            logger.info("3️⃣ Iniciando monitoramento automático...")
            self.monitor.start()
            logger.info("✅ Monitoramento ativo (somente linhas novas)")
            logger.info("   🔄 Rotação + retomada automáticas ao detectar limite")

        logger.info("=" * 60)
        logger.info("✅ FLUXO INICIADO COM SUCESSO!")
        logger.info("=" * 60)
        return True

    def stop_flow(self):
        logger.info("⏹️ Parando fluxo...")
        self.monitor.stop()
        self.opencode.stop()
        logger.info("✅ Fluxo parado")

    def get_status(self) -> dict:
        return {
            'connection': self.connection.get_status(),
            'opencode_running': self.opencode.is_running(),
            'service_running': self.opencode.is_service_running(),
            'monitoring': self.monitor.is_monitoring(),
            'rotation_count': self.rotation_count,
            'last_result': self.last_result,
        }
