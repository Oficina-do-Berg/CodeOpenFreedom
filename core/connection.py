"""
Gerenciamento de Conexões (WARP/Tor/Proxy)
"""

import subprocess
import requests
import time
from typing import Optional, Tuple
from utils.logger import get_logger

logger = get_logger(__name__)

class ConnectionManager:
    """Gerencia diferentes métodos de conexão"""
    
    def __init__(self, config):
        self.config = config
        self.current_method = None
        self.current_ip = None
        self.proxy_url = None
        self.warp_cli = "warp-cli"  # Comando padrão, pode ser caminho completo
        
    def get_current_ip(self, use_proxy: bool = True) -> Optional[str]:
        """Obtém IP atual através do Cloudflare Trace (igual ao original)"""
        try:
            # URL do trace do Cloudflare (igual ao opencode-infinite original)
            trace_url = "https://www.cloudflare.com/cdn-cgi/trace"
            
            # Se tiver proxy e use_proxy=True, usar o proxy
            proxies = None
            if use_proxy and self.proxy_url:
                proxies = {
                    'http': self.proxy_url,
                    'https': self.proxy_url
                }
            
            response = requests.get(trace_url, proxies=proxies, timeout=10)
            
            if response.status_code == 200:
                # Parse do trace (formato: ip=X.X.X.X\nwarp=on\nloc=XX\n...)
                lines = response.text.strip().split('\n')
                ip = None
                warp_status = None
                
                for line in lines:
                    if line.startswith('ip='):
                        ip = line.split('=', 1)[1]
                    elif line.startswith('warp='):
                        warp_status = line.split('=', 1)[1]
                
                # Se usar proxy WARP, DEVE ter warp=on ou warp=plus
                if use_proxy and self.proxy_url:
                    if warp_status in ['on', 'plus']:
                        return ip
                    else:
                        logger.warning(f"  ⚠️ Trace não passou pelo WARP: warp={warp_status}")
                        return None
                else:
                    # Conexão direta, retornar IP sem verificar WARP
                    return ip
            
            return None
        except Exception as e:
            logger.error(f"Erro ao obter IP: {e}")
            return None
    
    def check_warp_installed(self) -> bool:
        """Verifica se WARP está instalado"""
        # Tentar primeiro no PATH
        try:
            result = subprocess.run(
                ['warp-cli', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return True
        except Exception:
            pass
        
        # Tentar no local padrão de instalação
        import os
        warp_path = r"C:\Program Files\Cloudflare\Cloudflare WARP\warp-cli.exe"
        if os.path.exists(warp_path):
            self.warp_cli = warp_path
            return True
        
        return False
    
    def connect_warp(self) -> Tuple[bool, str]:
        """
        Conecta via WARP (igual ao warpUp() do original C++).
        Faz: check service → registration show → mode proxy → proxy port → connect → poll → verify
        """
        logger.info("🔌 Conectando via WARP...")
        
        if not self.check_warp_installed():
            return False, "WARP não está instalado"
        
        try:
            if self.warp_up():
                logger.info(f"✅ WARP conectado! IP: {self.current_ip}")
                return True, f"Conectado via WARP - IP: {self.current_ip}"
            else:
                return False, "WARP conectou mas não passou no trace check"
            
        except Exception as e:
            logger.error(f"Erro ao conectar WARP: {e}")
            return False, str(e)
    
    def disconnect_warp(self) -> Tuple[bool, str]:
        """Desconecta WARP"""
        try:
            subprocess.run(
                [self.warp_cli, 'disconnect'],
                capture_output=True,
                timeout=10
            )
            self.proxy_url = None
            self.current_method = None
            logger.info("⏹️ WARP desconectado")
            return True, "WARP desconectado"
        except Exception as e:
            return False, str(e)
    
    def warp_call(self, args: list, timeout: int = 10) -> subprocess.CompletedProcess:
        """Executa warp-cli com --accept-tos (igual ao original C++)"""
        cmd = [self.warp_cli, '--accept-tos'] + args
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result
        except subprocess.TimeoutExpired:
            logger.warning(f"  ⚠️ Timeout: warp-cli {' '.join(args)}")
            return subprocess.CompletedProcess(cmd, returncode=1, stdout='', stderr='timeout')
        except Exception as e:
            logger.error(f"  ❌ Erro warp-cli: {e}")
            return subprocess.CompletedProcess(cmd, returncode=1, stdout='', stderr=str(e))

    def warp_up(self) -> bool:
        """
        Configura e conecta WARP após novo registro (igual ao warpUp() do original C++).
        Faz: registration show → mode proxy → proxy port → connect → poll status → verify trace
        """
        port = self.config.get('warp_port', 40000)
        
        # Verificar se registro existe, se não criar
        result = self.warp_call(['registration', 'show'])
        if result.returncode != 0 or 'Missing' in result.stdout:
            self.warp_call(['registration', 'new'], timeout=15)
        
        # Configurar modo proxy (ESSENCIAL - o original sempre faz isso!)
        logger.info("  Configurando modo proxy...")
        self.warp_call(['mode', 'proxy'])
        self.warp_call(['proxy', 'port', str(port)])
        
        # Conectar
        logger.info("  Conectando WARP...")
        self.warp_call(['connect'], timeout=30)
        
        # Poll status até conectar (igual ao original: loop com warpCall("status"))
        wait_secs = 15
        logger.info(f"  Aguardando conexão (até {wait_secs}s)...")
        for i in range(wait_secs):
            result = self.warp_call(['status'])
            if result.returncode == 0 and 'Connected' in result.stdout:
                logger.info(f"  ✅ WARP conectado após {i+1}s")
                break
            time.sleep(1)
        
        # Configurar proxy URL
        self.proxy_url = f"http://127.0.0.1:{port}"
        self.current_method = "WARP"
        
        # Verificar via Cloudflare trace (igual ao warpCheck do original)
        new_ip = self.get_current_ip(use_proxy=True)
        if new_ip:
            self.current_ip = new_ip
            return True
        
        return False
    
    def rotate_warp_ip(self) -> Tuple[bool, str]:
        """
        Rotaciona IP do WARP (igual ao warpRotate() + warpUp() do original C++).
        
        Original C++ faz:
          1. warpCall("disconnect")
          2. warpCall("registration delete")
          3. warpCall("registration new")  ← falha = aborta
          4. warpUp() → mode proxy → proxy port → connect → poll → verify
        """
        logger.info("🔄 Rotacionando IP WARP...")
        
        old_ip = self.current_ip
        
        try:
            # PASSO 1: Desconectar (igual ao original: disconnect first so the old tunnel is gone)
            logger.info("  [1/3] Desconectando WARP...")
            self.warp_call(['disconnect'])
            
            # PASSO 2: Deletar registro antigo
            logger.info("  [2/3] Deletando registro antigo...")
            self.warp_call(['registration', 'delete'])
            
            # PASSO 3: Criar novo registro (falha = aborta, igual ao original)
            logger.info("  [3/3] Criando novo registro...")
            result = self.warp_call(['registration', 'new'], timeout=15)
            if result.returncode != 0:
                logger.error(f"  ❌ warp-cli registration new failed: {result.stderr}")
                return False, "warp-cli registration new failed"
            
            # PASSO 4: warpUp() - reconfigura tudo e reconecta
            logger.info("  Reconfigurando e reconectando (warpUp)...")
            if self.warp_up():
                new_ip = self.current_ip
                if new_ip != old_ip:
                    logger.info(f"✅ IP rotacionado: {old_ip} → {new_ip}")
                    return True, f"IP rotacionado para {new_ip}"
                else:
                    logger.info(f"✅ Registro renovado (IP mantido: {new_ip})")
                    return True, f"Registro renovado - IP: {new_ip}"
            else:
                logger.error("  ❌ warpUp falhou - proxy não respondeu")
                return False, "Falha ao verificar novo IP após reconexão"
                
        except Exception as e:
            logger.error(f"❌ Erro ao rotacionar IP: {e}")
            return False, str(e)
    
    def connect_tor(self) -> Tuple[bool, str]:
        """Conecta via Tor (placeholder)"""
        logger.info("🧅 Tor ainda não implementado")
        return False, "Tor ainda não implementado nesta versão"
    
    def connect_proxy(self) -> Tuple[bool, str]:
        """Conecta via proxy HTTP (placeholder)"""
        logger.info("🌐 Proxy ainda não implementado")
        return False, "Proxy ainda não implementado nesta versão"
    
    def connect_direct(self) -> Tuple[bool, str]:
        """Conexão direta (sem proxy)"""
        self.proxy_url = None
        self.current_method = "Direct"
        self.current_ip = self.get_current_ip()
        logger.info(f"🔓 Conexão direta. IP: {self.current_ip}")
        return True, "Conexão direta ativa"
    
    def connect(self, method: str) -> Tuple[bool, str]:
        """Conecta usando método especificado"""
        method = method.upper()
        
        if method == "WARP":
            return self.connect_warp()
        elif method == "TOR":
            return self.connect_tor()
        elif method == "PROXY":
            return self.connect_proxy()
        elif method == "DIRECT":
            return self.connect_direct()
        else:
            return False, f"Método desconhecido: {method}"
    
    def disconnect(self) -> Tuple[bool, str]:
        """Desconecta método atual"""
        if self.current_method == "WARP":
            return self.disconnect_warp()
        else:
            self.proxy_url = None
            self.current_method = None
            return True, "Desconectado"
    
    def get_status(self) -> dict:
        """Retorna status da conexão"""
        return {
            "method": self.current_method,
            "ip": self.current_ip,
            "proxy_url": self.proxy_url,
            "connected": self.current_method is not None
        }
