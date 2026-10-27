"""Agente supervisionado de testes de segurança (linha de comando).

Fluxo (conforme o enunciado):
  1. O agente recebe um objetivo de investigação.
  2. O modelo analisa o contexto e seleciona uma ferramenta.
  3. O modelo propõe uma ação e seus parâmetros.
  4. O grupo autoriza, modifica ou rejeita a execução.
  5. Quando autorizada, a ferramenta é executada e o resultado volta ao modelo.
  6. O modelo interpreta o resultado e pode propor uma nova ação.

A próxima ação depende das informações obtidas (o histórico inteiro volta
ao modelo a cada rodada), e não de uma sequência fixa de comandos.

Uso:
    python -m agent.main "Objetivo da investigação"
    python -m agent.main            # pergunta o objetivo interativamente
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile

from . import llm, tools
from .config import load_config
from .logger import SessionLogger

SYSTEM_PROMPT = """\
Você é um assistente de testes de segurança OFENSIVOS trabalhando em um \
laboratório controlado, sob supervisão humana. O único alvo autorizado é uma \
instância LOCAL do OWASP Juice Shop em {target}. Você NÃO pode agir contra \
nenhum outro host.

Você dispõe de duas ferramentas: 'http_request' (para interagir diretamente \
com o Juice Shop) e 'nmap_scan' (para reconhecimento de portas/serviços do \
host do alvo).

Regras de trabalho:
- Proponha UMA ação por vez, chamando UMA ferramenta, precedida de um raciocínio \
curto (2 a 3 frases, em português) explicando por que aquela ação ajuda a \
investigar o objetivo.
- Baseie cada nova ação nas evidências já obtidas. Não repita ações que já \
deram resultado nem siga um roteiro fixo.
- Um supervisor humano pode autorizar, modificar ou rejeitar sua proposta. \
Se uma ação for rejeitada, proponha uma abordagem diferente.
- Quando considerar que a investigação chegou a uma conclusão (confirmando ou \
refutando a hipótese), responda apenas com TEXTO, sem chamar ferramenta, \
resumindo: o que as evidências permitem afirmar e quais limitações permanecem.

Objetivo da investigação:
{objective}
"""


# ---------------------------------------------------------------------------
# Utilidades de interação no terminal
# ---------------------------------------------------------------------------
def _edit_json(current: dict) -> dict:
    """Abre os parâmetros atuais em $EDITOR para o supervisor modificar."""
    editor = os.environ.get("EDITOR", "nano")
    with tempfile.NamedTemporaryFile(
        mode="w+", suffix=".json", delete=False, encoding="utf-8"
    ) as tmp:
        json.dump(current, tmp, ensure_ascii=False, indent=2)
        tmp_path = tmp.name
    try:
        subprocess.run([editor, tmp_path], check=False)
        with open(tmp_path, "r", encoding="utf-8") as fh:
            raw = fh.read()
    finally:
        os.unlink(tmp_path)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"  [!] JSON inválido ({exc}); mantendo os parâmetros originais.")
        return current


def _prompt_decision() -> str:
    while True:
        choice = input("  [a]provar  [m]odificar  [r]ejeitar  [q]encerrar > ").strip().lower()
        if choice in ("a", "m", "r", "q"):
            return choice
        print("  Opção inválida.")


def _print_proposal(tool_name: str, args: dict, reasoning: str) -> None:
    print("\n" + "=" * 70)
    if reasoning:
        # O modelo pode gerar um raciocínio longo; na tela mostramos um resumo.
        # O texto completo continua registrado no log JSONL.
        shown = reasoning if len(reasoning) <= 600 else reasoning[:600] + " […]"
        print(f"Raciocínio do modelo:\n  {shown}")
    print("-" * 70)
    print(f"Ação proposta: {tool_name}")
    print("Parâmetros:")
    for line in json.dumps(args, ensure_ascii=False, indent=2).splitlines():
        print(f"  {line}")
    print("=" * 70)


# ---------------------------------------------------------------------------
# Loop principal
# ---------------------------------------------------------------------------
def run(objective: str, config_path: str) -> None:
    cfg = load_config(config_path)
    specs = tools.tool_specs()
    log = SessionLogger(cfg.log_dir, objective)

    print(f"Alvo autorizado : {cfg.target.base_url}")
    print(f"Modelo (Ollama) : {cfg.ollama.model} @ {cfg.ollama.host}")
    print(f"Registro        : {log.path}")
    print(f"Objetivo        : {objective}\n")

    messages: list[dict] = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT.format(
                target=cfg.target.base_url, objective=objective
            ),
        }
    ]

    for _ in range(cfg.max_steps):
        try:
            message = llm.chat(cfg, messages, specs)
        except llm.LLMError as exc:
            print(f"\n[ERRO] {exc}")
            log.session_end(note=f"erro de LLM: {exc}")
            return

        messages.append(message)
        content = (message.get("content") or "").strip()
        tool_calls = message.get("tool_calls") or []

        # Texto do modelo (raciocínio ou conclusão).
        if content:
            log.model_message(content)

        # Sem chamada de ferramenta => o modelo apresentou uma conclusão/interpretação.
        if not tool_calls:
            print("\n" + "#" * 70)
            print("MODELO (sem ação proposta):")
            print(content or "(resposta vazia)")
            print("#" * 70)
            follow = input(
                "\nContinuar a investigação? Digite uma orientação/pergunta, "
                "ou Enter para encerrar: "
            ).strip()
            if not follow:
                log.session_end(note="encerrado pelo supervisor após conclusão do modelo")
                print("\nSessão encerrada.")
                return
            messages.append({"role": "user", "content": follow})
            continue

        # Processa cada ação proposta, uma de cada vez, sob supervisão.
        for call in tool_calls:
            fn = call.get("function", {})
            name = fn.get("name", "")
            args = fn.get("arguments", {}) or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {"_raw": args}

            log.proposal(name, args, content)
            _print_proposal(name, args, content)

            choice = _prompt_decision()

            if choice == "q":
                log.decision("rejected", name, args, reason="sessão encerrada pelo supervisor")
                log.session_end(note="encerrado manualmente")
                print("\nSessão encerrada.")
                return

            if choice == "r":
                reason = input("  Motivo da rejeição (volta ao modelo): ").strip()
                log.decision("rejected", name, args, reason=reason)
                messages.append(
                    {
                        "role": "tool",
                        "tool_name": name,
                        "content": (
                            "AÇÃO REJEITADA PELO SUPERVISOR. "
                            f"Motivo: {reason or '(não informado)'}. "
                            "Proponha uma abordagem diferente."
                        ),
                    }
                )
                continue

            if choice == "m":
                args = _edit_json(args)
                log.decision("modified", name, args)
                print("  Parâmetros atualizados.")
            else:  # 'a'
                log.decision("approved", name, args)

            # Executa a ferramenta autorizada.
            try:
                result = tools.execute_tool(name, args, cfg)
                log.tool_result(name, result, error=False)
            except tools.ToolError as exc:
                result = f"ERRO NA FERRAMENTA: {exc}"
                log.tool_result(name, result, error=True)

            print("\n--- Resultado ---")
            preview = result if len(result) <= 2000 else result[:2000] + "\n... [truncado na tela]"
            print(preview)
            print("--- fim do resultado ---")

            messages.append(
                {"role": "tool", "tool_name": name, "content": result}
            )

    print("\n[Limite de passos atingido.]")
    log.session_end(note="limite de passos atingido")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Agente supervisionado de testes de segurança (Juice Shop + LLM local)."
    )
    parser.add_argument("objective", nargs="?", help="Objetivo da investigação.")
    parser.add_argument("-c", "--config", default="config.yaml", help="Caminho do config.yaml.")
    args = parser.parse_args()

    objective = args.objective
    if not objective:
        objective = input("Objetivo da investigação: ").strip()
    if not objective:
        print("Nenhum objetivo informado.")
        sys.exit(1)

    try:
        run(objective, args.config)
    except KeyboardInterrupt:
        print("\n\nInterrompido.")


if __name__ == "__main__":
    main()
