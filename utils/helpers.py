"""
Funções Auxiliares
"""

import re
from typing import Optional

def format_ip(ip: Optional[str]) -> str:
    """Formata IP para exibição"""
    if not ip:
        return "Desconhecido"
    return ip

def format_status(connected: bool) -> str:
    """Formata status de conexão"""
    return "🟢 Conectado" if connected else "🔴 Desconectado"

def validate_ip(ip: str) -> bool:
    """Valida formato de IP"""
    pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if not re.match(pattern, ip):
        return False
    
    parts = ip.split('.')
    return all(0 <= int(part) <= 255 for part in parts)

def truncate_text(text: str, max_length: int = 50) -> str:
    """Trunca texto longo"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."
