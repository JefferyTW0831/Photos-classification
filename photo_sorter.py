"""
Photo classification utility.

Scans the directory where this script resides (recursively) for files that
match one of the supported photo naming conventions and moves them into
``元修檔案/照片/<日期>`` folders that live alongside this script.
"""

from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path
from typing import Iterator

ROOT_FOLDER_NAME = "元修檔案"
PHOTOS_FOLDER_NAME = "照片"
MONTH_NAMES = [
    "一月",
    "二月",
    "三月",
    "四月",
    "五月",
    "六月",
    "七月",
    "八月",
    "九月",
    "十月",
    "十一月",
    "十二月",
]

# Pattern a: 20241019_111535，可接受額外尾碼
PATTERN_DATE_TIME = re.compile(r"^(?P<date>\d{8})_\d{4,6}.*$")

# Pattern b: Screenshot_20250831_203240_LINE (case insensitive suffix)
PATTERN_SCREENSHOT = re.compile(
    r"^screenshot_(?P<date>\d{8})_\d{4,6}_(?P<tail>.+)$",
    flags=re.IGNORECASE,
)

# Pattern c: VideoCapture_20251028，可接受尾碼
PATTERN_VIDEO_CAPTURE = re.compile(
    r"^videocapture_(?P<date>\d{8}).*$",
    flags=re.IGNORECASE,
)

DATE_FOLDER_PATTERN = re.compile(r"^(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})$")


def iter_candidate_files(root: Path) -> Iterator[Path]:
    """Yield files (not directories) under ``root`` recursively."""
    for path in root.rglob("*"):
        if path.is_file():
            yield path


def extract_date_from_name(filename: str) -> str | None:
    """Return YYYYMMDD date string if filename matches supported patterns."""
    stem = Path(filename).stem
    for pattern in (PATTERN_DATE_TIME, PATTERN_SCREENSHOT, PATTERN_VIDEO_CAPTURE):
        match = pattern.match(stem)
        if match:
            return match.group("date")
    return None


def move_file(src: Path, dest_dir: Path) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    destination = dest_dir / src.name

    if destination.exists():
        duplicate = 1
        while True:
            candidate = destination.with_stem(f"{destination.stem}_{duplicate}")
            if not candidate.exists():
                destination = candidate
                break
            duplicate += 1

    shutil.move(str(src), destination)


def classify_photos(search_root: Path, destination_root: Path) -> tuple[int, int]:
    moved = skipped = 0
    for file_path in iter_candidate_files(search_root):
        date_str = extract_date_from_name(file_path.name)
        if not date_str:
            skipped += 1
            continue

        dest_dir = destination_root / date_str

        try:
            if file_path.resolve().parent == dest_dir.resolve():
                skipped += 1
                continue
        except FileNotFoundError:
            skipped += 1
            continue

        move_file(file_path, dest_dir)
        moved += 1

    return moved, skipped


def move_date_folder_to_month(folder: Path, month_root: Path, month_name: str) -> None:
    month_dir = month_root / month_name
    month_dir.mkdir(parents=True, exist_ok=True)
    destination = month_dir / folder.name
    if destination.exists():
        duplicate = 1
        while True:
            candidate = month_dir / f"{folder.name}_{duplicate}"
            if not candidate.exists():
                destination = candidate
                break
            duplicate += 1
    shutil.move(str(folder), destination)


def group_date_folders_by_month(photos_root: Path) -> int:
    moved = 0
    entries = list(photos_root.iterdir())
    for entry in entries:
        if not entry.is_dir():
            continue
        match = DATE_FOLDER_PATTERN.match(entry.name)
        if not match:
            continue
        year = match.group("year")
        month_index = int(match.group("month")) - 1
        if month_index < 0 or month_index >= len(MONTH_NAMES):
            continue
        month_dir_name = f"{year}_{MONTH_NAMES[month_index]}"
        if entry.parent.name == month_dir_name:
            continue
        move_date_folder_to_month(entry, photos_root, month_dir_name)
        moved += 1
    return moved


def resolve_app_dir() -> Path:
    """Return the folder where this script/executable resides."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def main() -> None:
    app_dir = resolve_app_dir()
    os.chdir(app_dir)
    print(f"目前工作目錄：{app_dir}")
    root_folder = app_dir / ROOT_FOLDER_NAME
    photos_folder = root_folder / PHOTOS_FOLDER_NAME

    if not root_folder.exists():
        raise RuntimeError(f"找不到資料夾：{root_folder}")

    photos_folder.mkdir(parents=True, exist_ok=True)

    moved, skipped = classify_photos(app_dir, photos_folder)
    month_moves = group_date_folders_by_month(photos_folder)
    print(f"搬移完成：{moved} 檔案")
    print(f"忽略：{skipped} 檔案（不符合命名或已在目的地）")
    print(f"月份分類：{month_moves} 個日期資料夾")


if __name__ == "__main__":
    main()

