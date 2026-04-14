"""Unit tests for palimpsest.store.MemoryStore."""

from __future__ import annotations

from pathlib import Path

import pytest

from palimpsest.config import Config
from palimpsest.store import MemoryStore


def make_store(tmp_path: Path) -> MemoryStore:
    """Build a MemoryStore backed by a temporary directory.

    Parameters
    ----------
    tmp_path : Path
        Pytest-provided temporary directory.

    Returns
    -------
    MemoryStore
        Store with three default layers under ``tmp_path``.
    """
    config = Config(
        memory_dir=tmp_path,
        layers=("vital", "contextual", "long"),
    )
    return MemoryStore(config)


# ------------------------------------------------------------------ #
# Happy-path tests                                                   #
# ------------------------------------------------------------------ #


def test_write_and_read(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    content = "# Identity\n\nCore values go here."
    store.write_file("vital", "identity", content)
    assert store.read_file("vital", "identity") == content


def test_write_creates_md_extension(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.write_file("vital", "identity", "hello")
    assert (tmp_path / "vital" / "identity.md").exists()


def test_name_without_extension(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.write_file("contextual", "session", "data")
    result = store.read_file("contextual", "session")
    assert result == "data"


def test_name_with_extension(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.write_file("long", "archive.md", "old stuff")
    result = store.read_file("long", "archive.md")
    assert result == "old stuff"


def test_list_all_layers(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.write_file("vital", "values", "v")
    store.write_file("contextual", "current", "c")
    store.write_file("long", "position", "p")
    files = store.list_files()
    names = [(f["layer"], f["name"]) for f in files]
    assert ("vital", "values.md") in names
    assert ("contextual", "current.md") in names
    assert ("long", "position.md") in names


def test_list_single_layer(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.write_file("vital", "values", "v")
    store.write_file("contextual", "current", "c")
    files = store.list_files(layer="vital")
    assert len(files) == 1
    assert files[0]["layer"] == "vital"
    assert files[0]["name"] == "values.md"


def test_list_returns_size(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    content = "hello"
    store.write_file("vital", "test", content)
    files = store.list_files(layer="vital")
    assert files[0]["size_bytes"] == len(content.encode("utf-8"))


def test_delete(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.write_file("vital", "temp", "temporary")
    store.delete_file("vital", "temp")
    with pytest.raises(FileNotFoundError):
        store.read_file("vital", "temp")


def test_move(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.write_file("contextual", "note", "stable position")
    store.move_file("contextual", "note", "long")
    # Present at destination
    assert store.read_file("long", "note") == "stable position"
    # Absent from source
    with pytest.raises(FileNotFoundError):
        store.read_file("contextual", "note")


def test_move_overwrites_existing(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.write_file("contextual", "note", "new content")
    store.write_file("long", "note", "old content")
    store.move_file("contextual", "note", "long")
    assert store.read_file("long", "note") == "new content"


# ------------------------------------------------------------------ #
# Error cases                                                        #
# ------------------------------------------------------------------ #


def test_unknown_layer_raises_on_read(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    with pytest.raises(ValueError, match="Unknown layer"):
        store.read_file("nonexistent", "file")


def test_unknown_layer_raises_on_write(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    with pytest.raises(ValueError, match="Unknown layer"):
        store.write_file("nonexistent", "file", "content")


def test_unknown_layer_raises_on_list(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    with pytest.raises(ValueError, match="Unknown layer"):
        store.list_files(layer="nonexistent")


def test_unknown_layer_raises_on_delete(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    with pytest.raises(ValueError, match="Unknown layer"):
        store.delete_file("nonexistent", "file")


def test_unknown_layer_raises_on_move_source(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    with pytest.raises(ValueError, match="Unknown layer"):
        store.move_file("nonexistent", "file", "vital")


def test_unknown_layer_raises_on_move_target(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.write_file("vital", "file", "content")
    with pytest.raises(ValueError, match="Unknown layer"):
        store.move_file("vital", "file", "nonexistent")


def test_missing_file_raises_on_read(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    with pytest.raises(FileNotFoundError):
        store.read_file("vital", "does_not_exist")


def test_missing_file_raises_on_delete(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    with pytest.raises(FileNotFoundError):
        store.delete_file("vital", "does_not_exist")


def test_missing_file_raises_on_move(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    with pytest.raises(FileNotFoundError):
        store.move_file("vital", "does_not_exist", "long")
