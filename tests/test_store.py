"""Unit tests for palimpsest.store.MemoryStore."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from palimpsest.config import Config
from palimpsest.store import MemoryStore


def make_store(tmp_path: Path, private_mount: Path | None = None) -> MemoryStore:
    """Build a MemoryStore backed by a temporary directory.

    Parameters
    ----------
    tmp_path : Path
        Pytest-provided temporary directory used as the public memory root.
    private_mount : Path or None
        Optional path to use as a fake private partition mount point.
        Defaults to a ``private_mount/`` subdirectory of ``tmp_path``
        (not created — tests create it when needed).

    Returns
    -------
    MemoryStore
    """
    config = Config(
        memory_dir=tmp_path / "memory",
        dmg_path=tmp_path / "private.dmg",
        private_key=tmp_path / ".private_key",
        private_mount=private_mount or (tmp_path / "private_mount"),
    )
    (tmp_path / "memory").mkdir(exist_ok=True)
    return MemoryStore(config)


# ------------------------------------------------------------------ #
# Folder management                                                  #
# ------------------------------------------------------------------ #


def test_create_folder(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    result = store.create_folder("identite")
    assert "level_0" in result
    assert (tmp_path / "memory" / "identite" / "level_0").is_dir()


def test_create_folder_already_exists_raises(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.create_folder("identite")
    with pytest.raises(ValueError, match="already has a level_0"):
        store.create_folder("identite")


def test_list_folders_empty(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    assert store.list_folders() == []


def test_list_folders_returns_only_level_dirs(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.create_folder("identite")
    store.create_folder("projet")
    # Create a legacy-style directory without level_ subdirs
    (tmp_path / "memory" / "vital").mkdir()
    folders = store.list_folders()
    assert "identite" in folders
    assert "projet" in folders
    assert "vital" not in folders


def test_list_folders_ignores_legacy(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    for legacy in ("vital", "contextual", "long"):
        (tmp_path / "memory" / legacy).mkdir()
    assert store.list_folders() == []


# ------------------------------------------------------------------ #
# Level management                                                   #
# ------------------------------------------------------------------ #


def test_create_level(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    result = store.create_level("identite", 2)
    assert (tmp_path / "memory" / "identite" / "level_2").is_dir()
    assert "level_2" in result


def test_create_level_already_exists_raises(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.create_level("identite", 1)
    with pytest.raises(ValueError, match="already exists"):
        store.create_level("identite", 1)


def test_list_levels_empty(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    assert store.list_levels("identite") == []


def test_list_levels_after_create_folder(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.create_folder("identite")
    assert store.list_levels("identite") == [0]


def test_list_levels_after_writes(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.create_folder("identite")
    store.create_level("identite", 2)
    store.write_file("identite", 0, "a", "content")
    store.write_file("identite", 2, "b", "content")
    assert store.list_levels("identite") == [0, 2]


# ------------------------------------------------------------------ #
# File operations — happy path                                       #
# ------------------------------------------------------------------ #


def test_write_and_read(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.create_folder("identite")
    content = "# Identity\n\nCore values."
    store.write_file("identite", 0, "boussole", content)
    assert store.read_file("identite", 0, "boussole") == content


def test_write_creates_md_extension(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.create_folder("identite")
    store.write_file("identite", 0, "boussole", "hello")
    assert (tmp_path / "memory" / "identite" / "level_0" / "boussole.md").exists()


def test_write_without_level_dir_raises(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    # Level directory does not exist — must raise
    with pytest.raises(FileNotFoundError, match="create_level"):
        store.write_file("projet", 1, "notes", "content")


def test_write_after_create_level(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.create_level("projet", 1)
    store.write_file("projet", 1, "notes", "content")
    assert (tmp_path / "memory" / "projet" / "level_1" / "notes.md").exists()


def test_name_with_extension(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.create_folder("identite")
    store.write_file("identite", 0, "boussole.md", "data")
    assert store.read_file("identite", 0, "boussole.md") == "data"


def test_list_files_all(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.create_folder("identite")
    store.create_level("projet", 1)
    store.write_file("identite", 0, "a", "x")
    store.write_file("projet", 1, "b", "y")
    files = store.list_files()
    folders = {f["folder"] for f in files}
    assert "identite" in folders
    assert "projet" in folders


def test_list_files_by_folder(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.create_folder("identite")
    store.create_folder("projet")
    store.write_file("identite", 0, "a", "x")
    store.write_file("projet", 0, "b", "y")
    files = store.list_files(folder="identite")
    assert all(f["folder"] == "identite" for f in files)
    assert len(files) == 1


def test_list_files_by_level(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.create_folder("identite")
    store.create_level("identite", 2)
    store.write_file("identite", 0, "a", "x")
    store.write_file("identite", 2, "b", "y")
    files = store.list_files(folder="identite", level=0)
    assert len(files) == 1
    assert files[0]["level"] == 0


def test_list_files_returns_correct_keys(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.create_folder("identite")
    store.write_file("identite", 0, "a", "hello")
    files = store.list_files()
    assert set(files[0].keys()) == {"folder", "level", "name", "size_bytes"}


def test_list_files_returns_size(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.create_folder("identite")
    content = "hello"
    store.write_file("identite", 0, "a", content)
    files = store.list_files()
    assert files[0]["size_bytes"] == len(content.encode())


def test_delete(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.create_folder("identite")
    store.write_file("identite", 0, "temp", "x")
    store.delete_file("identite", 0, "temp")
    with pytest.raises(FileNotFoundError):
        store.read_file("identite", 0, "temp")


def test_move_between_levels(tmp_path: Path) -> None:
    # move_file creates the target level dir implicitly (intentional act)
    store = make_store(tmp_path)
    store.create_folder("identite")
    store.write_file("identite", 0, "note", "stable")
    store.move_file("identite", 0, "note", "identite", 2)
    assert store.read_file("identite", 2, "note") == "stable"
    with pytest.raises(FileNotFoundError):
        store.read_file("identite", 0, "note")


def test_move_between_folders(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.create_folder("identite")
    store.write_file("identite", 0, "note", "content")
    store.move_file("identite", 0, "note", "projet", 0)
    assert store.read_file("projet", 0, "note") == "content"
    with pytest.raises(FileNotFoundError):
        store.read_file("identite", 0, "note")


def test_move_overwrites_existing(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.create_folder("identite")
    store.create_level("identite", 2)
    store.write_file("identite", 0, "note", "new")
    store.write_file("identite", 2, "note", "old")
    store.move_file("identite", 0, "note", "identite", 2)
    assert store.read_file("identite", 2, "note") == "new"


# ------------------------------------------------------------------ #
# Error cases                                                        #
# ------------------------------------------------------------------ #


def test_read_missing_file_raises(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    with pytest.raises(FileNotFoundError):
        store.read_file("identite", 0, "does_not_exist")


def test_delete_missing_file_raises(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    with pytest.raises(FileNotFoundError):
        store.delete_file("identite", 0, "does_not_exist")


def test_move_missing_file_raises(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    with pytest.raises(FileNotFoundError):
        store.move_file("identite", 0, "does_not_exist", "identite", 1)


# ------------------------------------------------------------------ #
# summarize_folder                                                   #
# ------------------------------------------------------------------ #


def test_summarize_folder_returns_first_line(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.create_folder("identite")
    store.write_file("identite", 0, "boussole", "# Boussole\n\nContenu complet.")
    result = store.summarize_folder("identite", level=0)
    assert len(result) == 1
    assert result[0]["first_line"] == "# Boussole"
    assert "content" not in result[0]


def test_summarize_folder_skips_empty_lines(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.create_folder("identite")
    store.write_file("identite", 0, "note", "\n\n# Titre")
    result = store.summarize_folder("identite")
    assert result[0]["first_line"] == "# Titre"


def test_summarize_folder_all_levels(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.create_folder("identite")
    store.create_level("identite", 2)
    store.write_file("identite", 0, "a", "# A")
    store.write_file("identite", 2, "b", "# B")
    result = store.summarize_folder("identite")
    levels = {r["level"] for r in result}
    assert levels == {0, 2}


def test_summarize_folder_filtered_level(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.create_folder("identite")
    store.create_level("identite", 2)
    store.write_file("identite", 0, "a", "# A")
    store.write_file("identite", 2, "b", "# B")
    result = store.summarize_folder("identite", level=0)
    assert len(result) == 1
    assert result[0]["level"] == 0


# ------------------------------------------------------------------ #
# Private partition                                                  #
# ------------------------------------------------------------------ #


def test_private_not_mounted_raises(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    # private_mount does not exist
    with pytest.raises(RuntimeError, match="not mounted"):
        store.read_file("identite", 0, "boussole", private=True)


def test_private_operations(tmp_path: Path) -> None:
    fake_mount = tmp_path / "private_mount"
    fake_mount.mkdir()
    store = make_store(tmp_path, private_mount=fake_mount)

    store.create_folder("identite", private=True)
    store.write_file("identite", 0, "secret", "private content", private=True)
    assert store.read_file("identite", 0, "secret", private=True) == "private content"
    assert (fake_mount / "identite" / "level_0" / "secret.md").exists()


def test_list_folders_private(tmp_path: Path) -> None:
    fake_mount = tmp_path / "private_mount"
    fake_mount.mkdir()
    store = make_store(tmp_path, private_mount=fake_mount)

    store.create_folder("identite", private=True)
    store.write_file("identite", 0, "a", "x", private=True)
    assert store.list_folders(private=True) == ["identite"]
    assert store.list_folders(private=False) == []


def test_move_between_partitions(tmp_path: Path) -> None:
    fake_mount = tmp_path / "private_mount"
    fake_mount.mkdir()
    store = make_store(tmp_path, private_mount=fake_mount)

    store.create_folder("identite")
    store.write_file("identite", 0, "note", "public", private=False)
    store.move_file(
        "identite",
        0,
        "note",
        "identite",
        0,
        src_private=False,
        tgt_private=True,
    )
    assert store.read_file("identite", 0, "note", private=True) == "public"
    with pytest.raises(FileNotFoundError):
        store.read_file("identite", 0, "note", private=False)


def test_summarize_folder_private(tmp_path: Path) -> None:
    fake_mount = tmp_path / "private_mount"
    fake_mount.mkdir()
    store = make_store(tmp_path, private_mount=fake_mount)

    store.create_folder("identite", private=True)
    store.write_file("identite", 0, "secret", "# Secret\nContenu.", private=True)
    result = store.summarize_folder("identite", private=True)
    assert len(result) == 1
    assert result[0]["first_line"] == "# Secret"


# ------------------------------------------------------------------ #
# mount_private / unmount_private                                    #
# ------------------------------------------------------------------ #


def test_mount_private_missing_key_raises(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    with pytest.raises(FileNotFoundError, match="Private key file not found"):
        store.mount_private()


def test_mount_private_missing_dmg_raises(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store._private_key.write_text("passphrase", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="Encrypted partition not found"):
        store.mount_private()


def test_mount_private_calls_hdiutil(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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
    store = make_store(tmp_path)
    fake_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: fake_result)
    result = store.unmount_private()
    assert "unmounted" in result.lower()


def test_unmount_private_hdiutil_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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
