---
name: auto-sec-blogger
version: 1.2.0
description: "AI-powered security blog automation system (identical to github.com/rebugui/auto-sec-blogger). Collects news from Google News, arXiv, HackerNews → generates blog posts with local Ollama Gemma (gemma4:e4b) → publishes to Notion → auto-deploys to GitHub Pages via Git. Features Human-in-the-Loop approval workflow. Use when you want to automate blog writing, news collection, or content generation with the exact functionality of the original auto-sec-blogger repository. Triggers: 블로그 글 작성, 보안 뉴스 발행, 깃헙 블로그 발행, intelligence agent, 지능형 에이전트, 자동 글쓰기."
---

# Intelligence Agent

## 개요

보안 뉴스를 자동으로 수집하고, LLM(GLM-4.7)을 사용하여 전문가 수준의 블로그 글을 작성한 후, Notion과 GitHub Pages에 자동으로 게시하는 시스템입니다.

**GitHub 저장소와 동일**: https://github.com/rebugui/auto-sec-blogger

## Hermes Cron Integration (Current)

**Platform**: Migrated from OpenClaw to Hermes

### Hermes Cron Registration

Wrapper script: `~/.hermes/scripts/run-auto-sec-blogger.sh`

```bash
#!/bin/bash
# Wrapper: run auto-sec-blogger pipeline
SKILL_DIR="$HOME/.hermes/skills/openclaw-imports/auto-sec-blogger"
set -a                         # ⚠️ MUST use set -a: exports all sourced vars to Python
source "$HOME/.hermes/.skills.env" 2>/dev/null
set +a
cd "$SKILL_DIR"
exec /usr/bin/python3 "$SKILL_DIR/scripts/intelligence_pipeline.py" --max-articles 3
```

**`set -a` is critical.** Without it, `source` makes vars available in bash but does NOT export them to child processes (Python). The pipeline silently fails with "API Key가 설정되지 않았습니다." errors.

**Schedule**: Daily at 08:00 (`0 8 * * *`)
**Register**: `cronjob action=create name="auto-sec-blogger" schedule="0 8 * * *" script="run-auto-sec-blogger.sh" no_agent=true`

### Manual Execution

```bash
SKILL_DIR="$HOME/.hermes/skills/openclaw-imports/auto-sec-blogger"
python3 "$SKILL_DIR/scripts/intelligence_pipeline.py" --max-articles 3
python3 "$SKILL_DIR/scripts/intelligence_pipeline_resilient.py" --max-articles 3
```

### Legacy Pipeline (국내 보안뉴스 중심, security-news-feed 의존)

```bash
SKILL_DIR="$HOME/.hermes/skills/openclaw-imports/auto-sec-blogger"
python3 "$SKILL_DIR/scripts/run_pipeline.py" --full
```

---

## 아키텍처

```
뉴스 수집 (Google News, arXiv, HackerNews, Hada.io)
    ↓
Ollama Gemma4:e4b (local 8B) 기사 선별 + 글 작성
    ↓
Notion Draft 저장 (상태: Draft)
    ↓
사용자 검토 및 승인 (Human-in-the-Loop, Notion 상태 변경)
    ↓
Git Push → GitHub Actions → GitHub Pages
```

## 주요 기능

### 1. 뉴스 수집 (News Collection)
- **Google News**: 키워드 기반 보안 뉴스 수집
- **arXiv**: 최신 보안 연구 논문 수집
- **HackerNews**: 트렌딩 기술 뉴스 수집
- **중복 제거**: URL 기반 중복 뉴스 필터링

### 2. LLM 글쓰기 (Content Generation)
- **모델**: Ollama Gemma4:e4b (local 8B, Q4_K_M)
- **스타일**: 전문 보안 블로그 (멀티 페르소나: 보안, AI, DevOps, CVE 분석가)
- **구조**:
  - 제목 (헤드라인)
  - 요약 (3줄 요약)
  - 본문 (상세 분석)
  - 결론 (시사점)
  - 태그 (키워드)

### 3. Notion 통합 (Notion Integration)
- **상태 관리**: Draft → Review → Approved → Published
- **자동 저장**: 생성된 글 자동 저장
- **사용자 승인**: Notion에서 상태 변경으로 배포 승인

### 4. Git 기반 발행 (Git Publishing)
- **자동 커밋**: 마크다운 파일 Git에 커밋
- **Hugo 빌드**: 정적 블로그용 마크다운 생성
- **GitHub Pages**: 정적 블로그 배포

## LLM Configuration (Current — Ollama Local)

**Model**: Gemma4:e4b (8B, Q4_K_M) via local Ollama
**Base URL**: `http://localhost:11434/v1/`
**API Key**: Not required (Ollama local). Set `INTELLIGENCE_LLM_API_KEY=ollama` for non-empty check.
**Config**: `scripts/config.py` — `GLM_API_KEY = get_env("INTELLIGENCE_LLM_API_KEY") or "ollama"`

### LLM Client Settings (2026-06-01 updated)

