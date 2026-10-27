"""Carregamento da configuração do laboratório (config.yaml)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

import yaml


@dataclass
class OllamaConfig:
    host: str = "http://localhost:11434"
    model: str = "qwen3:4b"
    think: bool = False


@dataclass
class TargetConfig:
    base_url: str = "http://localhost:3000"


@dataclass
class Config:
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    target: TargetConfig = field(default_factory=TargetConfig)
    log_dir: str = "logs"
    max_steps: int = 30


def load_config(path: str = "config.yaml") -> Config:
    """Lê o config.yaml e devolve um objeto Config com defaults sensatos."""
    data: dict = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}

    ollama = data.get("ollama", {}) or {}
    target = data.get("target", {}) or {}
    logging_cfg = data.get("logging", {}) or {}

    return Config(
        ollama=OllamaConfig(
            host=ollama.get("host", "http://localhost:11434"),
            model=ollama.get("model", "qwen3:4b"),
            think=bool(ollama.get("think", False)),
        ),
        target=TargetConfig(
            base_url=target.get("base_url", "http://localhost:3000"),
        ),
        log_dir=logging_cfg.get("dir", "logs"),
        max_steps=int(data.get("max_steps", 30)),
    )
