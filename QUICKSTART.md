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

# Ou direto com Python
python main.py
```

## Controles

- **W/S** ou **↑/↓** = Navegar
- **ENTER** = Selecionar
- **ESC** = Sair

## Como Usar

1. Selecione **[ INICIAR OPENCODE ]**
2. O CodeOpen vai:
   - Conectar o WARP no modo proxy local
   - Iniciar o OpenCode roteado pelo proxy
   - Monitorar limites em tempo real
   - Rotacionar o IP automaticamente quando atingir o limite

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
pip install -r requirements.txt
```

---

✨ **CodeOpen** by OFICINA-DO-BERG
