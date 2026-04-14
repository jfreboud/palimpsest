"""File-system backed store for the palimpsest three-layer memory system.

All public methods are pure Python — no MCP types — so they can be called
directly from tests without importing any MCP machinery.

File layout
-----------
``<memory_dir>/``
    ``vital/``        — always-loaded identity layer
    ``contextual/``   — recent compressed history
    ``long/``         — developed positions, archives
"""

from __future__ import annotations

import shutil
from pathlib import Path

from palimpsest.config import Config

_MD_SUFFIX = ".md"


class MemoryStore:
    """File-system backed store for three-layer markdown memory files.

    Parameters
    ----------
    config : Config
        Resolved configuration (``memory_dir``, ``layers``).
    """

    def __init__(self, config: Config) -> None:
        self._root = config.memory_dir
        self._layers = config.layers
        self._ensure_dirs()

    # ------------------------------------------------------------------ #
    # Internal helpers                                                   #
    # ------------------------------------------------------------------ #

    def _ensure_dirs(self) -> None:
        """Create layer sub-directories if they do not exist."""
        for layer in self._layers:
            (self._root / layer).mkdir(parents=True, exist_ok=True)

    def _layer_dir(self, layer: str) -> Path:
        """Return the absolute path for a given layer.

        Parameters
        ----------
        layer : str
            One of the configured layer names.

        Returns
        -------
        Path
            Absolute directory path.

        Raises
        ------
        ValueError
            If ``layer`` is not a known layer name.
        """
        if layer not in self._layers:
            raise ValueError(
                f"Unknown layer '{layer}'. Valid layers: {list(self._layers)}"
            )
        return self._root / layer

    def _resolve_file(self, layer: str, name: str) -> Path:
        """Build the absolute path for a memory file.

        Appends ``.md`` if the name does not already end with it.
        Does **not** check whether the file exists.

        Parameters
        ----------
        layer : str
            Target layer name.
        name : str
            File name, with or without ``.md`` extension.

        Returns
        -------
        Path
            Absolute path to the ``.md`` file.
        """
        stem = name if name.endswith(_MD_SUFFIX) else f"{name}{_MD_SUFFIX}"
        return self._layer_dir(layer) / stem

    # ------------------------------------------------------------------ #
    # Public API                                                         #
    # ------------------------------------------------------------------ #

    def read_file(self, layer: str, name: str) -> str:
        """Read a memory file and return its content.

        Parameters
        ----------
        layer : str
            Layer that contains the file.
        name : str
            File name, with or without ``.md`` extension.

        Returns
        -------
        str
            Full UTF-8 content of the file.

        Raises
        ------
        FileNotFoundError
            If the file does not exist.
        ValueError
            If ``layer`` is unknown.
        """
        path = self._resolve_file(layer, name)
        if not path.exists():
            raise FileNotFoundError(f"Memory file not found: {path}")
        return path.read_text(encoding="utf-8")

    def write_file(self, layer: str, name: str, content: str) -> Path:
        """Write (create or overwrite) a memory file.

        Parameters
        ----------
        layer : str
            Target layer.
        name : str
            File name, with or without ``.md`` extension.
        content : str
            UTF-8 markdown content to write.

        Returns
        -------
        Path
            Absolute path to the written file.

        Raises
        ------
        ValueError
            If ``layer`` is unknown.
        """
        path = self._resolve_file(layer, name)
        path.write_text(content, encoding="utf-8")
        return path

    def list_files(self, layer: str | None = None) -> list[dict]:
        """List memory files, optionally filtered to one layer.

        Parameters
        ----------
        layer : str or None
            If provided, list only files in that layer.
            If ``None``, list files across all layers.

        Returns
        -------
        list of dict
            Each entry has keys ``layer`` (str), ``name`` (str),
            ``size_bytes`` (int).

        Raises
        ------
        ValueError
            If ``layer`` is provided and unknown.
        """
        layers = [layer] if layer else list(self._layers)
        result = []
        for lyr in layers:
            for path in sorted(self._layer_dir(lyr).glob(f"*{_MD_SUFFIX}")):
                result.append(
                    {
                        "layer": lyr,
                        "name": path.name,
                        "size_bytes": path.stat().st_size,
                    }
                )
        return result

    def delete_file(self, layer: str, name: str) -> str:
        """Delete a memory file.

        Parameters
        ----------
        layer : str
            Layer that contains the file.
        name : str
            File name, with or without ``.md`` extension.

        Returns
        -------
        str
            Confirmation message.

        Raises
        ------
        FileNotFoundError
            If the file does not exist.
        ValueError
            If ``layer`` is unknown.
        """
        path = self._resolve_file(layer, name)
        if not path.exists():
            raise FileNotFoundError(f"Memory file not found: {path}")
        path.unlink()
        return f"Deleted: {path}"

    def move_file(
        self, source_layer: str, name: str, target_layer: str
    ) -> dict:
        """Move a memory file from one layer to another.

        If a file with the same name already exists in the target layer it
        is overwritten.

        Parameters
        ----------
        source_layer : str
            Current layer of the file.
        name : str
            File name, with or without ``.md`` extension.
        target_layer : str
            Destination layer.

        Returns
        -------
        dict
            Keys: ``source`` (str), ``destination`` (str).

        Raises
        ------
        FileNotFoundError
            If the source file does not exist.
        ValueError
            If either layer is unknown.
        """
        src = self._resolve_file(source_layer, name)
        if not src.exists():
            raise FileNotFoundError(f"Memory file not found: {src}")
        dst = self._resolve_file(target_layer, name)
        shutil.move(str(src), str(dst))
        return {"source": str(src), "destination": str(dst)}
