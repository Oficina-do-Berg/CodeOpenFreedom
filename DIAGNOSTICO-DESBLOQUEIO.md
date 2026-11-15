# Diagnóstico: por que o desbloqueio automático não acontecia

## Sintoma

O launcher detectava o limite no log, rotacionava o WARP com sucesso e ainda
assim a conversa voltava com `Free usage limit reached` até esgotar as
tentativas. O log mostrava sempre a mesma sequência:

```text
🚨 Limite de uso confirmado no log.
2️⃣ Tentativa 1/3: rotacionando o WARP...
✅ IP rotacionado com sucesso: ... → ...
🧪 Testando a rota nova com uma chamada de modelo...
💬 Retomando a conversa: run -c "continue"
⚠️ A conversa ainda bateu no limite; rotacionando de novo...
```

## Causa raiz (comprovada)

Havia três erros encadeados, e o principal não era a rotação em si:

1. **O probe testava um modelo diferente do modelo da conversa.** O
   `core/opencode.py` chamava o probe **sem `-m`**. Sem modelo explícito, o
   OpenCode usa o modelo padrão (`iceman-free` no ambiente testado), que
   ainda tinha cota. O probe respondia `ok` e o launcher acreditava na rota
   nova, mas a retomada usava o modelo fixado na sessão
   (`deepseek-v4.1-flash-free`), que estava esgotado — 429 imediato.
2. **O probe aceitava qualquer retorno `0`.** Um run que terminava sem a
   resposta pedida era contado como rota boa; o main exige a resposta
   exata `pong`.
3. **A caçada desistia cedo (3 tentativas).** O limite gratuito é por
   modelo **e varia por rota/IP**: o mesmo modelo esgotado em uma rota pode
   ser aceito em outra. No teste real, o `deepseek` recusou em 6 rotas
   seguidas e passou na 8ª. Com 3 tentativas, o launcher parava antes de
   achar a rota boa.

O `main` acerta porque faz o probe com o **mesmo modelo da conversa**, só
aprova quando ele responde `pong` e repete a caçada até `hunt_max` (10 no
desktop, 20 no `.bat`). Trocar de modelo é o plano B, não o plano A.

### Evidência (14/11, OpenCode 2.2.7)

Testes controlados com o proxy WARP válido (`warp=on`):

| Teste | Modelo | Resultado |
|---|---|---|
| sessão nova, sem `-m` | `opencode/iceman-free` (padrão) | rc=0, resposta "ok" |
| sessão nova, `-m` explícito | `opencode/deepseek-v4.1-flash-free` | 429 `FreeUsageLimitError` |
| sessão nova, `-m` explícito | `opencode/glm-5.3-flash-free` | 429 `FreeUsageLimitError` |
| sessão existente, `-s` | `deepseek-v4.1-flash-free` | 429 `FreeUsageLimitError` |
| sessão existente, `-s` + `-m` | `opencode/iceman-free` | rc=0, conversa retomada |
| caçada, IPs 1–6 | `deepseek-v4.1-flash-free` | 429 em todas |
| caçada, IP 8 | `deepseek-v4.1-flash-free` | rc=0, retomada concluída |

As cinco primeiras linhas mostram que a cota é **por modelo** na mesma
rota. As duas últimas mostram que ela também **muda com a rota**: o mesmo
modelo voltou a responder em outro IP. Por isso o fluxo do main é caçar
rota com o modelo da conversa, e só depois considerar trocar de modelo. O
429 traz `"retryAfterMs"` (≈ 3h no dia do teste).

O log do OpenCode confirma que o probe criava uma sessão nova e que a
retomada escrevia no `ses_...` da conversa, com o modelo antigo.

## O que o main fazia diferente

O `OpenCode Infinite.bat` original usa o modelo da conversa nas duas pontas:

- `PROBE_MODEL`/`OC_MODEL` fazem o probe e a retomada usarem o mesmo modelo;
- o probe só aprova a rota quando o modelo responde exatamente `pong`;
- a caçada gira o IP até `hunt_max` vezes (10 no desktop, 20 no `.bat`)
  testando esse modelo;
- se a caçada esgota, o `.bat` troca de modelo
  (`LIMIT_ACTION=provider` + `LIMIT_MODEL`) antes de desistir.

Sem os campos de modelo, o main também depende do modelo padrão e sofre do
mesmo 429 quando a cota do modelo da conversa acabou.

## Correções aplicadas

### `core/opencode.py`

- `latest_session(cwd)`: lê `session_v2` no banco local e devolve a sessão
  mais recente da pasta, o modelo real (`provider/modelo`) e o diretório.
  É esse modelo que precisa ser testado nas duas pontas.
- `list_free_models()`: lista os modelos `opencode/*-free` via
  `opencode models`.
- `model_last_used()`: última utilização de cada modelo, para o fallback
  tentar primeiro os menos usados (maior chance de cota livre).
- `retry_after_ms(text)`: extrai o `retryAfterMs` do erro 429.
- `probe(..., model=...)`: o probe recebe o modelo da conversa (`-m`) e só
  aprova a rota quando a resposta contém `pong`. `rc=0` sem `pong` vira
  `broken`; 429/limite vira `burned`; timeout continua `timeout`.
- `resume(..., model=..., session_id=...)`: retoma a **mesma sessão**
  (`-s <id>`), com `-m <modelo>` explícito.
