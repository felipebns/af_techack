# Agente Supervisionado de Testes de Segurança — Juice Shop + LLM local

Avaliação Final de Tecnologias Hackers. Um agente de linha de comando no qual um
modelo de linguagem **local** (Ollama) participa de testes de segurança contra uma
instância **local** do OWASP Juice Shop: o modelo propõe ações usando ferramentas de
segurança, e o grupo **autoriza, modifica ou rejeita** cada uma delas antes da execução.

Todas as ações ficam restritas ao alvo local configurado — o agente não tem acesso
livre ao shell nem autorização para agir contra outros hosts.

## Arquitetura

```
  objetivo ──▶ [ LLM local / Ollama ] ──▶ propõe ferramenta + parâmetros
                     ▲                              │
                     │                              ▼
              resultado da              [ supervisão humana no terminal ]
               ferramenta                 autoriza / modifica / rejeita
                     │                              │
                     └──────── [ ferramentas ] ◀────┘
                               http_request · nmap_scan
                                (escopo travado no alvo local)
```

Cada rodada devolve o histórico inteiro ao modelo, então a próxima ação depende das
evidências já obtidas — não é uma sequência fixa de comandos.

### Componentes

| Arquivo              | Papel |
|----------------------|-------|
| `agent/main.py`      | Loop de investigação + supervisão humana (terminal) |
| `agent/llm.py`       | Cliente do Ollama (`/api/chat` com tool-calling) |
| `agent/tools.py`     | Ferramentas: `http_request` (fala com o Juice Shop) e `nmap_scan` |
| `agent/logger.py`    | Registro das execuções em JSONL |
| `agent/config.py`    | Carrega `config.yaml` |
| `config.yaml`        | **O que você ajusta na máquina real** (URL do alvo, host/modelo do Ollama) |
| `docker-compose.yml` | Juice Shop local |
| `docs/planejamento.md` | Template para o planejamento e o relatório das investigações |

## Pré-requisitos

- Docker (para o Juice Shop)
- Python 3.10+
- [Ollama](https://ollama.com) com um modelo baixado (ex.: `qwen3:4b`)
- `nmap` (`sudo apt install nmap`) — opcional, só para a ferramenta de recon

> Funciona em Ubuntu ou Kali; não depende de nada específico do Kali.

## Passo a passo

### 1. Subir o alvo (Juice Shop)

```bash
docker compose up -d
# acesse http://localhost:3000 para confirmar
```

Restaurar a um estado conhecido entre experimentos:

```bash
docker compose restart juice-shop
```

### 2. Subir o modelo local

```bash
ollama serve            # se ainda não estiver rodando
ollama pull qwen3:4b    # baixa o modelo quantizado
```

### 3. Instalar as dependências do agente

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Ajustar a configuração

Edite `config.yaml` se necessário (URL do Juice Shop, host/modelo do Ollama).

### 5. Rodar o agente

```bash
python -m agent.main "Enumerar a superfície da API REST do Juice Shop"
```

A cada ação proposta, o terminal pergunta:

```
[a]provar  [m]odificar  [r]ejeitar  [q]encerrar
```

- **a** — executa a ação como proposta.
- **m** — abre os parâmetros no `$EDITOR` para você ajustar antes de executar.
- **r** — você informa um motivo; a rejeição volta ao modelo, que deve propor outra abordagem.
- **q** — encerra a sessão.

Quando o modelo considera a investigação concluída, ele responde só com texto
(sem ação); você pode encerrar ou dar uma nova orientação para continuar.

## Registros

Cada sessão gera `logs/session-<data>.jsonl`, com um evento por linha:
ação proposta, ferramenta e parâmetros, decisão do grupo, resultado e interpretação
do modelo. Isso permite reconstruir e verificar a investigação (entregável 3).

## Escopo e segurança

- O agente só age contra o host configurado em `config.yaml` (`target.base_url`);
  requisições e scans para qualquer outro host são bloqueados.
- Não há execução arbitrária de shell: apenas as duas ferramentas, com parâmetros validados.
- Toda ação passa por autorização humana antes de executar.
