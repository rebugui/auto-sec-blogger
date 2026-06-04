"""
Article Selector - AI 기반 기사 평가 및 선별 모듈 (Async + Pydantic)
"""

import json
import re
import asyncio
from typing import List, Dict
from collections import defaultdict
from llm_client_async import AsyncLLMClient
from writer import CategoryClassifier, Persona, PersonaConfig
from utils import setup_logger
from prompt_manager import PromptManager
from models import EvaluationResponse, EvaluationItem

logger = setup_logger(__name__, "selector.log")

# 카테고리당 LLM 평가에 보낼 최대 후보 수 (JSON 크기·호출 시간 제한)
MAX_PER_CATEGORY = 12
# 단일 LLM 호출에 묶을 기사 수 (truncation 방지를 위해 작게 유지)
CHUNK_SIZE = 6

class ArticleSelector:
    """AI를 사용하여 수집된 기사 중 최적의 기사를 선별"""

    def __init__(self, client: AsyncLLMClient = None):
        self.client = client or AsyncLLMClient()

    async def evaluate_and_select(self, articles: List[Dict], max_articles: int = 5, min_score: int = 6) -> List[Dict]:
        if not articles:
            return []

        logger.info(f"Evaluating {len(articles)} articles for selection (Async)...")

        # 1. 카테고리별 그룹화
        category_groups = defaultdict(list)
        for i, article in enumerate(articles):
            persona = CategoryClassifier.classify(article)
            config = PersonaConfig.get(persona)
            category = config.get("category", "IT")
            
            article['_temp_id'] = i
            article['_category'] = category
            category_groups[category].append(article)

        # 2. 카테고리별 후보 사전 제한 (LLM 부하/JSON 크기 축소)
        #    수집기는 대략 최신순으로 반환하므로 앞에서부터 MAX_PER_CATEGORY건만 평가
        for category in list(category_groups.keys()):
            if len(category_groups[category]) > MAX_PER_CATEGORY:
                logger.info(
                    f"[{category}] 후보 {len(category_groups[category])}건 → 상위 {MAX_PER_CATEGORY}건으로 제한"
                )
                category_groups[category] = category_groups[category][:MAX_PER_CATEGORY]

        # 3. 각 카테고리별 평가 태스크 생성
        tasks = []
        for category, items in category_groups.items():
            if not items:
                continue
            tasks.append(self._score_articles_in_category(category, items))
        
        # 3. 병렬 실행 및 결과 수집
        scored_results = await asyncio.gather(*tasks)
        
        # 4. 점수 매핑
        for result_list in scored_results:
            scored_dict = {item.id: item for item in result_list}
            for item in result_list:
                original_idx = item.id
                if 0 <= original_idx < len(articles):
                    articles[original_idx]['_score'] = item.score
                    articles[original_idx]['_reason'] = item.reason

        # 5. 카테고리별 최종 선택 (Round-robin)
        final_selected = []
        categories = list(category_groups.keys())
        for cat in categories:
            category_groups[cat].sort(key=lambda x: x.get('_score', 0), reverse=True)

        while len(final_selected) < max_articles:
            all_empty = True
            for cat in categories:
                if len(final_selected) >= max_articles:
                    break
                
                if category_groups[cat]:
                    all_empty = False
                    article = category_groups[cat].pop(0)
                    
                    score = article.get('_score', 0)
                    if score < min_score:
                        logger.info(f"Skipped [{cat}] '{article['title'][:30]}...' (Score: {score} < {min_score})")
                        continue

                    final_selected.append(article)
                    logger.info(f"Selected [{cat}] (Score: {score}): {article['title'][:50]}...")
            
            if all_empty:
                break

        return final_selected

    async def _score_articles_in_category(self, category: str, items: List[Dict]):
        """AI 평가 (청크 분할 + 복원력 있는 JSON 파싱)

        - 카테고리 기사를 CHUNK_SIZE 단위로 나눠 호출 → 응답 truncation 확률 급감
        - 한 청크가 파싱에 완전히 실패해도 해당 청크만 건너뛰고 나머지는 보존
          (이전엔 except가 [] 반환 → 카테고리 전원 0점 → 선택 0건의 조용한 실패)
        """
        if len(items) == 1:
            # Mock object for single item
            return [EvaluationItem(id=items[0]['_temp_id'], score=9, reason="Only article in category")]

        chunks = [items[i:i + CHUNK_SIZE] for i in range(0, len(items), CHUNK_SIZE)]
        results: List[EvaluationItem] = []

        for chunk_idx, chunk in enumerate(chunks):
            articles_text = ""
            for item in chunk:
                safe_summary = (item.get('summary') or "")[:200].replace('\n', ' ')
                articles_text += f"ID: {item['_temp_id']}\nTitle: {item['title']}\nSummary: {safe_summary}\n---\n"

            system_prompt = PromptManager.get("selector.system", category=category)
            user_prompt = PromptManager.get("selector.user", category=category, articles_text=articles_text)

            evaluations = await self._score_chunk(category, chunk_idx, system_prompt, user_prompt)
            results.extend(evaluations)

        scored_ids = {e.id for e in results}
        missing = [it['_temp_id'] for it in items if it['_temp_id'] not in scored_ids]
        if missing:
            logger.warning(
                f"[{category}] {len(missing)}건 점수 획득 실패(파싱 누락) → 0점 처리: ids={missing[:10]}"
            )
        return results

    async def _score_chunk(self, category: str, chunk_idx: int, system_prompt: str, user_prompt: str):
        """단일 청크 평가 (JSON 강제 + 1회 재시도 + 복구 파싱)"""
        for attempt in range(2):
            try:
                response = await self.client.chat(system_prompt, user_prompt, json_mode=True)
                evaluations = self._parse_evaluations(response)
                if evaluations:
                    return evaluations
                logger.warning(
                    f"[{category}] 청크 {chunk_idx} 파싱 결과 0건 (시도 {attempt + 1}/2)"
                )
            except Exception as e:
                logger.error(f"[{category}] 청크 {chunk_idx} 평가 실패 (시도 {attempt + 1}/2): {e}")
        return []

    @staticmethod
    def _parse_evaluations(response: str) -> List[EvaluationItem]:
        """LLM 응답에서 EvaluationItem 목록을 복원력 있게 추출.

        1) 코드펜스/잡텍스트 제거 후 EvaluationResponse 엄격 파싱 시도
        2) 실패(예: truncation으로 'EOF while parsing a list') 시
           개별 {…} 객체를 정규식으로 뽑아 항목별 검증 → 잘린 마지막 객체만 자연 탈락
        """
        if not response:
            return []

        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        json_str = json_match.group(1) if json_match else response.strip()
        if '{' in json_str and '}' in json_str:
            json_str = json_str[json_str.find('{'):json_str.rfind('}') + 1]

        # 1차: 엄격 파싱
        try:
            return EvaluationResponse.model_validate_json(json_str).evaluations
        except Exception:
            pass

        # 2차: 객체 단위 복구 파싱 (truncation 내성)
        recovered: List[EvaluationItem] = []
        for obj in re.findall(r'\{[^{}]*\}', json_str, re.DOTALL):
            try:
                recovered.append(EvaluationItem.model_validate_json(obj))
            except Exception:
                continue
        if recovered:
            logger.info(f"복구 파싱으로 {len(recovered)}건 평가 항목 회수")
        return recovered