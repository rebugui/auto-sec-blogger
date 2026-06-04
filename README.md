# Auto Sec Blogger

[![Version](https://img.shields.io/badge/version-2.0.0-blue)](https://github.com/rebugui/auto-sec-blogger)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

> 보안·기술 뉴스를 자동 수집하고, **로컬 LLM(Ollama Gemma4)**으로 전문가 수준의 블로그 글을 작성한 뒤, Notion 초안으로 저장하고 사람이 승인한 글을 **GitHub Pages(Hugo)**에 자동 발행하는 지능형 에이전트.

GitHub: https://github.com/rebugui/auto-sec-blogger

## 개요

매일 정해진 시각에 다음을 수행합니다.

1. 여러 소스에서 보안/기술 뉴스를 수집
2. 로컬 LLM이 카테고리별로 평가·선별
3. 선별된 기사로 멀티 페르소나 블로그 글 작성
4. Notion에 `검토중` 초안으로 저장
5. **사람이 Notion에서 `검토 완료`로 승인한 글**만 Hugo 포스트로 변환해 git push → GitHub Actions가 빌드·배포

> **Human-in-the-Loop**: 글 생성은 자동이지만, 공개 발행은 사람이 Notion에서 승인한 글에 한합니다.

## 아키텍처

```
뉴스 수집 (Google News · arXiv · HackerNews · Hada.io)
    ↓
Ollama Gemma4 평가/선별 (카테고리별 점수, round-robin 선택)
    ↓
Ollama Gemma4 글 작성 (멀티 페르소나: 보안/AI/DevOps/CVE, Mermaid 다이어그램)
    ↓
Notion 저장  ── 상태: 초안 작성중 → 검토중
    ↓
[사람 검토]  ── Notion에서 검토중 → 검토 완료 로 승인
    ↓
auto_publish_approved.py ── Hugo content/post 생성 → git push(main)
    ↓
GitHub Actions(Hugo) → GitHub Pages (https://rebugui.github.io/)
    ↓
Notion 상태 → 게시 완료
```

## LLM (중요)

- **모델**: Ollama 로컬 **`gemma4:e4b`** (8B, Q4_K_M) — 외부 클라우드 API 호출 없음
- **엔드포인트**: `http://localhost:11434/v1/` (OpenAI 호환)
- 코드의 `GLM_*` 변수명은 레거시이며 실제로는 위 Ollama 모델을 가리킵니다. 선별·작성 모두 동일한 `AsyncLLMClient`를 사용합니다.
- 평가(JSON) 호출은 `response_format=json_object`로 유효 JSON을 강제하고, 응답이 잘려도 객체 단위 복구 파싱으로 견딥니다.

## 주요 기능

### 1. 뉴스 수집 (`collector.py`)
- Google News(키워드), arXiv(`arxiv.Client`로 rate-limit 회피), HackerNews, Hada.io
- SQLite(`scripts/news.db` · `data/intelligence.db`) 기반 URL 중복 제거

### 2. 평가·선별 (`selector.py`)
- 카테고리별 후보 사전 제한(`MAX_PER_CATEGORY`) + 청크 분할(`CHUNK_SIZE`)로 LLM 응답 truncation 방지
- 점수 ≥ `min_score`(기본 6)만 통과, 카테고리 round-robin으로 최종 선택

### 3. 글 작성 (`writer.py`)
- 멀티 페르소나(보안/AI·ML/DevOps/CVE), 2단계 생성(메타데이터 → 본문)
- Mermaid 다이어그램·코드·표 포함, 최소 2000자

### 4. Notion 발행 (`notion_publisher.py`)
- 상태 관리: `초안 작성중` → `검토중` → (사람) `검토 완료` → `게시 완료`
- 속성: 내용(제목)/상태/카테고리/태그

### 5. Git 발행 (`auto_publish_approved.py` → `publisher_github.py`)
- Notion에서 `검토 완료`(또는 `AUTO_PUBLISH_STATUS`) 글을 조회
- Notion 본문 → 마크다운 변환 → Hugo `content/post/<카테고리>/<slug>/index.md` 생성 → `git push origin main` → GitHub Actions가 Hugo 빌드·배포
- 발행 성공 시 Notion `게시된 플랫폼`(multi-select)에 `GitHub` 기록 → 재실행 시 중복 발행 방지, 상태 `게시 완료` 전환
- 1회 발행 상한 `AUTO_PUBLISH_MAX`(기본 5)

> **발행 대상은 GitHub Pages(Hugo)만 지원한다.** 네이버 블로그/티스토리 자동 발행도 검토했으나, 두 플랫폼 모두 글쓰기 시 캡차(네이버 자동등록방지 / 티스토리 DKAPTCHA 지도 캡차)로 봇 발행을 차단하여 자동화가 불가능해 제외했다.

## 설치

```bash
cd ~/.hermes/skills/openclaw-imports/auto-sec-blogger
pip3 install -r scripts/requirements.txt

# Ollama 및 모델 준비 (로컬)
ollama pull gemma4:e4b
```

## 환경 변수

`~/.hermes/.skills.env`에 정의합니다. `config.py`가 이 파일을 폴백 로드하므로 래퍼 없이 직접 실행해도 동작합니다.

### 필수
```bash
INTELLIGENCE_NOTION_TOKEN=ntn_xxx       # 또는 NOTION_API_KEY
INTELLIGENCE_BLOG_DATABASE_ID=xxxxxxxx  # Notion 블로그 DB ID
GITHUB_TOKEN=ghp_xxx                    # 블로그 repo push용
GITHUB_USERNAME=rebugui
BLOG_REPO_PATH=/Users/<you>/.hermes/workspace/blog   # 로컬 Hugo 저장소 경로
```

### 선택 (기본값 존재)
```bash
INTELLIGENCE_LLM_API_KEY=ollama                       # 기본 "ollama"
INTELLIGENCE_LLM_BASE_URL=http://localhost:11434/v1/  # 기본값
INTELLIGENCE_LLM_MODEL=gemma4:e4b                     # 기본값
BLOG_URL=https://rebugui.github.io/
AUTO_PUBLISH_STATUS=검토 완료    # '검토중'으로 바꾸면 완전 자동발행
AUTO_PUBLISH_MAX=5               # 1회 발행 상한
```

## 사용법

### 전체 파이프라인 + 자동 발행 (스케줄러가 실행하는 래퍼)
```bash
bash ~/.hermes/scripts/run-auto-sec-blogger.sh
```
이 래퍼는 `.skills.env`를 로드한 뒤 `intelligence_pipeline.py --max-articles 3` 실행 후 `auto_publish_approved.py`를 이어서 실행합니다.

### 파이프라인만 (Notion 초안까지)
```bash
cd ~/.hermes/skills/openclaw-imports/auto-sec-blogger
python3 scripts/intelligence_pipeline.py --max-articles 3
```

### 발행만 (승인된 글 → git)
```bash
python3 scripts/auto_publish_approved.py
# 1건만 테스트: AUTO_PUBLISH_MAX=1 python3 scripts/auto_publish_approved.py
```

## 스케줄링 (Hermes cron)

이 스킬은 시스템 crontab이 아니라 **Hermes cron**으로 매일 08:00(KST) 실행됩니다.

- 잡 이름: `auto-sec-blogger` (스크립트 모드, `no_agent`)
- 실행 스크립트: `~/.hermes/scripts/run-auto-sec-blogger.sh`
- 스크립트 타임아웃: `~/.hermes/config.yaml`의 `cron.script_timeout_seconds`
- 로컬 Gemma4 작성은 느릴 수 있으므로 타임아웃을 넉넉히(예: 1800초) 둡니다.

## 디렉토리 구조

```
auto-sec-blogger/
├── scripts/
│   ├── intelligence_pipeline.py    # 메인 파이프라인 (async)
│   ├── collector.py                # 뉴스 수집
│   ├── selector.py                 # AI 평가/선별
│   ├── writer.py                   # 블로그 글 작성 (멀티 페르소나)
│   ├── notion_publisher.py         # Notion 초안 발행
│   ├── auto_publish_approved.py    # 승인 글 → Hugo → git push
│   ├── llm_client_async.py         # Ollama(OpenAI 호환) 비동기 클라이언트
│   ├── prompt_manager.py / prompts.yaml
│   ├── models.py · config.py · utils.py
│   └── requirements.txt
├── references/
│   ├── architecture.md
│   └── pipeline-timing-diagnosis.md
├── SKILL.md
└── README.md
```

## 트러블슈팅

- **글이 0건 생성됨(조용한 실패)**: 셀렉터가 LLM JSON 응답 truncation으로 전 기사를 0점 처리하던 문제는 청크 분할 + 복구 파싱 + `json_mode`로 해결됨. `logs/selector.log`에 `EOF while parsing a list`가 보이면 청크 크기를 더 줄이세요.
- **`NOTION_API_KEY is not set`**: `config.py`가 `~/.hermes/.skills.env`를 로드하는지 확인. 래퍼 실행 시 `set -a; source`로 export 필요.
- **발행은 됐는데 사이트에 안 뜸**: 블로그 repo의 `.github/workflows/deploy.yml`(Hugo, `submodules: recursive`) Actions 빌드 로그 확인.
- **arXiv 429**: 일시적 rate-limit. arXiv는 선택 소스라 실패해도 파이프라인은 계속 진행.

## 라이선스

MIT License — [LICENSE](LICENSE) 참고.
