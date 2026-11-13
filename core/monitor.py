"""
Monitor de Logs do OpenCode
Detecta limites e erros
"""

import re
import time
from pathlib import Path
from typing import Optional, Callable
import threading
from utils.logger import get_logger

logger = get_logger(__name__)

class LogMonitor:
    """Monitora logs do OpenCode em busca de limites"""
    
    # Padrões de erro de limite
    LIMIT_PATTERNS = [
        r'usage limit',
        r'out of usage',
        r'insufficient credits',
        r'payment required',
        r'rate limit',
        r'rate_limit_exceeded',
        r'too many requests',
        r'status.*429',
        r'HTTP 429',
        r'quota.*exceeded',
        r'limit.*reached'
    ]
    
    def __init__(self, config, on_limit_callback: Optional[Callable] = None):
        self.config = config
        self.on_limit = on_limit_callback
        self.monitoring = False
        self.monitor_thread = None
        self.last_position = 0
        
    def _get_latest_log(self) -> Optional[Path]:
        """Obtém arquivo de log mais recente do OpenCode"""
        log_dir = Path.home() / ".local" / "share" / "opencode" / "log"
        if not log_dir.exists():
            return None
        
        logs = list(log_dir.glob("*.log"))
        if not logs:
            return None
        
        # Mais recente por data de modificação
        return max(logs, key=lambda p: p.stat().st_mtime)
    
    def _check_for_limits(self, text: str) -> bool:
        """Verifica se texto contém indicação de limite"""
        text_lower = text.lower()
        
        for pattern in self.LIMIT_PATTERNS:
            if re.search(pattern, text_lower):
                logger.warning(f"🚨 Limite detectado! Padrão: {pattern}")
                return True
        
        return False
    
    def _monitor_loop(self):
        """Loop de monitoramento contínuo"""
        logger.info("🔍 Iniciando monitoramento de logs...")
        
        log_file = None
        check_count = 0
        
        try:
            while self.monitoring:
                try:
                    # A cada 10 verificações, procura novo log
                    if check_count % 10 == 0:
                        new_log = self._get_latest_log()
                        if new_log and new_log != log_file:
                            log_file = new_log
                            self.last_position = 0
                            logger.info(f"📄 Monitorando: {log_file}")
                    
                    check_count += 1
                    
                    if not log_file or not log_file.exists():
                        time.sleep(2)
                        continue
                    
                    # Ler novas linhas
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        f.seek(self.last_position)
                        new_lines = f.readlines()
                        self.last_position = f.tell()
                    
                    # Verificar cada linha
                    limit_found = False
                    for line in new_lines:
                        if self._check_for_limits(line):
                            logger.warning(f"🚨 LIMITE DETECTADO: {line.strip()}")
                            limit_found = True
                            break
                    
                    if limit_found:
                        # Resetar flag antes de invocar callback para permitir restart limpo
                        self.monitoring = False
                        if self.on_limit:
                            threading.Thread(
                                target=self.on_limit,
                                daemon=True
                            ).start()
                        return
                    
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Erro no monitoramento: {e}")
                    time.sleep(2)
        finally:
            self.monitoring = False
            logger.info("⏹️ Loop de monitoramento finalizado")
    
    def start(self):
        """Inicia monitoramento"""
        # Se thread antiga ainda estiver viva, esperar ou limpar
        if self.is_monitoring():
            logger.warning("⚠️ Monitoramento já está ativo")
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True
        )
        self.monitor_thread.start()
        logger.info("✅ Monitoramento iniciado")
    
    def stop(self):
        """Para monitoramento"""
        if not self.monitoring and not (self.monitor_thread and self.monitor_thread.is_alive()):
            return
        
        self.monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=3)
        self.monitor_thread = None
        logger.info("⏹️ Monitoramento parado")
    
    def is_monitoring(self) -> bool:
        """Verifica se está monitorando"""
        return self.monitoring and (self.monitor_thread is not None and self.monitor_thread.is_alive())
