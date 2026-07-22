"""
build_index.py
data/corpus/*.md(광고규제 코퍼스)를 읽어 FAISS 인덱스를 빌드한다.
POC 1일차에 한 번만 실행하면 되고, 코퍼스를 고치면 다시 돌린다.

실행: (루트에서) python -m backend.retrieval.build_index

* Cluade AI 도구 활용
참고: https://claude.ai/chat/2c772191-67e4-42ad-bfab-2bbb9971216b
"""
import os
import glob
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS

from backend.retrieval.embedder import get_cached_embeddings
from utils.config import load_config
from utils.logger import get_logger

logger = get_logger(__name__)


def load_corpus(corpus_dir: str) -> list[Document]:
    """
    코퍼스 폴더의 .md/.txt를 Document로 읽는다.
    파일명을 source 메타로 남겨 답변의 출처 표기에 쓴다.
    """
    docs = []
    paths = sorted(glob.glob(os.path.join(corpus_dir, "*.md")) +
                   glob.glob(os.path.join(corpus_dir, "*.txt")))
    for p in paths:
        with open(p, encoding="utf-8") as f:          # 한글 → 반드시 utf-8
            text = f.read()
        docs.append(Document(page_content=text, metadata={"source": os.path.basename(p)}))
    logger.info(f"코퍼스 파일 {len(docs)}건 로드: {corpus_dir}")
    if not docs:
        logger.warning("코퍼스가 비어 있습니다. data/corpus에 .md 파일을 넣으세요.")
    return docs


def split_docs(docs: list[Document]) -> list[Document]:
    """문단 → 문장 → 문자 순으로 청크 분할(강의자료 RecursiveCharacterTextSplitter 방식)."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,      # 규제 조항은 짧아 500자면 조항 단위가 잘 유지됨
        chunk_overlap=80,
        length_function=len,
    )
    chunks = splitter.split_documents(docs)
    logger.info(f"청크 분할 완료: {len(chunks)}개")
    return chunks


def build():
    """코퍼스 → 청크 → FAISS 인덱스 저장."""
    cfg = load_config()
    docs = load_corpus(cfg["corpus_path"])
    if not docs:
        raise RuntimeError(f"코퍼스가 비어 있습니다: {cfg['corpus_path']}")
    chunks = split_docs(docs)
    vs = FAISS.from_documents(chunks, get_cached_embeddings())
    index_path = cfg["faiss_index_path"]          # config.py가 절대 경로로 변환해 둠
    os.makedirs(index_path, exist_ok=True)
    vs.save_local(index_path)
    # 절대 경로를 찍어 둔다: 서버가 다른 위치를 보는 사고를 로그만으로 판별하기 위함
    logger.info(f"FAISS 인덱스 저장 완료: {index_path} ({len(chunks)}청크)")
    return vs


if __name__ == "__main__":
    build()