- `set_session_model(session_id, 'provider/modelo')`: grava o modelo novo na
  coluna `model` da sessão. Em campo o `-m` do `run` valeu só para aquele
  turno: o TUI reaberto com `--continue` voltava ao modelo antigo e limitava
  de novo em segundos. Fixar na sessão é o equivalente ao `OC_MODEL`
  persistente do `.bat`.
- `start(..., session_id=...)`: reabre o TUI com `--session <id>`, fixado na
  conversa certa, em vez de `--continue` (que pega a mais recente).
- A classificação de probe e retomada usa o **evento estruturado** do
  `run --format json` (`{"type":"error","error":{...}}`), não o texto solto.
  A própria conversa pode citar "usage limit" ou "session not found" sem
  falha; só `provider.free-limit`/`FreeUsageLimitError` viram `limit` e só
  um retorno diferente de zero é lido em busca de erro no `stderr`.
- Timeouts iguais aos do main: retomada com 600 s de teto e 60 s de
  inatividade (`RESUME_IDLE`), probe com 60 s. Uma retomada longa continua
  viva enquanto escreve; travada sem saída, é encerrada com `rc=124`.
- Configs antigos (`resume_timeout=180`, `probe_timeout=120`) são migrados
  automaticamente para os padrões do main ao carregar.

### `core/orchestrator.py`

Fluxo (o mesmo do main, com fallback de modelo):

1. detecta o limite no log;
2. identifica a conversa e o modelo que ela usa;
3. para o TUI (e o serviço de background, se existir);
4. caça uma rota que aceite esse modelo: gira o IP até `hunt_max` vezes,
   reinicia o serviço e faz o probe com `-m <modelo>`;
5. probe quebrado `probe_broken_max` vezes seguidas desliga o probe e segue
   só com a retomada (equivalente ao `PROBE=0` do `.bat`);
6. quando o probe passa, retoma a mesma conversa com `-s <id> -m <modelo>`;
7. se a caçada esgota, troca para outro modelo livre na rota atual
   (`model_switch_fallback`, equivalente ao `LIMIT_ACTION=provider`);
8. fixa o modelo aprovado na conversa (`set_session_model`) e reabre o TUI
   com `--session <id>`, voltando a monitorar.

O anti-loop segue o `LIMIT_ROT_MAX` do `.bat`: `limit_rot_max` (3) conta
desbloqueios **seguidos** que não resolveram; sucesso zera, e qualquer ação
manual (nova conversa, rotacionar IP, iniciar) também libera. A opção
[ NOVA CONVERSA ] gira o IP e abre uma sessão nova, como a opção 1 do main.

O modelo que passou no probe fica salvo em `last_good_model` no
`~/.opencode-infinity-simple/config.json` e é testado primeiro na próxima
vez.

### `core/config.py`

Novas opções:

```json
{
  "hunt_max": 10,
  "probe_broken_max": 2,
  "max_model_switches": 5,
  "model_candidates": [],
  "last_good_model": "",
  "model_switch_fallback": true,
  "resume_timeout": 600,
  "resume_idle": 60,
  "probe_timeout": 60,
  "limit_rot_max": 3
}
```

`model_candidates` aceita modelos extras (por exemplo, de um provider pago)
para serem testados no fallback antes dos gratuitos.

## Testes

- `python test_orquestrador.py` → **11/11 cenários**.
  Inclui: rota nova aceita o modelo, rota limitada (gira de novo), retomada
  limitada, sem conversa, caçada esgotada, fallback de modelo, probe
  quebrado, anti-loop por streak, retomada com retorno não-padrão,
  concorrência e NOVA CONVERSA.
- `python test_fluxo.py` → **9/9 grupos** (regressão do monitor, comandos,
  probe com `pong`, evento estruturado de limite, texto da resposta que
  cita "usage limit", timeout por inatividade e reabertura do TUI).
- `python test_correcao.py`, `test_reset.py`, `test_sistema.py` → OK.

Validação real com o OpenCode 2.2.7 e WARP ligado:

```text
Alvo: ses_e248e918cffe0bXthCdB3U0uH7 | modelo: opencode/deepseek-v4.1-flash-free
Tentativa 1..6: rotacionou, probe = burned
Tentativa 7..8: rotação falhou (IP repetido) e continuou
Tentativa 9: rotacionou, probe = burned
Tentativa 10: rotacionou, probe = ok (pong)
💬 Retomando ... -m opencode/deepseek-v4.1-flash-free -s ses_...
✅ Conversa retomada; TUI reaberto; monitor religado
RESULTADO: desbloqueado | rotações: 8 | trocas de modelo: 0
```

## Como validar na prática

1. Deixe o Cloudflare WARP ligado e rode `INICIAR.bat`.
2. Use o chat até atingir o limite.
3. O log do simples deve mostrar, em ordem:
   - `Alvo: ses_... | modelo: opencode/...`
   - `2️⃣ Caçando uma rota que aceite opencode/... (até 10 rotações...)`
   - `Tentativa N/10: trocando o IP...`
   - `✅ Nova rota: ...`
   - `🧪 Testando a rota nova com uma chamada de modelo...`
   - `💬 Retomando ses_... com o modelo opencode/...`
   - `✅ Conversa retomada com o modelo opencode/...`
   - `✅ DESBLOQUEIO CONCLUÍDO`
4. Se nenhuma rota aceitar o modelo, aparece
   `Nenhuma rota aceitou esse modelo; tentando outro modelo livre`.
5. Se todos os modelos livres estiverem esgotados na rota atual e a caçada
   não achar rota, o log informa em quantas horas a próxima cota volta.
