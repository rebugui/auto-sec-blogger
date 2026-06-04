---
name: auto-sec-blogger
version: 2.2.0
description: "AI-powered security/tech blog automation (identical to github.com/rebugui/auto-sec-blogger). Collects news from Google News, arXiv, HackerNews, Hada.io → evaluates & writes expert blog posts with LOCAL Ollama Gemma (gemma4:e4b, no cloud API) → saves Notion drafts → human approves in Notion → auto-publishes approved posts to GitHub Pages (Hugo) via Git. Human-in-the-Loop approval workflow. Use to automate blog writing, security news curation, or content generation. Triggers: 블로그 글 작성, 보안 뉴스 발행, 깃헙 블로그 발행, intelligence agent, 지능형 에이전트, 자동 글쓰기."
---

# Auto Sec Blogger (Intelligence Agent)

보안·기술 뉴스를 자동 수집하고, **로컬 LLM(Ollama Gemma4)**으로 전문가 수준 블로그 글을 작성한 뒤, Notion 초안으로 저장하고 **사람이 승인한 글만** GitHub Pages(Hugo)에 자동 발행하는 시스템.

GitHub: https://github.com/rebugui/auto-sec-blogger

> 사용자 가이드/설치/환경변수 전반은 [README.md](README.md) 참고. 이 문서는 스킬 운영(스케줄러·내부 동작·함정)에 초점을 둡니다.

## 아키텍처

```
뉴스 수집 (Google News · arXiv · HackerNews · Hada.io)
    ↓
Ollama Gemma4:e4b 평가/선별 (카테고리별 점수, round-robin 선택)
    ↓
Ollama Gemma4:e4b 글 작성 (멀티 페르소나: 보안/AI/DevOps/CVE, Mermaid)
    ↓
Notion 저장 ── 상태: 초안 작성중 → 검토중
    ↓
[사람 검토] ── Notion에서 검토중 → 검토 완료 로 승인
    ↓
auto_publish_approved.py ── Hugo content/post 생성 → git push(main)
    ↓
GitHub Actions(Hugo, submodules recursive) → GitHub Pages
    ↓
Notion 상태 → 게시 완료
```

## LLM (Ollama 로컬)

- **모델**: `gemma4:e4b` (8B, Q4_K_M) — 외부 클라우드 API 호출 없음. 코드의 `GLM_*` 변수명은 레거시.
- **엔드포인트**: `http://localhost:11434/v1/` (OpenAI 호환). 선별·작성 모두 `AsyncLLMClient` 사용.
- **클라이언트 설정** (`scripts/llm_client_async.py`):

  | 항목 | 값 | 비고 |
  |------|----|----|
  | `timeout` | 600s | 로컬 8B는 호출당 30~40s, 긴 본문은 그 이상 |
  | `max_tokens` | 8000 | thinking + JSON/본문 충분 확보 |
  | `json_mode` | 옵션 | `response_format=json_object` 강제(평가 호출에서 사용) |

- **API 키**: 불필요하나 비어있으면 ValueError → `INTELLIGENCE_LLM_API_KEY=ollama`(기본값) 유지.

## Hermes Cron (스케줄러)

시스템 crontab이 아니라 **Hermes cron**으로 매일 08:00(KST) 실행.

- 잡 이름: `auto-sec-blogger` (스크립트 모드, `no_agent`)
- 실행 스크립트: `~/.hermes/scripts/run-auto-sec-blogger.sh`
- 스크립트 타임아웃: `~/.hermes/config.yaml`의 `cron.script_timeout_seconds`(현재 1800)
- 등록: `cronjob action=create name="auto-sec-blogger" schedule="0 8 * * *" script="run-auto-sec-blogger.sh" no_agent=true`

### 래퍼 스크립트 (`run-auto-sec-blogger.sh`)

```bash
#!/bin/bash
SKILL_DIR="$HOME/.hermes/skills/openclaw-imports/auto-sec-blogger"
set -a                                   # ⚠️ 필수: source한 변수를 Python 자식에 export
source "$HOME/.hermes/.skills.env" 2>/dev/null
set +a
cd "$SKILL_DIR"
/usr/bin/python3 "$SKILL_DIR/scripts/intelligence_pipeline.py" --max-articles 3   # 1) 작성 → Notion 초안(검토중)
/usr/bin/python3 "$SKILL_DIR/scripts/auto_publish_approved.py"                    # 2) 승인분 → git push
```

