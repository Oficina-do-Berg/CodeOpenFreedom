# Post para Divulgação no Reddit / Comunidades

> **Autor:** Berg (Oficina do Berg)  
> **Projeto:** CodeOpenFreedom  
> **Link:** https://github.com/Oficina-do-Berg/CodeOpenFreedom  

---

## Título Sugerido:
```text
Fiz uma ferramenta gratuita e open-source pra ajudar a comunidade com o novo limite de tempo do OpenCode CLI
```

---

## Conteúdo do Post (Pronto para Copiar e Colar):

Fala pessoal, tudo bem com vocês? Meu nome é Berg! 👋

Quem aqui usa o **OpenCode CLI** no dia a dia provavelmente sentiu o impacto da última atualização. Colocaram aquele limite de tempo que interrompe o código bem na hora em que a gente está mais produtivo, nos forçando a esperar horas ou a ter que assinar plano pago só pra conseguir terminar um trabalho.

Eu passei por essa mesma dor de cabeça e decidi criar uma solução: o **CodeOpenFreedom**. Fiz isso de desenvolvedor para desenvolvedor e tô disponibilizando 100% de graça pra somar com a nossa comunidade!

### O que o script faz por você:
De forma bem direta: ele **reseta o limite de tempo do OpenCode**. Quando a ferramenta trava por limite de requisições ou erro de tempo, o script renova sua rota e você consegue continuar programando normalmente, sem precisar ficar esperando o tempo de bloqueio passar.

### Como funciona (bem simples e leve):
* **Renovação rápida (~15 segundos):** Ele roda em segundo plano. Bateu o limite ou erro 429? Ele rotaciona seu IP via Cloudflare WARP (porta local 40000) e você volta a codar na hora.
* **Backup automático:** Se você precisar dar um reset geral, o script salva todas as suas conversas antigas automaticamente em uma pasta no seu Desktop. Seu histórico fica guardadinho com você.
* **Interface limpa:** Um menu simples no terminal que mostra tudo em tempo real.

### Como usar:
Basta ter o Python, o OpenCode CLI e o **Cloudflare WARP oficial** instalado no Windows (aquele gratuito do 1.1.1.1). A única coisa que você precisa fazer é **abrir o Cloudflare WARP e deixar ele ligado/conectado** antes de iniciar o script.

---

O código está todo aberto no GitHub pra quem quiser usar, estudar, sugerir melhorias ou contribuir com o projeto:  
👉 https://github.com/Oficina-do-Berg/CodeOpenFreedom

Espero de coração que essa ferramenta ajude vocês a manterem o ritmo de trabalho e os estudos sem interrupções. Se tiverem qualquer dúvida na instalação ou quiserem dar ideias, fiquem à vontade pra comentar aqui que eu respondo com o maior prazer!

Um grande abraço e bons códigos a todos! 🚀
