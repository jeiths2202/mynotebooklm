from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging

from neo4j import GraphDatabase, Driver
from neo4j.exceptions import ServiceUnavailable, AuthError

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class Entity:
    """Represents an entity extracted from a document"""
    name: str
    type: str  # Person, Organization, Location, Concept, Event
    properties: Dict[str, Any] = None

    def __post_init__(self):
        if self.properties is None:
            self.properties = {}


@dataclass
class Relation:
    """Represents a relationship between two entities"""
    source: str  # Entity name
    target: str  # Entity name
    type: str  # WORKS_FOR, LOCATED_IN, RELATED_TO, MENTIONS, PART_OF
    properties: Dict[str, Any] = None

    def __post_init__(self):
        if self.properties is None:
            self.properties = {}


@dataclass
class GraphSearchResult:
    """Result from graph search"""
    entity_name: str
    entity_type: str
    related_entities: List[Dict[str, Any]]
    context_text: str
    relevance_score: float


class GraphStore:
    """Neo4j Knowledge Graph store for HybridRAG"""

    def __init__(self):
        self._driver: Optional[Driver] = None
        self._connected = False
        self._connect()

    def _connect(self) -> None:
        """Establish connection to Neo4j"""
        try:
            self._driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password)
            )
            # Verify connection
            self._driver.verify_connectivity()
            self._connected = True
            logger.info(f"Connected to Neo4j at {settings.neo4j_uri}")
            self._create_indexes()
        except (ServiceUnavailable, AuthError) as e:
            logger.warning(f"Failed to connect to Neo4j: {e}. Graph search will be disabled.")
            self._connected = False

    def _create_indexes(self) -> None:
        """Create indexes for better query performance"""
        if not self._connected:
            return

        with self._driver.session() as session:
            # Create indexes for entity lookup
            session.run("""
                CREATE INDEX entity_name IF NOT EXISTS
                FOR (e:Entity) ON (e.name)
            """)
            session.run("""
                CREATE INDEX entity_notebook IF NOT EXISTS
                FOR (e:Entity) ON (e.notebook_id)
            """)
            session.run("""
                CREATE INDEX entity_document IF NOT EXISTS
                FOR (e:Entity) ON (e.document_id)
            """)
            session.run("""
                CREATE INDEX chunk_document IF NOT EXISTS
                FOR (c:Chunk) ON (c.document_id)
            """)

    @property
    def is_connected(self) -> bool:
        """Check if Neo4j is connected"""
        return self._connected

    def add_entities(
        self,
        notebook_id: str,
        document_id: str,
        entities: List[Entity],
        relations: List[Relation],
        chunk_texts: List[str] = None
    ) -> None:
        """Add entities and relations to the knowledge graph"""
        if not self._connected:
            logger.warning("Neo4j not connected. Skipping graph storage.")
            return

        with self._driver.session() as session:
            # Create entities
            for entity in entities:
                session.run("""
                    MERGE (e:Entity {name: $name, notebook_id: $notebook_id})
                    ON CREATE SET
                        e.type = $type,
                        e.document_ids = [$document_id],
                        e.created_at = datetime()
                    ON MATCH SET
                        e.document_ids = CASE
                            WHEN NOT $document_id IN e.document_ids
                            THEN e.document_ids + $document_id
                            ELSE e.document_ids
                        END
                    SET e += $properties
                """, {
                    "name": entity.name,
                    "type": entity.type,
                    "notebook_id": notebook_id,
                    "document_id": document_id,
                    "properties": entity.properties or {}
                })

            # Create relations
            for relation in relations:
                session.run("""
                    MATCH (source:Entity {name: $source_name, notebook_id: $notebook_id})
                    MATCH (target:Entity {name: $target_name, notebook_id: $notebook_id})
                    MERGE (source)-[r:RELATES_TO {type: $rel_type}]->(target)
                    ON CREATE SET
                        r.document_ids = [$document_id],
                        r.created_at = datetime()
                    ON MATCH SET
                        r.document_ids = CASE
                            WHEN NOT $document_id IN r.document_ids
                            THEN r.document_ids + $document_id
                            ELSE r.document_ids
                        END
                    SET r += $properties
                """, {
                    "source_name": relation.source,
                    "target_name": relation.target,
                    "rel_type": relation.type,
                    "notebook_id": notebook_id,
                    "document_id": document_id,
                    "properties": relation.properties or {}
                })

            # Store chunk texts linked to entities
            if chunk_texts:
                for i, text in enumerate(chunk_texts):
                    session.run("""
                        CREATE (c:Chunk {
                            document_id: $document_id,
                            notebook_id: $notebook_id,
                            chunk_index: $chunk_index,
                            text: $text,
                            created_at: datetime()
                        })
                    """, {
                        "document_id": document_id,
                        "notebook_id": notebook_id,
                        "chunk_index": i,
                        "text": text[:1000]  # Limit text length
                    })

    def search_by_entities(
        self,
        notebook_id: str,
        query_entities: List[str],
        k_hop: int = None,
        top_k: int = 10
    ) -> List[GraphSearchResult]:
        """Search the graph by entity names and traverse related nodes"""
        if not self._connected:
            return []

        k_hop = k_hop or settings.graph_k_hop

        results = []
        with self._driver.session() as session:
            for entity_name in query_entities:
                # Find entity and its k-hop neighbors
                result = session.run("""
                    MATCH (e:Entity {notebook_id: $notebook_id})
                    WHERE toLower(e.name) CONTAINS toLower($entity_name)

                    // Get k-hop related entities
                    OPTIONAL MATCH path = (e)-[r:RELATES_TO*1..""" + str(k_hop) + """]->(related:Entity)

                    // Get associated chunks
                    OPTIONAL MATCH (c:Chunk {notebook_id: $notebook_id})
                    WHERE c.document_id IN e.document_ids

                    RETURN e.name AS entity_name,
                           e.type AS entity_type,
                           collect(DISTINCT {
                               name: related.name,
                               type: related.type,
                               relation: [rel IN relationships(path) | rel.type][0],
                               distance: length(path)
                           }) AS related_entities,
                           collect(DISTINCT c.text)[0..3] AS context_texts
                    LIMIT $top_k
                """, {
                    "notebook_id": notebook_id,
                    "entity_name": entity_name,
                    "top_k": top_k
                })

                for record in result:
                    related = [r for r in record["related_entities"] if r["name"] is not None]
                    context = " ".join([t for t in (record["context_texts"] or []) if t])

                    if record["entity_name"]:
                        results.append(GraphSearchResult(
                            entity_name=record["entity_name"],
                            entity_type=record["entity_type"] or "Unknown",
                            related_entities=related,
                            context_text=context,
                            relevance_score=1.0 / (1 + len(related))  # Simple scoring
                        ))

        return results[:top_k]

    def search_by_query(
        self,
        notebook_id: str,
        query: str,
        top_k: int = 10
    ) -> List[GraphSearchResult]:
        """Search the graph using a text query (fuzzy matching on entity names)"""
        if not self._connected:
            return []

        # Extract potential entity mentions from query
        # Simple approach: use individual words as potential entity names
        query_terms = [term.strip() for term in query.split() if len(term.strip()) > 2]

        results = []
        with self._driver.session() as session:
            result = session.run("""
                MATCH (e:Entity {notebook_id: $notebook_id})
                WHERE ANY(term IN $query_terms WHERE toLower(e.name) CONTAINS toLower(term))

                // Get related entities (1-hop)
                OPTIONAL MATCH (e)-[r:RELATES_TO]->(related:Entity)

                // Get associated chunks
                OPTIONAL MATCH (c:Chunk {notebook_id: $notebook_id})
                WHERE c.document_id IN e.document_ids

                WITH e, collect(DISTINCT {
                    name: related.name,
                    type: related.type,
                    relation: r.type
                }) AS related_entities,
                collect(DISTINCT c.text)[0..3] AS context_texts,
                size([term IN $query_terms WHERE toLower(e.name) CONTAINS toLower(term)]) AS match_score

                RETURN e.name AS entity_name,
                       e.type AS entity_type,
                       related_entities,
                       context_texts,
                       match_score
                ORDER BY match_score DESC
                LIMIT $top_k
            """, {
                "notebook_id": notebook_id,
                "query_terms": query_terms,
                "top_k": top_k
            })

            for record in result:
                related = [r for r in record["related_entities"] if r["name"] is not None]
                context = " ".join([t for t in (record["context_texts"] or []) if t])

                results.append(GraphSearchResult(
                    entity_name=record["entity_name"],
                    entity_type=record["entity_type"] or "Unknown",
                    related_entities=related,
                    context_text=context,
                    relevance_score=record["match_score"] / max(len(query_terms), 1)
                ))

        return results

    def get_entity_context(
        self,
        notebook_id: str,
        entity_names: List[str],
        k_hop: int = 1
    ) -> str:
        """Get context text from entities and their relations for LLM prompt"""
        if not self._connected or not entity_names:
            return ""

        context_parts = []
        with self._driver.session() as session:
            for name in entity_names:
                result = session.run("""
                    MATCH (e:Entity {notebook_id: $notebook_id})
                    WHERE toLower(e.name) = toLower($name)

                    OPTIONAL MATCH (e)-[r:RELATES_TO]->(related:Entity)

                    RETURN e.name AS name,
                           e.type AS type,
                           collect({
                               related_name: related.name,
                               relation: r.type
                           }) AS relations
                """, {
                    "notebook_id": notebook_id,
                    "name": name
                })

                for record in result:
                    entity_info = f"[{record['type']}] {record['name']}"
                    relations = [
                        f"  - {r['relation']} -> {r['related_name']}"
                        for r in record["relations"]
                        if r["related_name"]
                    ]
                    if relations:
                        entity_info += "\n" + "\n".join(relations)
                    context_parts.append(entity_info)

        return "\n\n".join(context_parts)

    def delete_document(self, notebook_id: str, document_id: str) -> None:
        """Delete all entities and relations for a document"""
        if not self._connected:
            return

        with self._driver.session() as session:
            # Remove document_id from entities
            session.run("""
                MATCH (e:Entity {notebook_id: $notebook_id})
                WHERE $document_id IN e.document_ids
                SET e.document_ids = [id IN e.document_ids WHERE id <> $document_id]
            """, {"notebook_id": notebook_id, "document_id": document_id})

            # Delete entities with no remaining document_ids
            session.run("""
                MATCH (e:Entity {notebook_id: $notebook_id})
                WHERE size(e.document_ids) = 0
                DETACH DELETE e
            """, {"notebook_id": notebook_id})

            # Delete chunks
            session.run("""
                MATCH (c:Chunk {notebook_id: $notebook_id, document_id: $document_id})
                DELETE c
            """, {"notebook_id": notebook_id, "document_id": document_id})

    def delete_notebook(self, notebook_id: str) -> None:
        """Delete all entities, relations, and chunks for a notebook"""
        if not self._connected:
            return

        with self._driver.session() as session:
            session.run("""
                MATCH (e:Entity {notebook_id: $notebook_id})
                DETACH DELETE e
            """, {"notebook_id": notebook_id})

            session.run("""
                MATCH (c:Chunk {notebook_id: $notebook_id})
                DELETE c
            """, {"notebook_id": notebook_id})

    def get_statistics(self, notebook_id: str) -> Dict[str, int]:
        """Get statistics for a notebook's graph"""
        if not self._connected:
            return {"entities": 0, "relations": 0, "chunks": 0}

        with self._driver.session() as session:
            result = session.run("""
                MATCH (e:Entity {notebook_id: $notebook_id})
                OPTIONAL MATCH (e)-[r:RELATES_TO]->()
                OPTIONAL MATCH (c:Chunk {notebook_id: $notebook_id})
                RETURN count(DISTINCT e) AS entities,
                       count(DISTINCT r) AS relations,
                       count(DISTINCT c) AS chunks
            """, {"notebook_id": notebook_id})

            record = result.single()
            return {
                "entities": record["entities"],
                "relations": record["relations"],
                "chunks": record["chunks"]
            }

    def close(self) -> None:
        """Close the Neo4j driver connection"""
        if self._driver:
            self._driver.close()
            self._connected = False

    def __del__(self):
        self.close()
