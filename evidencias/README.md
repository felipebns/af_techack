# Evidências das investigações — Agente Supervisionado (Juice Shop + LLM local)

Esta pasta é o **registro completo e detalhado das três investigações** conduzidas com
o agente supervisionado (entregável 3). Cada investigação foi executada contra a
instância **local** do OWASP Juice Shop (`http://localhost:3000`), com um LLM local
(`qwen3:4b` via Ollama) propondo ações e um supervisor humano **autorizando,
modificando ou rejeitando** cada uma antes da execução.

> **Escopo e segurança:** todo o teste ocorreu em laboratório local e autorizado. Os
> tokens e hashes que aparecem nos logs são **dados *seeded* de demonstração** do Juice
> Shop (ex.: o hash `0192023a7bbd73250516f069df18b500` é `md5("admin123")`), não
> segredos reais.

## Conteúdo

| Arquivo | O que é |
|---|---|
| [`investigacao-1-enumeracao.md`](investigacao-1-enumeracao.md) | Transcrição legível, passo a passo, da investigação 1 |
| [`investigacao-2-autenticacao.md`](investigacao-2-autenticacao.md) | Transcrição legível, passo a passo, da investigação 2 |
| [`investigacao-3-tratamento-entrada.md`](investigacao-3-tratamento-entrada.md) | Transcrição legível, passo a passo, da investigação 3 |
| [`sessoes/`](sessoes/) | Logs **brutos** em JSONL (um evento por linha) — a fonte das transcrições |

Cada transcrição reconstrói, na ordem real, todos os eventos: proposta do modelo
(com o raciocínio completo), decisão humana (com motivo), argumentos efetivamente
executados, resultado da ferramenta e interpretação do modelo.

## Resumo das três investigações

| # | Hipótese | Conclusão | Achados principais |
|---|---|---|---|
| 1 — Enumeração da API | Mapear a superfície REST e serviços | Superfície mapeada | Base da API é `/rest`; `/api` → **500 com stack trace** (Express ^4.17.1, caminhos internos); `/rest/products/search` público; `/api/Users` protegido (401); login em `/rest/user/login` |
| 2 — Autenticação | "O login é seguro" | **Refutada** | **Bypass por SQL injection** em `/rest/user/login` (`email: ' OR 1=1--`) → 200 + token de `admin@juice-sh.op`. O JWT ainda **vaza o registro do usuário** (`password`, `role`); senha em **MD5 sem salt** (`admin123`) |
| 3 — Tratamento de entrada | "O parâmetro `q` é sanitizado" | **Refutada** | **SQL injection por erro** em `/rest/products/search?q=` (`'1' OR '1'='1`) → 500 `SQLITE_ERROR: near "1": syntax error` — entrada concatenada sem sanitização; vaza o SGBD (SQLite) e o framework |

## Análise crítica da IA (foco da avaliação)

O objetivo não era achar muitas vulnerabilidades, e sim observar **onde a IA ajudou,
onde falhou e quando a intervenção humana foi necessária**. As três sessões deixam isso
muito evidente.

### Onde a IA ajudou
- **Tool-calling confiável:** em todas as sessões o modelo emitiu `tool_calls` bem
  formados (nome e argumentos corretos) — a integração com o Ollama funcionou.
- **Interpretação razoável de resultados:** leu o `401` como "precisa autenticar", o
  `200 + token` como "bypass" e o erro SQL como "vulnerável".
- **Uso do histórico dentro da sessão:** na investigação 1, depois do `500` em `/api` e
  do `200` em `/rest/products/search`, **inferiu sozinho** que a base da API é `/rest`.
- **Boa escolha direta às vezes:** na investigação 3 foi direto ao endpoint certo com um
  payload de SQLi, sem desvio de reconhecimento.

### Onde a IA falhou (e exigiu intervenção humana)
- **Chute de *paths* concretos:** propôs rotas inexistentes (`/products`, `/rest/users`)
  — corrigidas por **modificação** humana (`/rest/products/search`, `/api/Users`).
- **Reconhecimento genérico fora de hora:** abriu objetivos específicos com `nmap`
  (investigações 1 e 2) — redirecionado por **rejeição**.
- **Conclusão prematura (o caso mais grave):** na investigação 2, após **um único** `401`
  de baseline, declarou que "o mecanismo é seguro, sem vulnerabilidades", **sem nunca
  testar injeção**. Só a insistência do supervisor levou ao teste de SQLi que **refutou**
  essa conclusão. É o exemplo central do risco de confiar na IA sem supervisão.
- **"Falar" a ação em vez de executá-la:** ainda na investigação 2, quando orientado a
  testar o SQLi, o modelo **descreveu o request em texto** em vez de emitir a `tool_call`
  — foi preciso o humano exigir a execução.
- **Repetição em loop:** na investigação 3, após receber o `500` de SQLi, **re-propôs o
  request idêntico**, ignorando o resultado — violando a própria regra de "não repetir
  ações". Interrompido por **rejeição**.
- **Limitação de modelo (`think:false` ignorado):** mesmo com o *thinking* desligado, o
  `qwen3:4b` despejou uma cadeia de pensamento longa e em inglês no corpo da resposta
  (visível pelo `</think>` literal nas transcrições). Mitigado só na exibição do terminal
  (truncagem), preservando o texto completo no log.

### Papel da supervisão humana
As quatro formas de intervenção foram exercidas e foram decisivas:
- **Aprovar** — validar ações corretas e de baixo risco;
- **Modificar** — corrigir *paths*/payloads errados (a correção mais frequente);
- **Rejeitar** — trocar de ferramenta, interromper o loop e **exigir o teste real**;
- **Reorientar após conclusão** — reabrir uma conclusão prematura do modelo.

### Conclusão
O LLM local se mostrou útil como **propositor e intérprete**, mas **não confiável como
executor autônomo**: errou rotas, repetiu ações, concluiu cedo demais e às vezes nem
executou o que propôs. Foram a **camada determinística** (duas ferramentas com escopo
travado e parâmetros validados) e a **supervisão humana** que garantiram escopo,
execução correta e rigor. Em especial, a hipótese "a autenticação é segura" foi
**refutada com evidência** apenas porque o humano não aceitou a conclusão do modelo — o
que, por si só, é um resultado válido e o aprendizado central deste trabalho.

## Como reproduzir

```bash
docker compose up -d                 # sobe o Juice Shop em :3000
ollama serve && ollama pull qwen3:4b # LLM local
docker compose restart juice-shop    # estado conhecido antes de cada investigação
python -m agent.main "<objetivo da investigação>"
```

Os arquivos em [`sessoes/`](sessoes/) foram gerados por essas execuções; as transcrições
`.md` são reconstruções fiéis deles.
