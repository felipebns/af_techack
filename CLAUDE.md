# CLAUDE.md — contexto para o Claude na máquina-alvo

Este arquivo é um handoff. Ele descreve o que já foi construído e o que falta fazer,
para que você (Claude Code rodando na máquina de laboratório) continue o trabalho.

## Contexto

Avaliação Final de Tecnologias Hackers (Insper). O objetivo é um **agente
supervisionado** no qual um LLM **local** (Ollama) participa de testes de segurança
contra uma instância **local** do OWASP Juice Shop. O modelo propõe ações usando
ferramentas; um humano **autoriza, modifica ou rejeita** cada uma antes de executar.

O foco da avaliação **não** é achar muitas vulnerabilidades, e sim analisar onde a IA
ajudou, onde falhou e quando a intervenção humana foi necessária. Uma hipótese
refutada com evidência é um resultado válido.

Todo o trabalho foi desenvolvido numa máquina diferente (sem o ambiente de lab). Aqui
é onde o ambiente será de fato montado e rodado.

## O que já está pronto (não precisa refazer)

O código do agente está completo e testado em nível de lógica (escopo, validação,
loop de supervisão com LLM e ferramentas simulados). Estrutura:

| Arquivo | Papel |
|---|---|
| `agent/main.py` | Loop de investigação + supervisão no terminal (`[a]provar/[m]odificar/[r]ejeitar/[q]`) |
| `agent/llm.py` | Cliente Ollama (`POST /api/chat` com tool-calling) |
| `agent/tools.py` | Ferramentas `http_request` (fala com o Juice Shop) e `nmap_scan`; escopo travado no alvo local |
| `agent/logger.py` | Registro das execuções em JSONL (`logs/session-<data>.jsonl`) |
| `agent/config.py` | Carrega `config.yaml` |
| `config.yaml` | Parâmetros ajustáveis: URL do alvo, host/modelo do Ollama |
| `docker-compose.yml` | Juice Shop local + restauração via `docker compose restart` |
| `README.md` | Instruções de uso e arquitetura |

Garantias já embutidas no código:
- O agente só age contra `target.base_url` do `config.yaml`; outros hosts são bloqueados (`_assert_in_scope`).
- Não há shell arbitrário: só as duas ferramentas, com parâmetros validados (ex.: portas do nmap só aceitam dígitos/vírgula/hífen).
- Toda ação passa por autorização humana.
- A próxima ação depende do histórico acumulado (não é sequência fixa).

## Próximos passos na máquina (o que falta)

### 1. Montar o ambiente
```bash
# Juice Shop
docker compose up -d                 # confirme em http://localhost:3000

# LLM local
ollama serve                         # se não estiver rodando
ollama pull qwen3:4b                 # ou outro modelo quantizado

# Dependências do agente
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# nmap (para a ferramenta de recon)
sudo apt install -y nmap
```
Ajuste `config.yaml` se os endereços/modelo forem diferentes.

### 2. Validar o tool-calling com o modelo REAL
Este é o ponto de maior risco. Modelos pequenos (Qwen3 4B) às vezes:
- devolvem `arguments` como string JSON em vez de objeto (o código já tolera isso em `main.py`);
- erram o nome da ferramenta ou os campos;
- não emitem `tool_calls` e descrevem a ação em texto.

Rode um teste real e observe `logs/`:
```bash
python -m agent.main "Enumerar a superfície da API REST do Juice Shop"
```
Se o modelo não chamar ferramentas corretamente, ajuste o `SYSTEM_PROMPT` em
`agent/main.py` (seja mais explícito sobre usar as ferramentas). **Não** troque a
arquitetura — documentar essa limitação é material valioso para a análise crítica.

### 3. Rodar as três investigações
Cenários distintos sugeridos pelo enunciado:
1. Reconhecimento/enumeração da aplicação.
2. Mecanismos de autenticação ou autorização.
3. Tratamento de entradas, requisições ou acesso a recursos.

Para cada uma, use `docker compose restart juice-shop` antes, para partir de estado
conhecido. Os registros em `logs/` são a evidência (entregável 3).

### 4. Produzir os entregáveis restantes (fora do código)
- **Relatório técnico (4–6 págs):** arquitetura do lab, estratégia, resultados das 3
  investigações e análise crítica da IA. Priorizar interpretação e evidências.
- **Vídeo (≤10 min):** demonstrar o agente + uma investigação completa (hipótese → conclusão).

> Importante: o repositório deve conter **apenas** documentação sobre o funcionamento
> do projeto (README, arquitetura, este handoff). Relatório e anotações de
> planejamento não vão versionados aqui.

## Regras de higiene do repositório
- Não commite: `.venv/`, `.env`, `logs/`, `__pycache__/`, nem o PDF da avaliação (já no `.gitignore`).
- `config.yaml` é versionado e só deve conter endereços locais e nome do modelo — nada sensível.
- Branch de trabalho: `feat/agente-supervisionado`.

## Possíveis extensões (só se o grupo pedir)
- Uma terceira ferramenta (ex.: fuzzer simples de rotas) — opcional; o mínimo do enunciado são duas.
- Mantenha qualquer ferramenta nova com o mesmo padrão de escopo travado e parâmetros validados de `tools.py`.
