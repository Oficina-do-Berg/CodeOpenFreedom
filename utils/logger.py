"""
Sistema de Logging
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

def setup_logger(name: str = "opencode-infinity") -> logging.Logger:
    """Configura sistema de logging"""
    
    # Criar diretório de logs
    log_dir = Path.home() / ".opencode-infinity-simple" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Nome do arquivo de log com data
    log_file = log_dir / f"{datetime.now().strftime('%Y%m%d')}.log"
    
    # Configurar logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # Remover handlers existentes
    logger.handlers.clear()
    
    # Handler para arquivo
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    
    # Handler para console. Em Windows o stdout pode ser cp1252: nunca deixe
    # um emoji derrubar o processo por UnicodeEncodeError.
    stream = sys.stdout
    try:
        if stream is not None and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    console_handler = logging.StreamHandler(stream)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    
    # Adicionar handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def get_logger(name: str = "opencode-infinity") -> logging.Logger:
    """Obtém logger configurado"""
    logger = logging.getLogger(name)
    if not logger.handlers:
        return setup_logger(name)
    return logger
