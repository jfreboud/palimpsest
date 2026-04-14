"""Configuration loader for the palimpsest MCP server."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

_DEFAULT_TOML = (
    Path(__file__).parent.parent / "scripts" / "mcp_server" / "config.toml"
)

LAYERS: tuple[str, ...] = ("vital", "contextual", "long")


@dataclass
class Config:
    """Resolved server configuration.

    Parameters
    ----------
    memory_dir : Path
        Absolute path to the root memory directory.
    layers : tuple of str
        Ordered layer names (e.g. ``("vital", "contextual", "long")``).
    """

    memory_dir: Path
    layers: tuple[str, ...]


def load_config(toml_path: Path | None = None) -> Config:
    """Load configuration from a TOML file.

    Parameters
    ----------
    toml_path : Path or None
        Path to the TOML config file.  Defaults to
        ``scripts/mcp_server/config.toml`` relative to the project root.

    Returns
    -------
    Config
        Resolved configuration with an absolute ``memory_dir``.
    """
    path = toml_path or _DEFAULT_TOML
    with open(path, "rb") as f:
        data = tomllib.load(f)
    raw_dir: str = data["defaults"]["memory_dir"]
    memory_dir = (path.parent / raw_dir).resolve()
    layers = tuple(data["defaults"].get("layers", list(LAYERS)))
    return Config(memory_dir=memory_dir, layers=layers)
