from backend.shared.brain.memory import KnowledgeGraph
import json

def test_memory():
    # Initialize an in-memory graph (no persistence for test)
    kg = KnowledgeGraph()
    
    # 1. Create Entities
    print("--- Creating Entities ---")
    created = kg.create_entities([
        {"name": "AAPL", "entity_type": "stock", "observations": ["Tech giant", "iPhone maker"]},
        {"name": "TSLA", "entity_type": "stock", "observations": ["EV leader", "High volatility"]},
        {"name": "Tech_Sector", "entity_type": "sector", "observations": ["Growth sector"]},
        {"name": "Q4_Earnings", "entity_type": "event", "observations": ["Starts Oct 2026"]}
    ])
    print(f"Created: {created}")
    
    # 2. Create Relations
    print("\n--- Creating Relations ---")
    count = kg.create_relations([
        {"from": "AAPL", "to": "Tech_Sector", "relation_type": "belongs_to"},
        {"from": "TSLA", "to": "Tech_Sector", "relation_type": "belongs_to"},
        {"from": "AAPL", "to": "Q4_Earnings", "relation_type": "reports_on"}
    ])
    print(f"Created {count} relations")
    
    # 3. Add Observations
    print("\n--- Adding Observations ---")
    kg.add_observations("AAPL", ["Price target $200", "Bullish RSI"])
    
    # 4. Search
    print("\n--- Searching for 'Tech' ---")
    results = kg.search_nodes("Tech")
    for r in results:
        print(f"  Found: {r.name} ({r.entity_type})")
    
    # 5. Get Related
    print("\n--- Getting AAPL's Relations ---")
    related = kg.get_related("AAPL")
    print(json.dumps(related, indent=2))
    
    # 6. Read Full Graph
    print("\n--- Full Graph Summary ---")
    graph = kg.read_graph()
    print(f"Entities: {len(graph['entities'])}, Relations: {len(graph['relations'])}")

if __name__ == "__main__":
    test_memory()
