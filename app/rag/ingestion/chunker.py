"""Chunking with LangChain's recursive text splitter."""

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.domain.models.chunk import Chunk
from app.rag.ingestion.parser import ParsedPage


class Chunker:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200) -> None:
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )

    def chunk_pages(self, pages: list[ParsedPage]) -> list[Chunk]:
        chunks: list[Chunk] = []
        index = 0
        for page in pages:
            parts = self._splitter.split_text(page.content)
            if not parts and page.content.strip():
                parts = [page.content]
            for part in parts:
                if part.strip():
                    chunks.append(
                        Chunk(
                            content=part,
                            chunk_index=index,
                            start_page=page.page,
                            end_page=page.page,
                        )
                    )
                    index += 1
        return chunks
