"""Registro das execuções.

Cada passo relevante é gravado como uma linha JSON (JSONL), permitindo
reconstruir a investigação: ação proposta pelo agente, ferramenta e
parâmetros, decisão do grupo (autorizar/modificar/rejeitar), resultado
produzido e interpretação do modelo.

Os eventos são escritos imediatamente, para que nada se perca caso a
sessão seja interrompida.
"""
from __future__ import annotations

import json
import os
from datetime import datetime


class SessionLogger:
    def __init__(self, log_dir: str, objective: str):
        os.makedirs(log_dir, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.path = os.path.join(log_dir, f"session-{stamp}.jsonl")
        self.step = 0
        self._write(
            {
                "event": "session_start",
                "objective": objective,
            }
        )

    def _write(self, record: dict) -> None:
        record["timestamp"] = datetime.now().isoformat(timespec="seconds")
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    def model_message(self, content: str) -> None:
        """Texto livre do modelo (interpretação, raciocínio, conclusão)."""
        self._write({"event": "model_message", "content": content})

    def proposal(self, tool: str, arguments: dict, reasoning: str) -> None:
        self.step += 1
        self._write(
            {
                "event": "proposal",
                "step": self.step,
                "tool": tool,
                "arguments": arguments,
                "model_reasoning": reasoning,
            }
        )

    def decision(
        self,
        decision: str,
        tool: str,
        final_arguments: dict,
        reason: str = "",
    ) -> None:
        """decision: 'approved' | 'modified' | 'rejected'."""
        self._write(
            {
                "event": "decision",
                "step": self.step,
                "decision": decision,
                "tool": tool,
                "final_arguments": final_arguments,
                "reason": reason,
            }
        )

    def tool_result(self, tool: str, result: str, error: bool = False) -> None:
        self._write(
            {
                "event": "tool_result",
                "step": self.step,
                "tool": tool,
                "error": error,
                "result": result,
            }
        )

    def session_end(self, note: str = "") -> None:
        self._write({"event": "session_end", "note": note})
