from qdrant_client import QdrantClient
from qdrant_client.http import models as qm


def ensure_collection(client: QdrantClient, collection: str, vector_size: int):
    existing = [c.name for c in client.get_collections().collections]
    if collection in existing:
        return
    client.create_collection(
        collection_name=collection,
        vectors_config=qm.VectorParams(size=vector_size, distance=qm.Distance.COSINE),
    )


def upsert_chunks(
    client: QdrantClient,
    collection: str,
    points: list[tuple[str, list[float], dict]],
):
    qpoints = [
        qm.PointStruct(id=pid, vector=vec, payload=payload)
        for pid, vec, payload in points
    ]
    client.upsert(collection_name=collection, points=qpoints)


def search(
    client: QdrantClient,
    collection: str,
    query_vector: list[float],
    limit: int,
):
    # qdrant-client API changed: use query_points for vector search.
    return client.query_points(
        collection_name=collection,
        query=query_vector,
        limit=limit,
        with_payload=True,
        with_vectors=False,
    )

