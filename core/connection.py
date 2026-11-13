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
        """Desconecta WARP com checagem de código de retorno"""
        try:
            result = self.warp_call(['disconnect'], timeout=10)
            self.proxy_url = None
            self.current_method = None
            if result.returncode == 0:
                logger.info("⏹️ WARP desconectado com sucesso")
                return True, "WARP desconectado"
            else:
                logger.warning(f"⚠️ Falha ao desconectar WARP: {result.stderr.strip()}")
                return False, f"Falha ao desconectar: {result.stderr.strip()}"
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
        Configura e conecta WARP com validação em cada etapa.
        Faz: registration show → mode proxy → proxy port → connect → poll status → verify trace
        """
        port = self.config.get('warp_port', 40000)
        
        # 1. Verificar se registro existe; se não, criar
        result = self.warp_call(['registration', 'show'])
        if result.returncode != 0 or 'Missing' in result.stdout:
            reg_new = self.warp_call(['registration', 'new'], timeout=15)
            if reg_new.returncode != 0:
                logger.error(f"  ❌ Falha ao criar novo registro WARP: {reg_new.stderr.strip()}")
                return False
        
        # 2. Configurar modo proxy e verificar retorno
        logger.info("  Configurando modo proxy...")
        mode_res = self.warp_call(['mode', 'proxy'])
        if mode_res.returncode != 0:
            logger.error(f"  ❌ Falha ao definir modo proxy: {mode_res.stderr.strip()}")
            return False
            
        port_res = self.warp_call(['proxy', 'port', str(port)])
        if port_res.returncode != 0:
            logger.error(f"  ❌ Falha ao configurar porta do proxy ({port}): {port_res.stderr.strip()}")
            return False
        
        # 3. Conectar
        logger.info("  Conectando WARP...")
        conn_res = self.warp_call(['connect'], timeout=30)
        if conn_res.returncode != 0 and 'Connected' not in conn_res.stdout:
            logger.warning(f"  ⚠️ Aviso na conexão inicial do WARP: {conn_res.stderr.strip()}")
        
        # 4. Polling de status até conectar
        wait_secs = 15
        logger.info(f"  Aguardando conexão (até {wait_secs}s)...")
        connected = False
        for i in range(wait_secs):
            status_res = self.warp_call(['status'])
            if status_res.returncode == 0 and 'Connected' in status_res.stdout:
                logger.info(f"  ✅ WARP conectado após {i+1}s")
                connected = True
                break
            time.sleep(1)
        
        if not connected:
            logger.error("  ❌ Timeout ao aguardar status 'Connected' do WARP")
            return False
        
        # 5. Configurar proxy URL e verificar trace real
        self.proxy_url = f"http://127.0.0.1:{port}"
        self.current_method = "WARP"
        
        new_ip = self.get_current_ip(use_proxy=True)
        if new_ip:
            self.current_ip = new_ip
            return True
        
        logger.error("  ❌ WARP conectou mas requisições no proxy não validaram com sucesso")
        return False
    
    def rotate_warp_ip(self, max_attempts: int = 3) -> Tuple[bool, str]:
        """
        Rotaciona IP do WARP com validação real de mudança de endereço.
        Garante que só retorna True se o novo IP for comprovadamente diferente do anterior.
        """
        logger.info("🔄 Rotacionando IP WARP...")
        old_ip = self.current_ip
        
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"  Tentativa {attempt}/{max_attempts} de renovação de rota...")
                
                # Passo 1: Desconectar túnel ativo
                self.warp_call(['disconnect'])
                time.sleep(1)
                
                # Passo 2: Deletar registro de sessão anterior
                self.warp_call(['registration', 'delete'])
                time.sleep(1)
                
                # Passo 3: Gerar novo registro
                reg_res = self.warp_call(['registration', 'new'], timeout=15)
                if reg_res.returncode != 0:
                    logger.error(f"  ❌ warp-cli registration new falhou: {reg_res.stderr.strip()}")
                    time.sleep(2)
                    continue
                
                # Passo 4: Subir proxy e verificar IP
                if self.warp_up():
                    new_ip = self.current_ip
                    if old_ip and new_ip == old_ip:
                        if attempt < max_attempts:
                            logger.warning(f"  ⚠️ IP obtido é idêntico ao anterior ({new_ip}). Solicitando nova rota...")
                            time.sleep(2)
                            continue
                        else:
                            logger.warning(f"⚠️ Registro renovado mas o Cloudflare manteve o mesmo IP ({new_ip})")
                            return False, f"IP não mudou após {max_attempts} tentativas (mantido: {new_ip})"
                    else:
                        logger.info(f"✅ IP rotacionado com sucesso: {old_ip or 'Nenhum'} → {new_ip}")
                        return True, f"IP rotacionado para {new_ip}"
                else:
                    logger.warning(f"  ⚠️ Falha ao reestabelecer proxy na tentativa {attempt}")
                    time.sleep(2)
                    
            except Exception as e:
                logger.error(f"❌ Erro na rotação: {e}")
                time.sleep(2)
                
        return False, f"Falha ao obter novo IP após {max_attempts} tentativas"
    
    def connect_direct(self) -> Tuple[bool, str]:
        """Conexão direta (sem proxy)"""
        self.proxy_url = None
        self.current_method = "Direct"
        self.current_ip = self.get_current_ip(use_proxy=False)
        logger.info(f"🔓 Conexão direta ativa. IP: {self.current_ip}")
        return True, "Conexão direta ativa"
    
    def connect(self, method: str) -> Tuple[bool, str]:
        """Conecta usando método especificado (WARP ou DIRECT)"""
        method = method.upper()
        
        if method == "WARP":
            return self.connect_warp()
        elif method == "DIRECT":
            return self.connect_direct()
        else:
            return False, f"Método não suportado: {method}. Métodos disponíveis: WARP, DIRECT"
    
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
