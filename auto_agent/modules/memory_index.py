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
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

VAULT_DIR = Path(os.environ.get("KAIROS_VAULT_DIR", "/Volumes/kairos/kairos_vault/kairos-vault"))
MEMORY_DIR = VAULT_DIR / "09-memory"
CHROMA_DIR = MEMORY_DIR / ".chroma"

# 3개 컬렉션으로 분리
COLLECTIONS = {
    "memory": {
        "name": "vault_memory",
        "description": "기억 — 세션/결정/패턴 (세션 시작 시 로드)",
        "dirs": [
            MEMORY_DIR / "sessions",
            MEMORY_DIR / "decisions",
            MEMORY_DIR / "patterns",
        ],
    },
    "analysis": {
        "name": "vault_analysis",
        "description": "분석 — 인사이트/피드백/기획안/경쟁분석",
        "dirs": [
            VAULT_DIR / "insights" / "performance",
            VAULT_DIR / "insights" / "feedback",
            VAULT_DIR / "insights" / "planning",
        ],
    },
    "research": {
        "name": "vault_research",
        "description": "리서치 — 채널 영상 데이터/리서치 노트",
        "dirs": [
            VAULT_DIR / "channels" / "semoji" / "videos",
            VAULT_DIR / "channels" / "iromism" / "videos",
            VAULT_DIR / "02-research" / "topics",
        ],
    },
}


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


def build_index(collection_key: str = None):
    """볼트 파일을 chromadb에 벡터 인덱싱. 컬렉션별 또는 전체."""
    try:
        import chromadb
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("chromadb, sentence-transformers 필요: pip install chromadb sentence-transformers")
        sys.exit(1)

    model = SentenceTransformer("all-MiniLM-L6-v2")
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    targets = {collection_key: COLLECTIONS[collection_key]} if collection_key else COLLECTIONS
    total_chunks = 0
    total_files = 0

    for key, cfg in targets.items():
        col_name = cfg["name"]
        try:
            client.delete_collection(col_name)
        except Exception:
            pass
        collection = client.create_collection(name=col_name, metadata={"hnsw:space": "cosine"})

        documents = []
        metadatas = []
        ids = []

        for dir_path in cfg["dirs"]:
            if not dir_path.exists():
                continue
            for md_file in sorted(dir_path.glob("*.md")):
                if md_file.name.startswith("_"):
                    continue
                text = md_file.read_text(encoding="utf-8")
                meta, body = _parse_frontmatter(text)
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
                    "collection": key,
                }

                chunks = _chunk_text(body, max_chars=1000)
                for i, chunk in enumerate(chunks):
                    doc_id = f"{key}_{dir_path.name}_{md_file.stem}_chunk{i}"
                    documents.append(chunk)
                    metadatas.append(doc_meta)
                    ids.append(doc_id)

        if documents:
            embeddings = model.encode(documents).tolist()
            collection.add(documents=documents, embeddings=embeddings, metadatas=metadatas, ids=ids)
            file_count = len(set(m["path"] for m in metadatas))
            print(f"  [{key}] {len(documents)}개 청크 ({file_count}개 파일)")
            total_chunks += len(documents)
            total_files += file_count

    print(f"인덱싱 완료: {total_chunks}개 청크 ({total_files}개 파일) — {len(targets)}개 컬렉션")


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


def search(query: str, top_k: int = 5, collection_key: str = "memory") -> list[dict]:
    """시맨틱 검색. collection_key: memory, analysis, research, all."""
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
    query_embedding = model.encode([query]).tolist()

    # 컬렉션 선택
    if collection_key == "all":
        col_names = [c["name"] for c in COLLECTIONS.values()]
    elif collection_key in COLLECTIONS:
        col_names = [COLLECTIONS[collection_key]["name"]]
    else:
        col_names = [COLLECTIONS["memory"]["name"]]

    # 여러 컬렉션에서 검색 후 병합
    all_results = []
    for col_name in col_names:
        try:
            collection = client.get_collection(col_name)
            results = collection.query(query_embeddings=query_embedding, n_results=top_k)
            for i, doc_id in enumerate(results["ids"][0]):
                all_results.append({
                    "_meta": results["metadatas"][0][i],
                    "_distance": results["distances"][0][i] if results.get("distances") else 0,
                    "_doc": results["documents"][0][i],
                })
        except Exception:
            continue

    # 거리순 정렬
    all_results.sort(key=lambda x: x["_distance"])
    results_proxy = {"ids": [[]], "metadatas": [[]], "distances": [[]], "documents": [[]]}
    for r in all_results[:top_k * 2]:
        results_proxy["ids"][0].append("")
        results_proxy["metadatas"][0].append(r["_meta"])
        results_proxy["distances"][0].append(r["_distance"])
        results_proxy["documents"][0].append(r["_doc"])

    results = results_proxy

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
        col = args[1] if len(args) > 1 else None
        build_index(col)
    elif args[0] == "search" and len(args) > 1:
        # --col memory|analysis|research|all
        col = "memory"
        query_parts = []
        i = 1
        while i < len(args):
            if args[i] == "--col" and i + 1 < len(args):
                col = args[i + 1]
                i += 2
            else:
                query_parts.append(args[i])
                i += 1
        query = " ".join(query_parts)
        results = search(query, collection_key=col)
        for r in results:
            print(f"[{r['distance']:.3f}] {r['title']} ({r['type']}) — {r['snippet'][:100]}")
    elif args[0] == "recall" and len(args) > 1:
        context = " ".join(args[1:])
        print(recall(context))
    else:
        print("Usage:")
        print("  build [memory|analysis|research]  — 인덱스 빌드 (전체 또는 특정)")
        print("  search <query> [--col memory|analysis|research|all]")
        print("  recall <context>")
