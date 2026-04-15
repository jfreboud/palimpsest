# Changelog

All notable changes to this project will be documented in this file.

## [unreleased]

### Added
- **Two-dimensional memory structure** : `memory/<folder>/level_N/<file>.md`
  - Folders are thematic (e.g. `identite`, `projet`) and emerge from use
  - Consciousness levels are numbered from 0 (most distilled) upward
  - Legacy directories (`vital/`, `contextual/`, `long/`) left intact
- **New MCP tools** : `list_memory_folders`, `list_consciousness_levels`,
  `create_memory_folder`, `create_consciousness_level`
- **Private partition** : encrypted `.dmg` mounted/unmounted via MCP
  (`mount_private`, `unmount_private`) — all file operations accept `private=True`
- `summarize_folder` : returns file metadata (name, size, first line) without
  exposing full content — for describing private content to an interlocutor
- `move_memory_file` supports cross-partition moves (`src_private ≠ tgt_private`)
- Config : `dmg_path`, `private_key`, `private_mount` — `layers` removed

### Changed
- `write_memory_file` requires the level directory to pre-exist — no implicit
  creation. Level 0 is opened by `create_memory_folder`; deeper levels by
  `create_consciousness_level`. This makes every level an intentional act.
- All MCP docstrings rewritten to orient the call decision, not just describe
  the mechanics
- Config drops hardcoded `layers` tuple — folders and levels are fully dynamic

### Initial
- MCP memory server with three-layer architecture (`vital`, `contextual`, `long`)
