# CodeOpen
**by OFICINA-DO-BERG**

Rotação automática de IP via WARP quando os limites do OpenCode são atingidos.

## ✨ Funcionalidades

- ✅ Rotação automática de IP via WARP
- ✅ Monitoramento de logs em tempo real  
- ✅ Detecção automática de limites (11 padrões de erro)
- ✅ Reset Profundo seguro (arquiva seus chats no Desktop antes de resetar a cota)
- ✅ Interface CLI nativa sem piscar (Windows Terminal / PowerShell)
- ✅ Suporte bilíngue (Português / English)
- ✅ Navegação intuitiva por teclado (W/S ou ↑/↓) e menu de Ajuda integrado

## 🚀 Instalação

### Opção 1: INSTALAR.bat (Recomendado)
```bash
INSTALAR.bat
```
O script vai:
1. Verificar se Python está instalado
2. Atualizar pip
3. Instalar todas as dependências
4. Verificar instalação

### Opção 2: Manual
1. **Instalar Python 3.8+**

2. **Instalar dependências:**
```bash
pip install -r requirements.txt
```

3. **Instalar Cloudflare WARP:**
   - Download: https://1.1.1.1/
   - Instale e abra o aplicativo pelo menos uma vez para aceitar os termos.
   - 💡 **Importante:** Você **NÃO** precisa configurar proxy nem porta 40000 manualmente. O CodeOpen configura o modo proxy na porta local 40000 de forma 100% automática via `warp-cli`.

## 🎮 Como Usar

### Método 1: INICIAR.bat (Recomendado)
```bash
INICIAR.bat
```

### Método 2: Python direto
```bash
python main.py
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
| **ESC** | Sair do aplicativo |

## 🔧 Estrutura

```
opencode-infinity-simple/
├── core/              # Lógica principal
│   ├── config.py      # Configurações locais
│   ├── connection.py  # Gerenciamento de rede e Cloudflare WARP
│   ├── opencode.py    # Gerenciamento de processo, auth e chats
│   ├── rotator.py     # Rotação de IP e Deep Reset
│   ├── monitor.py     # Monitoramento de logs em tempo real
│   └── orchestrator.py # Orquestração do ciclo automático
├── utils/             # Utilitários
│   └── logger.py      # Sistema de logs
├── main.py            # Ponto de entrada padrão em Python
├── select_language.py # Seletor interativo de idioma
├── cli.py             # Interface de terminal (TUI)
├── INICIAR.bat        # Launcher de 1 clique para Windows
├── INSTALAR.bat       # Instalador de dependências
└── README.md          # Documentação principal
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

**v1.0 (Funcional)**
- ✅ Rotação automática de IP via Cloudflare WARP com proxy na porta 40000
- ✅ Reset Profundo seguro com preservação do banco de dados no Desktop
- ✅ Menu dinâmico de 1 clique (Iniciar / Parar / Rotacionar / Reset / Ajuda)
- ✅ Interface CLI sem piscar
- ✅ Suporte bilíngue (Português / English)

## 🤝 Créditos

**Desenvolvido por**: OFICINA-DO-BERG  
**Baseado em**: OpenCode Infinite

## 📜 Licença

Livre para uso pessoal.

---

**CodeOpen** - Rotação inteligente de IP para OpenCode 🚀
