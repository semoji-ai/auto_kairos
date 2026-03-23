"""
대시보드 Vault RAG 검색 API.

Routes:
    GET /api/vault/search?q=쿼리&top_k=5&folder=01-patterns
    GET /api/vault/stats
"""
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

router = APIRouter(tags=["vault"])


@router.get("/api/vault/search")
async def vault_search(
    q: str = Query(..., min_length=1),
    top_k: int = Query(5, ge=1, le=20),
    folder: str = Query(None),
    channel: str = Query(None),
):
    """볼트 시맨틱 검색 API. channel: "이로미즘" | "세모지" | None(전체)"""
    try:
        from auto_agent.orchestrator.vault_rag import VaultRAG
        rag = VaultRAG()
        if not rag.enabled:
            return JSONResponse({"results": [], "query": q, "total": 0, "mode": "disabled"})

        results = rag.semantic_search(q, top_k=top_k, folder_filter=folder, channel=channel or None)
        mode = "keyword" if all(r["score"] == 0.0 for r in results) else "semantic"
        return {"results": results, "query": q, "total": len(results), "mode": mode}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/api/vault/stats")
async def vault_stats():
    """볼트 인덱스 통계."""
    try:
        from auto_agent.orchestrator.vault_indexer import VaultIndexer
        return VaultIndexer().get_stats()
    except ImportError:
        return {"error": "RAG 미설치", "chunk_count": 0, "file_count": 0}
