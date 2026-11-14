"""
Rotação Automática de IP
"""

import time
from typing import Optional

from utils.logger import get_logger

logger = get_logger(__name__)


class IPRotator:
    """Gerencia rotação automática de IP"""

    def __init__(self, connection_manager, config, opencode_manager=None):
        self.connection = connection_manager
        self.config = config
        self.opencode = opencode_manager
        self.enabled = False
        self.rotation_count = 0

    def should_rotate(self, error_msg: str) -> bool:
        """Verifica se deve rotacionar baseado no erro."""
        limit_keywords = [
            'usage limit',
            'out of usage',
            'insufficient credits',
            'payment required',
            'rate limit',
            'too many requests',
            '429',
        ]
        error_lower = error_msg.lower()
        return any(keyword in error_lower for keyword in limit_keywords)

    def rotate(self, max_retries: Optional[int] = None, deep_reset: bool = False) -> bool:
        """Rotaciona o IP.

        O número de tentativas é controlado aqui; `rotate_warp_ip` faz uma
        tentativa por chamada (sem retry aninhado).
        """
        method = self.connection.current_method or self.config.get('connection_method', 'WARP')
        self.connection.current_method = method

        logger.info(f"🔄 Iniciando rotação de IP (método: {method})...")

        if deep_reset and self.opencode:
            logger.info("🔥 Executando DEEP RESET...")
            if self.opencode.opencode_path is None:
                self.opencode.find_opencode()
            if self.opencode.deep_reset():
                logger.info("✅ Chats arquivados, tokens e cache limpos")
            else:
                logger.warning("⚠️ Deep reset teve avisos; prosseguindo com a rotação")

        if method != "WARP":
            logger.warning(f"⚠️ Rotação não implementada para {method}")
            return False

        retries = int(self.config.get('max_retries', 3)) if max_retries is None else int(max_retries)
        retries = max(1, retries)

        for attempt in range(1, retries + 1):
            logger.info(f"  Tentativa {attempt}/{retries}...")
            success, msg = self.connection.rotate_warp_ip(max_attempts=1)

            if success:
                self.rotation_count += 1
                logger.info(f"✅ Rotação #{self.rotation_count} bem-sucedida: {msg}")
                return True

            logger.warning(f"⚠️ Falha: {msg}")
            if attempt < retries:
                delay = int(self.config.get('retry_delay', 5))
                logger.info(f"  Aguardando {delay}s antes de retentar...")
                time.sleep(delay)

        logger.error(f"❌ Rotação falhou após {retries} tentativas")
        return False

    def enable(self):
        self.enabled = True
        logger.info("✅ Rotação automática ativada")

    def disable(self):
        self.enabled = False
        logger.info("⏹️ Rotação automática desativada")
