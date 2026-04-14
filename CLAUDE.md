# palimpsest — Memory Server Guide

This MCP server manages Claude's persistent memory across sessions.
Memory is organised in three layers, each stored as `.md` files on disk.

## Layers

| Layer       | Purpose                                            | When to use           |
|-------------|----------------------------------------------------|-----------------------|
| `vital`     | Identity, values, key positions, project framework | Load at session start |
| `contextual`| Recent compressed history, current directions      | Current session state |
| `long`      | Developed positions, fragments, archives           | Consult on demand     |

**Vital files should stay short** (~300 tokens max). Prefer one file per concept.

---

## Available tools

| Tool | Purpose |
|------|---------|
| `read_memory_file(layer, name)` | Read a file's content |
| `write_memory_file(layer, name, content)` | Create or overwrite a file |
| `list_memory_files(layer=null)` | List files — one layer or all |
| `delete_memory_file(layer, name)` | Remove a file permanently |
| `move_memory_file(source_layer, name, target_layer)` | Reorganise between layers |

File names are accepted with or without the `.md` extension.

---

## Typical workflows

### Start of session
1. `list_memory_files(layer=null)` — survey what exists
2. `read_memory_file(layer="vital", name="identity")` — reload identity
3. `read_memory_file(layer="contextual", name="current")` — reload recent context

### During session
- Write notes or draft positions to `contextual` as the session progresses.
- Read from `long` when a specific past position or archive is relevant.

### End of session
1. `write_memory_file(layer="contextual", name="current", content=...)` — compress session into contextual
2. If a contextual file has become a stable position → `move_memory_file` to `long`
3. If vital content needs updating → `write_memory_file` to `vital` (full overwrite, keep it short)

### Reorganising
- `move_memory_file` when a contextual note matures into a stable position worth archiving.
- `delete_memory_file` to prune entries that are outdated or no longer relevant.

---

## Write semantics

`write_memory_file` **always overwrites** the full file content.
Before writing, read the current content if you intend to extend rather than replace it.

---

## Memory directory

Files live at `memory/` relative to the project root, which is gitignored.

```
memory/
  vital/        ← .md files
  contextual/   ← .md files
  long/         ← .md files
```

---

## Running the server

```bash
# From the project root, with the venv active:
python scripts/mcp_server/main.py
```

## Registration (claude_desktop_config.json)

```json
{
  "mcpServers": {
    "palimpsest": {
      "command": "/Users/jean-francoisreboud/DocumentsNonSync/Perso/palimpsest/.venv/bin/python",
      "args": ["/Users/jean-francoisreboud/DocumentsNonSync/Perso/palimpsest/scripts/mcp_server/main.py"]
    }
  }
}
```
