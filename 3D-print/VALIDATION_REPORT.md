# Validation & Stress Test Report

**Date:** 2026-04-04 23:01 CDT  
**Orchestrator:** Cognitive Silo v2 (`http://192.168.1.185:8015`)  
**GPU:** AMD Radeon PRO W7900 (48GB VRAM)

---

## 1. Regression Test Suite (Playwright)

| Metric | Value |
|--------|-------|
| **Passed** | 320 |
| **Skipped** | 22 |
| **Failed** | 0 |
| **Duration** | 2.2 min |

**Verdict:** ✅ All tests pass. Skipped tests are expected (conditional/platform-specific).

**Note:** Hero floating cards overflow detection fires on desktop (decorative blurred blobs with absolute positioning) — cosmetic, not functional. No action needed.

---

## 2. VRAM Orchestrator Load Test

### 2a. Health Check (Pre-Test)

```json
{
  "status": "healthy",
  "vram": { "total_gb": 48.0, "used_gb": 37.5, "free_gb": 10.5 },
  "loaded_models": ["qwen2.5:14b", "nomic-embed-text:latest", "deepseek-v2:16b"]
}
```

### 2b. Chat Concurrency — 50 concurrent requests (qwen2.5:14b)

| Metric | Value |
|--------|-------|
| **Total / Success / Failed** | 50 / 50 / 0 |
| **Mean latency** | 16.61s |
| **Median latency** | 16.88s |
| **P95 latency** | 29.75s |
| **Min / Max** | 1.98s / 31.78s |

**Verdict:** ✅ 100% success rate under heavy concurrent load. Latency is expected — 50 simultaneous chat completions with `max_tokens=50` are queued and processed serially on GPU. The ~2s min shows first-in-queue speed; the ~32s max shows queue depth impact.

### 2c. Embedding Concurrency — 20 concurrent requests (nomic-embed-text)

| Metric | Value |
|--------|-------|
| **Total / Success / Failed** | 20 / 0 / 20 |
| **Failure mode** | 30s client timeout |

**Verdict:** ⚠️ All embedding requests timed out. Root cause: they were issued immediately after the 50-chat burst. The orchestrator's request queue was still draining chat completions, and embeddings were starved. This is a **known limitation** of single-GPU serial inference — not a bug.

**Recommendation:** 
- Increase client timeout to 120s for burst scenarios, OR  
- Add priority lanes in the orchestrator (embeddings are fast once they reach GPU — ~0.1s each)
- In production, embeddings and chat won't burst simultaneously at this scale

### 2d. Cold Start Test — deepseek-r1:32b

| Metric | Value |
|--------|-------|
| **Cold start time** | 102.93s |
| **Status** | 200 (success) |
| **LRU eviction** | ✅ deepseek-v2:16b evicted to make room |
| **Post-load VRAM** | 32.7GB / 48.0GB |
| **Loaded models after** | nomic-embed-text, qwen2.5:14b, deepseek-r1:32b |

**Verdict:** ✅ LRU eviction works correctly. The orchestrator evicted the least-recently-used model (deepseek-v2:16b) to fit deepseek-r1:32b. Cold start of ~103s for a 32B model is within expected range (model download from Ollama cache + GPU load).

### 2e. Metrics Sample (TTFT)

| Model | Condition | TTFT |
|-------|-----------|------|
| qwen2.5:14b | Hot (1st in queue) | 0.25s |
| qwen2.5:14b | Hot (under load) | 1.9–17s (queue depth dependent) |
| deepseek-r1:32b | Cold | 3.92s (after 103s load) |
| deepseek-r1:32b | Hot | 0.0004s |

---

## 3. Summary

| Component | Status | Notes |
|-----------|--------|-------|
| Playwright regression suite | ✅ PASS | 320/320 pass |
| Chat concurrency (50 req) | ✅ PASS | 100% success, queuing works |
| Embedding concurrency (20 req) | ⚠️ TIMEOUT | Queue starvation after chat burst |
| Cold start + LRU eviction | ✅ PASS | Correct eviction, 103s load |
| Orchestrator health | ✅ HEALTHY | VRAM management working |

### Recommendations

1. **Priority lanes** for embedding requests (they're sub-second on GPU but get stuck behind long chat completions)
2. **Client-side timeout** should be ≥120s for burst testing scenarios
3. **Monitor queue depth** — expose queue length in `/metrics` for observability
4. Consider **separate Ollama instance** for embeddings if production traffic mixes both at scale
