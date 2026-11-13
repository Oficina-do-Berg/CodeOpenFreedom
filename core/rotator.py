"""
Rotação Automática de IP
"""

import time
from typing import Callable
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
        """Verifica se deve rotacionar baseado no erro"""
        limit_keywords = [
            'usage limit',
            'out of usage',
            'insufficient credits',
            'payment required',
            'rate limit',
            'too many requests',
            '429'
        ]
        
        error_lower = error_msg.lower()
        return any(keyword in error_lower for keyword in limit_keywords)
    
    def rotate(self, max_retries: int = 3, deep_reset: bool = False) -> bool:
        """
        Rotaciona IP
        
        Args:
            max_retries: Número máximo de tentativas
            deep_reset: Se True, executa deep reset (arquiva chats + deleta auth.json)
        """
        method = self.connection.current_method or self.config.get('connection_method', 'WARP')
        self.connection.current_method = method
        
        logger.info(f"🔄 Iniciando rotação de IP (método: {method})...")
        
        # Deep reset se solicitado
        if deep_reset and self.opencode:
            logger.info("🔥 Executando DEEP RESET (padrão C++)...")
            logger.info("   1. Parando OpenCode se estiver rodando")
            logger.info("   2. Arquivando chats em Desktop/opencode_chats_archiviate")
            logger.info("   3. Limpando tokens (auth/service) e removendo snapshot DPAPI")
            logger.info("   4. Limpando cache (~/.cache/opencode)")
            logger.info("   5. Rotacionando IP via WARP")
            logger.info("")
            
            # Parar OpenCode se estiver rodando
            if self.opencode.is_running():
                logger.info("⏹️ Parando OpenCode...")
                self.opencode.stop()
            
            # Executar deep reset
            if self.opencode.deep_reset():
                logger.info("✅ Arquivamento, tokens e cache limpos!")
            else:
                logger.warning("⚠️ Deep reset teve avisos, prosseguindo com rotação...")
        
        for attempt in range(1, max_retries + 1):
            logger.info(f"  Tentativa {attempt}/{max_retries}...")
            
            try:
                if method == "WARP":
                    success, msg = self.connection.rotate_warp_ip()
                    if success:
                        self.rotation_count += 1
                        logger.info(f"✅ Rotação #{self.rotation_count} bem-sucedida!")
                        return True
                    else:
                        logger.warning(f"⚠️ Falha: {msg}")
                else:
                    logger.warning(f"⚠️ Rotação não implementada para {method}")
                    return False
                
                # Aguardar antes de retentar
                if attempt < max_retries:
                    delay = self.config.get('retry_delay', 10)
                    logger.info(f"  Aguardando {delay}s antes de retentar...")
                    time.sleep(delay)
                    
            except Exception as e:
                logger.error(f"❌ Erro na tentativa {attempt}: {e}")
        
        logger.error(f"❌ Rotação falhou após {max_retries} tentativas")
        return False
    
    def enable(self):
        """Ativa rotação automática"""
        self.enabled = True
        logger.info("✅ Rotação automática ativada")
    
    def disable(self):
        """Desativa rotação automática"""
        self.enabled = False
        logger.info("⏹️ Rotação automática desativada")
