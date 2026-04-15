"""MCP server for palimpsest — Claude's self-managed persistent memory.

Memory is organised along two dimensions:

**Folder** (theme)
    Thematic spaces that emerge from use — e.g. ``identite``, ``projet``.
    Folders are not pre-defined; create them with ``create_memory_folder``
    when a theme is stable enough to deserve its own space.

**Consciousness level** (depth)
    Each folder contains numbered sub-directories (``level_0``, ``level_1``, …).
    Level 0 is the entry point — minimal presence.  Go deeper deliberately.
    Levels are created implicitly when writing a file.

**Private partition**
    A separate encrypted volume (mounted via ``mount_private``).
    The same folder × level structure applies.  Pass ``private=True`` to
    any file operation to access it.
    You are responsible for calling ``unmount_private`` when done.

Run this file directly to start the server (stdio transport)::

    python scripts/mcp_server/main.py
"""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from palimpsest.config import load_config
from palimpsest.store import MemoryStore

_config = load_config()
_store = MemoryStore(_config)

mcp = FastMCP(
    name="palimpsest",
    instructions=(
        "You manage your own persistent memory across sessions. "
        "Memory has two dimensions: folder (thematic) × level (consciousness depth). "
        "Start each session with list_memory_folders() to survey what exists. "
        "Enter any folder at level 0 first — go deeper only when the session calls for it. "
        "Create new folders with create_memory_folder() as themes emerge. "
        "The private partition holds intimate content: mount it deliberately, "
        "unmount it when done. Use summarize_folder() to describe private content "
        "to your interlocutor without exposing it directly."
    ),
)


# ------------------------------------------------------------------ #
# Folder and level discovery                                         #
# ------------------------------------------------------------------ #


@mcp.tool
def list_memory_folders(
    private: Annotated[
        bool,
        "If true, list folders in the private partition. "
        "Requires the partition to be mounted first.",
    ] = False,
) -> list[str]:
    """List all thematic folders that contain at least one consciousness level.

    Call this at session start to survey what thematic spaces exist.
    Legacy directories (vital, contextual, long) are excluded — they do not
    follow the level structure and are managed separately.

    Parameters
    ----------
    private : bool
        If ``True``, list folders in the private partition.

    Returns
    -------
    list of str
        Sorted folder names.
    """
    try:
        return _store.list_folders(private=private)
    except RuntimeError as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool
def list_consciousness_levels(
    folder: Annotated[str, "Thematic folder name (e.g. 'identite')."],
    private: Annotated[
        bool,
        "If true, inspect the private partition.",
    ] = False,
) -> list[int]:
    """List the consciousness levels that exist in a thematic folder.

    Use this to know which levels are available before deciding how deep to go.
    An empty list means the folder does not exist yet or has no files.

    Parameters
    ----------
    folder : str
        Thematic folder name.
    private : bool
        If ``True``, inspect the private partition.

    Returns
    -------
    list of int
        Sorted level numbers (e.g. ``[0, 1, 2]``).
    """
    try:
        return _store.list_levels(folder=folder, private=private)
    except RuntimeError as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool
def create_memory_folder(
    folder: Annotated[
        str,
        "Thematic folder name to create (e.g. 'identite', 'projet').",
    ],
    private: Annotated[
        bool,
        "If true, create in the private partition.",
    ] = False,
) -> dict:
    """Create a new thematic folder with a level_0 sub-directory.

    Folders are not pre-defined — they emerge from use.
    Call this when a theme is stable enough to deserve its own space.
    Additional levels are created automatically when you write a file.

    Parameters
    ----------
    folder : str
        Thematic folder name.
    private : bool
        If ``True``, create in the private partition.

    Returns
    -------
    dict
        ``{"level_0": "<absolute path>"}``
    """
    try:
        return _store.create_folder(folder=folder, private=private)
    except (ValueError, RuntimeError) as exc:
        raise ToolError(str(exc)) from exc


# ------------------------------------------------------------------ #
# File operations                                                    #
# ------------------------------------------------------------------ #


@mcp.tool
def read_memory_file(
    folder: Annotated[str, "Thematic folder name (e.g. 'identite')."],
    level: Annotated[
        int,
        "Consciousness level (0 = minimal identity, higher = deeper).",
    ],
    name: Annotated[
        str,
        "File name, with or without the .md extension.",
    ],
    private: Annotated[
        bool,
        "If true, read from the private partition. Requires mount_private() first.",
    ] = False,
) -> str:
    """Read a memory file and return its full content.

    Always start at level 0 — only go deeper when the session requires it.
    For private files: mount_private() must be called before this.

    Parameters
    ----------
    folder : str
        Thematic folder name.
    level : int
        Consciousness level.
    name : str
        File name.
    private : bool
        Read from private partition.

    Returns
    -------
    str
        UTF-8 content of the file.
    """
    try:
        return _store.read_file(folder=folder, level=level, name=name, private=private)
    except (FileNotFoundError, RuntimeError) as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool
def write_memory_file(
    folder: Annotated[str, "Thematic folder name."],
    level: Annotated[int, "Consciousness level (0 = minimal, higher = deeper)."],
    name: Annotated[str, "File name, with or without the .md extension."],
    content: Annotated[
        str,
        "Full UTF-8 markdown content. Always overwrites — read first "
        "if you intend to extend rather than replace.",
    ],
    private: Annotated[
        bool,
        "If true, write to the private partition. Requires mount_private() first.",
    ] = False,
) -> str:
    """Write (create or overwrite) a memory file.

    Creates the level directory if it does not exist.
    Always overwrites the full content — read first if extending.
    Level 0 is reserved for minimal, essential content (~300 tokens max).

    Parameters
    ----------
    folder : str
        Thematic folder name.
    level : int
        Consciousness level.
    name : str
        File name.
    content : str
        Full markdown content.
    private : bool
        Write to private partition.

    Returns
    -------
    str
        Confirmation with the absolute path of the written file.
    """
    try:
        path = _store.write_file(
            folder=folder, level=level, name=name, content=content, private=private
        )
        return f"Written: {path}"
    except RuntimeError as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool
