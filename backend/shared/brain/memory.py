"""
Knowledge Graph Memory System
Ported from MCP Memory Server for the Trading Platform.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import json
import os

class Entity(BaseModel):
    """A node in the knowledge graph"""
    name: str
    entity_type: str
    observations: List[str] = Field(default_factory=list)

class Relation(BaseModel):
    """A directed edge in the knowledge graph"""
    source: str  # 'from' is reserved keyword
    target: str  # 'to' is reserved keyword
    relation_type: str

class KnowledgeGraph:
    """
    An in-memory knowledge graph that can persist to disk.
    Designed for trading context: Stocks, Sectors, Events, User Preferences.
    """
    
    def __init__(self, persist_path: Optional[str] = None):
        self.entities: Dict[str, Entity] = {}
        self.relations: List[Relation] = []
        self.persist_path = persist_path
        
        if persist_path and os.path.exists(persist_path):
            self._load()
    
    # --- Entity Operations ---
    def create_entities(self, entities: List[Dict[str, Any]]) -> List[str]:
        """Create multiple entities. Returns names of created entities."""
        created = []
        for e in entities:
            name = e.get("name")
            if name and name not in self.entities:
                self.entities[name] = Entity(
                    name=name,
                    entity_type=e.get("entity_type", "unknown"),
                    observations=e.get("observations", [])
                )
                created.append(name)
        self._save()
        return created
    
    def add_observations(self, entity_name: str, observations: List[str]) -> bool:
        """Add observations to an existing entity."""
        if entity_name not in self.entities:
            return False
        self.entities[entity_name].observations.extend(observations)
        self._save()
        return True
    
    def delete_entity(self, entity_name: str) -> bool:
        """Delete an entity and all its relations."""
        if entity_name not in self.entities:
            return False
        del self.entities[entity_name]
        # Cascade delete relations
        self.relations = [r for r in self.relations 
                         if r.source != entity_name and r.target != entity_name]
        self._save()
        return True
    
    # --- Relation Operations ---
    def create_relations(self, relations: List[Dict[str, Any]]) -> int:
        """Create multiple relations. Returns count of created."""
        count = 0
        for r in relations:
            rel = Relation(
                source=r.get("from", r.get("source", "")),
                target=r.get("to", r.get("target", "")),
                relation_type=r.get("relation_type", "")
            )
            # Check for duplicate
            if not any(existing.source == rel.source and 
                       existing.target == rel.target and 
                       existing.relation_type == rel.relation_type 
                       for existing in self.relations):
                self.relations.append(rel)
                count += 1
        self._save()
        return count
    
    # --- Query Operations ---
    def search_nodes(self, query: str) -> List[Entity]:
        """Search entities by name, type, or observation content."""
        query_lower = query.lower()
        results = []
        for entity in self.entities.values():
            if query_lower in entity.name.lower():
                results.append(entity)
            elif query_lower in entity.entity_type.lower():
                results.append(entity)
            elif any(query_lower in obs.lower() for obs in entity.observations):
                results.append(entity)
        return results
    
    def get_related(self, entity_name: str) -> Dict[str, Any]:
        """Get an entity and all its direct relations."""
        if entity_name not in self.entities:
            return {}
        
        entity = self.entities[entity_name]
        outgoing = [r for r in self.relations if r.source == entity_name]
        incoming = [r for r in self.relations if r.target == entity_name]
        
        return {
            "entity": entity.dict(),
            "outgoing_relations": [r.dict() for r in outgoing],
            "incoming_relations": [r.dict() for r in incoming]
        }
    
    def read_graph(self) -> Dict[str, Any]:
        """Return the full graph structure."""
        return {
            "entities": [e.dict() for e in self.entities.values()],
            "relations": [r.dict() for r in self.relations]
        }
    
    # --- Persistence ---
    def _save(self):
        if not self.persist_path:
            return
        data = self.read_graph()
        with open(self.persist_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _load(self):
        if not self.persist_path or not os.path.exists(self.persist_path):
            return
        with open(self.persist_path, 'r') as f:
            data = json.load(f)
        
        for e in data.get("entities", []):
            self.entities[e["name"]] = Entity(**e)
        
        for r in data.get("relations", []):
            self.relations.append(Relation(**r))