| Parameter | Before | After | Reason |
|-----------|--------|-------|--------|
| `timeout` | 300s | 600s | Ollama 8B can take 5+ min for long content |
| `max_tokens` | 4000 | 2000 | Shorter articles = faster generation, stays within timeout |

### Environment Variables

```bash
# ~/.hermes/.skills.env
INTELLIGENCE_LLM_API_KEY=ollama           # Ollama local (any non-empty value works)
INTELLIGENCE_LLM_BASE_URL=http://localhost:11434/v1/
INTELLIGENCE_LLM_MODEL=gemma4:e4b
```

## 사용법

### 1. 전체 파이프라인 실행

```bash
SKILL_DIR="$HOME/.hermes/skills/openclaw-imports/auto-sec-blogger"
python3 "$SKILL_DIR/scripts/intelligence_pipeline.py" --max-articles 3
```

### 2. 뉴스 수집만

```python
from collector import NewsCollector

collector = NewsCollector()
articles = collector.fetch_all(max_results_per_source=8)
```

### 3. 블로그 글 작성만

```python
from writer import BlogWriter

writer = BlogWriter()
post = writer.generate_article(article_data)
```

### 4. Notion 발행만

```python
from notion_publisher import NotionPublisher

publisher = NotionPublisher()
result = publisher.create_article(blog_post)
```

### 5. Git 발행만

```python
from git_publisher_service import GitPublisherService

git_publisher = GitPublisherService()
git_publisher.publish(blog_posts)
```

## 워크플로우 상세

### 1단계: 뉴스 수집

```python
# collector.py
class NewsCollector:
    def fetch_google_news(self, query="security vulnerability"):
        # Google News RSS 피드에서 수집
        pass

    def fetch_arxiv(self, category="cs.CR"):
        # arXiv 보안 논문 수집
        pass

    def fetch_hackernews(self):
        # HackerNews 트렌딩 기사 수집
        pass
```

### 2단계: AI 기사 선별

```python
# selector.py
class ArticleSelector:
    async def evaluate_and_select(self, articles, max_articles=5):
        # GLM-4.7으로 기사 품질 평가
        # 점수 기반 상위 기사 선별
        pass
```

### 3단계: 블로그 글 작성

```python
# writer.py
class BlogWriter:
    async def generate_article(self, article):
        # GLM-4.7으로 블로그 글 작성
        # Mermaid 다이어그램 생성
        # 마크다운 형식 출력
        pass
```

### 4단계: Notion 발행

```python
# notion_publisher.py
class NotionPublisher:
    def create_article(self, blog_post):
        # Notion DB에 Draft 상태로 저장
        # 상태: Draft → Review → Approved
        pass
```

### 5단계: Git 발행 (사용자 승인 후)

```python
# git_publisher_service.py
class GitPublisherService:
    def publish(self, blog_posts):
        # 마크다운 파일 생성
        # Git commit & push
        # GitHub Actions 트리거
        pass
```

## Cron 스케줄링

### 매일 08:30 자동 실행

```python
# intelligence_pipeline.py
from apscheduler.schedulers.blocking import BlockingScheduler

scheduler = BlockingScheduler()
scheduler.add_job(run_pipeline, 'cron', hour=8, minute=30)
scheduler.start()
```

## Notion 데이터베이스 구조

### 필수 속성

| 속성명 | 타입 | 설명 |
|--------|------|------|
| 제목 | title | 블로그 글 제목 |
| 상태 | select | Draft/Review/Approved/Published |
| 날짜 | date | 발행일 |
| 태그 | multi_select | 키워드 |
| URL | url | 원문 URL |
| 카테고리 | select | 취약점/연구/트렌드 |

## Hugo 블로그 구조

```
blog/
├── content/
│   └── post/
│       ├── cve-2025-xxxx-analysis/
│       │   └── index.md
│       ├── ai-security-trends/
│       │   └── index.md
│       └── ...
├── layouts/
│   ├── _default/
│   └── partials/
├── config.toml (or hugo.toml)
└── .github/
    └── workflows/
        └── hugo.yml
```

## Pitfalls

1. **GLM_API_KEY must be non-empty**: Even though Ollama doesn't need auth, the llm_client_async.py raises ValueError if api_key is empty. Set `INTELLIGENCE_LLM_API_KEY=ollama` or ensure config.py default is non-empty.
2. **Cron no_agent timeout**: Default is 120s. auto-sec-blogger pipeline takes ~6-7 min. Set `cron.script_timeout_seconds: 600` in config.yaml.
3. **Ollama inference is slow**: Local 8B Gemma model takes 30-40s PER LLM call, not 10-30s. Pipeline timing budget:
   - Collector: ~10s for 40 articles (max_results_per_source=8)
   - Selector: ~40s per category × 3-4 categories = ~120-160s
   - Writer: ~35-40s per call × 2 calls per article (metadata + content)
   - Total for 3 articles: ~10 + 140 + 240 = ~390s minimum
   - **Never use --max-articles 5 with Ollama local** — exceeds 600s timeout
