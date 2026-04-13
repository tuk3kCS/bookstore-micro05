# Kubernetes manifests (dev/prod skeleton)

This folder contains baseline Kubernetes manifests for the new AI services:
- behavior-analytics-service
- kb-rag-service (+ Qdrant)
- chat-advisor-service

Secrets:
- `LLM_API_KEY` should be stored in a Kubernetes Secret and injected as env vars.

