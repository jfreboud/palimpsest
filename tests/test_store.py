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
        dmg_path=tmp_path / "private.dmg",
        private_key=tmp_path / ".private_key",
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


# ------------------------------------------------------------------ #
# Folder and circle tests                                            #
# ------------------------------------------------------------------ #


def test_create_folder(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    result = store.create_folder("identite")
    assert set(result.keys()) == {"vital", "contextual", "long"}
    for layer in ("vital", "contextual", "long"):
        assert (tmp_path / "identite" / layer).is_dir()


def test_create_folder_already_exists_raises(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.create_folder("identite")
    with pytest.raises(ValueError, match="already exists"):
        store.create_folder("identite")


def test_write_and_read_with_folder(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.create_folder("identite")
    store.write_file("vital", "boussole", "# Boussole", folder="identite")
    assert store.read_file("vital", "boussole", folder="identite") == "# Boussole"
    assert (tmp_path / "identite" / "vital" / "boussole.md").exists()


def test_write_with_folder_creates_dirs_implicitly(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    # No create_folder call — write_file must create dirs on its own
    store.write_file("contextual", "note", "content", folder="projet")
    assert store.read_file("contextual", "note", folder="projet") == "content"


def test_list_files_with_folder(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.write_file("vital", "boussole", "v", folder="identite")
    store.write_file("contextual", "directions", "c", folder="identite")
    store.write_file("vital", "other", "x")  # flat, no folder

    folder_files = store.list_files(folder="identite")
    names = [(f["layer"], f["name"]) for f in folder_files]
    assert ("vital", "boussole.md") in names
    assert ("contextual", "directions.md") in names
    # Flat file must not appear
    assert ("vital", "other.md") not in names
    # folder key present in entries
    assert all(f["folder"] == "identite" for f in folder_files)


def test_list_files_folder_missing_layer_skipped(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.write_file("vital", "boussole", "v", folder="identite")
    # contextual and long sub-dirs of identite don't exist — should not raise
    result = store.list_files(folder="identite")
    assert len(result) == 1


def test_delete_with_folder(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.write_file("vital", "temp", "x", folder="identite")
    store.delete_file("vital", "temp", folder="identite")
    with pytest.raises(FileNotFoundError):
        store.read_file("vital", "temp", folder="identite")


def test_move_with_folders(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.write_file("contextual", "note", "stable", folder="identite")
    store.move_file(
        "contextual",
        "note",
        "long",
        source_folder="identite",
        target_folder="identite",
    )
    assert store.read_file("long", "note", folder="identite") == "stable"
    with pytest.raises(FileNotFoundError):
        store.read_file("contextual", "note", folder="identite")


def test_list_by_circle(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.write_file("vital", "c0", "circle zero", folder="identite")
    store.write_file("contextual", "c1", "circle one", folder="identite")
    store.write_file("long", "c2", "circle two", folder="identite")

    assert store.list_by_circle("identite", 0)[0]["name"] == "c0.md"
    assert store.list_by_circle("identite", 1)[0]["name"] == "c1.md"
    assert store.list_by_circle("identite", 2)[0]["name"] == "c2.md"


def test_list_by_circle_invalid(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    with pytest.raises(ValueError, match="Invalid circle"):
        store.list_by_circle("identite", 3)


def test_summarize_folder_returns_first_line(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.write_file("vital", "boussole", "# Boussole\n\nContenu.", folder="identite")
    result = store.summarize_folder("identite", circle=0)
    assert len(result) == 1
    assert result[0]["first_line"] == "# Boussole"
    assert "content" not in result[0]  # full content must NOT be present


def test_summarize_folder_all_circles(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.write_file("vital", "c0", "# C0", folder="identite")
    store.write_file("long", "c2", "# C2", folder="identite")
    result = store.summarize_folder("identite")
    layers = [r["layer"] for r in result]
    assert "vital" in layers
    assert "long" in layers


# ------------------------------------------------------------------ #
# mount_private / unmount_private tests                              #
# ------------------------------------------------------------------ #


def test_mount_private_missing_key_raises(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    # key file does not exist
    with pytest.raises(FileNotFoundError, match="Private key file not found"):
        store.mount_private()


def test_mount_private_missing_dmg_raises(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    # Create the key file but not the dmg
    store._private_key.write_text("passphrase", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="Encrypted partition not found"):
        store.mount_private()


def test_mount_private_calls_hdiutil(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import subprocess

    store = make_store(tmp_path)
    store._private_key.write_text("secret", encoding="utf-8")
    store._dmg_path.write_text("fake", encoding="utf-8")

    fake_result = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout="image\t/dev/disk9\t/Volumes/private\n",
        stderr="",
    )
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: fake_result)
    result = store.mount_private()
    assert "/Volumes/private" in result


def test_mount_private_hdiutil_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import subprocess

    store = make_store(tmp_path)
    store._private_key.write_text("wrong", encoding="utf-8")
    store._dmg_path.write_text("fake", encoding="utf-8")

    fake_result = subprocess.CompletedProcess(
        args=[],
        returncode=1,
        stdout="",
        stderr="hdiutil: attach failed - Authentication error",
    )
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: fake_result)
    with pytest.raises(RuntimeError, match="hdiutil attach failed"):
        store.mount_private()


def test_unmount_private_calls_hdiutil(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import subprocess

    store = make_store(tmp_path)
    fake_result = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout="",
        stderr="",
    )
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: fake_result)
    result = store.unmount_private()
    assert "unmounted" in result.lower()


def test_unmount_private_hdiutil_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import subprocess

    store = make_store(tmp_path)
    fake_result = subprocess.CompletedProcess(
        args=[],
        returncode=1,
        stdout="",
        stderr="hdiutil: detach failed - not mounted",
    )
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: fake_result)
    with pytest.raises(RuntimeError, match="hdiutil detach failed"):
        store.unmount_private()
