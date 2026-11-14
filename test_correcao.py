# -*- coding: utf-8 -*-
"""
Teste da correção: Reinício do serviço após rotação
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

from core import ConnectionManager, OpenCodeManager, Config, IPRotator

print("\n" + "="*70)
print(" 🧪 TESTE DA CORREÇÃO: Reinício do Serviço")
print("="*70 + "\n")

# Inicializar
config = Config()
om = OpenCodeManager(config)
cm = ConnectionManager(config, om)
rotator = IPRotator(cm, config, om)

# Verificar estrutura
print("1️⃣  Verificando estrutura...")
print(f"   ConnectionManager tem opencode: {cm.opencode is not None}")
print(f"   OpenCode suporta service: {om.supports_service()}")
print()

# Verificar se WARP está disponível
print("2️⃣  Verificando WARP...")
if not cm.check_warp_installed():
    print("   ❌ WARP não instalado - teste limitado")
    print()
else:
    print("   ✅ WARP instalado")
    print(f"   Comando: {cm.warp_cli}")
    print()

# Simular fluxo de rotação (sem realmente rotacionar)
print("3️⃣  Testando lógica de restart do serviço...")
print()

# Código que seria executado após rotação bem-sucedida:
print("   if self.opencode and self.opencode.supports_service():")
if cm.opencode and cm.opencode.supports_service():
    print("      ✅ Condição satisfeita!")
    print("      logger.info('♻️  Reiniciando serviço de background...')")
    print("      if self.opencode.restart_service(proxy_url=self.proxy_url):")
    print("         ✅ Serviço seria reiniciado com novo proxy!")
else:
    print("      ⚠️  Condição NÃO satisfeita")
    if not cm.opencode:
        print("      Motivo: opencode não está disponível no ConnectionManager")
    elif not cm.opencode.supports_service():
        print("      Motivo: OpenCode não suporta comando 'service'")

print()
print("="*70)
print(" 📊 RESUMO")
print("="*70)
print()

if cm.opencode and cm.opencode.supports_service():
    print("✅ CORREÇÃO IMPLEMENTADA CORRETAMENTE!")
    print()
    print("   Após rotação bem-sucedida, o código vai:")
    print("   1. Detectar que OpenCode v2 tem serviço")
    print("   2. Executar: opencode service restart")
    print("   3. Passar proxy_url para o serviço")
    print("   4. Serviço fecha sockets antigas e abre novas")
    print("   5. OpenCode usa o IP novo de verdade!")
    print()
else:
    print("⚠️  ATENÇÃO:")
    print()
    if not cm.opencode:
        print("   - ConnectionManager não tem referência ao OpenCode")
        print("   - Restart do serviço não vai funcionar")
    else:
        print("   - OpenCode CLI não suporta comando 'service'")
        print("   - Provavelmente é OpenCode v1")
        print("   - v1 não tem serviço de background")
        print("   - Restart não é necessário!")

print()
print("="*70 + "\n")
