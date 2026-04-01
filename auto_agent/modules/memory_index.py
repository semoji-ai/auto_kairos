"""볼트 기억 시스템 — 벡터 인덱싱 + 시맨틱 검색 + 위키링크.

볼트 09-memory/ 및 insights/ 파일을 chromadb로 벡터화하여
세션 시작 시 관련 기억을 시맨틱 검색으로 로드.

사용법:
  # 인덱스 빌드 (전체)
  python -m auto_agent.modules.memory_index build

  # 검색
  python -m auto_agent.modules.memory_index search "래칫 리뷰 시스템"

  # 세션 시작 시 자동 로드
  python -m auto_agent.modules.memory_index recall --context "Stage 3 에이전트 모드"
"""
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

VAULT_DIR = Path(os.environ.get("KAIROS_VAULT_DIR", "/Volumes/kairos/kairos_vault/kairos-vault"))
MEMORY_DIR = VAULT_DIR / "09-memory"
CHROMA_DIR = MEMORY_DIR / ".chroma"

# 인덱싱 대상 디렉토리
INDEX_DIRS = [
    MEMORY_DIR / "sessions",
    MEMORY_DIR / "decisions",
    MEMORY_DIR / "patterns",
    VAULT_DIR / "insights" / "performance",
    VAULT_DIR / "insights" / "feedback",
    VAULT_DIR / "insights" / "planning",
    VAULT_DIR / "channels" / "semoji" / "videos",
    VAULT_DIR / "channels" / "iromism" / "videos",
]


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """YAML 프론트매터 파싱."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("---", 3)
    if end == -1:
        return {}, text
    fm_text = text[3:end].strip()
    body = text[end + 3:].strip()
    meta = {}
    for line in fm_text.split("\n"):
        if ":" in line:
            key, val = line.split(":", 1)
            meta[key.strip()] = val.strip().strip('"').strip("'")
    return meta, body


def _extract_wikilinks(text: str) -> list[str]:
    """위키링크 추출."""
    return re.findall(r'\[\[([^\]]+)\]\]', text)


def build_index():
    """볼트 기억 파일 전체를 chromadb에 벡터 인덱싱."""
    try:
        import chromadb
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("chromadb, sentence-transformers 필요: pip install chromadb sentence-transformers")
        sys.exit(1)

    model = SentenceTransformer("all-MiniLM-L6-v2")
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    # 기존 컬렉션 삭제 후 재생성
    try:
        client.delete_collection("vault_memory")
    except Exception:
        pass
    collection = client.create_collection(
        name="vault_memory",
        metadata={"hnsw:space": "cosine"},
    )

    documents = []
    metadatas = []
    ids = []

    for dir_path in INDEX_DIRS:
        if not dir_path.exists():
            continue
        for md_file in sorted(dir_path.glob("*.md")):
            if md_file.name.startswith("_"):
                continue
            text = md_file.read_text(encoding="utf-8")
            meta, body = _parse_frontmatter(text)

            # 위키링크 추출
            wikilinks = _extract_wikilinks(body)

            doc_meta = {
                "path": str(md_file),
                "title": meta.get("title", md_file.stem),
                "type": meta.get("type", "unknown"),
                "created": meta.get("created", ""),
                "tags": meta.get("tags", ""),
                "channel": meta.get("channel", ""),
                "wikilinks": ",".join(wikilinks) if wikilinks else "",
                "dir": dir_path.name,
            }

            # 본문을 청크로 분할 (1000자 단위)
            chunks = _chunk_text(body, max_chars=1000)
            for i, chunk in enumerate(chunks):
                doc_id = f"{dir_path.name}_{md_file.stem}_chunk{i}"
                documents.append(chunk)
                metadatas.append(doc_meta)
                ids.append(doc_id)

    if documents:
        # 배치 임베딩
        embeddings = model.encode(documents).tolist()
        collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
        )
        print(f"인덱싱 완료: {len(documents)}개 청크 ({len(set(m['path'] for m in metadatas))}개 파일)")
    else:
        print("인덱싱할 파일 없음")


def _chunk_text(text: str, max_chars: int = 1000) -> list[str]:
    """텍스트를 의미 단위로 분할."""
    sections = re.split(r'\n##+ ', text)
    chunks = []
    current = ""
    for section in sections:
        if len(current) + len(section) > max_chars and current:
            chunks.append(current.strip())
            current = section
        else:
            current += "\n## " + section if current else section
    if current.strip():
        chunks.append(current.strip())
    return chunks if chunks else [text[:max_chars]]


def search(query: str, top_k: int = 5) -> list[dict]:
    """시맨틱 검색."""
    try:
        import chromadb
        from sentence_transformers import SentenceTransformer
    except ImportError:
        return []

    if not CHROMA_DIR.exists():
        print("인덱스 없음. 먼저 build를 실행하세요.")
        return []

    model = SentenceTransformer("all-MiniLM-L6-v2")
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    try:
        collection = client.get_collection("vault_memory")
    except Exception:
        print("컬렉션 없음. build 먼저 실행.")
        return []

    query_embedding = model.encode([query]).tolist()
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
    )

    output = []
    seen_paths = set()
    for i, doc_id in enumerate(results["ids"][0]):
        meta = results["metadatas"][0][i]
        distance = results["distances"][0][i] if results.get("distances") else 0
        path = meta.get("path", "")

        # 같은 파일의 다른 청크는 스킵
        if path in seen_paths:
            continue
        seen_paths.add(path)

        output.append({
            "title": meta.get("title", ""),
            "type": meta.get("type", ""),
            "path": path,
            "distance": round(distance, 3),
            "snippet": results["documents"][0][i][:200],
            "tags": meta.get("tags", ""),
            "created": meta.get("created", ""),
        })

    return output


def recall(context: str, max_items: int = 5) -> str:
    """세션 시작 시 컨텍스트 기반 기억 로드.

    관련 기억을 마크다운으로 포맷팅하여 반환.
    """
    results = search(context, top_k=max_items)
    if not results:
        return "볼트 기억: 관련 기억 없음 (인덱스 빌드 필요: python -m auto_agent.modules.memory_index build)"

    lines = ["## 볼트 기억 (관련도 순)", ""]
    for r in results:
        lines.append(f"### {r['title']} ({r['type']}, {r['created']})")
        lines.append(f"거리: {r['distance']} | 태그: {r['tags']}")
        lines.append(f"```\n{r['snippet']}\n```")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    args = sys.argv[1:]

    if not args or args[0] == "build":
        build_index()
    elif args[0] == "search" and len(args) > 1:
        query = " ".join(args[1:])
        results = search(query)
        for r in results:
            print(f"[{r['distance']:.3f}] {r['title']} ({r['type']}) — {r['snippet'][:100]}")
    elif args[0] == "recall" and len(args) > 1:
        context = " ".join(args[1:])
        print(recall(context))
    else:
        print("Usage: python -m auto_agent.modules.memory_index [build|search <query>|recall <context>]")
