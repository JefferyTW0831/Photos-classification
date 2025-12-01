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
from datetime import datetime
from pathlib import Path
from typing import Iterator

ROOT_FOLDER_NAME = "元修檔案"
PHOTOS_FOLDER_NAME = "照片"
LOG_FILE_NAME = "photo_sorter.log"

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

class Logger:
    """同時輸出到終端和日誌文件的記錄器"""

    def __init__(self, log_file_path: Path):
        self.log_file_path = log_file_path
        self.log_file = None

    def __enter__(self):
        """開啟日誌文件（追加模式）"""
        self.log_file = open(self.log_file_path, "a", encoding="utf-8")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_file.write(f"\n{'='*60}\n")
        self.log_file.write(f"執行時間：{timestamp}\n")
        self.log_file.write(f"{'='*60}\n")
        self.log_file.flush()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """關閉日誌文件"""
        if self.log_file:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.log_file.write(f"結束時間：{timestamp}\n")
            self.log_file.write(f"{'='*60}\n\n")
            self.log_file.close()

    def log(self, message: str) -> None:
        """同時輸出到終端和日誌文件"""
        # 輸出到終端
        print(message)
        # 輸出到日誌文件（帶時間戳）
        if self.log_file:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.log_file.write(f"[{timestamp}] {message}\n")
            self.log_file.flush()


def iter_candidate_files(root: Path, exclude_path: Path | None = None) -> Iterator[Path]:
    """Yield files (not directories) under ``root`` recursively, excluding subdirectories of exclude_path."""
    for path in root.rglob("*"):
        if path.is_file():
            # 如果指定了排除路徑，且文件在排除路徑的子目錄中（不包括排除路徑本身），則跳過
            if exclude_path:
                try:
                    path_resolved = path.resolve()
                    exclude_resolved = exclude_path.resolve()
                    # 如果文件的父目錄是排除路徑的子目錄（不包括排除路徑本身），則跳過
                    # 這樣可以掃描排除路徑本身，但不掃描其子目錄
                    if path_resolved.parent != exclude_resolved and exclude_resolved in path_resolved.parents:
                        continue
                except (FileNotFoundError, ValueError):
                    pass
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
    
    for file_path in iter_candidate_files(search_root, exclude_path=destination_root):
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


def resolve_app_dir() -> Path:
    """Return the folder where this script/executable resides."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def main() -> None:
    app_dir = resolve_app_dir()
    os.chdir(app_dir)
    log_file_path = app_dir / LOG_FILE_NAME

    # 使用Logger來記錄所有輸出
    with Logger(log_file_path) as logger:
        logger.log(f"目前工作目錄：{app_dir}")
        root_folder = app_dir / ROOT_FOLDER_NAME
        photos_folder = root_folder / PHOTOS_FOLDER_NAME

        if not root_folder.exists():
            error_msg = f"找不到資料夾：{root_folder}"
            logger.log(f"錯誤：{error_msg}")
            raise RuntimeError(error_msg)

        photos_folder.mkdir(parents=True, exist_ok=True)

        moved, skipped = classify_photos(app_dir, photos_folder)
        logger.log(f"搬移完成：{moved} 檔案")
        logger.log(f"忽略：{skipped} 檔案（不符合命名或已在目的地）")


if __name__ == "__main__":
    main()

