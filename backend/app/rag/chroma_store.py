from __future__ import annotations

from typing import Optional

import chromadb

from ..config import get_settings


COLLECTION_NAME = "lecture_chunks"


class ChromaStore:
    def __init__(self) -> None:
        settings = get_settings()
        self.client = chromadb.PersistentClient(path=settings.chroma_path)
        self.collection = self.client.get_or_create_collection(name=COLLECTION_NAME)

    def upsert_chunks(self, ids: list[str], texts: list[str], embeddings: list[list[float]], metadatas: list[dict]) -> None:
        self.collection.upsert(ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas)

    def query(self, embedding: list[float], lecture_ids: Optional[list[int]] = None, n_results: int = 8) -> list[dict]:
        where = {"lecture_id": {"$in": lecture_ids}} if lecture_ids else None
        result = self.collection.query(
            query_embeddings=[embedding],
            where=where,
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )
        ids = result.get("ids", [[]])[0]
        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        dists = result.get("distances", [[]])[0]
        out = []
        for idx, doc_id in enumerate(ids):
            out.append(
                {
                    "id": doc_id,
                    "document": docs[idx],
                    "metadata": metas[idx],
                    "distance": dists[idx] if idx < len(dists) else None,
                }
            )
        return out

    def count(self) -> int:
        return self.collection.count()

    def delete_lecture(self, lecture_id: int) -> None:
        self.collection.delete(where={"lecture_id": lecture_id})

