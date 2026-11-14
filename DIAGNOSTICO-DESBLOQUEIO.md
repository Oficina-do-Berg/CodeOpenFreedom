# Diagnóstico: por que o desbloqueio automático não acontecia

## Sintoma

O launcher do main detectava o limite e desbloqueava o OpenCode. O projeto
simples recebia o mesmo erro no log, mas registrava
`Erro de limite seguido de atividade normal; a sessão se recuperou sozinha`
e seguia em frente sem rotacionar o WARP.

## Causa raiz

`core/monitor.py`, no método `_decide`:

1. o monitor encontrava um `level=ERROR` com `Free usage limit reached`;
2. esperava `settle_seconds`;
3. relia o log e, se encontrasse **qualquer** linha `level=INFO` ou
   `level=DEBUG` depois do erro, cancelava a rotação.

O OpenCode continua escrevendo INFO depois de recusar a requisição: MCP
conectado, watcher, eventos, reconexão. O limite real era sempre cancelado
por uma linha de INFO escrita cerca de 1 segundo depois.

Evidência no log do simples (`~/.opencode-infinity-simple/logs/20261114.log`):

```text
2026-11-14 13:07:53 | INFO | core.monitor | Erro de limite seguido de atividade normal; a sessão se recuperou sozinha.
2026-11-14 13:08:19 | INFO | core.monitor | Erro de limite seguido de atividade normal; a sessão se recuperou sozinha.
```

Evidência no log real do OpenCode (`~/.local/share/opencode/log/opencode.log`):

```text
16:10:07.539 level=ERROR message="Failed to drain Session"
             cause="AI.Error: Free usage limit reached..."
16:10:08.754 level=INFO  message="mcp connected"
16:10:08.758 level=INFO  message=event ...
```

Com a regra antiga, o INFO de 1,2 s depois anulava o ERROR de cota.

## O que o main faz diferente

- No `OpenCode Infinite.bat`, `:scan_log` classifica cada linha na ordem
  `noop` → `rotate` → `ask` e para no primeiro `rotate`. Não existe a
  janela de "recuperação" por INFO. O watcher contínuo do `.bat` está
  desligado por padrão (`WATCH=0`); quem desbloqueia no dia a dia é o app
  desktop, que escuta o evento `provider.free-limit` e chama a rotação.
- O main guarda os PIDs que iniciou (`OC_PIDS`) e só mata esses. O simples
  procurava qualquer `opencode.exe` da máquina; em 14/11 chegou a parar o
  TUI do main (PID 9244) enquanto o TUI do simples era outro.
- O probe do main usa `--standalone --archived` e mantém a sessão de teste
  fora da lista. No `.bat`, saída `0` é rota boa; só uma execução que falhou
  lê o texto de limite.
- O main prefere o caminho de OpenCode que ele mesmo detectou. O simples
  pegava o primeiro `opencode` do `PATH`, que era o atalho
  `...\opencode-infinite\bin\opencode.CMD` criado pelo main.

## Correções aplicadas

### `core/monitor.py`

- Removida a recuperação por INFO/DEBUG. Um `rotate` confirmado sempre
  retorna `rotate`.
- `settle_seconds` continua apenas como debounce para o bloco de erro
  terminar de ser escrito.
- O log agora mostra a linha exata que disparou o desbloqueio.

### `core/opencode.py`

- `find_opencode` prefere o `.exe` real do npm
  (`%APPDATA%\npm\node_modules\@opencode\cli\bin\opencode.exe`) e ignora o
  atalho do launcher do main.
- `find_running_pid(only_dir=...)` e `stop()` só param o TUI do próprio
  launcher (PID registrado) ou um TUI na mesma pasta de trabalho. O deep
  reset usa `force_all=True` porque é uma ação destrutiva explícita.
- `start()` só recusa abrir se já existir um TUI na mesma pasta; o TUI de
  outro projeto não bloqueia mais.
- O probe usa `--archived` quando o CLI suporta, trata `returncode == 0`
  como rota boa antes de ler texto de limite e considera 429/rate limit
  como rota queimada.
- `supports_archived()` detecta o flag sem quebrar versões antigas.

### `core/orchestrator.py`

- `_run_unlock` para o monitor antes de girar o WARP, evitando um segundo
  gatilho durante probe/retomada.

### Documentação

- README (inglês, português e espanhol) e `GUIA-COMPLETO.md` atualizados
  para não falar mais em "sessão se recupera sozinha".

## Testes

- `python test_fluxo.py` → **8/8 grupos**. Inclui a regressão
  `ERROR de limite + INFO posterior → rotate`.
- `python test_orquestrador.py` → **6/6 cenários**.
- Bloco real do log de 14/11 reprocessado: agora retorna `rotate`.
- Verificação de processo: o TUI atual roda em
  `...\opencode-infinite-main`; `find_running_pid(only_dir=...simple)`
  retorna `None`, então o simples não para mais o TUI do main.

## Como validar na prática

1. Feche o launcher do main; os dois disputam o mesmo WARP e o mesmo log.
2. Deixe o Cloudflare WARP ligado e rode `INICIAR.bat`.
3. Use o chat até atingir o limite. O log do simples deve mostrar
   `Limite de uso confirmado no log`, seguido de rotação, probe, retomada
   e reabertura do TUI.

## Observações

- Rate limit puro (HTTP 429) continua sendo `ask` no monitor: não rotaciona
  sozinho por padrão. O probe trata 429 como rota ruim, igual ao desktop do
  main.
- O `~/.config/opencode/opencode.json` atual tem `provider` e `model` em
  formato inválido (`skipped malformed recognized value`). Isso não é a
  causa do desbloqueio, mas pode afetar o modelo usado no probe/retomada.
