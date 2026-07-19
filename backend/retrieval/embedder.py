"""
embedder.py
임베딩 모델 로드 및 캐싱. 파트3 embedder_hf.py와 동일한 인터페이스
(get_cached_embeddings)를 유지해, 본 프로젝트에서 bge-m3로 교체할 때
이 파일만 바꾸면 되도록 한다.

POC 기본값: OpenAI text-embedding-3-small
  - 모델 다운로드가 없어 1인·5일 일정에 유리(bge-m3는 2GB+ 다운로드/CPU 추론 느림)
  - 본 프로젝트에서 bge-m3로 갈아끼울 경우 USE_HF=True로 전환

⚠️ FAISS 인덱스는 임베딩 모델에 종속된다. 모델을 바꾸면 인덱스를 반드시 재빌드할 것.
"""
from functools import lru_cache
from utils.config import load_config, get_openai_key

USE_HF = False   # True로 바꾸면 BAAI/bge-m3 사용(본 프로젝트 확장용)


@lru_cache(maxsize=1)
def get_cached_embeddings():
    """임베딩 모델을 1회만 만들어 캐싱 반환한다."""
    cfg = load_config()
    if USE_HF:
        from langchain_huggingface import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(
            model_name="BAAI/bge-m3",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    from langchain_openai import OpenAIEmbeddings
    return OpenAIEmbeddings(model=cfg["embedding_model"], api_key=get_openai_key())
