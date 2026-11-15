"""
Orquestrador - Fluxo completo de desbloqueio

Mesma lógica do main:

1. limite real detectado;
2. descobre a conversa e o modelo que ela usa;
3. para o TUI;
4. caça de IP: troca o registro do WARP, testa a rota com o modelo da
   conversa (probe com "pong") e repete até o probe passar ou até o limite
   de tentativas (o main usa 10 no desktop e 20 no .bat);
5. retoma a mesma conversa na rota aprovada;
6. se a caçada inteira falhar, tenta outro modelo livre na rota atual
   (equivalente ao LIMIT_ACTION=provider do .bat);
7. reabre o TUI e volta a monitorar linhas novas.
"""

import os
import threading
import time
from typing import Optional

from utils.logger import get_logger

logger = get_logger(__name__)


class Orchestrator:
    """Gerencia o fluxo: monitorar → detectar limite → caçar rota → retomar."""

    def __init__(self, connection_manager, opencode_manager, rotator, monitor, config):
        self.connection = connection_manager
        self.opencode = opencode_manager
        self.rotator = rotator
        self.monitor = monitor
        self.config = config
        self.rotation_count = 0
        self.model_switch_count = 0
        self.working_dir: Optional[str] = None
        self.last_result = ""
        self.is_unlocking = False

        self._handling = threading.Lock()
        self._quota_streak = 0  # desbloqueios seguidos que não resolveram (main: QUOTA_STREAK)

        self.monitor.on_limit = self.handle_limit_detected
        self.monitor.on_ask = self.handle_rate_limit_detected

    # ------------------------------------------------------------------ anti-loop
    # O .bat removeu o teto por janela de tempo (v2.44): conta só desbloqueios
    # seguidos que voltaram a bater no limite (LIMIT_ROT_MAX) e um resume bom
    # zera o contador. Ação manual também libera (reset_streak).

    def reset_streak(self) -> None:
        """Ação manual (rotacionar, iniciar, conversa nova) libera o automático."""
        self._quota_streak = 0

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
        limit = int(self.config.get('limit_rot_max', 3) or 0)
        if limit and self._quota_streak >= limit:
            logger.error(
                f"❌ {self._quota_streak} desbloqueios seguidos sem resolver "
                f"(limit_rot_max={limit}). Automático pausado, como no .bat "
                f"(LIMIT_ROT_MAX). Use ROTACIONAR IP ou NOVA CONVERSA para tentar de novo."
            )
            self.last_result = "limite de desbloqueios seguidos"
            return
        if not self._handling.acquire(blocking=False):
            logger.info("ℹ️ Um desbloqueio já está em andamento; gatilho ignorado.")
            return
        self.is_unlocking = True
        try:
            self._run_unlock()
        finally:
            self.is_unlocking = False
            self._handling.release()

    # --------------------------------------------------------------------- fluxo
    def _model_candidates(self, current_model: Optional[str]) -> list:
        """Modelos livres para o fallback, do mais provável ao menos usado."""
        seen = set()
        ordered = []

        def add(model):
            if model and model not in seen:
                seen.add(model)
                ordered.append(model)

        add(current_model)
        add(self.config.get('last_good_model'))
        for model in self.config.get('model_candidates') or []:
            add(model)

        try:
            free = self.opencode.list_free_models() or []
            usage = self.opencode.model_last_used() or {}
            free = sorted(free, key=lambda m: usage.get(m, 0))
        except Exception as e:
            logger.debug(f"Falha ao listar modelos livres: {e}")
            free = []

        for model in free:
            add(model)

        limit = max(1, int(self.config.get('max_model_switches', 5)))
        return ordered[:limit]

    def _remember_model(self, model: Optional[str]) -> None:
        if not model:
            return
        if self.config.get('last_good_model') == model:
            return
        try:
            self.config.set('last_good_model', model)
        except Exception as e:
            logger.debug(f"Não foi possível salvar o modelo bom: {e}")

    def _stick_model(self, session_id: Optional[str], old_model: Optional[str],
                     new_model: Optional[str]) -> None:
        """Fixa o modelo novo na conversa, para o TUI reabrir com ele.

        O `-m` da retomada vale só para aquele run: em campo a sessão seguiu
        no modelo antigo e o TUI re-limitava segundos depois do desbloqueio.
        """
        if not session_id or not new_model or new_model == old_model:
            return
        if not hasattr(self.opencode, 'set_session_model'):
            return
        if self.opencode.set_session_model(session_id, new_model):
            logger.info(f"📌 Conversa fixada no modelo {new_model} (o TUI reabre com ele).")
        else:
            logger.warning(
                f"⚠️ Não consegui fixar {new_model} na conversa; "
                "o TUI pode reabrir no modelo antigo e limitar de novo."
            )

    def _restart_service(self):
        if hasattr(self.opencode, 'restart_service') and self.opencode.supports_service():
            self.opencode.restart_service(self.connection.proxy_url)

    def _resume_target(self, workdir: str, session_id: Optional[str],
                       model: Optional[str]) -> tuple:
        """Retoma a conversa e classifica o resultado."""
        rstatus, rdetail = self.opencode.resume(
            self.connection.proxy_url, cwd=workdir, model=model, session_id=session_id
        )

        if rstatus == 'ok':
            logger.info(f"✅ Conversa retomada com o modelo {model or 'padrão'}.")
            self._remember_model(model)
            return True, f"modelo {model or 'padrão'}"
        if rstatus == 'no_session':
            logger.info("ℹ️ Não existe conversa anterior para retomar.")
            return True, "sem conversa"
        if rstatus == 'auth':
            logger.warning(
                "⚠️ O OpenCode pediu login; não adianta trocar modelo ou IP. "
                "Reabrindo para você autenticar."
            )
            return True, "login necessário"
        if rstatus == 'limit':
            logger.warning("   ⚠️ A retomada também bateu no limite; girando de novo...")
            return False, rdetail
        if rstatus == 'timeout':
            logger.warning("   ⚠️ A retomada expirou; girando de novo...")
            return False, rdetail

        # Probe passou e a retomada deu erro não relacionado a cota
        # (ex.: nenhuma mensagem pendente). A rota/modelo é boa.
        logger.warning(
            f"ℹ️ Retomada com retorno não-padrão ({rdetail[:160]}), "
            "mas a rota foi validada no probe. Prosseguindo..."
        )
        return True, f"modelo {model or 'padrão'} (aviso)"

    def _run_unlock(self):
        logger.info("=" * 60)
        logger.info("🚨 LIMITE DETECTADO - iniciando desbloqueio")
        logger.info("=" * 60)

        # o monitor já se desligou ao disparar o callback; garantir que
        # nenhuma linha nova (probe/resume) dispare outro desbloqueio.
        self.monitor.stop()

        workdir = self.working_dir or os.getcwd()
        session_id = None
        session_model = None
        original_model = None
        try:
            session_id, session_model, session_dir = self.opencode.latest_session(workdir)
            original_model = session_model
            if session_dir:
                workdir = session_dir
        except Exception as e:
            logger.debug(f"Não foi possível ler a sessão atual: {e}")

        probe_model = self.config.get('probe_model') or session_model
        logger.info(
            "Alvo: "
            + (session_id or "conversa mais recente da pasta")
            + " | modelo: "
            + (probe_model or "padrão do OpenCode")
        )

        # 1. parar o TUI (o serviço v2 não é usado: TUI/probe/resume usam --standalone)
        logger.info("1️⃣ Parando o TUI do OpenCode...")
        self.opencode.stop()

        if self.opencode.is_service_running():
            logger.info("   Parando o serviço de background (rota antiga)...")
            self.opencode.stop_service()

        time.sleep(1)

        hunt_max = max(1, int(self.config.get('hunt_max') or self.config.get('max_retries', 10)))
        probe_enabled = bool(self.config.get('probe_enabled', True))
        probe_broken_max = max(1, int(self.config.get('probe_broken_max', 2)))
        retry_delay = int(self.config.get('retry_delay', 5))

        resumed = False
        unlock_reason = ""
        last_retry_ms = 0
        broken = 0

        logger.info(
            f"2️⃣ Caçando uma rota que aceite {probe_model or 'o modelo padrão'} "
            f"(até {hunt_max} rotações, igual ao main)..."
        )

        for attempt in range(1, hunt_max + 1):
            logger.info(f"   Tentativa {attempt}/{hunt_max}: trocando o IP...")
            if not self.rotator.rotate(max_retries=1):
                logger.warning("   ⚠️ A rotação do WARP falhou; tentando de novo...")
                time.sleep(retry_delay)
                continue

            logger.info(f"   ✅ Nova rota: {self.connection.current_ip}")
            self._restart_service()

            if probe_enabled:
                status, detail = self.opencode.probe(
                    self.connection.proxy_url, cwd=workdir, model=probe_model
                )

                if status == 'burned':
                    last_retry_ms = max(last_retry_ms, self.opencode.retry_after_ms(detail))
                    logger.warning(
                        f"   ⚠️ A rota {attempt} ainda está limitada para "
                        f"{probe_model or 'o modelo padrão'}; girando de novo..."
                    )
                    continue
                if status == 'timeout':
                    logger.warning("   ⚠️ O probe não respondeu; girando de novo...")
                    continue
                if status == 'broken':
                    broken += 1
                    logger.warning(
                        f"   ⚠️ O probe falhou por outro motivo ({detail[:160]})."
                    )
                    if broken >= probe_broken_max:
                        logger.warning(
                            "   ⚠️ O probe está quebrado (não é limite). "
                            "Continuando sem probe, como o .bat com PROBE=0."
                        )
                        probe_enabled = False
                    continue

            # Rota aprovada no probe (ou probe desativado): retomar a conversa.
            ok, reason = self._resume_target(workdir, session_id, probe_model)
            if ok:
                self._stick_model(session_id, original_model, probe_model)
                resumed = True
                unlock_reason = reason
                break
            time.sleep(retry_delay)

        # 3. Fallback do .bat (LIMIT_ACTION=provider): a caçada de IP não
        # resolveu; tenta outro modelo livre na rota atual.
        if not resumed and probe_enabled and self.config.get('model_switch_fallback', True):
            logger.info(
                "3️⃣ Nenhuma rota aceitou esse modelo; tentando outro modelo livre "
                "na rota atual (fallback do .bat)..."
            )
            for model in self._model_candidates(probe_model):
                if not model or model == probe_model:
                    continue

                status, detail = self.opencode.probe(
                    self.connection.proxy_url, cwd=workdir, model=model
                )
                if status == 'burned':
                    last_retry_ms = max(last_retry_ms, self.opencode.retry_after_ms(detail))
                    logger.warning(f"   ⚠️ {model}: cota gratuita também esgotada...")
                    continue
                if status in ('timeout',):
                    logger.warning(f"   ⚠️ {model}: o teste não respondeu...")
                    continue
                if status == 'broken':
                    logger.warning(
                        f"   ⚠️ {model}: o teste falhou ({detail[:160]}); tentando retomar mesmo assim."
                    )

                ok, reason = self._resume_target(workdir, session_id, model)
                if ok:
                    self.model_switch_count += 1
                    self._stick_model(session_id, original_model, model)
                    resumed = True
                    unlock_reason = f"fallback: {reason}"
                    break

        # 4. reabrir o TUI na MESMA conversa (fixado pelo id, como o .bat fixa o chat)
        if resumed:
            logger.info("4️⃣ Reabrindo o OpenCode na conversa...")
            if self.opencode.start(
                proxy_url=self.connection.proxy_url,
                continue_session=True,
                session_id=session_id,
            ):
                self.rotation_count += 1
                self._quota_streak = 0
                self.last_result = "desbloqueado"
                if self.config.get('auto_rotate', True):
                    logger.info("5️⃣ Reativando o monitor (somente linhas novas)...")
                    self.monitor.start()
                logger.info("=" * 60)
                logger.info(f"✅ DESBLOQUEIO CONCLUÍDO ({unlock_reason})")
                logger.info("=" * 60)
                return

            logger.error("❌ Não foi possível reabrir o OpenCode.")
            self.last_result = "falha ao reabrir"
            return

        # 5. todas as tentativas falharam: reabre para o usuário ver o erro
        if last_retry_ms:
            hours = last_retry_ms / 3600000
            logger.error(
                "❌ Nenhuma rota nem modelo livre aceitou a conversa. "
                f"A próxima cota deve voltar em ~{hours:.1f}h. "
                "Troque de modelo manualmente ou conecte um provider pago."
            )
        else:
            logger.error(
                "❌ Não foi possível desbloquear após as tentativas. "
                "Automático pausado."
            )
        self.last_result = "falha no desbloqueio"
        self._quota_streak += 1
        self.opencode.start(
            proxy_url=self.connection.proxy_url,
            continue_session=True,
            session_id=session_id,
        )

    # ------------------------------------------------------------------- start/stop
    def start_full_flow(self, folder: Optional[str] = None, fresh: bool = False) -> bool:
        if self.is_unlocking or self._handling.locked():
            logger.warning("⚠️ Um desbloqueio já está em andamento. Aguarde a conclusão.")
            return False

        logger.info("=" * 60)
        logger.info("🚀 INICIANDO FLUXO COMPLETO" + (" (CONVERSA NOVA)" if fresh else ""))
        logger.info("=" * 60)

        self.working_dir = os.path.abspath(folder) if folder else os.getcwd()
        self._quota_streak = 0
        self.last_result = ""

        method = self.config.get('connection_method', 'WARP')
        logger.info(f"1️⃣ Conectando via {method}...")
        success, msg = self.connection.connect(method)
        if not success:
            logger.error(f"❌ Falha: {msg}")
            return False

        logger.info(f"✅ {msg}")
        logger.info(f"   IP: {self.connection.current_ip}")

        if fresh:
            # opção 1 do main (fresh start): IP novo + sessão nova. A cota
            # gratuita é por modelo; uma conversa nova usa o modelo padrão,
            # que costuma ter cota mesmo quando o modelo antigo esgotou.
            logger.info("   Conversa nova: trocando o IP antes de abrir...")
            if not self.rotator.rotate(max_retries=1):
                logger.warning(
                    "   ⚠️ Não consegui trocar o IP; abrindo a conversa nova mesmo assim."
                )

        # Reiniciar o serviço de background sob o novo proxy (padrão do main)
        self._restart_service()

        logger.info("2️⃣ Iniciando OpenCode...")
        success = self.opencode.start(
            folder=self.working_dir,
            proxy_url=self.connection.proxy_url,
            continue_session=bool(self.config.get('start_continue', True)) and not fresh,
        )
        if not success:
            logger.error("❌ Falha ao iniciar OpenCode")
            return False

        logger.info("✅ OpenCode iniciado!")

        if self.config.get('auto_rotate', True):
            logger.info("3️⃣ Iniciando monitoramento automático...")
            self.monitor.start()
            logger.info("✅ Monitoramento ativo (somente linhas novas)")
            logger.info("   🔄 Caça de IP + retomada automáticas ao detectar limite")

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
            'opencode_running': self.opencode.is_running(only_dir=self.working_dir),
            'service_running': self.opencode.is_service_running(),
            'monitoring': self.monitor.is_monitoring(),
            'is_unlocking': self.is_unlocking,
            'rotation_count': self.rotation_count,
            'model_switch_count': self.model_switch_count,
            'last_result': self.last_result,
        }
