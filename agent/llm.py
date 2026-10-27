"""Cliente mínimo para o Ollama usando a API /api/chat com tool-calling.

Mantido simples de propósito: uma única função `chat` que envia o histórico
de mensagens e as ferramentas disponíveis, e devolve a mensagem do modelo
(texto e/ou chamadas de ferramenta). Assim o grupo consegue explicar
exatamente como a integração funciona.
"""
from __future__ import annotations

import requests

from .config import Config


class LLMError(Exception):
    pass


def chat(cfg: Config, messages: list[dict], tools: list[dict]) -> dict:
    """Envia uma rodada de chat ao Ollama e devolve a mensagem do assistente.

    Retorno: dict no formato do Ollama, ex.:
      {"role": "assistant", "content": "...", "tool_calls": [...]}
    """
    url = cfg.ollama.host.rstrip("/") + "/api/chat"
    payload = {
        "model": cfg.ollama.model,
        "messages": messages,
        "tools": tools,
        "stream": False,
        "think": cfg.ollama.think,
        "options": {"temperature": 0.4},
    }

    try:
        resp = requests.post(url, json=payload, timeout=300)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise LLMError(
            f"Falha ao falar com o Ollama em {url}: {exc}\n"
            "Verifique se o Ollama está rodando e se o modelo foi baixado "
            f"(ollama pull {cfg.ollama.model})."
        ) from exc

    data = resp.json()
    message = data.get("message")
    if not message:
        raise LLMError(f"Resposta inesperada do Ollama: {data}")
    return message
