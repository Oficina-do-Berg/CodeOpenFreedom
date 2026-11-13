# 🎯 CodeOpen - Guia Passo a Passo Completo

## PASSO 1: INSTALAÇÃO INICIAL

### O que você precisa ter instalado:

✅ **Python 3.8 ou superior**
   - Abra PowerShell e digite: `python --version`
   - Se não tiver, baixe em: https://www.python.org/downloads/

✅ **Cloudflare WARP**
   - Baixe em: https://1.1.1.1/
   - Instale normalmente
   - Abra o app WARP pelo menos uma vez

✅ **OpenCode** (se ainda não tiver)
   - Abra PowerShell e digite: `npm install -g @opencode/cli`

---

## PASSO 2: INSTALAR DEPENDÊNCIAS

1. Abra o **PowerShell** ou **Windows Terminal**
2. Navegue até a pasta:
```powershell
cd "c:\Users\berg\Desktop\OPENCODE INFINITE TESTE\opencode-infinity-simple"
```

3. Execute o instalador:
```powershell
.\INSTALAR.bat
```

**O que isso faz:**
- ✓ Verifica se Python está instalado
- ✓ Atualiza o pip
- ✓ Instala todas as bibliotecas necessárias
- ✓ Mostra mensagem de sucesso

---

## PASSO 3: INICIAR O PROGRAMA

### Opção A: Via Launcher (Recomendado)
```powershell
.\INICIAR.bat
```

### Opção B: Manualmente
```powershell
python select_language.py
```

---

## PASSO 4: ESCOLHER IDIOMA

Ao iniciar, você verá:

```
┌─────────────────────────────┐
│   SELECIONE SEU IDIOMA      │
├─────────────────────────────┤
│ > [ Portugues ]             │
│   [ English ]               │
└─────────────────────────────┘
```

**Navegação:**
- Use **W/S** ou **↑/↓** para mover
- Pressione **ENTER** para confirmar

---

## PASSO 5: MENU PRINCIPAL

Você verá a tela principal:

```
   ██████╗ ██████╗ ██████╗ ███████╗ ██████╗ ██████╗ ███████╗███╗   ██╗
  ██╔════╝██╔═══██╗██╔══██╗██╔════╝██╔═══██╗██╔══██╗██╔════╝████╗  ██║
  ██║     ██║   ██║██║  ██║█████╗  ██║   ██║██████╔╝█████╗  ██╔██╗ ██║
  ██║     ██║   ██║██║  ██║██╔══╝  ██║   ██║██╔═══╝ ██╔══╝  ██║╚██╗██║
  ╚██████╗╚██████╔╝██████╔╝███████╗╚██████╔╝██║     ███████╗██║ ╚████║
   ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝ ╚═════╝ ╚═╝     ╚══════╝╚═╝  ╚═══╝
                                           by OFICINA-DO-BERG

  Conexao: Desconectado
  OpenCode: PARADO
  Monitor: INATIVO
  Rotacoes: 0

──────────────────────────────────────────────────────────────────────

  > [ MODO AUTOMATICO ]
    [ INICIAR ]
    [ PARAR ]
    [ ROTACIONAR IP ]
    [ CONEXAO ]
    [ SAIR ]

  Use W/S ou ↑/↓ | ENTER | ESC para sair
```

---

## PASSO 6: USAR AS FUNCIONALIDADES

### 🔴 Opção 1: MODO AUTOMATICO (Recomendado)

**O que faz:**
- Monitora os logs do OpenCode em tempo real
- Detecta automaticamente quando você atinge o limite
- Para o OpenCode
- Rotaciona seu IP via WARP
- Reinicia o OpenCode
- Repete o ciclo infinitamente

**Como usar:**
1. Navegue até `[ MODO AUTOMATICO ]`
2. Pressione ENTER
3. O sistema fará tudo automaticamente!

**Quando usar:** Quando você vai trabalhar por horas e quer que o IP rotacione sozinho

---

### 🔴 Opção 2: INICIAR OpenCode

