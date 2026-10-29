"""스토리보드 카드용 선택 이미지 미리보기. 원본은 읽기만 한다."""
from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

from PIL import Image, ImageOps


def selected_image_preview(images_dir: Path, selected: str, cache_dir: Path,
                           scene_num: int) -> Path:
    """선택된 원본의 960px WebP를 캐시하고 경로를 돌려준다.

    파일 경로·크기·수정 시각이 바뀌면 새 캐시 파일을 만들어 선택 변경을 반영한다.
    기존 원본과 이전 캐시는 삭제하지 않는다.
    """
    images_dir = Path(images_dir).resolve()
    source = (images_dir / selected).resolve()
    if images_dir not in source.parents:
        raise ValueError("이미지 폴더 밖의 파일")
    stat = source.stat()
    key = hashlib.sha256(
        f"{source}:{stat.st_mtime_ns}:{stat.st_size}".encode("utf-8")
    ).hexdigest()[:16]
    cache_dir = Path(cache_dir)
    target = cache_dir / f"selected_{scene_num:03d}_{key}.webp"
    if target.is_file():
        return target

    cache_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as opened:
        image = ImageOps.exif_transpose(opened)
        image.thumbnail((960, 540), Image.Resampling.LANCZOS)
        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
        with tempfile.NamedTemporaryFile(dir=cache_dir, suffix=".webp", delete=False) as tmp:
            temp_path = Path(tmp.name)
        try:
            image.save(temp_path, format="WEBP", quality=82, method=4)
            os.replace(temp_path, target)
        finally:
            if temp_path.exists():
                temp_path.unlink()
    return target
