# CodeOpen
**by OFICINA-DO-BERG**

Rotação automática de IP via WARP quando os limites do OpenCode são atingidos.

## ✨ Funcionalidades

- ✅ Rotação automática de IP via WARP
- ✅ Monitoramento de logs em tempo real  
- ✅ Detecção automática de limites (11 padrões)
- ✅ Interface CLI sem piscar (blessed)
- ✅ Suporte bilíngue (PT/EN)
- ✅ Navegação por teclado (W/S ou ↑/↓)

## 🚀 Instalação

1. **Instalar Python 3.8+**

2. **Instalar dependências:**
```bash
pip install -r requirements.txt
```

3. **Instalar Cloudflare WARP:**
   - Download: https://1.1.1.1/
   - Criar conta gratuita

## 🎮 Como Usar

### Método 1: INICIAR.bat (Recomendado)
```bash
INICIAR.bat
```

### Método 2: Python direto
```bash
python select_language.py
```

### Método 3: CLI direto com idioma
```bash
python cli.py pt   # Português
python cli.py en   # English
```

## 🎮 Controles

| Tecla | Ação |
|-------|------|
| **W** ou **↑** | Subir no menu |
| **S** ou **↓** | Descer no menu |
| **ENTER** | Selecionar opção |
| **ESC** ou **Q** | Voltar/Sair |

## 🔧 Estrutura

```
opencode-infinity-simple/
├── core/              # Lógica principal
│   ├── config.py      # Configurações
│   ├── connection.py  # Gerenciamento WARP
│   ├── opencode.py    # Controle OpenCode
│   ├── rotator.py     # Rotação de IP
│   ├── monitor.py     # Monitoramento logs
│   └── orchestrator.py # Orquestração
├── utils/             # Utilitários
│   └── logger.py      # Sistema de logs
├── select_language.py # Seletor de idioma
├── cli.py             # Interface CLI principal
├── INICIAR.bat        # Launcher Windows
└── README.md          # Este arquivo
```

## 🌐 Fluxo Automático

1. Conecta ao WARP
2. Inicia OpenCode
3. Monitora logs
4. Detecta mensagens de limite
5. Rotaciona IP automaticamente
6. Reinicia OpenCode
7. Repete o processo

## 🐛 Solução de Problemas

### Interface piscando
✅ **Recomendado**: Use Windows Terminal
- Download: https://aka.ms/terminal
- A interface fica 100% suave

### WARP não conecta
```bash
warp-cli status
warp-cli disconnect
warp-cli connect
```

### OpenCode não encontrado
Editar configuração:
```
C:\Users\SEU_USUARIO\.opencode-infinity-simple\config.json
```

## 💻 Requisitos

- **OS**: Windows 10/11
- **Python**: 3.8+
- **WARP**: Cloudflare WARP
- **OpenCode**: Instalado via npm

## 📦 Versão

**v2.0** - Interface Blessed (Estável)
- ✅ Rotação de IP funcionando
- ✅ Interface sem piscar (blessed)
- ✅ Suporte bilíngue

## 🤝 Créditos

**Desenvolvido por**: OFICINA-DO-BERG  
**Baseado em**: OpenCode Infinite

## 📜 Licença

Livre para uso pessoal.

---

**CodeOpen** - Rotação inteligente de IP para OpenCode 🚀