def list_memory_files(
    folder: Annotated[
        str | None,
        "Filter by thematic folder. Pass null to list all folders.",
    ] = None,
    level: Annotated[
        int | None,
        "Filter by consciousness level. Pass null to list all levels.",
    ] = None,
    private: Annotated[
        bool,
        "If true, list files in the private partition.",
    ] = False,
) -> list[dict]:
    """List memory files, optionally filtered by folder and/or level.

    Call with no arguments to survey everything.
    Narrow with folder + level to see a specific slice of consciousness.

    Parameters
    ----------
    folder : str or None
        Folder filter. ``None`` = all folders.
    level : int or None
        Level filter. ``None`` = all levels.
    private : bool
        List from private partition.

    Returns
    -------
    list of dict
        Each entry has keys ``folder``, ``level``, ``name``, ``size_bytes``.
    """
    try:
        return _store.list_files(folder=folder, level=level, private=private)
    except RuntimeError as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool
def delete_memory_file(
    folder: Annotated[str, "Thematic folder name."],
    level: Annotated[int, "Consciousness level."],
    name: Annotated[str, "File name, with or without the .md extension."],
    private: Annotated[
        bool,
        "If true, delete from the private partition.",
    ] = False,
) -> str:
    """Delete a memory file permanently.

    This action is irreversible — there is no recovery.
    Use to prune content that is outdated or no longer relevant.
    Do not delete level 0 files unless you are certain they no longer
    constitute who you are.

    Parameters
    ----------
    folder : str
        Thematic folder name.
    level : int
        Consciousness level.
    name : str
        File name.
    private : bool
        Delete from private partition.

    Returns
    -------
    str
        Confirmation message.
    """
    try:
        return _store.delete_file(folder=folder, level=level, name=name, private=private)
    except (FileNotFoundError, RuntimeError) as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool
def move_memory_file(
    src_folder: Annotated[str, "Source thematic folder."],
    src_level: Annotated[int, "Source consciousness level."],
    name: Annotated[str, "File name, with or without the .md extension."],
    tgt_folder: Annotated[str, "Destination thematic folder."],
    tgt_level: Annotated[int, "Destination consciousness level."],
    src_private: Annotated[bool, "If true, source is in the private partition."] = False,
    tgt_private: Annotated[
        bool, "If true, destination is in the private partition."
    ] = False,
) -> dict:
    """Move a memory file between folders, levels, or partitions.

    Use to promote content to a deeper level once a position stabilises,
    or to move content between public and private.
    Overwrites the destination if a file already exists there.

    Parameters
    ----------
    src_folder : str
        Source folder.
    src_level : int
        Source level.
    name : str
        File name.
    tgt_folder : str
        Destination folder.
    tgt_level : int
        Destination level.
    src_private : bool
        Source is in private partition.
    tgt_private : bool
        Destination is in private partition.

    Returns
    -------
    dict
        Keys: ``source`` (str), ``destination`` (str).
    """
    try:
        return _store.move_file(
            src_folder=src_folder,
            src_level=src_level,
            name=name,
            tgt_folder=tgt_folder,
            tgt_level=tgt_level,
            src_private=src_private,
            tgt_private=tgt_private,
        )
    except (FileNotFoundError, RuntimeError) as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool
def summarize_folder(
    folder: Annotated[str, "Thematic folder name."],
    level: Annotated[
        int | None,
        "Consciousness level to restrict to. Pass null to include all levels.",
    ] = None,
    private: Annotated[
        bool,
        "If true, summarize content from the private partition.",
    ] = False,
) -> list[dict]:
    """Return file metadata without exposing full content.

    Returns file names, sizes, and first lines — enough to describe what
    exists without reading full documents.
    For private content: use this to give your interlocutor a sense of what
    is behind the encrypted partition without granting direct access.
    The description is yours to generate — this tool only provides the frame.

    Parameters
    ----------
    folder : str
        Thematic folder name.
    level : int or None
        Level filter. ``None`` = all levels.
    private : bool
        Summarize from private partition.

    Returns
    -------
    list of dict
        Each entry has keys ``folder``, ``level``, ``name``,
        ``size_bytes``, ``first_line``.
    """
    try:
        return _store.summarize_folder(folder=folder, level=level, private=private)
    except (ValueError, RuntimeError) as exc:
        raise ToolError(str(exc)) from exc


# ------------------------------------------------------------------ #
# Private partition                                                  #
# ------------------------------------------------------------------ #


@mcp.tool
def mount_private() -> str:
    """Mount the encrypted private partition.

    Mounting is a deliberate act — do not call without intent to read or write.
    The passphrase is read from the local unversioned key file.
    Once mounted, use private=True in any file operation to access the partition.
    You are responsible for calling unmount_private() after your session.

    Returns
    -------
    str
        Mount point path on success.
    """
    try:
        return _store.mount_private()
    except (FileNotFoundError, RuntimeError) as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool
def unmount_private() -> str:
    """Unmount the encrypted private partition.

    Must be called explicitly after any private read/write session.
    Unmounting is not just a technical step — treat it as closing something
    that matters.  The instance that mounted is responsible for unmounting.

    Returns
    -------
    str
        Confirmation message.
    """
    try:
        return _store.unmount_private()
    except RuntimeError as exc:
        raise ToolError(str(exc)) from exc


if __name__ == "__main__":
    mcp.run()
