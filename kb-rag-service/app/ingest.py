import hashlib
import os
from dataclasses import dataclass

import yaml
from qdrant_client import QdrantClient

from .embeddings import embed_texts
from .models import KBDocument, KBChunk
from .qdrant_index import ensure_collection, upsert_chunks


@dataclass
class ParsedDoc:
    title: str
    tags: list[str]
    updated_at: str
    body: str


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_markdown_with_frontmatter(raw: str) -> ParsedDoc:
    raw = raw.lstrip("\ufeff")
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            fm = yaml.safe_load(parts[1]) or {}
            body = parts[2].lstrip("\r\n")
            return ParsedDoc(
                title=str(fm.get("title", "") or ""),
                tags=list(fm.get("tags", []) or []),
                updated_at=str(fm.get("updated_at", "") or ""),
                body=body,
            )
    return ParsedDoc(title="", tags=[], updated_at="", body=raw)


def chunk_markdown(text: str, max_chars: int = 1200) -> list[tuple[str, str]]:
    """
    Very simple chunker: split by headings, then pack into ~max_chars chunks.
    Returns list[(heading, chunk_text)].
    """
    lines = text.splitlines()
    sections: list[tuple[str, list[str]]] = []
    heading = ""
    buf: list[str] = []
    for ln in lines:
        if ln.startswith("#"):
            if buf:
                sections.append((heading, buf))
            heading = ln.lstrip("#").strip()
            buf = []
        else:
            buf.append(ln)
    if buf:
        sections.append((heading, buf))

    chunks: list[tuple[str, str]] = []
    for h, ls in sections:
        block = "\n".join(ls).strip()
        if not block:
            continue
        while len(block) > max_chars:
            cut = block.rfind("\n", 0, max_chars)
            if cut <= 0:
                cut = max_chars
            part = block[:cut].strip()
            if part:
                chunks.append((h, part))
            block = block[cut:].strip()
        if block:
            chunks.append((h, block))
    return chunks


def ingest_kb_dir(source_dir: str, qdrant_url: str, collection: str) -> dict:
    client = QdrantClient(url=qdrant_url)

    md_files = []
    for root, _, files in os.walk(source_dir):
        for f in files:
            if f.lower().endswith(".md"):
                md_files.append(os.path.join(root, f))
    md_files.sort()

    summary = {"documents": 0, "chunks": 0, "skipped": 0}

    # Determine vector size with a single embedding call.
    vector_size = len(embed_texts(["vector_size_probe"])[0])
    ensure_collection(client, collection, vector_size)

    for path in md_files:
        rel = os.path.relpath(path, source_dir).replace("\\", "/")
        raw = open(path, "r", encoding="utf-8").read()
        checksum = _sha256(raw)

        doc, created = KBDocument.objects.get_or_create(source_path=rel)
        if (not created) and doc.checksum == checksum:
            summary["skipped"] += 1
            continue

        parsed = parse_markdown_with_frontmatter(raw)
        doc.title = parsed.title
        doc.tags = parsed.tags
        doc.updated_at = parsed.updated_at
        doc.checksum = checksum
        doc.save()

        # Replace chunks for this document
        KBChunk.objects.filter(document=doc).delete()

        chunks = chunk_markdown(parsed.body)
        texts = [t for _, t in chunks]
        vectors = embed_texts(texts) if texts else []

        points = []
        for idx, ((heading, text), vec) in enumerate(zip(chunks, vectors)):
            ch = KBChunk.objects.create(
                document=doc,
                chunk_index=idx,
                heading=heading,
                text=text,
                token_count=max(1, len(text) // 4),
            )
            payload = {
                "chunk_id": str(ch.id),
                "doc_path": doc.source_path,
                "title": doc.title,
                "heading": heading,
                "tags": doc.tags,
                "updated_at": doc.updated_at,
            }
            points.append((str(ch.id), vec, payload))

        if points:
            upsert_chunks(client, collection, points)

        summary["documents"] += 1
        summary["chunks"] += len(points)

    return summary

