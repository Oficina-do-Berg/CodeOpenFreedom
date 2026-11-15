# 🎯 CodeOpen - Guia Passo a Passo Completo

## PASSO 1: INSTALAÇÃO INICIAL

### O que você precisa ter instalado:

✅ **Python 3.8 ou superior**
   - Abra PowerShell e digite: `python --version`
   - Se não tiver, baixe em: https://www.python.org/downloads/

✅ **Cloudflare WARP**
   - Baixe em: https://1.1.1.1/
   - Instale normalmente
   - **OBRIGATÓRIO:** Abra o aplicativo Cloudflare WARP e **ligue-o (deixe conectado)** antes de iniciar o script!

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

> **AVISO OBRIGATÓRIO:** Antes de iniciar o programa, abra o aplicativo **Cloudflare WARP** e certifique-se de que ele está **ligado / conectado**.

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

  > [ INICIAR OPENCODE ]
    [ NOVA CONVERSA ]
    [ ROTACIONAR IP ]
    [ RESET PROFUNDO ]
    [ AJUDA ]
    [ SAIR ]

  Use W/S ou ↑/↓ | ENTER | ESC para sair
```

---

## PASSO 6: USAR AS FUNCIONALIDADES

### 🔴 Opção 1: INICIAR / PARAR OPENCODE (modo automático)

**O que faz ao iniciar:**
- Conecta/reutiliza o WARP na porta proxy 40000
- Abre o OpenCode com `--standalone` (e `--continue` quando existe conversa)
- Começa a monitorar **somente linhas novas** do log do OpenCode

**Quando um limite real aparece no log:**
1. Confirma que é `level=ERROR` e espera 4 segundos para o bloco de erro terminar (uma linha INFO posterior não cancela o limite)
2. Para o TUI (e o serviço de background, se existir)
3. Identifica no banco local a conversa e o **modelo** que ela usa
4. Caça uma rota que aceite esse modelo: gira o IP do WARP até 10 vezes e faz o probe com `-m <modelo>` (o probe só aprova quando o modelo responde `pong`)
5. Retoma a mesma conversa com `opencode run --auto -s <id> -m <modelo>`
6. Se nenhuma rota aceitar o modelo, troca para outro modelo `*-free` na rota atual (a cota é por modelo e também varia por rota: a caçada de IP é o plano A, a troca de modelo é o plano B)
7. Grava o modelo novo na própria conversa (`📌 Conversa fixada no modelo ...`), porque o `-m` do `run` vale só para aquele turno
8. Reabre o TUI fixado na conversa (`--session <id>`) e volta a monitorar

A retomada tem 600 s de teto e 60 s de inatividade (o mesmo `RESUME_IDLE`
do main): um turno longo continua vivo enquanto escreve; travado sem saída,
volta a girar.

O modelo que passou no probe fica salvo em `last_good_model` no
`~/.opencode-infinity-simple/config.json` e é testado primeiro na próxima vez.
Se a caçada de IP e o fallback de modelo esgotarem, o log informa em quantas
horas a próxima cota volta.

**Anti-loop:** igual ao `LIMIT_ROT_MAX` do `.bat`: **3 desbloqueios seguidos**
que voltam a bater no limite pausam o automático (`limit_rot_max` no
`config.json`; `0` desliga a trava). Um desbloqueio bem-sucedido zera a
contagem, e qualquer ação manual ([ NOVA CONVERSA ], [ ROTACIONAR IP ],
[ INICIAR OPENCODE ]) libera o automático de novo.

**Rate limit puro (HTTP 429)** não rotaciona sozinho, porque costuma ser
temporário. Use **[ ROTACIONAR IP ]** se quiser trocar a rota na mão.

**Como usar:**
1. Confirme que o aplicativo do Cloudflare WARP está ligado
2. Selecione `[ INICIAR OPENCODE ]` e pressione ENTER
3. Trabalhe normalmente; o desbloqueio acontece sozinho ao atingir o limite

**Quando usar:** quando você vai trabalhar por horas e quer que o desbloqueio aconteça sozinho (caçada de IP igual ao main + fallback para outro modelo livre)

---

### 🔴 Opção 2: NOVA CONVERSA (IP novo + sessão nova)

**O que faz:**
- Para o TUI e o monitor, gira o IP do WARP e abre uma conversa **nova**
- Não mexe na conversa antiga: ela continua guardada para [ INICIAR OPENCODE ]
- É a opção 1 do launcher original: a cota gratuita é por modelo, e uma
  conversa nova usa o modelo padrão, que costuma ter cota mesmo quando o
  modelo antigo esgotou

**Como usar:**
1. Navegue até `[ NOVA CONVERSA ]`
2. Pressione ENTER
3. Aguarde a troca de IP (~16 s) e o TUI abrir

**Quando usar:** quando o automático pausou (3 desbloqueios seguidos) ou você
quer começar um assunto do zero sem esperar a cota do modelo antigo voltar.

---

### 🔴 Opção 3: ROTACIONAR IP

**O que faz:**
- Força uma rotação de IP imediata via WARP
- Processo: desconecta → deleta registro → cria novo → reconecta → valida o IP
- Demora cerca de 16 segundos
- Se o OpenCode estiver aberto, ele é reaberto na mesma conversa com a rota nova

**Como usar:**
1. Navegue até `[ ROTACIONAR IP ]`
2. Pressione ENTER
3. Aguarde ~16 segundos

**Quando usar:** quando você precisa de um IP novo na hora (bloqueio regional, teste de rota ou rate limit por IP). Para cota gratuita de modelo esgotada, use `[ INICIAR OPENCODE ]`: ele caça uma rota que aceite o modelo e, se não houver, troca para outro modelo livre.

---

### 🔴 Opção 4: RESET PROFUNDO

**O que faz:**
- Para o TUI e o serviço de background
- Arquiva os chats em `Desktop\opencode_chats_archiviate`
- Remove `~/.local/share/opencode/auth.json` (com backup verificado antes)
- Limpa o cache de `~/.cache/opencode`
- Rotaciona o WARP e reabre o OpenCode para um novo login

**Como usar:**
1. Navegue até `[ RESET PROFUNDO ]`
2. Pressione ENTER e confirme com `S` ou `Y`

**Quando usar:** quando a cota da conta esgotou e você quer começar do zero.

> O `service.json` do OpenCode v2 (senha local do serviço) **nunca** é apagado.

---

### 🔴 Opção 5: AJUDA

Mostra o resumo das funções, teclas e requisitos.

---

### 🔴 Opção 6: SAIR

**O que faz:**
- Encerra o programa com segurança
- Para o monitoramento se estiver ativo
- Para o TUI do OpenCode se estiver rodando

---

## PASSO 7: FLUXO DE TRABALHO RECOMENDADO

### 📌 Cenário A: Uso Automático (Ideal para trabalho longo)

```
1. Abra o CodeOpen (INICIAR.bat)
2. Selecione o idioma
3. Confirme que o aplicativo Cloudflare WARP está ligado
4. Selecione [ INICIAR OPENCODE ]
5. Deixe rodando!
```

O programa vai:
- ✓ Abrir o OpenCode já roteado pelo WARP
- ✓ Monitorar somente erros novos do log
- ✓ Girar o IP do WARP como o main, testando o modelo da conversa a cada rota
- ✓ Se nenhuma rota aceitar o modelo, trocar para outro modelo livre e retomar a conversa automaticamente
- ✓ Reabrir o TUI na mesma conversa

---

### 📌 Cenário B: Uso Manual (Controle total)

```
1. Abra o CodeOpen (INICIAR.bat)
2. Selecione o idioma
3. Confirme que o aplicativo Cloudflare WARP está ligado
4. Selecione [ INICIAR OPENCODE ]
5. Quando atingir limite: deixe o automático agir (ele caça uma rota que aceite o modelo e troca de modelo se a cota acabou). Use [ ROTACIONAR IP ] apenas para blocos regionais.
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
1. Abra o aplicativo Cloudflare WARP e deixe-o conectado
2. No CodeOpen, selecione [ ROTACIONAR IP ]
3. Aguarde 3-5 segundos
4. Tente rotacionar novamente

