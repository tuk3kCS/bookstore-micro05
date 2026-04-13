import uuid
from django.db import models


class KBDocument(models.Model):
    source_path = models.CharField(max_length=255, unique=True)
    title = models.CharField(max_length=255, blank=True)
    tags = models.JSONField(default=list, blank=True)
    updated_at = models.CharField(max_length=32, blank=True)
    checksum = models.CharField(max_length=64, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    ingested_at = models.DateTimeField(auto_now=True)


class KBChunk(models.Model):
    """
    Chunk text stored in Postgres for citations.
    Vector is stored in Qdrant with point_id.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(KBDocument, on_delete=models.CASCADE)
    chunk_index = models.IntegerField()
    heading = models.CharField(max_length=255, blank=True)
    text = models.TextField()
    token_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("document", "chunk_index")]

