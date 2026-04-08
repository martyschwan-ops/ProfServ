"""
File storage service – handles receipt file naming, moving, and organisation.

Naming convention: YYYY-MM-DD - Vendor Name.ext
Duplicates:        YYYY-MM-DD - Vendor Name (2).ext, (3).ext, ...
Storage:           receipts/<trip-name>/  or  receipts/unassigned/
"""
from __future__ import annotations

import re
import shutil
import uuid
from datetime import date
from pathlib import Path
from typing import Optional

from config import settings

# Characters not allowed in filenames on macOS/Linux/Windows
_UNSAFE_RE = re.compile(r'[\\/:*?"<>|]')
_MULTI_SPACE = re.compile(r"\s+")


def _sanitize(name: str, max_len: int = 60) -> str:
    """Remove unsafe characters and trim whitespace."""
    name = _UNSAFE_RE.sub("", name)
    name = _MULTI_SPACE.sub(" ", name).strip()
    return name[:max_len] if name else "unknown"


def _trip_folder(trip_name: Optional[str]) -> Path:
    if trip_name:
        folder_name = _sanitize(trip_name, max_len=80)
    else:
        folder_name = "unassigned"
    folder = settings.receipts_dir / folder_name
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def build_receipt_filename(expense_date: date, vendor_name: str, extension: str) -> str:
    """Return the canonical receipt filename (without uniqueness suffix)."""
    safe_vendor = _sanitize(vendor_name)
    ext = extension.lstrip(".").lower() if extension else "bin"
    return f"{expense_date.isoformat()} - {safe_vendor}.{ext}"


def unique_filename(folder: Path, base_name: str) -> str:
    """Return a filename that does not already exist in *folder*."""
    target = folder / base_name
    if not target.exists():
        return base_name

    stem, _, suffix = base_name.rpartition(".")
    counter = 2
    while True:
        candidate = f"{stem} ({counter}).{suffix}"
        if not (folder / candidate).exists():
            return candidate
        counter += 1


def store_receipt(
    source_path: Path,
    expense_date: date,
    vendor_name: str,
    trip_name: Optional[str],
) -> tuple[str, str]:
    """
    Move *source_path* into the appropriate receipts folder with the canonical name.

    Returns (file_name, file_path_str).
    """
    folder = _trip_folder(trip_name)
    base_name = build_receipt_filename(expense_date, vendor_name, source_path.suffix)
    final_name = unique_filename(folder, base_name)
    dest = folder / final_name
    shutil.copy2(source_path, dest)
    return final_name, str(dest)


# ── Temporary upload staging ──────────────────────────────────────────────────

def temp_dir() -> Path:
    d = settings.data_dir / "tmp_uploads"
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_temp_upload(filename: str, content: bytes) -> tuple[str, Path]:
    """Save uploaded bytes to a temp file.  Returns (temp_key, path)."""
    key = str(uuid.uuid4())
    suffix = Path(filename).suffix.lower()
    dest = temp_dir() / f"{key}{suffix}"
    dest.write_bytes(content)
    return key, dest


def get_temp_path(temp_key: str) -> Optional[Path]:
    """Locate a temp file by key (looks for any extension)."""
    d = temp_dir()
    for p in d.iterdir():
        if p.stem == temp_key:
            return p
    return None


def delete_temp(temp_key: str) -> None:
    p = get_temp_path(temp_key)
    if p:
        p.unlink(missing_ok=True)
