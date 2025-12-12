from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import json
import re
import logging

import httpx

from app.config import settings
from .graph_store import Entity, Relation

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    """Result of entity and relation extraction"""
    entities: List[Entity]
    relations: List[Relation]


class EntityExtractor:
    """LLM-based entity and relation extraction from text"""

    def __init__(self):
        self.api_url = settings.llm_api_url
        self.model = settings.llm_model
        self.timeout = httpx.Timeout(120.0, connect=10.0)

        # Entity and relation types
        self.entity_types = ["Person", "Organization", "Location", "Concept", "Event", "Product", "Technology"]
        self.relation_types = ["WORKS_FOR", "LOCATED_IN", "RELATED_TO", "MENTIONS", "PART_OF", "CREATED_BY", "USES"]

    def _build_extraction_prompt(self, text: str) -> List[Dict[str, str]]:
        """Build the prompt for entity and relation extraction"""
        system_prompt = f"""You are an expert at extracting structured information from text.
Your task is to identify entities and their relationships from the given text.

Entity Types: {', '.join(self.entity_types)}
Relation Types: {', '.join(self.relation_types)}

Output Format (JSON):
{{
    "entities": [
        {{"name": "Entity Name", "type": "EntityType", "description": "Brief description"}}
    ],
    "relations": [
        {{"source": "Source Entity Name", "target": "Target Entity Name", "type": "RelationType", "description": "Brief description"}}
    ]
}}

Rules:
1. Extract only important, specific entities (names of people, organizations, places, key concepts)
2. Avoid generic terms like "the company", "the person", etc.
3. Normalize entity names (e.g., "Apple Inc." and "Apple" should be "Apple")
4. Only create relations between entities you've extracted
5. Keep descriptions concise (under 50 characters)
6. Output valid JSON only, no additional text"""

        user_prompt = f"""Extract entities and relations from the following text:

---
{text[:4000]}
---

Output the JSON:"""

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

    async def extract(self, text: str) -> ExtractionResult:
        """Extract entities and relations from text using LLM"""
        if not text or len(text.strip()) < 50:
            return ExtractionResult(entities=[], relations=[])

        messages = self._build_extraction_prompt(text)

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,  # Low temperature for consistent extraction
            "max_tokens": 2048,
            "stream": False
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(self.api_url, json=payload)
                response.raise_for_status()

                data = response.json()
                content = data["choices"][0]["message"]["content"]

                return self._parse_extraction_response(content)

        except httpx.HTTPError as e:
            logger.error(f"HTTP error during entity extraction: {e}")
            return ExtractionResult(entities=[], relations=[])
        except Exception as e:
            logger.error(f"Error during entity extraction: {e}")
            return ExtractionResult(entities=[], relations=[])

    def _parse_extraction_response(self, content: str) -> ExtractionResult:
        """Parse the LLM response to extract entities and relations"""
        entities = []
        relations = []

        try:
            # Try to extract JSON from the response
            json_match = re.search(r'\{[\s\S]*\}', content)
            if not json_match:
                logger.warning("No JSON found in extraction response")
                return ExtractionResult(entities=[], relations=[])

            json_str = json_match.group()
            data = json.loads(json_str)

            # Parse entities
            for entity_data in data.get("entities", []):
                if isinstance(entity_data, dict) and "name" in entity_data:
                    entity_type = entity_data.get("type", "Concept")
                    if entity_type not in self.entity_types:
                        entity_type = "Concept"

                    entities.append(Entity(
                        name=entity_data["name"].strip(),
                        type=entity_type,
                        properties={"description": entity_data.get("description", "")}
                    ))

            # Parse relations
            entity_names = {e.name.lower() for e in entities}
            for rel_data in data.get("relations", []):
                if isinstance(rel_data, dict) and "source" in rel_data and "target" in rel_data:
                    source = rel_data["source"].strip()
                    target = rel_data["target"].strip()
                    rel_type = rel_data.get("type", "RELATED_TO")

                    if rel_type not in self.relation_types:
                        rel_type = "RELATED_TO"

                    # Only add relation if both entities exist
                    if source.lower() in entity_names and target.lower() in entity_names:
                        relations.append(Relation(
                            source=source,
                            target=target,
                            type=rel_type,
                            properties={"description": rel_data.get("description", "")}
                        ))

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from extraction response: {e}")
        except Exception as e:
            logger.warning(f"Error parsing extraction response: {e}")

        return ExtractionResult(entities=entities, relations=relations)

    async def extract_batch(self, texts: List[str]) -> List[ExtractionResult]:
        """Extract entities and relations from multiple texts"""
        results = []
        for text in texts:
            result = await self.extract(text)
            results.append(result)
        return results

    def extract_entities_from_query(self, query: str) -> List[str]:
        """Simple extraction of potential entity mentions from a query (no LLM call)"""
        # Simple heuristic: extract capitalized words and phrases
        entities = []

        # Find capitalized words (potential proper nouns)
        words = query.split()
        i = 0
        while i < len(words):
            word = words[i].strip('.,!?;:')
            if word and word[0].isupper():
                # Check for multi-word entity (consecutive capitalized words)
                entity_words = [word]
                j = i + 1
                while j < len(words):
                    next_word = words[j].strip('.,!?;:')
                    if next_word and next_word[0].isupper():
                        entity_words.append(next_word)
                        j += 1
                    else:
                        break

                entity = " ".join(entity_words)
                if len(entity) > 1:  # Avoid single characters
                    entities.append(entity)
                i = j
            else:
                i += 1

        # Also extract quoted phrases
        quoted = re.findall(r'"([^"]+)"', query)
        entities.extend(quoted)

        quoted_single = re.findall(r"'([^']+)'", query)
        entities.extend(quoted_single)

        # Remove duplicates while preserving order
        seen = set()
        unique_entities = []
        for e in entities:
            if e.lower() not in seen:
                seen.add(e.lower())
                unique_entities.append(e)

        return unique_entities


class EntityExtractorSimple:
    """Simple rule-based entity extractor (fallback when LLM is not available)"""

    def __init__(self):
        self.entity_types = ["Person", "Organization", "Location", "Concept"]

    async def extract(self, text: str) -> ExtractionResult:
        """Extract entities using simple heuristics"""
        entities = []

        # Extract capitalized phrases as potential entities
        words = text.split()
        i = 0
        while i < len(words):
            word = words[i].strip('.,!?;:()[]{}')
            if word and len(word) > 1 and word[0].isupper() and not word.isupper():
                entity_words = [word]
                j = i + 1
                while j < len(words) and j - i < 5:  # Max 5 words per entity
                    next_word = words[j].strip('.,!?;:()[]{}')
                    if next_word and next_word[0].isupper() and not next_word.isupper():
                        entity_words.append(next_word)
                        j += 1
                    else:
                        break

                entity_name = " ".join(entity_words)
                if len(entity_name) > 2:
                    entities.append(Entity(
                        name=entity_name,
                        type="Concept",
                        properties={}
                    ))
                i = j
            else:
                i += 1

        # Remove duplicates
        seen = set()
        unique_entities = []
        for e in entities:
            if e.name.lower() not in seen:
                seen.add(e.name.lower())
                unique_entities.append(e)

        return ExtractionResult(entities=unique_entities[:20], relations=[])
