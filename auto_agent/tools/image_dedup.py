"""
이미지 중복 제거 — URL 수집 + pHash 기반 유사 이미지 필터링.

사용법 (모듈):
    from auto_agent.tools.image_dedup import collect_and_dedup
    unique = collect_and_dedup(image_records)   # image_manifest.jsonl 항목 리스트

사용법 (CLI):
    python3 -m auto_agent.tools.image_dedup --input images.jsonl [--threshold 8]
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import struct
import sys
import zlib
from typing import Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

_UA = "KairosAgent/3.1 (educational video production) Python/urllib"
_THUMB_SIZE = 32  # pHash용 다운샘플 크기


# ---------------------------------------------------------------------------
# 경량 pHash — PIL/numpy 없이 순수 Python 구현
# ---------------------------------------------------------------------------

def _fetch_bytes(url: str, timeout: int = 10) -> Optional[bytes]:
    """이미지 URL → raw bytes. 실패 시 None."""
    try:
        req = Request(url, headers={"User-Agent": _UA})
        with urlopen(req, timeout=timeout) as resp:
            ct = resp.headers.get("Content-Type", "")
            if not ct.startswith("image/"):
                return None
            data = resp.read(512 * 1024)  # 최대 512KB
            return data
    except (URLError, Exception):
        return None


def _decode_png_pixels(data: bytes) -> Optional[list[list[int]]]:
    """PNG → 그레이스케일 픽셀 2D 리스트 (매우 단순, 8bpp RGBA/RGB/Gray만)."""
    try:
        if data[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        # IHDR
        pos = 8
        length = struct.unpack(">I", data[pos:pos+4])[0]
        chunk_type = data[pos+4:pos+8]
        if chunk_type != b"IHDR":
            return None
        width = struct.unpack(">I", data[pos+8:pos+12])[0]
        height = struct.unpack(">I", data[pos+12:pos+16])[0]
        bit_depth = data[pos+16]
        color_type = data[pos+17]
        if bit_depth != 8 or color_type not in (0, 2, 3, 4, 6):
            return None  # 16bit/indexed complex 스킵

        # IDAT 수집
        pos = 8
        idat_chunks: list[bytes] = []
        while pos < len(data) - 12:
            length = struct.unpack(">I", data[pos:pos+4])[0]
            chunk_type = data[pos+4:pos+8]
            chunk_data = data[pos+8:pos+8+length]
            if chunk_type == b"IDAT":
                idat_chunks.append(chunk_data)
            elif chunk_type == b"IEND":
                break
            pos += 12 + length

        raw = zlib.decompress(b"".join(idat_chunks))
        channels = {0: 1, 2: 3, 4: 2, 6: 4}.get(color_type, 3)
        stride = width * channels + 1  # +1 for filter byte

        pixels: list[list[int]] = []
        for row in range(height):
            row_data = raw[row * stride + 1: row * stride + 1 + width * channels]
            gray_row: list[int] = []
            for col in range(width):
                base = col * channels
                if channels == 1:
                    gray_row.append(row_data[base])
                elif channels >= 3:
                    r, g, b = row_data[base], row_data[base+1], row_data[base+2]
                    gray_row.append(int(0.299 * r + 0.587 * g + 0.114 * b))
            pixels.append(gray_row)
        return pixels
    except Exception:
        return None


def _decode_jpeg_gray(data: bytes) -> Optional[list[list[int]]]:
    """JPEG → 그레이스케일 픽셀 (DCT 기반 완전 디코딩은 복잡하므로 SHA 폴백용)."""
    return None  # JPEG는 pHash 대신 SHA-256 폴백 사용


def _resize_bilinear(pixels: list[list[int]], target: int) -> list[list[int]]:
    """최근접 이웃 리샘플 (target x target)."""
    h, w = len(pixels), len(pixels[0])
    out: list[list[int]] = []
    for r in range(target):
        src_r = min(int(r * h / target), h - 1)
        row: list[int] = []
        for c in range(target):
            src_c = min(int(c * w / target), w - 1)
            row.append(pixels[src_r][src_c])
        out.append(row)
    return out


def _phash(pixels: list[list[int]], size: int = 8) -> Optional[int]:
    """Perceptual hash: DCT 근사 (mean-hash 변형, 64bit)."""
    resized = _resize_bilinear(pixels, size * 4)  # 오버샘플 후 평균
    # 8x8 블록 평균
    block: list[int] = []
    for r in range(size):
        for c in range(size):
            total = 0
            for dr in range(4):
                for dc in range(4):
                    total += resized[r*4+dr][c*4+dc]
            block.append(total // 16)
    mean = sum(block) // len(block)
    bits = 0
    for bit in block:
        bits = (bits << 1) | (1 if bit >= mean else 0)
    return bits


def compute_image_hash(url: str) -> Optional[str]:
    """
    URL에서 이미지를 다운로드해 pHash 계산.
    PIL 사용 가능 시: JPEG/PNG/WebP 등 모두 지원.
    PIL 없을 시: PNG는 순수 Python pHash, 그 외는 MD5 폴백.
    반환값: 'phash:{16진수}' 또는 'md5:{32자}' 또는 None(실패).
    """
    data = _fetch_bytes(url)
    if not data:
        return None

    # PIL 우선 (JPEG·PNG·WebP 등 모두 처리)
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(data)).convert("L")  # 그레이스케일
        img = img.resize((_THUMB_SIZE, _THUMB_SIZE), Image.LANCZOS if hasattr(Image, "LANCZOS") else Image.ANTIALIAS)
        pixels_flat = list(img.getdata())
        mean = sum(pixels_flat) // len(pixels_flat)
        bits = 0
        for px in pixels_flat:
            bits = (bits << 1) | (1 if px >= mean else 0)
        return f"phash:{bits:016x}"
    except Exception:
        pass

    # 순수 Python PNG pHash 폴백
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        pixels = _decode_png_pixels(data)
        if pixels and len(pixels) >= 8 and len(pixels[0]) >= 8:
            h = _phash(pixels)
            if h is not None:
                return f"phash:{h:016x}"

    # 최후 폴백: MD5
    return f"md5:{hashlib.md5(data).hexdigest()}"


def hamming_distance(h1: str, h2: str) -> int:
    """두 pHash 간 해밍 거리. 타입 다르면 64 반환."""
    try:
        if not h1.startswith("phash:") or not h2.startswith("phash:"):
            return 0 if h1 == h2 else 64
        a = int(h1[6:], 16)
        b = int(h2[6:], 16)
        xor = a ^ b
        # 비트 카운트
        count = 0
        while xor:
            count += xor & 1
            xor >>= 1
        return count
    except Exception:
        return 64


# ---------------------------------------------------------------------------
# 메인 API
# ---------------------------------------------------------------------------

def collect_and_dedup(
    records: list[dict],
    *,
    hamming_threshold: int = 8,
    url_field: str = "image_url",
    download_hash: bool = True,
    verbose: bool = False,
) -> list[dict]:
    """
    이미지 레코드 리스트에서 중복 제거.

    Parameters
    ----------
    records : list[dict]
        각 항목은 최소한 ``url_field`` 키를 가져야 함.
    hamming_threshold : int
        pHash 해밍 거리 임계값 (이하면 동일 이미지로 판정). 기본 8 (64비트 중 12.5%).
    url_field : str
        이미지 URL 필드명.
    download_hash : bool
        True이면 실제 이미지를 다운로드해 pHash 계산. False이면 URL 문자열 중복만 제거.
    verbose : bool
        진행 상황 stderr 출력.

    Returns
    -------
    list[dict]
        중복 제거된 레코드 리스트. 각 항목에 ``image_hash`` 필드 추가.
    """
    # 1단계: URL 정규화 + 빈 URL 제거
    clean: list[dict] = []
    seen_urls: set[str] = set()
    for rec in records:
        url = (rec.get(url_field) or "").strip()
        if not url or url in seen_urls:
            continue
        # 쿼리스트링 제거한 URL도 중복 체크
        base_url = url.split("?")[0]
        if base_url in seen_urls:
            continue
        seen_urls.add(url)
        seen_urls.add(base_url)
        clean.append({**rec, url_field: url})

    if not download_hash:
        return clean

    # 2단계: pHash 계산 및 시각적 중복 제거
    hashed: list[dict] = []
    hash_list: list[str] = []

    for i, rec in enumerate(clean):
        url = rec[url_field]
        if verbose:
            print(f"  [image_dedup] ({i+1}/{len(clean)}) {url[:80]}", file=sys.stderr)

        img_hash = compute_image_hash(url)
        if img_hash is None:
            # 다운로드 실패 → URL만 보존
            rec = {**rec, "image_hash": None, "hash_failed": True}
            hashed.append(rec)
            hash_list.append("")
            continue

        # 기존 해시들과 비교
        is_dup = False
        for existing_hash in hash_list:
            if not existing_hash:
                continue
            dist = hamming_distance(img_hash, existing_hash)
            if dist <= hamming_threshold:
                is_dup = True
                if verbose:
                    print(f"  [image_dedup] 중복 제거 (hamming={dist}): {url[:60]}", file=sys.stderr)
                break

        if not is_dup:
            hashed.append({**rec, "image_hash": img_hash})
            hash_list.append(img_hash)

    return hashed


def main() -> None:
    parser = argparse.ArgumentParser(description="이미지 중복 제거 — pHash 기반")
    parser.add_argument("--input", required=True, help="입력 JSONL 파일 (image_url 필드 포함)")
    parser.add_argument("--output", default="-", help="출력 JSONL 파일 (기본: stdout)")
    parser.add_argument("--threshold", type=int, default=8, help="pHash 해밍 거리 임계값 (기본 8)")
    parser.add_argument("--url-field", default="image_url", help="URL 필드명 (기본: image_url)")
    parser.add_argument("--no-download", action="store_true", help="다운로드 없이 URL 중복만 제거")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    records: list[dict] = []
    with open(args.input, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    unique = collect_and_dedup(
        records,
        hamming_threshold=args.threshold,
        url_field=args.url_field,
        download_hash=not args.no_download,
        verbose=args.verbose,
    )

    out = sys.stdout if args.output == "-" else open(args.output, "w", encoding="utf-8")
    for rec in unique:
        out.write(json.dumps(rec, ensure_ascii=False) + "\n")
    if args.output != "-":
        out.close()

    print(f"[image_dedup] {len(records)} → {len(unique)}개 (중복 {len(records)-len(unique)}개 제거)", file=sys.stderr)


if __name__ == "__main__":
    main()
