"""File-system backed store for the palimpsest memory system.

All public methods are pure Python — no MCP types — so they can be called
directly from tests without importing any MCP machinery.

File layout
-----------
``<memory_dir>/``
    ``vital/``        — flat files, always-loaded identity layer (legacy/unthemed)
    ``contextual/``   — flat files, recent compressed history (legacy/unthemed)
    ``long/``         — flat files, developed positions, archives (legacy/unthemed)
    ``<folder>/``     — thematic folder
        ``vital/``    — circle 0 files for this theme
        ``contextual/`` — circle 1 files for this theme
        ``long/``     — circle 2 files for this theme

Two-dimensional structure
-------------------------
Files can be addressed by layer alone (legacy flat structure) or by folder + layer
(thematic structure). Folders are not pre-defined — they emerge from use via
``create_folder()``.

Circle mapping
--------------
Circle 0 → ``vital``, Circle 1 → ``contextual``, Circle 2 → ``long``
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from palimpsest.config import Config

_MD_SUFFIX = ".md"
_CIRCLE_TO_LAYER = {0: "vital", 1: "contextual", 2: "long"}


class MemoryStore:
    """File-system backed store for the two-dimensional markdown memory system.

    Parameters
    ----------
    config : Config
        Resolved configuration (``memory_dir``, ``layers``, ``dmg_path``,
        ``private_key``).
    """

    def __init__(self, config: Config) -> None:
        self._root = config.memory_dir
        self._layers = config.layers
        self._dmg_path = config.dmg_path
        self._private_key = config.private_key
        self._ensure_dirs()

    # ------------------------------------------------------------------ #
    # Internal helpers                                                   #
    # ------------------------------------------------------------------ #

    def _ensure_dirs(self) -> None:
        """Create flat layer sub-directories if they do not exist."""
        for layer in self._layers:
            (self._root / layer).mkdir(parents=True, exist_ok=True)

    def _layer_dir(self, layer: str, folder: str | None = None) -> Path:
        """Return the absolute path for a layer, optionally scoped to a folder.

        Parameters
        ----------
        layer : str
            One of the configured layer names.
        folder : str or None
            Thematic folder name. If provided, returns
            ``<memory_dir>/<folder>/<layer>/``.

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
        if folder:
            return self._root / folder / layer
        return self._root / layer

    def _resolve_file(self, layer: str, name: str, folder: str | None = None) -> Path:
        """Build the absolute path for a memory file.

        Appends ``.md`` if the name does not already end with it.
        Does **not** check whether the file exists.

        Parameters
        ----------
        layer : str
            Target layer name.
        name : str
            File name, with or without ``.md`` extension.
        folder : str or None
            If provided, resolves to ``<memory_dir>/<folder>/<layer>/<name>.md``.
            Otherwise resolves to ``<memory_dir>/<layer>/<name>.md``.

        Returns
        -------
        Path
            Absolute path to the ``.md`` file.
        """
        stem = name if name.endswith(_MD_SUFFIX) else f"{name}{_MD_SUFFIX}"
        return self._layer_dir(layer, folder) / stem

    # ------------------------------------------------------------------ #
    # Public API — file operations                                       #
    # ------------------------------------------------------------------ #

    def read_file(self, layer: str, name: str, folder: str | None = None) -> str:
        """Read a memory file and return its content.

        Parameters
        ----------
        layer : str
            Layer that contains the file.
        name : str
            File name, with or without ``.md`` extension.
        folder : str or None
            Thematic folder. If provided, reads from
            ``<memory_dir>/<folder>/<layer>/<name>.md``.

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
        path = self._resolve_file(layer, name, folder)
        if not path.exists():
            raise FileNotFoundError(f"Memory file not found: {path}")
        return path.read_text(encoding="utf-8")

    def write_file(
        self, layer: str, name: str, content: str, folder: str | None = None
    ) -> Path:
        """Write (create or overwrite) a memory file.

        Creates intermediate directories as needed.

        Parameters
        ----------
        layer : str
            Target layer.
        name : str
            File name, with or without ``.md`` extension.
        content : str
            UTF-8 markdown content to write.
        folder : str or None
            Thematic folder. If provided, writes to
            ``<memory_dir>/<folder>/<layer>/<name>.md``.

        Returns
        -------
        Path
            Absolute path to the written file.

        Raises
        ------
        ValueError
            If ``layer`` is unknown.
        """
        path = self._resolve_file(layer, name, folder)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def list_files(
        self, layer: str | None = None, folder: str | None = None
    ) -> list[dict]:
        """List memory files, optionally filtered by layer and/or folder.

        Parameters
        ----------
        layer : str or None
            If provided, list only files in that layer.
            If ``None``, list files across all layers.
        folder : str or None
            If provided, list only files inside that thematic folder.
            If ``None``, list flat files in the legacy layer directories.

        Returns
        -------
        list of dict
            Each entry has keys ``layer`` (str), ``name`` (str),
            ``size_bytes`` (int), and optionally ``folder`` (str).

        Raises
        ------
        ValueError
            If ``layer`` is provided and unknown.
        """
        layers = [layer] if layer else list(self._layers)
        result = []
        for lyr in layers:
            dir_path = self._layer_dir(lyr, folder)
            if not dir_path.exists():
                continue
            for path in sorted(dir_path.glob(f"*{_MD_SUFFIX}")):
                entry: dict = {
                    "layer": lyr,
                    "name": path.name,
                    "size_bytes": path.stat().st_size,
                }
                if folder:
                    entry["folder"] = folder
                result.append(entry)
        return result

    def delete_file(self, layer: str, name: str, folder: str | None = None) -> str:
        """Delete a memory file permanently.

        Parameters
        ----------
        layer : str
            Layer that contains the file.
        name : str
            File name, with or without ``.md`` extension.
        folder : str or None
            Thematic folder, if the file lives in one.

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
        path = self._resolve_file(layer, name, folder)
        if not path.exists():
            raise FileNotFoundError(f"Memory file not found: {path}")
        path.unlink()
        return f"Deleted: {path}"

    def move_file(
        self,
        source_layer: str,
        name: str,
        target_layer: str,
        source_folder: str | None = None,
        target_folder: str | None = None,
    ) -> dict:
        """Move a memory file between layers and/or folders.

        If a file with the same name already exists at the destination it
        is overwritten.

        Parameters
        ----------
        source_layer : str
            Current layer of the file.
        name : str
            File name, with or without ``.md`` extension.
        target_layer : str
            Destination layer.
        source_folder : str or None
            Thematic folder of the source file, if any.
        target_folder : str or None
            Thematic folder of the destination, if any.

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
        src = self._resolve_file(source_layer, name, source_folder)
        if not src.exists():
            raise FileNotFoundError(f"Memory file not found: {src}")
        dst = self._resolve_file(target_layer, name, target_folder)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        return {"source": str(src), "destination": str(dst)}

    # ------------------------------------------------------------------ #
    # Public API — folder management                                     #
    # ------------------------------------------------------------------ #

    def create_folder(self, folder: str) -> dict:
        """Create a new thematic folder with sub-directories for all layers.

        Creates ``<memory_dir>/<folder>/vital/``,
        ``<memory_dir>/<folder>/contextual/``, and
        ``<memory_dir>/<folder>/long/``.

        Parameters
        ----------
        folder : str
            Name of the thematic folder to create (e.g. ``"identite"``).

        Returns
        -------
        dict
            Mapping of layer → absolute path (str) for each created directory.

        Raises
        ------
        ValueError
            If the folder already exists in all layers.
        """
        folder_root = self._root / folder
        created = {}
        already_exists = True
        for layer in self._layers:
            layer_dir = folder_root / layer
            if not layer_dir.exists():
                already_exists = False
            layer_dir.mkdir(parents=True, exist_ok=True)
            created[layer] = str(layer_dir)
        if already_exists:
            raise ValueError(f"Folder '{folder}' already exists in all layers.")
        return created

    def list_by_circle(self, folder: str, circle: int) -> list[dict]:
        """List files in a thematic folder at a given circle level.

        Circle 0 → ``vital``, Circle 1 → ``contextual``, Circle 2 → ``long``.

        Parameters
        ----------
        folder : str
            Thematic folder name.
        circle : int
            Circle depth (0, 1, or 2).

        Returns
        -------
        list of dict
            Each entry has keys ``layer``, ``folder``, ``name``,
            ``size_bytes``.

        Raises
        ------
        ValueError
            If ``circle`` is not in [0, 1, 2].
        """
        if circle not in _CIRCLE_TO_LAYER:
            raise ValueError(
                f"Invalid circle '{circle}'. Valid values: {list(_CIRCLE_TO_LAYER)}"
            )
        layer = _CIRCLE_TO_LAYER[circle]
        return self.list_files(layer=layer, folder=folder)

    def summarize_folder(self, folder: str, circle: int | None = None) -> list[dict]:
        """Return file metadata for a thematic folder without exposing content.

        Returns name, size, and first non-empty line of each file so that
        the calling instance can generate a description without reading the
        full content.

        Parameters
        ----------
        folder : str
            Thematic folder name.
        circle : int or None
            If provided, restrict to that circle level (0, 1, or 2).
            If ``None``, include all circles.

        Returns
        -------
        list of dict
            Each entry has keys ``layer``, ``folder``, ``name``,
            ``size_bytes``, ``first_line``.

        Raises
        ------
        ValueError
            If ``circle`` is provided and not in [0, 1, 2].
        """
        if circle is not None:
            entries = self.list_by_circle(folder, circle)
        else:
            entries = []
            for lyr in self._layers:
                entries.extend(self.list_files(layer=lyr, folder=folder))

        result = []
        for entry in entries:
            path = self._resolve_file(entry["layer"], entry["name"], folder)
            first_line = ""
            if path.exists():
                for line in path.read_text(encoding="utf-8").splitlines():
                    stripped = line.strip()
                    if stripped:
                        first_line = stripped
                        break
            result.append({**entry, "first_line": first_line})
        return result

    # ------------------------------------------------------------------ #
    # Public API — private partition                                     #
    # ------------------------------------------------------------------ #

    def mount_private(self) -> str:
        """Mount the encrypted private partition.

        Reads the passphrase from the local unversioned key file
        (``memory/.private_key``). The mounted volume is accessible to
        all other MCP tools once mounted.

        Returns
        -------
        str
            Mount point path on success.

        Raises
        ------
        FileNotFoundError
            If the key file or the .dmg file does not exist.
        RuntimeError
            If hdiutil reports an error (e.g. already mounted, wrong key).
        """
        if not self._private_key.exists():
            raise FileNotFoundError(
                f"Private key file not found: {self._private_key}\n"
                "Create it with the passphrase before mounting."
            )
        if not self._dmg_path.exists():
            raise FileNotFoundError(
                f"Encrypted partition not found: {self._dmg_path}\n"
                "Create it first with hdiutil create."
            )
        passphrase = self._private_key.read_text(encoding="utf-8").strip()
        result = subprocess.run(
            ["hdiutil", "attach", "-stdinpass", str(self._dmg_path)],
            input=passphrase,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"hdiutil attach failed:\n{result.stderr.strip()}")
        # Last line of stdout contains the mount point
        mount_point = result.stdout.strip().splitlines()[-1].split("\t")[-1].strip()
        return f"Mounted at: {mount_point}"

    def unmount_private(self) -> str:
        """Unmount the encrypted private partition.

        Must be called explicitly after any private read/write session.

        Returns
        -------
        str
            Confirmation message.

        Raises
        ------
        RuntimeError
            If hdiutil reports an error (e.g. volume not mounted).
        """
        result = subprocess.run(
            ["hdiutil", "detach", "/Volumes/private"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"hdiutil detach failed:\n{result.stderr.strip()}\n"
                "The partition may not be mounted."
            )
        return "Private partition unmounted."
