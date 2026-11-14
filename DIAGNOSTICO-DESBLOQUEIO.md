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

O limite gratuito do OpenCode **não é por IP**: é por **modelo**. Cada modelo
`*-free` do provider `opencode` tem a sua própria cota (janela de algumas
horas, com `retryAfterMs` na resposta 429). Girar o registro do WARP troca o
IP, mas não devolve a cota do modelo que a conversa usa.

O `core/opencode.py` fazia o probe **sem `-m`**. Sem modelo explícito, o
OpenCode escolhe o modelo padrão (`iceman-free` no ambiente testado), que
ainda tinha cota. O probe então respondia `ok` e o launcher acreditava na
rota nova. A retomada, porém, usa o modelo fixado na sessão
(`deepseek-v4.1-flash-free`), que estava esgotado — daí o 429 imediato.

Ou seja: o probe testava um modelo, a retomada usava outro, e o IP não tinha
nada a ver com o problema. Além disso, o probe aceitava qualquer retorno `0`
como rota boa, mesmo quando o modelo não respondia à pergunta pedida.

### Evidência (14/11, OpenCode 2.2.7)

Testes controlados, todos com o proxy WARP novo e válido (`warp=on`):

| Teste | Modelo | Resultado |
|---|---|---|
| sessão nova, sem `-m` | `opencode/iceman-free` (padrão) | rc=0, resposta "ok" |
| sessão nova, `-m` explícito | `opencode/deepseek-v4.1-flash-free` | 429 `FreeUsageLimitError` |
| sessão nova, `-m` explícito | `opencode/glm-5.3-flash-free` | 429 `FreeUsageLimitError` |
| sessão existente, `-s` | `deepseek-v4.1-flash-free` | 429 `FreeUsageLimitError` |
| sessão existente, `-s` + `-m` | `opencode/iceman-free` | rc=0, conversa retomada |

O 429 traz `"retryAfterMs"` (≈ 3h no dia do teste). O mesmo IP aceitava um
modelo com cota e recusava outro esgotado; um IP novo recusava o modelo
esgotado do mesmo jeito.

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
  (`-s <id>`), com `-m <modelo>` explícito. Um `-m` novo troca o modelo
  fixado na conversa; é isso que desbloqueia.
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
8. reabre o TUI com `--continue` e volta a monitorar.

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
  "probe_timeout": 60
}
```

`model_candidates` aceita modelos extras (por exemplo, de um provider pago)
para serem testados no fallback antes dos gratuitos.

## Testes

- `python test_orquestrador.py` → **10/10 cenários**.
  Inclui: rota nova aceita o modelo, rota limitada (gira de novo), retomada
  limitada, sem conversa, caçada esgotada, fallback de modelo, probe
  quebrado, anti-loop, retomada com retorno não-padrão e concorrência.
- `python test_fluxo.py` → **9/9 grupos** (regressão do monitor, comandos,
  probe com `pong`, evento estruturado de limite e timeout por inatividade).
- `python test_correcao.py`, `test_reset.py`, `test_sistema.py` → OK.

Validação real com o OpenCode 2.2.7 e WARP ligado:

```text
opencode/deepseek-v4.1-flash-free -> burned (retryAfterMs ≈ 3h)
opencode/iceman-free              -> ok (pong)
sessão retomada com -s ses_... -m opencode/iceman-free -> rc=0
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
5. Se todos os modelos livres estiverem esgotados, o log informa em quantas
   horas a próxima cota volta. Nesse caso, nem IP novo resolve.
