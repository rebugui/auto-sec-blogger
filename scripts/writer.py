"""
LLM Writer - 다중 페르소나 블로그 글 작성 시스템 (Async + Pydantic)
"""

import os
import re
import json
import asyncio
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum
from config import GLM_API_KEY, GLM_BASE_URL, GLM_MODEL
from llm_client_async import AsyncLLMClient
from utils import setup_logger
from prompt_manager import PromptManager
from models import BlogPost

logger = setup_logger(__name__, "writer.log")

class Persona(Enum):
    SECURITY = "security"
    AI_ML = "ai_ml"
    DEVOPS = "devops"
    CVE_ANALYST = "cve_analyst"

class PersonaConfig:
    NOTION_CATEGORIES = ["보안", "AI", "DevOps", "CVE", "IT"]
    
    # 기존 하드코딩된 PERSONAS 딕셔너리는 제거되고 prompts.yaml로 이동됨

    @classmethod
    def get(cls, persona: Persona) -> Dict:
        """PromptManager를 통해 페르소나 설정을 로드합니다."""
        persona_key = persona.value
        config = PromptManager.get_raw(f"personas.{persona_key}")
        
        if not config:
            logger.error(f"Persona config for '{persona_key}' not found in prompts.yaml")
            # Fallback (최소한의 설정)
            return {
                "name": "기술 블로거",
                "expertise": "IT 기술 전반",
                "tone": "친절하고 명확하게",
                "category": "IT",
                "default_tags": ["IT", "Tech"],
                "tag_keywords": [],
                "specific_prompt": ""
            }
        return config

class CategoryClassifier:
    KEYWORDS = {
        Persona.SECURITY: ["취약점", "해킹", "보안", "exploit", "security"],
        Persona.AI_ML: ["ai", "ml", "딥러닝", "llm", "gpt", "model"],
        Persona.DEVOPS: ["devops", "ci/cd", "k8s", "docker", "cloud"],
        Persona.CVE_ANALYST: ["cve", "cvss", "poc", "패치"],
    }

    @classmethod
    def classify(cls, article_data: Dict) -> Persona:
        text = (article_data.get("title", "") + " " + article_data.get("summary", "")).lower()
        scores = {p: sum(1 for kw in kws if kw in text) for p, kws in cls.KEYWORDS.items()}
        if not scores or max(scores.values()) == 0:
            return Persona.SECURITY
        return max(scores, key=scores.get)

class TagExtractor:
    @classmethod
    def extract_tags(cls, article_data: Dict, persona: Persona, max_tags: int = 5) -> List[str]:
        config = PersonaConfig.get(persona)
        text = (article_data.get("title", "") + " " + article_data.get("summary", "")).lower()
        tags = []
        for kw in config.get("tag_keywords", []):
            if kw.lower() in text:
                tags.append(kw)
        tags.extend(re.findall(r'CVE-\d{4}-\d{4,7}', text, re.IGNORECASE))
        if len(tags) < max_tags:
            for t in config.get("default_tags", []):
                if t not in tags:
                    tags.append(t)
        return list(dict.fromkeys(tags))[:max_tags]

    @classmethod
    def get_category(cls, persona: Persona) -> str:
        return PersonaConfig.get(persona).get("category", "IT")