`set -a` 없이 `source`하면 변수가 bash에만 남고 자식 프로세스(Python)로 export되지 않아 "API Key가 설정되지 않았습니다." / "NOTION_API_KEY is not set"로 조용히 실패합니다. (보강책으로 `config.py`가 `.skills.env`를 폴백 로드하지만, 래퍼에서도 `set -a` 유지 권장.)

### 수동 실행

```bash
bash ~/.hermes/scripts/run-auto-sec-blogger.sh            # 전체(작성+발행)
python3 scripts/intelligence_pipeline.py --max-articles 3 # 작성만
python3 scripts/auto_publish_approved.py                  # 발행만
AUTO_PUBLISH_MAX=1 python3 scripts/auto_publish_approved.py  # 1건만 발행 테스트
```

## 모듈별 동작

### 수집 (`collector.py`)
- Google News, arXiv(`arxiv.Client`로 page_size 축소 + 지연/재시도 → 429 완화), HackerNews, Hada.io
- SQLite(`scripts/news.db`, `data/intelligence.db`)로 URL 중복 제거
- arXiv는 선택 소스: 실패(429/타임아웃)해도 graceful하게 빈 결과 반환 후 진행

### 선별 (`selector.py`)
- 카테고리별 후보 사전 제한 `MAX_PER_CATEGORY=12`, 청크 분할 `CHUNK_SIZE=6`
- `json_mode`로 유효 JSON 강제, 응답이 잘려도 **객체 단위 복구 파싱**으로 완전한 항목만 회수
- 한 청크 실패가 카테고리 전체를 0점으로 죽이지 않음(과거 "조용한 실패" 원인 제거)
- 점수 ≥ `min_score`(기본 6) 통과분을 카테고리 round-robin으로 최종 선택

### 작성 (`writer.py`)
- 멀티 페르소나(보안/AI·ML/DevOps/CVE), 2단계 생성(메타데이터 → 본문)
- Mermaid 다이어그램(스타일 속성 금지, 심플), 코드/표 포함, 최소 2000자

### Notion 발행 (`notion_publisher.py`)
- `create_article`: 상태 `초안 작성중`으로 생성 후 `검토중`으로 갱신
- 사람이 `검토 완료`로 승인 → `auto_publish`가 발행 후 `게시 완료`로 전환

### Git 발행 (`auto_publish_approved.py` → `publisher_github.py`)
- Notion에서 `AUTO_PUBLISH_STATUS`(기본 `검토 완료`) 글 조회 → 본문 마크다운 변환
- `publisher_github.publish`: 마크다운→Hugo `content/post/<카테고리>/<slug>/index.md` → 글당 `git push origin main`
- 성공 시 `게시된 플랫폼`(multi-select)에 `GitHub` 기록 → 중복 방지, 상태 `게시 완료`
- 경로 `config.BLOG_REPO_PATH`, DB는 파이프라인과 동일, 1회 상한 `AUTO_PUBLISH_MAX`(기본 5)
- **GitHub Pages만 지원.** 네이버/티스토리는 캡차(네이버 자동등록방지 / 티스토리 DKAPTCHA 지도 캡차)로 봇 발행 차단 → 자동화 불가로 제외.

## Notion 데이터베이스 스키마

| 속성명 | 타입 | 값/설명 |
|--------|------|---------|
| 내용 | title | 블로그 글 제목 |
| 상태 | status | `초안 작성중` → `검토중` → `검토 완료` → `게시 완료` |
| 카테고리 | select | 보안 / AI / DevOps / CVE / IT |
| 테그 | multi_select | 키워드(최대 5) |
| URL | url | 원문 URL |

## Hugo 블로그 구조 (rebugui/rebugui.github.io)

```
blog/
├── hugo.toml                  # theme = 'hugo-theme-stack', [permalinks] post = '/:slug/'
├── content/post/<카테고리>/<slug>/index.md
├── themes/hugo-theme-stack/   # git submodule
└── .github/workflows/deploy.yml   # main push → actions-hugo 빌드 → Pages (submodules: recursive)
```

## 환경 변수 (`~/.hermes/.skills.env`)

`config.py`가 이 파일을 폴백 로드하므로 래퍼 없이도 동작.

