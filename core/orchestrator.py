"""
Orquestrador - Fluxo completo igual ao original
"""

import time
from typing import Optional
from utils.logger import get_logger

logger = get_logger(__name__)

class Orchestrator:
    """Gerencia o fluxo completo: monitorar → detectar limite → rotacionar → continuar"""
    
    def __init__(self, connection_manager, opencode_manager, rotator, monitor, config):
        self.connection = connection_manager
        self.opencode = opencode_manager
        self.rotator = rotator
        self.monitor = monitor
        self.config = config
        self.rotation_count = 0
        
        # Conectar callback do monitor
        self.monitor.on_limit = self.handle_limit_detected
        
    def handle_limit_detected(self):
        """Callback quando limite é detectado"""
        logger.info("=" * 60)
        logger.info("🚨 LIMITE DETECTADO - Iniciando rotação automática")
        logger.info("=" * 60)
        
        # 1. Parar OpenCode
        logger.info("1️⃣ Parando OpenCode...")
        if self.opencode.is_running():
            self.opencode.stop()
            time.sleep(2)
        
        # 2. Backup auth.json (opcional)
        if self.config.get('backup_on_rotate', False):
            logger.info("2️⃣ Fazendo backup de auth.json...")
            self.opencode.backup_auth()
        
        # 3. Rotacionar IP
        logger.info("3️⃣ Rotacionando IP...")
        success = self.rotator.rotate()
        
        if not success:
            logger.error("❌ Falha na rotação! Abortando...")
            return
        
        self.rotation_count += 1
        logger.info(f"✅ Rotação #{self.rotation_count} bem-sucedida!")
        
        # 4. Reiniciar OpenCode
        logger.info("4️⃣ Reiniciando OpenCode...")
        proxy_url = self.connection.proxy_url
        success = self.opencode.start(proxy_url=proxy_url)
        
        if not success:
            logger.error("❌ Falha ao reiniciar OpenCode!")
            return
        
        time.sleep(3)
        
        # 5. Continuar conversa (se habilitado)
        if self.config.get('auto_continue', True):
            logger.info("5️⃣ Continuando conversa...")
            self._send_continue_message()
        
        # 6. Reiniciar monitoramento
        logger.info("6️⃣ Reiniciando monitoramento...")
        self.monitor.start()
        
        logger.info("=" * 60)
        logger.info("✅ ROTAÇÃO AUTOMÁTICA CONCLUÍDA!")
        logger.info(f"   Total de rotações: {self.rotation_count}")
        logger.info("=" * 60)
    
    def _send_continue_message(self):
        """Envia mensagem de continuação (placeholder)"""
        # TODO: Implementar envio de mensagem via CLI
        message = self.config.get('resume_msg', 'continue')
        logger.info(f"💬 Enviando: '{message}'")
        logger.info("⏳ (Implementação futura: enviar via opencode CLI)")
    
    def start_full_flow(self, folder: Optional[str] = None):
        """Inicia fluxo completo"""
        logger.info("=" * 60)
        logger.info("🚀 INICIANDO FLUXO COMPLETO")
        logger.info("=" * 60)
        
        # 1. Conectar via método escolhido
        method = self.config.get('connection_method', 'WARP')
        logger.info(f"1️⃣ Conectando via {method}...")
        
        success, msg = self.connection.connect(method)
        if not success:
            logger.error(f"❌ Falha: {msg}")
            return False
        
        logger.info(f"✅ {msg}")
        logger.info(f"   IP: {self.connection.current_ip}")
        
        # 2. Iniciar OpenCode
        logger.info("2️⃣ Iniciando OpenCode...")
        proxy_url = self.connection.proxy_url
        success = self.opencode.start(folder=folder, proxy_url=proxy_url)
        
        if not success:
            logger.error("❌ Falha ao iniciar OpenCode")
            return False
        
        logger.info("✅ OpenCode iniciado!")
        
        # 3. Iniciar monitoramento
        if self.config.get('auto_rotate', True):
            logger.info("3️⃣ Iniciando monitoramento automático...")
            self.monitor.start()
            logger.info("✅ Monitoramento ativo!")
            logger.info("   🔍 Observando logs...")
            logger.info("   🔄 Rotação automática ao detectar limite")
        
        logger.info("=" * 60)
        logger.info("✅ FLUXO INICIADO COM SUCESSO!")
        logger.info("=" * 60)
        return True
    
    def stop_flow(self):
        """Para todo o fluxo"""
        logger.info("⏹️ Parando fluxo...")
        
        self.monitor.stop()
        self.opencode.stop()
        
        logger.info("✅ Fluxo parado")
    
    def get_status(self) -> dict:
        """Retorna status completo"""
        return {
            'connection': self.connection.get_status(),
            'opencode_running': self.opencode.is_running(),
            'monitoring': self.monitor.is_monitoring(),
            'rotation_count': self.rotation_count
        }
