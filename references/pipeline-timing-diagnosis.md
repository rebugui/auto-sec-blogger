# Pipeline Timing Diagnosis (2026-06-01)

## Symptom
Cron job `auto-sec-blogger` (be514a679a1b) timed out every day since May 16.
Cron output files were 228 bytes: "Script timed out after 600s."

## Root Cause Analysis

### Step 1: Check cron job state
```bash
cronjob action=list
# → last_status: "error"
```

### Step 2: Check cron output
```
~/.hermes/cron/output/be514a679a1b/2026-06-01_08-11-18.md
# → "Script timed out after 600s"
```

### Step 3: Check skill logs
Logs live at: `~/.hermes/skills/openclaw-imports/auto-sec-blogger/logs/`
Files: pipeline.log, collector.log, selector.log, writer.log, llm_client_async.log

### Step 4: Trace timing per step (from actual test run)

Before fix (max_results_per_source=15, max_articles=2):
| Step | Time | LLM calls | Notes |
|------|------|-----------|-------|
| Collector | 8s | 0 | 79 articles from 5 sources |
| Selector | 222s (3.7m) | ~5 | 1 LLM call per category |
| Writer | 180s+ (partial) | 4 of 10 | Timed out mid-generation |
| **Total** | **>600s** | **~9** | **Timed out** |

After fix (max_results_per_source=8, max_articles=3):
| Step | Time | LLM calls | Notes |
|------|------|-----------|-------|
| Collector | 8s | 0 | ~40 articles |
| Selector | ~120s | 3-4 | Categories = LLM calls |
| Writer | ~240s | 6 | 3 × (metadata + content) |
| **Total** | **~370-400s** | **9-10** | **Within 600s** |

### Key Insights

1. **Ollama 8B (Gemma4:e4b)**: Each LLM call takes **30-40 seconds** consistently. Not 10-30s.
2. **Selector scales with categories, not articles**: 1 LLM call per unique category. 79 articles → 5 categories → 5 calls. 18 articles → 4 categories → 4 calls.
3. **Writer calls per article**: 2 LLM calls (metadata + content). For `--max-articles N`, that's 2N calls.
4. **Total LLM call estimate**: `categories + (2 × max_articles)` = 4 + 6 = 10 calls × 35s = 350s + overhead + collector = ~390-450s safe.

## Applied Fixes (2026-06-01)

| File | Change | Why |
|------|--------|-----|
| `intelligence_pipeline.py` | `max_results_per_source=15` → `8` | Fewer articles → fewer categories |
| `intelligence_pipeline_resilient.py` | same + `max_results=8` for arXiv/HN | Consistency |
| `llm_client_async.py` | `timeout=300` → `600`, `max_tokens=4000` → `2000` | Prevent content gen timeout; shorter gen |
| `models.py` | `score: int` → `score: float` | Accept LLM float scores (8.5) |
| `run-auto-sec-blogger.sh` | `--max-articles 5` → `3` | Writer 10→6 calls, fits in 600s |
