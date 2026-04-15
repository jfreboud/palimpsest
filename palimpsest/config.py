"""Configuration loader for the palimpsest MCP server."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

_DEFAULT_TOML = Path(__file__).parent.parent / "scripts" / "mcp_server" / "config.toml"

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
    dmg_path : Path
        Absolute path to the encrypted private .dmg file.
    private_key : Path
        Absolute path to the unversioned key file used to mount the .dmg.
    """

    memory_dir: Path
    layers: tuple[str, ...]
    dmg_path: Path
    private_key: Path


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
        Resolved configuration with absolute paths.
    """
    path = toml_path or _DEFAULT_TOML
    with open(path, "rb") as f:
        data = tomllib.load(f)
    defaults = data["defaults"]
    memory_dir = (path.parent / defaults["memory_dir"]).resolve()
    layers = tuple(defaults.get("layers", list(LAYERS)))
    dmg_path = (
        path.parent / defaults.get("dmg_path", "../../memory_private.dmg")
    ).resolve()
    private_key = (
        path.parent / defaults.get("private_key", "../../memory/.private_key")
    ).resolve()
    return Config(
        memory_dir=memory_dir, layers=layers, dmg_path=dmg_path, private_key=private_key
    )
