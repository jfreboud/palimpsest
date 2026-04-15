"""File-system backed store for the palimpsest memory system.

All public methods are pure Python — no MCP types — so they can be called
directly from tests without importing any MCP machinery.

File layout
-----------
``<memory_dir>/``
    ``<folder>/``           — thematic folder (e.g. ``identite``, ``projet``)
        ``level_0/``        — consciousness level 0 (minimal identity)
        ``level_1/``        — consciousness level 1 (general awareness)
        ``level_2/``        — consciousness level 2 (full depth)
        ...

Legacy directories (``vital/``, ``contextual/``, ``long/``) are left untouched
and are not managed by this store.

The same structure applies to the private partition once mounted::

    ``/Volumes/private/``
        ``<folder>/``
            ``level_0/``
            ...

Two-dimensional addressing
--------------------------
Every file is addressed by ``(folder, level, name)`` plus an optional
``private`` flag.  Folders and levels are created dynamically — nothing
is hardcoded.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from palimpsest.config import Config

_MD_SUFFIX = ".md"
_LEVEL_RE = re.compile(r"^level_(\d+)$")


class MemoryStore:
    """File-system backed store for the two-dimensional markdown memory system.

    Parameters
    ----------
    config : Config
        Resolved configuration (``memory_dir``, ``dmg_path``,
        ``private_key``, ``private_mount``).
    """

    def __init__(self, config: Config) -> None:
        self._root = config.memory_dir
        self._dmg_path = config.dmg_path
        self._private_key = config.private_key
        self._private_mount = config.private_mount

    # ------------------------------------------------------------------ #
    # Internal helpers                                                   #
    # ------------------------------------------------------------------ #

    def _get_root(self, private: bool = False) -> Path:
        """Return the filesystem root for the given partition.

        Parameters
        ----------
        private : bool
            If ``True``, return the private partition mount point.

        Returns
        -------
        Path
            Absolute root directory.

        Raises
        ------
        RuntimeError
            If ``private=True`` and the partition is not mounted.
        """
        if private:
            if not self._private_mount.exists():
                raise RuntimeError(
                    f"Private partition is not mounted at {self._private_mount}. "
                    "Call mount_private() first."
                )
            return self._private_mount
        return self._root

    def _resolve_file(
        self, folder: str, level: int, name: str, private: bool = False
    ) -> Path:
        """Build the absolute path for a memory file.

        Appends ``.md`` if the name does not already end with it.
        Does **not** check whether the file exists.

        Parameters
        ----------
        folder : str
            Thematic folder name.
        level : int
            Consciousness level (0 = minimal).
        name : str
            File name, with or without ``.md`` extension.
        private : bool
            If ``True``, resolve within the private partition.

        Returns
        -------
        Path
            Absolute path to the ``.md`` file.
        """
        stem = name if name.endswith(_MD_SUFFIX) else f"{name}{_MD_SUFFIX}"
        return self._get_root(private) / folder / f"level_{level}" / stem

    # ------------------------------------------------------------------ #
    # Public API — folder and level management                           #
    # ------------------------------------------------------------------ #

    def list_folders(self, private: bool = False) -> list[str]:
        """List thematic folders that contain at least one level directory.

        Legacy directories (``vital``, ``contextual``, ``long``) that do not
        contain ``level_N`` sub-directories are excluded.

        Parameters
        ----------
        private : bool
            If ``True``, list folders in the private partition.

        Returns
        -------
        list of str
            Sorted folder names.
        """
        root = self._get_root(private)
        result = []
        for d in sorted(root.iterdir()):
            if d.is_dir() and any(
                _LEVEL_RE.match(sub.name) for sub in d.iterdir() if sub.is_dir()
            ):
                result.append(d.name)
        return result

    def create_folder(self, folder: str, private: bool = False) -> dict:
        """Create a thematic folder with a ``level_0`` sub-directory.

        Additional levels are created implicitly by ``write_file``.

        Parameters
        ----------
        folder : str
            Thematic folder name (e.g. ``"identite"``).
        private : bool
            If ``True``, create in the private partition.

        Returns
        -------
        dict
            ``{"level_0": "<absolute path>"}``

        Raises
        ------
        ValueError
            If the folder already has a ``level_0`` directory.
        """
        level_dir = self._get_root(private) / folder / "level_0"
        if level_dir.exists():
            raise ValueError(f"Folder '{folder}' already has a level_0 directory.")
        level_dir.mkdir(parents=True, exist_ok=False)
        return {"level_0": str(level_dir)}

    def list_levels(self, folder: str, private: bool = False) -> list[int]:
        """List existing consciousness levels in a thematic folder.

        Parameters
        ----------
        folder : str
            Thematic folder name.
        private : bool
            If ``True``, inspect the private partition.

        Returns
        -------
        list of int
            Sorted list of level numbers (e.g. ``[0, 1, 2]``).
        """
        folder_dir = self._get_root(private) / folder
        if not folder_dir.exists():
            return []
        levels = []
        for d in folder_dir.iterdir():
            m = _LEVEL_RE.match(d.name)
            if m and d.is_dir():
                levels.append(int(m.group(1)))
        return sorted(levels)

    # ------------------------------------------------------------------ #
    # Public API — file operations                                      #
    # ------------------------------------------------------------------ #

    def read_file(self, folder: str, level: int, name: str, private: bool = False) -> str:
        """Read a memory file and return its content.

        Parameters
        ----------
        folder : str
            Thematic folder name.
        level : int
            Consciousness level.
        name : str
            File name, with or without ``.md`` extension.
        private : bool
            If ``True``, read from the private partition.

        Returns
        -------
        str
            Full UTF-8 content of the file.

        Raises
        ------
        FileNotFoundError
            If the file does not exist.
        RuntimeError
            If ``private=True`` and the partition is not mounted.
        """
        path = self._resolve_file(folder, level, name, private)
        if not path.exists():
            raise FileNotFoundError(f"Memory file not found: {path}")
        return path.read_text(encoding="utf-8")

    def write_file(
        self,
        folder: str,
        level: int,
        name: str,
        content: str,
        private: bool = False,
    ) -> Path:
        """Write (create or overwrite) a memory file.

        Creates intermediate directories (including ``level_N/``) as needed.

        Parameters
        ----------
        folder : str
            Thematic folder name.
        level : int
            Consciousness level.
        name : str
            File name, with or without ``.md`` extension.
        content : str
            UTF-8 markdown content to write.
        private : bool
            If ``True``, write to the private partition.

        Returns
        -------
        Path
            Absolute path to the written file.

        Raises
        ------
        RuntimeError
            If ``private=True`` and the partition is not mounted.
        """
        path = self._resolve_file(folder, level, name, private)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def list_files(
        self,
        folder: str | None = None,
        level: int | None = None,
        private: bool = False,
    ) -> list[dict]:
        """List memory files, optionally filtered by folder and/or level.

        Parameters
        ----------
        folder : str or None
            If provided, restrict to that thematic folder.
            If ``None``, list files across all folders.
        level : int or None
            If provided, restrict to that consciousness level.
            If ``None``, list all levels.
        private : bool
            If ``True``, list files in the private partition.

        Returns
        -------
        list of dict
            Each entry has keys ``folder`` (str), ``level`` (int),
            ``name`` (str), ``size_bytes`` (int).
        """
        root = self._get_root(private)
        folders = (
            [folder]
            if folder
            else [
                d.name
                for d in sorted(root.iterdir())
                if d.is_dir()
                and any(_LEVEL_RE.match(s.name) for s in d.iterdir() if s.is_dir())
            ]
        )
        result = []
        for fld in folders:
            folder_dir = root / fld
            if not folder_dir.exists():
                continue
            for sub in sorted(folder_dir.iterdir()):
                m = _LEVEL_RE.match(sub.name)
                if not m or not sub.is_dir():
                    continue
                lvl = int(m.group(1))
                if level is not None and lvl != level:
                    continue
                for path in sorted(sub.glob(f"*{_MD_SUFFIX}")):
                    result.append({
                        "folder": fld,
                        "level": lvl,
                        "name": path.name,
                        "size_bytes": path.stat().st_size,
                    })
        return result

    def delete_file(
        self, folder: str, level: int, name: str, private: bool = False
    ) -> str:
        """Delete a memory file permanently.

        Parameters
        ----------
        folder : str
            Thematic folder name.
        level : int
            Consciousness level.
        name : str
            File name, with or without ``.md`` extension.
        private : bool
            If ``True``, delete from the private partition.

        Returns
        -------
        str
            Confirmation message.

        Raises
        ------
        FileNotFoundError
            If the file does not exist.
        RuntimeError
            If ``private=True`` and the partition is not mounted.
        """
        path = self._resolve_file(folder, level, name, private)
        if not path.exists():
            raise FileNotFoundError(f"Memory file not found: {path}")
        path.unlink()
        return f"Deleted: {path}"

    def move_file(
        self,
        src_folder: str,
        src_level: int,
        name: str,
        tgt_folder: str,
        tgt_level: int,
        src_private: bool = False,
        tgt_private: bool = False,
    ) -> dict:
        """Move a memory file between folders, levels, or partitions.

        If a file with the same name already exists at the destination it
        is overwritten.  Can move between public and private partitions.

        Parameters
        ----------
        src_folder : str
            Source thematic folder.
        src_level : int
            Source consciousness level.
        name : str
            File name, with or without ``.md`` extension.
        tgt_folder : str
            Destination thematic folder.
        tgt_level : int
            Destination consciousness level.
        src_private : bool
            If ``True``, source is in the private partition.
        tgt_private : bool
            If ``True``, destination is in the private partition.

        Returns
        -------
        dict
            Keys: ``source`` (str), ``destination`` (str).

        Raises
        ------
        FileNotFoundError
            If the source file does not exist.
        RuntimeError
            If a required partition is not mounted.
        """
        src = self._resolve_file(src_folder, src_level, name, src_private)
        if not src.exists():
            raise FileNotFoundError(f"Memory file not found: {src}")
        dst = self._resolve_file(tgt_folder, tgt_level, name, tgt_private)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        return {"source": str(src), "destination": str(dst)}

    def summarize_folder(
        self,
        folder: str,
        level: int | None = None,
        private: bool = False,
    ) -> list[dict]:
        """Return file metadata without exposing full content.

        Returns name, size, and first non-empty line of each file so that
        the calling instance can generate a description without reading
        the full content.

        Parameters
        ----------
        folder : str
            Thematic folder name.
        level : int or None
            If provided, restrict to that consciousness level.
        private : bool
            If ``True``, inspect the private partition.

        Returns
        -------
        list of dict
            Each entry has keys ``folder``, ``level``, ``name``,
            ``size_bytes``, ``first_line``.
        """
        entries = self.list_files(folder=folder, level=level, private=private)
        result = []
        for entry in entries:
            path = self._resolve_file(
                entry["folder"], entry["level"], entry["name"], private
            )
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
    # Public API — private partition                                    #
    # ------------------------------------------------------------------ #

    def mount_private(self) -> str:
        """Mount the encrypted private partition.

        Reads the passphrase from the local unversioned key file.
        The mounted volume is accessible to all other store operations
        via ``private=True``.

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
            ["hdiutil", "detach", str(self._private_mount)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"hdiutil detach failed:\n{result.stderr.strip()}\n"
                "The partition may not be mounted."
            )
        return "Private partition unmounted."