**O que faz:**
- Inicia o OpenCode manualmente (equivalente a digitar `opencode` no terminal)

**Como usar:**
1. Navegue até `[ INICIAR ]`
2. Pressione ENTER
3. Aguarde a mensagem de confirmação

**Quando usar:** Para iniciar o OpenCode uma única vez manualmente

---

### 🔴 Opção 3: PARAR OpenCode

**O que faz:**
- Para todos os processos do OpenCode rodando

**Como usar:**
1. Navegue até `[ PARAR ]`
2. Pressione ENTER

**Quando usar:** Quando quiser encerrar o OpenCode

---

### 🔴 Opção 4: ROTACIONAR IP

**O que faz:**
- Força uma rotação de IP imediata via WARP
- Processo: desconecta → deleta registro → cria novo → reconecta
- Demora cerca de 16 segundos

**Como usar:**
1. Navegue até `[ ROTACIONAR IP ]`
2. Pressione ENTER
3. Aguarde ~16 segundos

**Quando usar:** Quando você atingiu o limite e quer rotacionar manualmente

---

### 🔴 Opção 5: CONEXAO (Menu de gerenciamento)

**O que tem dentro:**
```
  > [ CONECTAR WARP ]    → Conecta ao WARP
    [ DESCONECTAR ]      → Desconecta do WARP
    [ ROTACIONAR ]       → Rotaciona o IP
    [ VOLTAR ]           → Volta ao menu principal
```

**Como usar:**
1. Navegue até `[ CONEXAO ]`
2. Pressione ENTER
3. Escolha a sub-opção desejada
4. Pressione ESC para voltar

---

### 🔴 Opção 6: SAIR

**O que faz:**
- Encerra o programa com segurança
- Para monitoramento se estiver ativo
- Para OpenCode se estiver rodando

---

## PASSO 7: FLUXO DE TRABALHO RECOMENDADO

### 📌 Cenário A: Uso Automático (Ideal para trabalho longo)

```
1. Abra o CodeOpen (INICIAR.bat)
2. Selecione o idioma
3. Vá em [ CONEXAO ] → [ CONECTAR WARP ]
4. Volte ao menu principal (ESC)
5. Selecione [ MODO AUTOMATICO ]
6. Deixe rodando!
```

O programa vai:
- ✓ Iniciar o OpenCode
- ✓ Monitorar os logs
- ✓ Rotacionar automaticamente quando atingir limite
- ✓ Continuar trabalhando sem interrupção

---

### 📌 Cenário B: Uso Manual (Controle total)

```
1. Abra o CodeOpen (INICIAR.bat)
2. Selecione o idioma
3. Vá em [ CONEXAO ] → [ CONECTAR WARP ]
4. Volte e selecione [ INICIAR ]
5. Quando atingir limite: [ ROTACIONAR IP ]
6. Repita passo 5 quando necessário
```

---

## PASSO 8: CONTROLES DE NAVEGAÇÃO

| Tecla | Ação |
|-------|------|
| **W** ou **↑** | Move para cima |
| **S** ou **↓** | Move para baixo |
| **ENTER** | Confirma seleção |
| **ESC** | Volta/Sai |

---

## PASSO 9: ENTENDENDO A TELA DE STATUS

```
  Conexao: WARP - 2a0d:xxxx:xxxx    ← Seu IP atual via WARP
  OpenCode: ATIVO                    ← OpenCode está rodando
  Monitor: ATIVO                     ← Sistema monitorando logs
  Rotacoes: 5                        ← Quantas vezes já rotacionou
```

**Status possíveis:**
- `Conexao: Desconectado` → WARP não está conectado
- `OpenCode: PARADO` → OpenCode não está rodando
- `Monitor: INATIVO` → Não está monitorando logs
- `Rotacoes: X` → Contador de rotações realizadas

---

## PASSO 10: SOLUÇÃO DE PROBLEMAS

### ❌ Erro: "WARP-CLI não encontrado"
**Causa:** WARP não está instalado ou está em local diferente

