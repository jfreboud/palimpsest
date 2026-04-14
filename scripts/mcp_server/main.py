"""MCP server for palimpsest — Claude's self-managed persistent memory.

Exposes five tools that Claude can call autonomously to read, write,
list, delete, and move ``.md`` memory files organised in three layers:

``vital``
    Identity criterion, values, key positions.  Always loaded.
``contextual``
    Recent compressed history, current directions.
``long``
    Developed positions, archives.  Consulted on demand.

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
        "Memory is organised in three layers: "
        "'vital' (always loaded — identity and values), "
        "'contextual' (recent history and current directions), "
        "'long' (developed positions and archives — consult on demand). "
        "Use read_memory_file to retrieve content, write_memory_file to "
        "create or update files, list_memory_files to survey what exists, "
        "delete_memory_file to remove obsolete entries, and "
        "move_memory_file to reorganise between layers."
    ),
)


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
) -> str:
    """Read a memory file and return its full content.

    Parameters
    ----------
    layer : str
        Memory layer (``'vital'``, ``'contextual'``, or ``'long'``).
    name : str
        File name, with or without ``.md`` extension.

    Returns
    -------
    str
        UTF-8 content of the file.
    """
    try:
        return _store.read_file(layer=layer, name=name)
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
        "Full UTF-8 markdown content to write. Overwrites any existing file.",
    ],
) -> str:
    """Write (create or overwrite) a memory file.

    Parameters
    ----------
    layer : str
        Memory layer.
    name : str
        File name.
    content : str
        Full markdown content to write.  Overwrites any existing file.

    Returns
    -------
    str
        Confirmation with the absolute path of the written file.
    """
    try:
        path = _store.write_file(layer=layer, name=name, content=content)
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
) -> list[dict]:
    """List available memory files, optionally filtered to one layer.

    Parameters
    ----------
    layer : str or None
        Layer filter.  ``None`` returns files from all layers.

    Returns
    -------
    list of dict
        Each entry has keys ``layer`` (str), ``name`` (str),
        ``size_bytes`` (int).
    """
    try:
        return _store.list_files(layer=layer)
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
) -> str:
    """Delete a memory file permanently.

    Parameters
    ----------
    layer : str
        Memory layer.
    name : str
        File name.

    Returns
    -------
    str
        Confirmation message.
    """
    try:
        return _store.delete_file(layer=layer, name=name)
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
) -> dict:
    """Move a memory file from one layer to another.

    Parameters
    ----------
    source_layer : str
        Layer the file currently lives in.
    name : str
        File name.
    target_layer : str
        Destination layer.

    Returns
    -------
    dict
        Keys: ``source`` (str, absolute path before move),
        ``destination`` (str, absolute path after move).
    """
    try:
        return _store.move_file(
            source_layer=source_layer, name=name, target_layer=target_layer
        )
    except (FileNotFoundError, ValueError) as exc:
        raise ToolError(str(exc)) from exc


if __name__ == "__main__":
    mcp.run()
