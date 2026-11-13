# QuickStart - CodeOpenFreedom
*Oficina do Berg*

## Instalação Rápida

### Automática (Recomendado)
```cmd
INSTALAR.bat
```

### Manual
```cmd
pip install -r requirements.txt
```

---

## Passo Fundamental: Cloudflare WARP

1. Baixe e instale o cliente oficial: https://1.1.1.1/
2. **OBRIGATÓRIO:** Abra o aplicativo do Cloudflare WARP e **ligue-o (deixe conectado)** antes de executar o script.
3. Não precisa configurar portas ou proxy manualmente; o CodeOpenFreedom cuida do roteamento na porta local 40000 de forma automática.

---

## Como Iniciar

Abra o Cloudflare WARP, certifique-se de que está conectado e execute:

```cmd
INICIAR.bat
```
*(Ou execute diretamente: `python main.py`)*

---

## Controles de Navegação

* **W / S** ou **↑ / ↓**: Navegar pelas opções
* **ENTER**: Selecionar opção
* **ESC**: Sair

---

## Fluxo de Operação

1. Selecione **[ INICIAR OPENCODE ]**
2. O CodeOpenFreedom irá:
   * Estabelecer o proxy local via WARP na porta 40000
   * Iniciar o OpenCode CLI roteado pelo túnel seguro
   * Monitorar streams de requisições e status HTTP 429
   * Rotacionar o IP automaticamente quando atingir o limite