class BlogWriter:
    """다중 페르소나 블로그 작성기 (Async)"""

    def __init__(self, client: AsyncLLMClient = None):
        self.client = client or AsyncLLMClient()

    async def generate_article(self, article_data: Dict, persona: Optional[Persona] = None) -> Dict:
        """단일 기사 생성 (비동기) - 2단계 분리 방식"""
        persona = persona or CategoryClassifier.classify(article_data)
        config = PersonaConfig.get(persona)

        category = TagExtractor.get_category(persona)

        # ===== 1단계: 메타데이터 생성 (제목 + 요약 + 태그) =====
        logger.info(f"[Step 1/2] Generating metadata for: {article_data.get('title', 'N/A')[:40]}")
        metadata = await self._generate_metadata(article_data, persona, config, category)

        # ===== 2단계: 본문 생성 (순수 Markdown) =====
        logger.info(f"[Step 2/2] Generating content for: {metadata['title'][:40]}")
        content = await self._generate_content(article_data, metadata, persona, config)

        return {
            "title": metadata['title'],
            "summary": metadata['summary'],
            "content": content,
            "tags": metadata['tags'],
            "category": metadata['category'],
            "persona": persona.value,
            "original_url": article_data.get("url"),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    async def _generate_metadata(self, article_data: Dict, persona: Persona, config: Dict, category: str) -> Dict:
        """1단계: 메타데이터 생성 (제목 + 요약 + 태그)"""
        system_prompt = PromptManager.get("writer_metadata.base_system",
                                        name=config['name'],
                                        expertise=config['expertise'],
                                        tone=config['tone'],
                                        persona_specific=config.get('specific_prompt', ''))

        user_prompt = PromptManager.get("writer_metadata.user",
                                      source=article_data.get('source', 'Unknown'),
                                      title=article_data.get('title', 'N/A'),
                                      url=article_data.get('url', 'N/A'),
                                      summary=article_data.get('summary', 'N/A'),
                                      category=category)

        meta = None
        try:
            response = await self.client.chat(system_prompt, user_prompt, json_mode=True)
            meta = self._parse_metadata_response(response, category)
        except Exception as e:
            logger.error(f"메타데이터 생성 호출 실패: {e}")
        # 파싱/호출 실패 시에도 글 전체를 죽이지 않고 원문 기반으로 폴백
        if not meta:
            logger.warning("메타데이터 파싱 실패 → 원문 기반 폴백 사용")
            persona = CategoryClassifier.classify(article_data)
            meta = self._metadata_fallback(article_data, persona, category)
        return meta

    def _metadata_fallback(self, article_data: Dict, persona: Persona, category: str) -> Dict:
        """메타데이터 생성 실패 시 원문에서 최소 메타데이터 구성."""
        title = (article_data.get('title') or '제목 없음').strip()[:60]
        summary = (article_data.get('summary') or title).strip()[:300]
        tags = TagExtractor.extract_tags(article_data, persona)
        return {"title": title, "summary": summary, "tags": tags, "category": category}

    async def _generate_content(self, article_data: Dict, metadata: Dict, persona: Persona, config: Dict) -> str:
        """2단계: 본문 생성 (순수 Markdown)"""
        system_prompt = PromptManager.get("writer_content.base_system",
                                        name=config['name'],
                                        expertise=config['expertise'],
                                        tone=config['tone'],
                                        persona_specific=config.get('specific_prompt', ''))

        user_prompt = PromptManager.get("writer_content.user",
                                      title=metadata['title'],
                                      summary=metadata['summary'],
                                      tags=", ".join(metadata['tags']),
                                      source=article_data.get('source', 'Unknown'),
                                      original_title=article_data.get('title', 'N/A'),
                                      url=article_data.get('url', 'N/A'),
                                      original_summary=article_data.get('summary', 'N/A'))

        # 기술 본문은 환각·산만 억제를 위해 낮은 온도 사용
        try:
            response = await self.client.chat(system_prompt, user_prompt, temperature=0.45)
            content = self._clean_markdown(self._sanitize_mermaid(response.strip()))
            if len(content) < 300:
                logger.warning(f"본문 과소({len(content)}자) → 폴백 사용")
                return self._content_fallback(article_data, metadata)
            if len(content) < 1000:
                logger.warning(f"본문 다소 짧음({len(content)}자)")
            return content
        except Exception as e:
            logger.error(f"본문 생성 실패: {e} → 폴백 사용")
            return self._content_fallback(article_data, metadata)

    def _clean_markdown(self, content: str) -> str:
        """가벼운 마크다운 정리: 중복 헤딩 마커('### ## 서론' → '## 서론') 정규화."""
        return re.sub(r'(?m)^#{1,6}[ \t]+(#{1,6})[ \t]+', r'\1 ', content)

    def _content_fallback(self, article_data: Dict, metadata: Dict) -> str:
        """본문 생성 실패 시 요약 기반 최소 본문(글 전체 실패 방지)."""
        src = article_data.get('url', '') or ''
        body = (f"## 개요\n\n{metadata.get('summary', '')}\n\n"
                f"## 핵심\n\n- 원문 주제: {article_data.get('title', '')}\n\n"
                f"---\n\n> 자동 본문 생성에 실패하여 요약만 게시합니다. 원문을 참고하세요.")
        if src:
            body += f"\n\n**출처**: [{src}]({src})"
        return body

    # 유효한 Mermaid 다이어그램 헤더 (없으면 깨진 블록으로 간주)
    _MERMAID_TYPES = ("graph", "flowchart", "sequenceDiagram", "classDiagram",
                      "stateDiagram", "erDiagram", "gantt", "pie", "journey",
                      "gitGraph", "mindmap", "timeline")

    def _sanitize_mermaid(self, content: str) -> str:
        """Mermaid 블록 후처리: 금지된 스타일 라인 제거, 헤더 없으면 블록 삭제.
        (깨진 다이어그램 하나가 Hugo 페이지 전체를 깨뜨리는 것 방지)
        """
        def _fix(m):
            lines = [ln for ln in m.group(1).splitlines()
                     if not re.match(r'\s*(style|classDef|class)\s', ln)
                     and 'fill:' not in ln and 'stroke:' not in ln]
            cleaned = "\n".join(lines).strip()
            first = next((ln.strip() for ln in cleaned.splitlines() if ln.strip()), "")
            if not first.startswith(self._MERMAID_TYPES):
                logger.warning("유효하지 않은 Mermaid 블록 제거")
                return ""
            return f"```mermaid\n{cleaned}\n```"
        return re.sub(r"```mermaid\s*\n(.*?)\n```", _fix, content, flags=re.DOTALL)

    def _parse_metadata_response(self, response: str, category: str):
        """메타데이터 JSON 응답 파싱 (실패 시 None 반환 — 호출부에서 폴백)."""
        if not response:
            return None
        import json as json_lib
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
        json_str = json_match.group(1) if json_match else response
        if '{' in json_str and '}' in json_str:
            json_str = json_str[json_str.find('{'):json_str.rfind('}') + 1]

        data = None
        try:
            data = json_lib.loads(json_str)
        except Exception:
            # 복구: 필드 단위 정규식 추출 (truncation 내성)
            t = re.search(r'"title"\s*:\s*"((?:[^"\\]|\\.)*)"', json_str)
            s = re.search(r'"summary"\s*:\s*"((?:[^"\\]|\\.)*)"', json_str)
            tags = []
            tm = re.search(r'"tags"\s*:\s*\[([^\]]*)', json_str, re.DOTALL)  # 닫는 ] 없어도 회수
            if tm:
                tags = re.findall(r'"([^"]+)"', tm.group(1))
            if t:
                data = {"title": t.group(1), "summary": s.group(1) if s else "", "tags": tags}

        if not data or not data.get('title'):
            logger.error(f"메타데이터 파싱 실패. 응답: {response[:300]}")
            return None
        return {
            "title": data['title'],
            "summary": data.get('summary') or data['title'],
            "tags": data.get('tags') or [],
            "category": data.get('category', category),
        }

    # 카테고리 → 페르소나 (오리지널 딥다이브 생성용)
    _CAT_PERSONA = {
        "보안": Persona.SECURITY, "AI": Persona.AI_ML,
        "DevOps": Persona.DEVOPS, "CVE": Persona.CVE_ANALYST,
    }

    async def generate_original(self, topic: str, category: str = "보안") -> Dict:
        """뉴스에 매이지 않는 에버그린 오리지널 심층 글 생성 (토픽 기반)."""
        persona = self._CAT_PERSONA.get(category, Persona.SECURITY)
        config = PersonaConfig.get(persona)
        logger.info(f"[Original] 생성: {topic[:50]} ({category})")
        meta = await self._gen_original_meta(topic, config, category)
        body = await self._gen_original_body(topic, meta, config)
        return {
            "title": meta["title"], "summary": meta["summary"], "content": body,
            "tags": meta["tags"], "category": category, "persona": persona.value,
            "original_url": "", "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    async def _gen_original_meta(self, topic: str, config: Dict, category: str) -> Dict:
        sysp = PromptManager.get("writer_original_meta.base_system", name=config['name'],
                                 expertise=config['expertise'], tone=config['tone'],
                                 persona_specific=config.get('specific_prompt', ''))
        usrp = PromptManager.get("writer_original_meta.user", topic=topic, category=category)
        meta = None
        try:
            r = await self.client.chat(sysp, usrp, json_mode=True)
            meta = self._parse_metadata_response(r, category)
        except Exception as e:
            logger.error(f"오리지널 메타 생성 실패: {e}")
        if not meta:
            meta = {"title": topic[:60], "summary": topic, "tags": [category], "category": category}
        return meta

    async def _gen_original_body(self, topic: str, meta: Dict, config: Dict) -> str:
        sysp = PromptManager.get("writer_original_body.base_system", name=config['name'],
                                 expertise=config['expertise'], tone=config['tone'],
                                 persona_specific=config.get('specific_prompt', ''))
        usrp = PromptManager.get("writer_original_body.user", title=meta['title'],
                                 summary=meta['summary'], tags=", ".join(meta['tags']), topic=topic)
        try:
            r = await self.client.chat(sysp, usrp, temperature=0.5)
            content = self._clean_markdown(self._sanitize_mermaid(r.strip()))
            if len(content) < 300:
                return self._content_fallback({"title": meta['title'], "url": ""}, meta)
            return content
        except Exception as e:
            logger.error(f"오리지널 본문 생성 실패: {e}")
            return self._content_fallback({"title": meta['title'], "url": ""}, meta)

    async def generate_article_batch(self, articles: List[Dict]) -> List[Dict]:
        """여러 기사 병렬 생성"""
        tasks = [self.generate_article(article) for article in articles]
        return await asyncio.gather(*tasks, return_exceptions=True)

    def _parse_result(self, content: str, original: Dict, persona: Persona, category: str, tags: List[str]) -> Dict:
        """Pydantic 모델을 사용한 파싱"""
        # 빈 응답 체크
        if not content or not content.strip():
            logger.error("LLM returned empty response")
            return self._create_fallback(original, persona, category, tags)

        try:
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            json_str = json_match.group(1) if json_match else content

            # JSON 범위 추출 개선
            if '{' in json_str:
                start = json_str.find('{')
                # 중괄호 균형 맞추기
                brace_count = 0
                end = start
                for i in range(start, len(json_str)):
                    if json_str[i] == '{':
                        brace_count += 1
                    elif json_str[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end = i + 1
                            break
                json_str = json_str[start:end]

            # Pydantic 파싱
            blog_post = BlogPost.model_validate_json(json_str)

            return {
                "title": blog_post.title,
                "summary": blog_post.summary,
                "content": blog_post.content,
                "tags": blog_post.tags or tags,
                "category": blog_post.category or category,
                "persona": persona.value,
                "original_url": original.get("url"),
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            logger.warning(f"Pydantic parsing failed ({e}), attempting fallback parsing...")
            return self._create_fallback(original, persona, category, tags, content)

    def _create_fallback(self, original: Dict, persona: Persona, category: str, tags: List[str], llm_response: str = None) -> Dict:
        """Fallback 결과 생성"""
        # LLM 응답에서 JSON 블록 제거 후 content 사용
        content_text = llm_response or ""

        # 디버깅: LLM 원본 응답 로깅
        logger.info(f"[FALLBACK] LLM response length: {len(content_text)}, First 200 chars: {content_text[:200] if content_text else '(EMPTY)'}")

        if content_text:
            # JSON 코드 블록 제거 (전체 JSON 객체 제거, content 필드 추출 아님!)
            # ````json ... ``` 블록 제거 후 그 안의 content만 사용
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', content_text, re.DOTALL)
            if json_match:
                # JSON 문자열에서 content 필드 추출
                json_str = json_match.group(1)
                # 정규식으로 content 필드 값 추출
                content_match = re.search(r'"content"\s*:\s*"((?:[^"\\]|\\.)*)"', json_str, re.DOTALL)
                if content_match:
                    import json as json_lib
                    try:
                        content_value = f'"{content_match.group(1)}"'
                        content_text = json_lib.loads(content_value)
                    except json_lib.JSONDecodeError:
                        content_text = content_match.group(1)
                    except Exception:
                        content_text = content_match.group(1)
                else:
                    content_text = ""
            else:
                # 코드 블록이 없으면 그냥 사용
                content_text = content_text.strip()

        # 여전히 비어있거나 너무 짧으면 원본 요약 사용
        if not content_text or len(content_text) < 100:
            logger.warning(f"[FALLBACK] Content still too short ({len(content_text)}), using original summary")
            content_text = f"# {original.get('title', '제목 없음')}\n\n{original.get('summary', '요약 없음')}\n\n> 본문 생성 실패: 원본 기사를 참고하세요\n\n원본 URL: {original.get('url', '')}"

        logger.info(f"[FALLBACK] Final content length: {len(content_text)}, First 200 chars: {content_text[:200]}")

        return {
            "title": original.get("title"),
            "summary": original.get("summary"),
            "content": content_text,
            "tags": tags,
            "category": category,
            "persona": persona.value,
            "original_url": original.get("url"),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }