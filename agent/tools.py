"""Ferramentas de segurança disponibilizadas ao agente.

Duas ferramentas, conforme o mínimo exigido pelo enunciado:

  - http_request: interage diretamente com o Juice Shop (o alvo).
  - nmap_scan:    reconhecimento de portas/serviços do host do alvo.

Ambas têm o escopo TRAVADO na instância local configurada em config.yaml.
O agente não consegue agir contra outros hosts, e não há acesso livre ao
shell do sistema operacional: só estas duas operações, com parâmetros
validados.
"""
from __future__ import annotations

import ipaddress
import shutil
import socket
import subprocess
from urllib.parse import urljoin, urlparse

import requests

from .config import Config


class ToolError(Exception):
    """Erro de validação/execução de uma ferramenta (fica no registro)."""


# ---------------------------------------------------------------------------
# Especificação das ferramentas no formato de tool-calling do Ollama.
# É isto que o modelo "enxerga" ao decidir qual ferramenta usar.
# ---------------------------------------------------------------------------
def tool_specs() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": "http_request",
                "description": (
                    "Faz uma requisição HTTP à instância local do OWASP Juice Shop "
                    "(o alvo dos testes). Use para explorar rotas, enviar payloads em "
                    "parâmetros ou corpo, inspecionar cabeçalhos e códigos de resposta, "
                    "testar autenticação/autorização e analisar o comportamento da API. "
                    "O caminho é relativo à base do alvo (ex.: '/rest/products/search?q=')."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "method": {
                            "type": "string",
                            "enum": ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
                            "description": "Método HTTP.",
                        },
                        "path": {
                            "type": "string",
                            "description": "Caminho relativo ao alvo, incluindo query string. Ex.: '/rest/user/login'.",
                        },
                        "headers": {
                            "type": "object",
                            "description": "Cabeçalhos HTTP adicionais (opcional).",
                        },
                        "body": {
                            "type": "string",
                            "description": "Corpo da requisição como texto. Para JSON, envie a string JSON.",
                        },
                        "json_body": {
                            "type": "object",
                            "description": "Corpo da requisição como objeto JSON (alternativa a 'body').",
                        },
                    },
                    "required": ["method", "path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "nmap_scan",
                "description": (
                    "Executa um scan Nmap contra o HOST do alvo local, para reconhecimento "
                    "de portas e serviços. O alvo é fixo (não é possível escanear outros hosts). "
                    "Use na etapa de reconhecimento para descobrir serviços expostos."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ports": {
                            "type": "string",
                            "description": "Portas a escanear (ex.: '3000', '1-1000', '80,443,3000'). Padrão: 3000.",
                        },
                        "scan_type": {
                            "type": "string",
                            "enum": ["service_version", "default_scripts", "quick"],
                            "description": (
                                "service_version = -sV (detecção de versão); "
                                "default_scripts = -sV -sC (scripts padrão); "
                                "quick = scan simples de portas."
                            ),
                        },
                    },
                    "required": [],
                },
            },
        },
    ]


# ---------------------------------------------------------------------------
# Executores
# ---------------------------------------------------------------------------
def _target_host(cfg: Config) -> str:
    return urlparse(cfg.target.base_url).hostname or "localhost"


def _assert_in_scope(host: str, cfg: Config) -> None:
    """Garante que o host resolvido é o mesmo do alvo configurado.

    Impede que o modelo (ou um payload) desvie as ações para serviços
    externos ou máquinas de outros grupos.
    """
    allowed = _target_host(cfg)
    if host != allowed:
        raise ToolError(
            f"Fora do escopo: '{host}' não corresponde ao alvo autorizado '{allowed}'. "
            "O agente só pode agir contra a instância local configurada."
        )


def run_http_request(args: dict, cfg: Config) -> str:
    method = str(args.get("method", "GET")).upper()
    path = args.get("path")
    if not path:
        raise ToolError("Parâmetro 'path' é obrigatório.")

    url = urljoin(cfg.target.base_url.rstrip("/") + "/", str(path).lstrip("/"))
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ToolError(f"Esquema não permitido: {parsed.scheme}")
    _assert_in_scope(parsed.hostname or "", cfg)

    headers = args.get("headers") or {}
    if not isinstance(headers, dict):
        raise ToolError("'headers' deve ser um objeto.")

    json_body = args.get("json_body")
    body = args.get("body")

    try:
        resp = requests.request(
            method=method,
            url=url,
            headers=headers,
            data=body if json_body is None else None,
            json=json_body if json_body is not None else None,
            timeout=30,
            allow_redirects=False,
        )
    except requests.RequestException as exc:
        raise ToolError(f"Falha na requisição: {exc}") from exc

    # Monta um resumo legível e truncado (para não estourar o contexto do LLM).
    header_lines = "\n".join(f"{k}: {v}" for k, v in resp.headers.items())
    text = resp.text
    truncated = ""
    if len(text) > 4000:
        truncated = f"\n... [corpo truncado, {len(text)} bytes no total]"
        text = text[:4000]

    return (
        f"HTTP {resp.status_code} {resp.reason} ({method} {url})\n"
        f"--- Cabeçalhos ---\n{header_lines}\n"
        f"--- Corpo ---\n{text}{truncated}"
    )


def run_nmap_scan(args: dict, cfg: Config) -> str:
    if shutil.which("nmap") is None:
        raise ToolError("nmap não está instalado (instale com: sudo apt install nmap).")

    host = _target_host(cfg)
    # Resolve e confere o escopo também aqui.
    try:
        resolved = socket.gethostbyname(host)
        ipaddress.ip_address(resolved)
    except (socket.gaierror, ValueError) as exc:
        raise ToolError(f"Não foi possível resolver o host do alvo '{host}': {exc}") from exc
    _assert_in_scope(host, cfg)

    ports = str(args.get("ports", "3000")).strip() or "3000"
    # Validação estrita de portas: só dígitos, vírgulas e hífens.
    if not all(c.isdigit() or c in ",-" for c in ports):
        raise ToolError(f"Especificação de portas inválida: '{ports}'.")

    scan_type = args.get("scan_type", "service_version")
    flags = {
        "service_version": ["-sV"],
        "default_scripts": ["-sV", "-sC"],
        "quick": ["-T4"],
    }.get(scan_type, ["-sV"])

    cmd = ["nmap", *flags, "-p", ports, host]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except subprocess.TimeoutExpired:
        raise ToolError("nmap excedeu o tempo limite (180s).") from None

    out = proc.stdout.strip()
    err = proc.stderr.strip()
    result = f"$ {' '.join(cmd)}\n{out}"
    if err:
        result += f"\n[stderr]\n{err}"
    return result


# Mapa nome -> executor, usado pelo loop principal.
EXECUTORS = {
    "http_request": run_http_request,
    "nmap_scan": run_nmap_scan,
}


def execute_tool(name: str, args: dict, cfg: Config) -> str:
    executor = EXECUTORS.get(name)
    if executor is None:
        raise ToolError(f"Ferramenta desconhecida: {name}")
    return executor(args, cfg)
