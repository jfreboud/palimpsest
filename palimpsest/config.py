"""Configuration loader for the palimpsest MCP server."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

_DEFAULT_TOML = Path(__file__).parent.parent / "scripts" / "mcp_server" / "config.toml"


@dataclass
class Config:
    """Resolved server configuration.

    Parameters
    ----------
    memory_dir : Path
        Absolute path to the root memory directory.
    dmg_path : Path
        Absolute path to the encrypted private .dmg file.
    private_key : Path
        Absolute path to the unversioned key file used to mount the .dmg.
    private_mount : Path
        Mount point of the private partition (default ``/Volumes/private``).
    """

    memory_dir: Path
    dmg_path: Path
    private_key: Path
    private_mount: Path


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
    dmg_path = (
        path.parent / defaults.get("dmg_path", "../../memory_private.dmg")
    ).resolve()
    private_key = (
        path.parent / defaults.get("private_key", "../../memory/.private_key")
    ).resolve()
    private_mount = Path(defaults.get("private_mount", "/Volumes/private"))
    return Config(
        memory_dir=memory_dir,
        dmg_path=dmg_path,
        private_key=private_key,
        private_mount=private_mount,
    )