---

### ❌ Problema: o desbloqueio automático não acontece
**Causa:** o monitor só considera linhas `level=ERROR` **novas**, com timestamp
posterior ao início do monitoramento. Além disso, a cota gratuita do
OpenCode é por modelo e muda com a rota: o launcher precisa caçar uma rota
que aceite o **modelo da conversa** (probe com `pong`) e só troca de modelo
se a caçada esgotar.

**Solução:**
1. Confirme que o WARP está ligado e que o OpenCode foi aberto pelo CodeOpen
2. Veja o log do CodeOpen em `~/.opencode-infinity-simple/logs/` (arquivo do dia)
3. Procure por `Caçando uma rota que aceite`, `Nova rota`, `Conversa retomada
   com o modelo` e `Nenhuma rota aceitou esse modelo; tentando outro modelo
   livre`. Se aparecer `Nenhuma rota nem modelo livre aceitou`, aguarde o
   tempo indicado (≈ 3h) ou configure `model_candidates` com um
   provider/modelo pago no `config.json`
4. Se aparecer "desbloqueios seguidos sem resolver", use [ NOVA CONVERSA ]
   (IP novo + sessão nova) ou [ ROTACIONAR IP ] manualmente; qualquer ação
   manual libera o automático. Para mudar o limite, ajuste `limit_rot_max`
   no `config.json` (`0` desliga)
5. Rate limit puro (HTTP 429) **não** rotaciona sozinho por padrão; use
   [ ROTACIONAR IP ] se quiser trocar a rota

---

## 📂 ARQUIVOS E PASTAS

### Onde ficam os arquivos:

**Logs do programa:**
```
C:\Users\berg\.opencode-infinity-simple\logs\AAAAMMDD.log
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
# - Deixe o automático agir (ele caça rota/modelo e reabre a conversa)
# - Se o automático pausar, use [ NOVA CONVERSA ] ou [ ROTACIONAR IP ]
# - Continue trabalhando!
```

---

## 💡 DICAS IMPORTANTES

✅ **Use Windows Terminal** para melhor experiência visual

✅ **Modo Automático** é o padrão do [ INICIAR OPENCODE ]: ideal para sessões longas

✅ **Modo Manual** dá mais controle: use [ ROTACIONAR IP ] quando quiser

✅ **Sempre conecte ao WARP primeiro** antes de usar outras funções

✅ **Logs são salvos automaticamente** em `~/.opencode-infinity-simple/logs/`

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
   explorer "$HOME\.opencode-infinity-simple\logs"
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

Os logs salvos em `~/.opencode-infinity-simple/logs/` mostram:

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
