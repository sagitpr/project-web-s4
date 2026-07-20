# GPU & VRAM Analysis Report — Warungio Marketplace

**Date:** July 20, 2026

---

## 1. GPU Requirements Assessment

| Component | GPU Required | VRAM Required | Notes |
|-----------|-------------|---------------|-------|
| Django web server | ❌ No | 0 MB | Pure CPU workload |
| MariaDB database | ❌ No | 0 MB | CPU + RAM only |
| Redis cache | ❌ No | 0 MB | In-memory only |
| Celery worker | ❌ No | 0 MB | Python tasks |
| Nginx proxy | ❌ No | 0 MB | Static/dynamic proxy |
| **AI - Gemini API** | ❌ No | 0 MB | **API calls — inference on Google servers** |

## 2. Gemini API Inference Location

All AI features use the **Google Gemini API** as a hosted service — inference runs on Google Cloud TPUs/GPUs, NOT on the local server.

| Feature | API Called | Local GPU? | Server Load |
|---------|-----------|-----------|-------------|
| Text generation | `generativelanguage.googleapis.com` | ❌ | Network I/O only |
| Vision analysis | `generativelanguage.googleapis.com` | ❌ | Network I/O only |
| Content generation | `generativelanguage.googleapis.com` | ❌ | Network I/O only |

## 3. Local Machine Learning Elimination

The project has **no local ML model inference**. All AI/ML workloads are offloaded to external APIs:

- ❌ No TensorFlow/PyTorch models loaded locally
- ❌ No ONNX runtime
- ❌ No local LLM inference (would require 8-24 GB VRAM)
- ❌ No custom ML training pipelines
- ✅ All AI is REST API calls to Google Gemini

## 4. VRAM Requirements

| Scenario | VRAM | Notes |
|----------|------|-------|
| Current setup | **0 MB** | No GPU needed |
| If adding local Whisper (STT) | 1-2 GB | Optional feature |
| If adding local YOLO (detection) | 2-4 GB | Optional feature |
| If adding local LLM (7B params) | 8-16 GB | Not recommended for 1GB VPS |
| If adding local embedding model | 1-2 GB | Optional for RAG |

## 5. Recommendation

**No GPU is required for the current Warungio architecture.**

All AI inference happens on Google's Gemini infrastructure. The local server only needs:
- Standard CPU: 1-2 cores (burst to 3)
- Standard RAM: 256-512 MB for Django

If future features require local ML (offline OCR, embeddings), budget an additional **2-4 GB VRAM** for a lightweight GPU.
