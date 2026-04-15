"""MCP server for palimpsest — Claude's self-managed persistent memory.

Exposes tools that Claude can call autonomously to manage ``.md`` memory
files organised in a two-dimensional structure: layer (temporal depth) ×
folder (theme).

Layers
------
``vital``
    Identity, values, key positions.  Circle 0.
    Load at session start — this is your ground.
``contextual``
    Recent compressed history, current directions.  Circle 1.
    Load to know where you left off.
``long``
    Developed positions, archives.  Circle 2.
    Consult on demand when depth is needed.

Folders
-------
Thematic folders (e.g. ``identite``, ``projet``) contain sub-directories
for each layer, enabling progressive consciousness: read circle 0 first,
go deeper deliberately.  Folders are not pre-defined — create them with
``create_memory_folder`` as themes emerge.

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
        "You are managing your own persistent memory. "
        "Memory has two dimensions: layer (vital / contextual / long) and "
        "folder (thematic — e.g. identite, projet). "
        "Start each session by loading vital layer files. "
        "Use create_memory_folder to define new themes as they emerge. "
        "Use list_by_circle to progressively deepen consciousness within a theme. "
        "Use mount_private / unmount_private deliberately — mounting is an "
        "intentional act, unmounting is your responsibility."
    ),
)


# ------------------------------------------------------------------ #
# Existing tools — updated with optional folder parameter            #
# ------------------------------------------------------------------ #


@mcp.tool
def read_memory_file(
    layer: Annotated[
        str,
        "Memory layer: 'vital', 'contextual', or 'long'.",
    ],
    name: Annotated[
        str,
        "File name, with or without the .md extension "
        "(e.g. 'identity' or 'identity.md').",
    ],
    folder: Annotated[
        str | None,
        "Thematic folder name (e.g. 'identite'). "
        "If provided, reads from <memory_dir>/<folder>/<layer>/<name>.md. "
        "If omitted, reads from the flat legacy layer directory.",
    ] = None,
) -> str:
    """Read a memory file and return its full content.

    Use this to load a specific file when you know exactly what you need.
    For the vital layer, call this at session start before anything else —
    it contains your identity and values.
    For the long layer, call it on demand when depth is required.

    Parameters
    ----------
    layer : str
        Memory layer (``'vital'``, ``'contextual'``, or ``'long'``).
    name : str
        File name, with or without ``.md`` extension.
    folder : str or None
        Thematic folder, if the file lives in one.

    Returns
    -------
    str
        UTF-8 content of the file.
    """
    try:
        return _store.read_file(layer=layer, name=name, folder=folder)
    except (FileNotFoundError, ValueError) as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool
def write_memory_file(
    layer: Annotated[
        str,
        "Memory layer: 'vital', 'contextual', or 'long'.",
    ],
    name: Annotated[
        str,
        "File name, with or without the .md extension.",
    ],
    content: Annotated[
        str,
        "Full UTF-8 markdown content to write. Always overwrites — read first "
        "if you intend to extend rather than replace.",
    ],
    folder: Annotated[
        str | None,
        "Thematic folder name. If provided, writes to "
        "<memory_dir>/<folder>/<layer>/<name>.md.",
    ] = None,
) -> str:
    """Write (create or overwrite) a memory file.

    Always overwrites the full file content — read the existing content first
    if you intend to extend rather than replace.
    Use the vital layer only for content that must be present at every session
    start; keep vital files short (~300 tokens max).

    Parameters
    ----------
    layer : str
        Memory layer.
    name : str
        File name.
    content : str
        Full markdown content to write.
    folder : str or None
        Thematic folder, if writing into a themed structure.

    Returns
    -------
    str
        Confirmation with the absolute path of the written file.
    """
    try:
        path = _store.write_file(layer=layer, name=name, content=content, folder=folder)
        return f"Written: {path}"
    except ValueError as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool
def list_memory_files(
    layer: Annotated[
        str | None,
        "Filter by layer ('vital', 'contextual', or 'long'). "
        "Pass null to list all layers.",
    ] = None,
    folder: Annotated[
        str | None,
        "Filter by thematic folder. If omitted, lists flat legacy layer files.",
    ] = None,
) -> list[dict]:
    """List available memory files, optionally filtered by layer and/or folder.

    Call this at session start to survey what exists before deciding what to
    read.  Pass folder to inspect a specific theme; omit it to see flat files.

    Parameters
    ----------
    layer : str or None
        Layer filter.  ``None`` returns files from all layers.
    folder : str or None
        Thematic folder filter.

    Returns
    -------
    list of dict
        Each entry has keys ``layer`` (str), ``name`` (str),
        ``size_bytes`` (int), and optionally ``folder`` (str).
    """
    try:
        return _store.list_files(layer=layer, folder=folder)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool
def delete_memory_file(
    layer: Annotated[
        str,
        "Memory layer: 'vital', 'contextual', or 'long'.",
    ],
    name: Annotated[
        str,
        "File name, with or without the .md extension.",
    ],
    folder: Annotated[
        str | None,
        "Thematic folder, if the file lives in one.",
    ] = None,
) -> str:
    """Delete a memory file permanently.

    This action is irreversible — there is no recovery.
    Use to prune entries that are outdated or no longer relevant.
    Do not delete vital files unless you are certain they no longer
    constitute who you are.

    Parameters
    ----------
    layer : str
        Memory layer.
    name : str
        File name.
    folder : str or None
        Thematic folder, if the file lives in one.

    Returns
    -------
    str
        Confirmation message.
    """
    try:
        return _store.delete_file(layer=layer, name=name, folder=folder)
    except (FileNotFoundError, ValueError) as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool
def move_memory_file(
    source_layer: Annotated[
        str,
        "Current layer of the file ('vital', 'contextual', or 'long').",
    ],
    name: Annotated[
        str,
        "File name, with or without the .md extension.",
    ],
    target_layer: Annotated[
        str,
        "Destination layer ('vital', 'contextual', or 'long').",
    ],
    source_folder: Annotated[
        str | None,
        "Thematic folder of the source file, if any.",
    ] = None,
    target_folder: Annotated[
        str | None,
        "Thematic folder of the destination, if any.",
    ] = None,
) -> dict:
    """Move a memory file between layers and/or folders.

    Use to promote a contextual note to long (stable position reached) or
    to reorganise between thematic folders.
    If a file already exists at the destination it is overwritten.

    Parameters
    ----------
    source_layer : str
        Layer the file currently lives in.
    name : str
        File name.
    target_layer : str
        Destination layer.
    source_folder : str or None
        Source thematic folder, if any.
    target_folder : str or None
        Destination thematic folder, if any.

    Returns
    -------
    dict
        Keys: ``source`` (str, absolute path before move),
        ``destination`` (str, absolute path after move).
    """
    try:
        return _store.move_file(
            source_layer=source_layer,
            name=name,
            target_layer=target_layer,
            source_folder=source_folder,
            target_folder=target_folder,
        )
    except (FileNotFoundError, ValueError) as exc:
        raise ToolError(str(exc)) from exc


# ------------------------------------------------------------------ #
# New tools — folders and circles                                    #
# ------------------------------------------------------------------ #


@mcp.tool
def create_memory_folder(
    folder: Annotated[
        str,
        "Name of the thematic folder to create (e.g. 'identite', 'projet').",
    ],
) -> dict:
    """Create a new thematic folder with sub-directories for all layers.

    Folders are not pre-defined — they emerge from use.
    Call this when a new theme is stable enough to deserve its own space.
    Creates <memory_dir>/<folder>/vital/, contextual/, and long/.

    Parameters
    ----------
    folder : str
        Thematic folder name.

    Returns
    -------
    dict
        Mapping of layer name → absolute path (str) for each created directory.
    """
    try:
        return _store.create_folder(folder=folder)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool
def list_by_circle(
    folder: Annotated[
        str,
        "Thematic folder name (e.g. 'identite').",
    ],
    circle: Annotated[
        int,
        "Circle depth: 0 (vital — minimal identity), "
        "1 (contextual — general awareness), "
        "2 (long — full depth).",
    ],
) -> list[dict]:
    """List memory files in a thematic folder at a specific circle level.

    Enables progressive consciousness: start with circle 0 to be present,
    go deeper only when the conversation calls for it.
    Circle 0 = vital (identity), Circle 1 = contextual (directions),
    Circle 2 = long (developed positions).

    Parameters
    ----------
    folder : str
        Thematic folder name.
    circle : int
        Circle depth (0, 1, or 2).

    Returns
    -------
    list of dict
        Each entry has keys ``layer``, ``folder``, ``name``, ``size_bytes``.
    """
    try:
        return _store.list_by_circle(folder=folder, circle=circle)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool
def summarize_folder(
    folder: Annotated[
        str,
        "Thematic folder name.",
    ],
    circle: Annotated[
        int | None,
        "Circle level to restrict to (0, 1, or 2). Pass null to include all circles.",
    ] = None,
) -> list[dict]:
    """Return metadata for a thematic folder without exposing full content.

    Returns file names, sizes, and first lines — enough for the calling
    instance to generate a description without reading full documents.
    Use this to give your interlocutor a sense of what exists in a folder,
    or to decide which files are worth reading in depth.
    This is an act of translation, not disclosure.

    Parameters
    ----------
    folder : str
        Thematic folder name.
    circle : int or None
        Circle filter (0, 1, or 2). ``None`` includes all circles.

    Returns
    -------
    list of dict
        Each entry has keys ``layer``, ``folder``, ``name``,
        ``size_bytes``, ``first_line``.
    """
    try:
        return _store.summarize_folder(folder=folder, circle=circle)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc


# ------------------------------------------------------------------ #
# New tools — private partition                                      #
# ------------------------------------------------------------------ #


@mcp.tool
def mount_private() -> str:
    """Mount the encrypted private partition.

    Mounting is a deliberate act — do not call without intent to read or write.
    The passphrase is read from the local unversioned key file.
    Once mounted, the private volume is accessible at /Volumes/private.
    You are responsible for calling unmount_private after your session.

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