**Solução:**
1. Baixe WARP em https://1.1.1.1/
2. Instale normalmente
3. Abra o app WARP pelo menos uma vez

---

### ❌ Erro: "OpenCode não encontrado"
**Causa:** OpenCode não está instalado globalmente

**Solução:**
```powershell
npm install -g @opencode/cli
```

---

### ❌ Problema: Caracteres estranhos/embaralhados
**Causa:** PowerShell antigo não suporta UTF-8 corretamente

**Solução:** Use **Windows Terminal** ao invés do PowerShell tradicional
- Baixe na Microsoft Store: "Windows Terminal"
- Abra e execute `INICIAR.bat` nele

---

### ❌ Problema: Setas não funcionam
**Causa:** Terminal com suporte limitado a teclas especiais

**Solução:** Use **W** (cima) e **S** (baixo) ao invés das setas

---

### ❌ Problema: IP não rotaciona
**Causa:** WARP não está conectado

**Solução:**
1. Vá em [ CONEXAO ]
2. Selecione [ CONECTAR WARP ]
3. Aguarde 3-5 segundos
4. Tente rotacionar novamente

---

### ❌ Problema: "Modo Automático em desenvolvimento"
**Causa:** Funcionalidade ainda não implementada completamente

**Solução:** Use o modo manual por enquanto:
1. [ CONEXAO ] → [ CONECTAR WARP ]
2. [ INICIAR ] para iniciar OpenCode
3. Quando atingir limite: [ ROTACIONAR IP ]

---

## 📂 ARQUIVOS E PASTAS

### Onde ficam os arquivos:

**Logs do programa:**
```
C:\Users\berg\.opencode-infinity-simple\app.log
```

**Configuração:**
```
C:\Users\berg\.opencode-infinity-simple\config.json
```

**Arquivos do projeto:**
```
opencode-infinity-simple/
├── cli.py                    ← Interface principal
├── select_language.py        ← Seletor de idioma
├── INICIAR.bat              ← Launcher
├── INSTALAR.bat             ← Instalador
├── requirements.txt         ← Dependências
├── README.md                ← Documentação técnica
├── QUICKSTART.md            ← Guia rápido
├── GUIA-COMPLETO.md         ← Este guia
├── core/                    ← Módulos principais
│   ├── config.py
│   ├── connection.py
│   ├── opencode.py
│   ├── rotator.py
│   ├── monitor.py
│   └── orchestrator.py
└── utils/                   ← Utilitários
    ├── logger.py
    └── helpers.py
```

---

## 🎯 EXEMPLO PRÁTICO: PRIMEIRO USO

### Passo a passo completo para primeira vez:

```powershell
# ─────────────────────────────────────────────────
# PASSO 1: Instalar dependências
# ─────────────────────────────────────────────────
cd "c:\Users\berg\Desktop\OPENCODE INFINITE TESTE\opencode-infinity-simple"
.\INSTALAR.bat

# Aguarde aparecer: "Instalacao concluida com sucesso!"

# ─────────────────────────────────────────────────
# PASSO 2: Iniciar programa
# ─────────────────────────────────────────────────
.\INICIAR.bat

# ─────────────────────────────────────────────────
# PASSO 3: No seletor de idioma
# ─────────────────────────────────────────────────
# - [ Portugues ] já está selecionado
# - Pressione ENTER

# ─────────────────────────────────────────────────
# PASSO 4: No menu principal
# ─────────────────────────────────────────────────
# - Navegue até [ CONEXAO ] (use W/S ou setas)
# - Pressione ENTER

# ─────────────────────────────────────────────────
# PASSO 5: No submenu de conexão
# ─────────────────────────────────────────────────
# - Selecione [ CONECTAR WARP ]
# - Pressione ENTER
# - Aguarde 3-5 segundos conectar
# - Pressione qualquer tecla quando aparecer a mensagem

# ─────────────────────────────────────────────────
# PASSO 6: Voltar ao menu (ESC)
# ─────────────────────────────────────────────────
# - Pressione ESC

# ─────────────────────────────────────────────────
# PASSO 7: Iniciar OpenCode
# ─────────────────────────────────────────────────
# - Navegue até [ INICIAR ]
# - Pressione ENTER
# - Aguarde mensagem de confirmação
# - Pressione qualquer tecla

# ─────────────────────────────────────────────────
# PASSO 8: Trabalhe normalmente!
# ─────────────────────────────────────────────────
# Quando o OpenCode atingir o limite:
# - Volte ao CodeOpen
# - Selecione [ ROTACIONAR IP ]
# - Aguarde ~16 segundos
# - Continue trabalhando!
```

