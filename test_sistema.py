# -*- coding: utf-8 -*-
"""
Script de teste completo do sistema
"""

import sys
import os

# Configurar UTF-8
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    import io
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    else:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from core import Config, ConnectionManager, OpenCodeManager

def test_all():
    print("\n" + "="*70)
    print(" 🧪 TESTE COMPLETO DO SISTEMA CODEOPEN")
    print("="*70 + "\n")
    
    # 1. Config
    print("1️⃣  Testando Config...")
    try:
        config = Config()
        print("   ✅ Config OK")
    except Exception as e:
        print(f"   ❌ ERRO Config: {e}")
        return
    
    # 2. ConnectionManager
    print("\n2️⃣  Testando ConnectionManager...")
    try:
        cm = ConnectionManager(config)
        print("   ✅ ConnectionManager OK")
        
        # Verificar WARP
        print("\n   🔍 Verificando WARP...")
        warp_ok = cm.check_warp_installed()
        print(f"   {'✅' if warp_ok else '❌'} WARP instalado: {warp_ok}")
        if warp_ok:
            print(f"   📍 WARP CLI: {cm.warp_cli}")
        
        # Status atual
        status = cm.get_status()
        print(f"\n   📊 Status conexão:")
        print(f"      - Método: {status['method'] or 'Nenhum'}")
        print(f"      - IP: {status['ip'] or 'N/A'}")
        print(f"      - Conectado: {status['connected']}")
        
        # Testar conexão WARP
        print("\n   🔌 Testando conexão WARP...")
        success, msg = cm.connect('WARP')
        print(f"   {'✅' if success else '❌'} {msg}")
        
        if success:
            status = cm.get_status()
            print(f"   📍 IP conectado: {status['ip']}")
            print(f"   🌐 Proxy URL: {status['proxy_url']}")
        
    except Exception as e:
        print(f"   ❌ ERRO ConnectionManager: {e}")
        import traceback
        traceback.print_exc()
    
    # 3. OpenCodeManager
    print("\n3️⃣  Testando OpenCodeManager...")
    try:
        om = OpenCodeManager(config)
        print("   ✅ OpenCodeManager OK")
        
        # Verificar OpenCode
        print("\n   🔍 Procurando OpenCode...")
        opencode_path = om.find_opencode()
        if opencode_path:
            print(f"   ✅ OpenCode encontrado: {opencode_path}")
        else:
            print("   ❌ OpenCode NÃO encontrado")
            print("   💡 Instale com: npm install -g @opencode/cli")
        
        # Verificar se está rodando
        running = om.is_running()
        print(f"   {'🟢' if running else '⚪'} OpenCode rodando: {running}")
        
    except Exception as e:
        print(f"   ❌ ERRO OpenCodeManager: {e}")
        import traceback
        traceback.print_exc()
    
    # Resumo
    print("\n" + "="*70)
    print(" 📋 RESUMO")
    print("="*70)
    print(f"\n   ✅ Python: {sys.version.split()[0]}")
    print(f"   {'✅' if warp_ok else '❌'} WARP: {'Instalado' if warp_ok else 'NÃO instalado'}")
    print(f"   {'✅' if opencode_path else '❌'} OpenCode: {'Instalado' if opencode_path else 'NÃO instalado'}")
    print(f"   {'🟢' if success else '⚪'} Conexão WARP: {'Funcionando' if success else 'Erro'}")
    
    print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    test_all()