```bash
# 필수
INTELLIGENCE_NOTION_TOKEN=ntn_xxx        # 또는 NOTION_API_KEY
INTELLIGENCE_BLOG_DATABASE_ID=xxxx       # Notion 블로그 DB (BLOG_DATABASE_ID와 동일 DB)
GITHUB_TOKEN=ghp_xxx
GITHUB_USERNAME=rebugui
BLOG_REPO_PATH=/Users/<you>/.hermes/workspace/blog

# 선택 (기본값 존재)
INTELLIGENCE_LLM_API_KEY=ollama
INTELLIGENCE_LLM_BASE_URL=http://localhost:11434/v1/
INTELLIGENCE_LLM_MODEL=gemma4:e4b
BLOG_URL=https://rebugui.github.io/
AUTO_PUBLISH_STATUS=검토 완료            # '검토중'으로 바꾸면 완전 자동발행
AUTO_PUBLISH_MAX=5
```

## Pitfalls (운영 함정)

1. **글 0건 생성(조용한 실패)**: 셀렉터가 카테고리 배치 JSON truncation으로 전 기사를 0점 처리하던 문제 → 청크 분할 + 복구 파싱 + `json_mode`로 해결. `logs/selector.log`에 `EOF while parsing a list`가 재발하면 `CHUNK_SIZE`를 더 낮추세요. 또한 cron `last_status: ok`라도 "No articles passed"면 실제 산출물 0건일 수 있으니 로그 확인.
2. **`NOTION_API_KEY is not set`**: `config.py`가 `~/.hermes/.skills.env`를 로드하는지, 래퍼가 `set -a; source`로 export하는지 확인.
3. **Ollama가 느림(정상)**: 로컬 8B는 호출당 30~40s. 3건 작성은 수 분~십수 분. 작업량을 줄이지 말고 `cron.script_timeout_seconds`를 넉넉히(현재 1800) 유지.
4. **백로그 대량 발행 방지**: 승인 글이 많아도 1회 `AUTO_PUBLISH_MAX`건만 발행(최신순). 일괄 발행이 필요하면 환경변수로 일시 상향.
5. **발행됐는데 사이트 미반영**: 블로그 repo `.github/workflows/deploy.yml`(Hugo, `submodules: recursive`) Actions 빌드 로그 확인. 테마는 submodule이라 CI가 recursive 체크아웃해야 빌드됨.
6. **arXiv 429**: 일시적 IP rate-limit. arXiv는 선택 소스이므로 실패해도 파이프라인 계속.
7. **Pydantic score는 float**: `models.py` `EvaluationItem.score`는 `float`(Gemma가 8.5 같은 값 반환). `int`로 되돌리면 검증 실패로 항목이 떨어짐.
8. **cron 실패 진단 순서**: ① `~/.hermes/cron/jobs.json`의 `last_status`/`last_error` → ② `~/.hermes/cron/output/<job_id>/<date>.md` 스크립트 종료/타임아웃 → ③ `logs/pipeline.log` 단계 추적 → ④ `logs/selector.log`·`writer.log` → ⑤ 래퍼 수동 재현.
9. **jobs.json 인라인 `prompt`는 미사용**: 실행은 `script`(run-auto-sec-blogger.sh) 기준. 래퍼만 수정하면 됨.

## 파일 구조

```
auto-sec-blogger/
├── SKILL.md / README.md
├── .gitignore
├── scripts/
│   ├── intelligence_pipeline.py        # 메인 파이프라인(async)
│   ├── collector.py                    # 수집 (Google News/arXiv/HN/Hada.io)
│   ├── selector.py                     # AI 평가/선별 (청크+복구 파싱)
│   ├── writer.py                       # 글 작성 (멀티 페르소나)
│   ├── notion_publisher.py             # Notion 초안 발행
│   ├── auto_publish_approved.py        # 승인 글 → 발행 디스패치
│   ├── publisher_github.py · publisher_base.py   # GitHub(Hugo) 퍼블리셔
│   ├── llm_client_async.py             # Ollama 비동기 클라이언트
│   ├── prompt_manager.py / prompts.yaml
│   ├── models.py · config.py · utils.py
│   └── requirements.txt
└── references/
    ├── architecture.md
    └── pipeline-timing-diagnosis.md    # 타임아웃 원인 분석/수정 기록
```

## 참고자료

- [GitHub 저장소](https://github.com/rebugui/auto-sec-blogger)
- [Ollama](https://ollama.com/) · [Notion API](https://developers.notion.com/) · [Hugo](https://gohugo.io/documentation/)