---

## 💡 DICAS IMPORTANTES

✅ **Use Windows Terminal** para melhor experiência visual

✅ **Modo Automático** (quando implementado) será ideal para sessões longas

✅ **Modo Manual** dá mais controle mas requer intervenção

✅ **Sempre conecte ao WARP primeiro** antes de usar outras funções

✅ **Logs são salvos automaticamente** em `~/.opencode-infinity-simple/app.log`

✅ **Rotação demora ~16 segundos** - é normal, não é bug

✅ **ESC funciona em qualquer tela** para voltar/sair

✅ **Deixe o CodeOpen aberto** em segundo plano enquanto trabalha

---

## 🔄 PROCESSO DE ROTAÇÃO DETALHADO

Quando você seleciona **[ ROTACIONAR IP ]**, acontece:

```
1. Desconectar WARP          (2 segundos)
   └─> warp-cli disconnect

2. Deletar registro atual    (3 segundos)
   └─> warp-cli registration delete

3. Criar novo registro       (3 segundos)
   └─> warp-cli registration new

4. Reconectar WARP           (8 segundos)
   └─> warp-cli connect

5. Verificar nova conexão
   └─> https://www.cloudflare.com/cdn-cgi/trace

Total: ~16 segundos
```

**Por que demora?**
- Cloudflare precisa processar o novo registro
- Nova rota de rede precisa se estabelecer
- Verificação de segurança do WARP

---

## 🆘 PRECISA DE AJUDA?

1. **Verifique os logs:**
   ```powershell
   notepad C:\Users\berg\.opencode-infinity-simple\app.log
   ```

2. **Teste WARP manualmente:**
   ```powershell
   warp-cli status
   ```

3. **Teste OpenCode manualmente:**
   ```powershell
   opencode --version
   ```

4. **Reinicie tudo:**
   ```powershell
   # Feche o CodeOpen (ESC ou [ SAIR ])
   # Desconecte WARP
   warp-cli disconnect
   
   # Reconecte
   warp-cli connect
   
   # Reinicie o CodeOpen
   .\INICIAR.bat
   ```

---

## 📊 ENTENDENDO OS LOGS

Os logs salvos em `app.log` mostram:

```
2026-11-12 10:30:15 - INFO - Conexão WARP estabelecida
2026-11-12 10:30:16 - INFO - IP atual: 2a0d:xxxx:xxxx
2026-11-12 10:35:20 - INFO - OpenCode iniciado (PID: 12345)
2026-11-12 10:45:30 - WARNING - Limite detectado nos logs
2026-11-12 10:45:31 - INFO - Iniciando rotação de IP
2026-11-12 10:45:47 - INFO - IP rotacionado com sucesso
2026-11-12 10:45:50 - INFO - OpenCode reiniciado
```

**Use os logs para:**
- Verificar se rotações estão funcionando
- Diagnosticar problemas
- Ver histórico de uso

---

## 🚀 PRÓXIMOS PASSOS

Depois de dominar o básico, você pode:

1. **Personalizar configurações** em `config.json`
2. **Verificar padrões de detecção** no monitor
3. **Ajustar tempos de espera** se necessário
4. **Contribuir com melhorias** no projeto

---

**CodeOpen by OFICINA-DO-BERG**
*Rotação inteligente de IP para OpenCode*

Versão: 2.1-stable
Última atualização: Novembro 2026