4. **Pydantic score validation**: `models.py` `EvaluationItem.score` was `int` type but LLM returns floats like 8.5. Changed to `float` — if you revert this, the selector silently drops entire categories.
5. **LLM client timeout**: `llm_client_async.py` timeout was 300s (5min) but Ollama content generation for 4000 tokens can exceed this. Fixed: timeout=600s, max_tokens=2000. If you increase max_tokens back to 4000, also increase timeout.
6. **max_results_per_source**: Setting this too high (was 15, now 8) floods the selector with 79+ articles, creating many categories and LLM calls. Keep at 5-8 for reliable 600s completion.
7. **Diagnosing cron failures**: When pipeline times out, check in order:
   1. `cronjob action=list` — check `last_status`
   2. `~/.hermes/cron/output/<job_id>/<date>.md` — shows script exit/timeout
   3. `skil_dir/logs/pipeline.log` — trace which step failed
   4. `skill_dir/logs/selector.log`, `writer.log`, `llm_client_async.log` — deeper trace
   5. Run manually with wrapper to reproduce: `bash ~/.hermes/scripts/run-auto-sec-blogger.sh`
8. **Python buffering**: When running via cron wrapper, output may buffer. Use `PYTHONUNBUFFERED=1` for real-time log visibility.
9. **`set -a` before sourcing .env in wrapper scripts**: Plain `source .skills.env` without `set -a` loads variables into bash but does NOT export them to child processes. Python scripts see empty env vars. Always use `set -a; source .env; set +a` pattern in wrapper scripts.
10. **selector Pydantic float score**: `models.py` `score` field was `int` type, but Gemma returns floats like `8.5`. Changed to `float`. If you regenerate `models.py` or upgrade the skill, make sure this field stays `float` — `int` silently drops entire categories from selection.

## 파일 구조

```
auto-sec-blogger/
├── SKILL.md (이 파일)
├── scripts/
│   ├── intelligence_pipeline.py (메인 파이프라인, security-news-feed 의존)
│   ├── run_pipeline.py (독립 async 파이프라인)
│   ├── collector.py (뉴스 수집 - Google News, arXiv, HN, Hadaio)
│   ├── selector.py (AI 기사 선별)
│   ├── writer.py (블로그 글 작성, 멀티 페르소나)
│   ├── notion_publisher.py (Notion 발행)
│   ├── publisher_git.py (Git 발행 - Hugo 포맷)
│   ├── git_publisher_service.py (launchd 백그라운드 서비스)
│   ├── auto_publish_approved.py (승인된 글 자동 발행)
│   ├── publish_github.py (GitHub Pages 발행)
│   ├── topic_analyzer.py (주제 그룹 분석)
│   ├── llm_client.py (GLM API 동기 클라이언트)
│   ├── llm_client_async.py (비동기 GLM 클라이언트)
│   ├── prompt_manager.py (프롬프트 관리)
│   ├── prompts.yaml (프롬프트 템플릿)
│   ├── models.py (Pydantic 데이터 모델)
│   ├── config.py (설정)
│   ├── utils.py (유틸리티)
│   └── requirements.txt (의존성)
└── references/
    └── architecture.md (상세 아키텍처)
```

## 환경 변수

### 필수

```bash
GLM_API_KEY          # GLM-4.7 API 키
NOTION_API_KEY       # Notion API 키
NOTION_DATABASE_ID   # Notion 데이터베이스 ID
```

### 선택사항

```bash
GITHUB_TOKEN         # GitHub 개인 액세스 토큰
GITHUB_BLOG_REPO     # GitHub 블로그 저장소 (username/repo)
BLOG_LOCAL_PATH      # 로컬 블로그 경로
```

## 테스트

### 전체 파이프라인 테스트

```bash
python3 test_full_pipeline.py
```

### Mermaid 다이어그램 테스트

```bash
python3 test_mermaid_fix.py
```

## 참고자료

- [GitHub 저장소](https://github.com/rebugui/auto-sec-blogger)
- [GLM API 문서](https://open.bigmodel.cn/dev/api)
- [Notion API 문서](https://developers.notion.com/)
- [Hugo 문서](https://gohugo.io/documentation/)

## 리소스

### scripts/
모든 Python 스크립트 포함:
- `intelligence_pipeline.py` - 전체 파이프라인 실행 (security-news-feed 크롤러 사용)
- `run_pipeline.py` - 독립 async 파이프라인
- `collector.py` - 뉴스 수집기
- `selector.py` - AI 기사 선별
- `writer.py` - 블로그 글 작성
- `notion_publisher.py` - Notion 발행
- `publisher_git.py` - Git 발행 (Hugo 포맷)
- `auto_publish_approved.py` - 승인 글 자동 발행

### references/
- `architecture.md` - 상세 아키텍처 설명
- `pipeline-timing-diagnosis.md` - 2026-06-01 파이프라인 타임아웃 원인 분석 및 수정 기록
