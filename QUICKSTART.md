# 🚀 QuickStart - CodeOpen

## Instalação Rápida

### Automática (Recomendado)
```bash
INSTALAR.bat
```

### Manual
```bash
pip install -r requirements.txt
```

**Depois instale o Cloudflare WARP:**
- Download: https://1.1.1.1/
- Abra-o pelo menos uma vez. (O CodeOpen configura o proxy na porta 40000 automaticamente).

## Usar Agora

```bash
# Windows
INICIAR.bat

# Ou direto
python select_language.py
```

## Controles

- **W/S** ou **↑/↓** = Navegar
- **ENTER** = Selecionar
- **ESC/Q** = Sair

## Modo Automático

1. Selecione "MODO AUTOMATICO"
2. CodeOpen vai:
   - Conectar WARP
   - Iniciar OpenCode
   - Monitorar limites
   - Rotacionar IP automaticamente
   - Reiniciar quando necessário

## Troubleshooting

**Interface piscando?**
→ Use Windows Terminal: https://aka.ms/terminal

**WARP não conecta?**
```bash
warp-cli disconnect
warp-cli connect
```

**Falta alguma lib?**
```bash
pip install blessed windows-curses psutil requests watchdog
```

---

✨ **CodeOpen** by OFICINA-DO-BERG
