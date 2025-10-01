"""Main orchestration script for STEP file to Neo4j knowledge graph pipeline."""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv
sys.path.insert(0, str(Path(__file__).parent))

from step_parser import parse_step_file
from neo4j_schema import CADKnowledgeGraph
from agent import create_knowledge_graph_with_agent


def main():
    """Main entry point for the STEP to knowledge graph pipeline."""
    parser = argparse.ArgumentParser(
        description="Convert STEP file to Neo4j knowledge graph using OpenAI agents"
    )
    parser.add_argument(
        "--step-file",
        type=str,
        help="Path to STEP file (overrides .env)"
    )
    parser.add_argument(
        "--neo4j-uri",
        type=str,
        help="Neo4j URI (overrides .env)"
    )
    parser.add_argument(
        "--neo4j-user",
        type=str,
        help="Neo4j username (overrides .env)"
    )
    parser.add_argument(
        "--neo4j-password",
        type=str,
        help="Neo4j password (overrides .env)"
    )
    parser.add_argument(
        "--clear-graph",
        action="store_true",
        help="Clear existing graph data before loading"
    )
    parser.add_argument(
        "--skip-agent",
        action="store_true",
        help="Skip AI agent enrichment and use direct mapping"
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Only show statistics, don't populate graph"
    )

    args = parser.parse_args()

    load_dotenv()

    # configuration
    step_file_path = args.step_file or os.getenv("STEP_FILE_PATH")
    neo4j_uri = args.neo4j_uri or os.getenv("NEO4J_URI")
    neo4j_user = args.neo4j_user or os.getenv("NEO4J_USER")
    neo4j_password = args.neo4j_password or os.getenv("NEO4J_PASSWORD")

    # validate configuration
    if not step_file_path:
        print("[X] Error: STEP file path not provided")
        print("[OK]   Set STEP_FILE_PATH in .env or use --step-file")
        return 1

    if not Path(step_file_path).exists():
        print(f"L Error: STEP file not found: {step_file_path}")
        return 1

    if not args.stats_only:
        if not all([neo4j_uri, neo4j_user, neo4j_password]):
            print("[X] Error: Neo4j connection details not provided")
            print("[OK]   Set NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD in .env")
            return 1

        # ollama configuration if using agent
        if not args.skip_agent:
            ollama_base = os.getenv("OPENAI_API_BASE")
            manager_model = os.getenv("OPENAI_MODEL_MANAGER")
            specialist_model = os.getenv("OPENAI_MODEL_SPECIALIST")
            if not ollama_base or not manager_model or not specialist_model:
                print("[X] Error: Ollama configuration not found")
                print("[OK]   Set OPENAI_API_BASE, OPENAI_MODEL_MANAGER, and OPENAI_MODEL_SPECIALIST in .env")
                print("[OK]   Or use --skip-agent to skip AI enrichment")
                return 1

    print("=" * 70)
    print("STEP FILE TO NEO4J KNOWLEDGE GRAPH PIPELINE")
    print("=" * 70)
    print()

    # parse step file
    print("[*] Step 1: Parsing STEP file...")
    print(f"   File: {step_file_path}")
    print()

    assemblies, stats = parse_step_file(step_file_path)

    if not assemblies:
        print("[X] Error: Failed to parse STEP file")
        return 1

    print(" STEP file parsed successfully")
    print()
    print("[*] STEP File Statistics:")
    print(f"   - File: {stats['file_path']}")
    print(f"   - Root shapes: {stats['root_shapes_count']}")
    print(f"   - Total assemblies: {stats['total_assemblies']}")
    print(f"   - Total parts: {stats['total_parts']}")
    print(f"   - Total components: {stats['total_components']}")
    print()

    if args.stats_only:
        print("9  Stats-only mode enabled. Exiting.")
        return 0

    # process with agents (optional)
    if not args.skip_agent:
        print("[*] Step 2: Processing with multi-agent system...")
        print(f"   Base URL: {os.getenv('OPENAI_API_BASE')}")
        print(f"   Manager model: {os.getenv('OPENAI_MODEL_MANAGER')}")
        print(f"   Specialist model: {os.getenv('OPENAI_MODEL_SPECIALIST')}")
        print()

        try:
            enriched_data = create_knowledge_graph_with_agent(assemblies)
            print(" AI agent processing complete")
            print()
            print("[*] Agent Analysis:")
            print(f"   - Entities identified: {enriched_data['metadata']['total_entities']}")
            print(f"   - Relationships identified: {enriched_data['metadata']['total_relationships']}")
            print()
        except Exception as e:
            print(f"  Warning: AI agent processing failed: {str(e)}")
            print("[OK]   Falling back to direct mapping...")
            enriched_data = None
    else:
        print("  Step 2: Skipping AI agent (--skip-agent enabled)")
        print()
        enriched_data = None

    # connect to neo4j
    print("= Step 3: Connecting to Neo4j...")
    print(f"   URI: {neo4j_uri}")
    print()

    try:
        with CADKnowledgeGraph(neo4j_uri, neo4j_user, neo4j_password) as kg:
            # clear graph
            if args.clear_graph:
                print("=  Clearing existing graph data...")
                kg.clear_graph()
                print()

            # initialize schema
            print("<  Initializing Neo4j schema...")
            kg.initialize_schema()
            print()

            # populate graph
            print("[*] Step 4: Populating knowledge graph...")
            print()

            kg.populate_from_assembly_tree(assemblies)

            print(" Knowledge graph populated successfully")
            print()

            # get + display graph statistics
            graph_stats = kg.get_statistics()
            print("[*] Knowledge Graph Statistics:")
            print("   Nodes:")
            for label, count in graph_stats["nodes"].items():
                print(f"       - {label}: {count}")
            print(f"   - Total relationships: {graph_stats['relationships']}")
            print()

            # example queries
            print("[*] Sample Queries:")
            print()

            # query assembly hierarchy
            print("[OK]   Assembly Hierarchy (first 10):")
            hierarchy = kg.query_assembly_hierarchy()
            for i, item in enumerate(hierarchy[:10], 1):
                print(f"     {i}. {item['root']}  {item['child']} (depth: {item['depth']})")
            print()

            # query parts with geometry
            print("[OK]   Parts with Geometry (top 5 by vertex count):")
            parts = kg.find_parts_with_geometry()
            for i, part in enumerate(parts[:5], 1):
                print(f"     {i}. {part['part_name']}")
                print(f"        Vertices: {part['vertex_count']}, Edges: {part['edges']}, Faces: {part['faces']}")
            print()

        print("=" * 70)
        print(" PIPELINE COMPLETE")
        print("=" * 70)
        print()
        print("Next steps:")
        print("  - Open Neo4j Browser to explore the graph")
        print(f"  - Visit: {neo4j_uri.replace('bolt://', 'http://').replace(':7687', ':7474')}")
        print("  - Try queries like:")
        print("[OK]    MATCH (n) RETURN n LIMIT 25")
        print("[OK]    MATCH p=(a:Assembly)-[:CONTAINS*]->(child) RETURN p LIMIT 50")
        print()

        return 0

    except Exception as e:
        print(f"L Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
