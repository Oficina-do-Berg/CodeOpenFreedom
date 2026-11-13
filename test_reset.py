# -*- coding: utf-8 -*-
"""
Teste do Deep Reset (Padrão Original C++)
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

from core import OpenCodeManager, Config
from pathlib import Path

print("\n" + "="*70)
print(" 🧪 TESTE DE VERIFICAÇÃO DO DEEP RESET (PADRÃO ORIGINAL)")
print("="*70 + "\n")

config = Config()
om = OpenCodeManager(config)

# 1. Pastas do OpenCode
print("📂 Estrutura de Diretórios:")
print(f"   Data folder:    {om.get_data_folder()} (Existe: {'✅' if om.get_data_folder().exists() else '❌'})")
print(f"   Config folder:  {om.get_config_folder()} (Existe: {'✅' if om.get_config_folder().exists() else '❌'})")
print(f"   Cache folder:   {om.get_cache_folder()} (Existe: {'✅' if om.get_cache_folder().exists() else '❌'})")

# 2. Arquivos de autenticação
auth_file = om.get_auth_file()
print(f"\n🔑 Arquivo de Autenticação Ativo:")
print(f"   Caminho: {auth_file}")
print(f"   Existe:  {'✅' if auth_file.exists() else '❌'}")

# 3. Snapshot DPAPI (Token Guard do C++)
snap_dir = om.get_token_snapshot_dir()
snap_file = om.get_token_snapshot_file()
print(f"\n🛡️ Token Guard (Snapshot DPAPI):")
print(f"   Snapshot Dir:  {snap_dir}")
print(f"   auth.dpapi:    {'✅ Presente' if snap_file.exists() else '⚪ Não criado'}")

# 4. Banco de dados e Chats
print(f"\n📊 Arquivos de Chat:")
for db_file in om.get_chat_files():
    size_str = f"({db_file.stat().st_size // (1024*1024)} MB)" if db_file.exists() else ""
    print(f"   {'✅' if db_file.exists() else '❌'} {db_file.name} {size_str}")

storage = om.get_storage_folder()
print(f"   {'✅' if storage.exists() else '❌'} storage/ ({storage})")

print("\n" + "="*70)
print("💡 FLUXO REAL DO RESET (IGUAL AO C++ ORIGINAL):")
print("   1. Para o OpenCode (stopApp)")
print("   2. Arquiva os chats em: Desktop/opencode_chats_archiviate/<timestamp>")
print("   3. Faz backup e deleta os tokens (clearTokens)")
print("   4. Remove snapshot DPAPI (tokenDropSnapshot) para não restaurar sessão")
print("   5. Limpa pasta de cache: ~/.cache/opencode (clearCache)")
print("   6. Rotaciona IP via WARP: disconnect → delete → new → proxy setup → connect")
print("   7. Inicia OpenCode limpo com novo IP")
print("="*70 + "\n")
