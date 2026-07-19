"""
retriever.py
FAISS 벡터스토어 로드 + 검색 함수 2종.
파트3 retriever.py의 역할(load_vectorstore / get_retriever / re_retrieve_*)을
POC 규모로 축소해 이식한 것이다.

  get_retriever(query, vs, k)        : 1차 검색 (유사도 기반)
  re_retrieve_recall_fn(query, vs)   : 재검색 (k 확대 + MMR 다양성 강화)
"""
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from backend.retrieval.embedder import get_cached_embeddings
from utils.config import load_config
from utils.logger import get_logger

logger = get_logger(__name__)
_vectorstore = None


def load_vectorstore() -> FAISS:
    """저장된 FAISS 인덱스를 로드한다(없으면 안내 예외)."""
    cfg = load_config()
    path = cfg["faiss_index_path"]
    try:
        vs = FAISS.load_local(path, get_cached_embeddings(),
                              allow_dangerous_deserialization=True)
    except Exception as e:
        raise RuntimeError(
            f"FAISS 인덱스를 열 수 없습니다({path}). "
            f"먼저 `python -m backend.retrieval.build_index`를 실행하세요. 원인: {e}"
        )
    logger.info(f"벡터스토어 로드 완료: {path}")
    return vs


def get_vectorstore() -> FAISS:
    """벡터스토어는 로드 비용이 크므로 모듈 레벨에서 1회만 로드해 재사용한다."""
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = load_vectorstore()
    return _vectorstore


def get_retriever(query: str, vectorstore: FAISS = None, k: int = None) -> list[Document]:
    """
    1차 검색: 유사도 상위 k개 청크를 회수하고 score를 metadata에 부착한다.

    Returns:
        list[Document] (metadata에 score 포함)
    """
    cfg = load_config()
    k = k or cfg["top_k"]
    vs = vectorstore or get_vectorstore()
    pairs = vs.similarity_search_with_score(query, k=k)
    docs = []
    for d, score in pairs:
        d.metadata["score"] = float(score)
        docs.append(d)
    logger.info(f"1차 검색 k={k} → {len(docs)}청크")
    return docs


def re_retrieve_recall_fn(query: str, vectorstore: FAISS = None) -> list[Document]:
    """
    재검색(recall 확대): k를 늘리고 MMR로 다양성을 키워 1차와 다른 청크를 끌어온다.
    1차가 부실했으므로 좁히지 않고 넓히는 전략을 기본으로 둔다(파트3 re_retrieve와 동일 철학).
    """
    cfg = load_config()
    k = cfg["re_retrieve_top_k"]
    vs = vectorstore or get_vectorstore()
    docs = vs.max_marginal_relevance_search(query, k=k, fetch_k=k * 4, lambda_mult=0.4)
    logger.info(f"재검색(recall, MMR) k={k} → {len(docs)}청크")
    return docs
