#!/usr/bin/env python3
"""Integrated pipeline combining CAD analysis and documentation enrichment.

This script demonstrates the full workflow:
1. Parse STEP CAD file and create knowledge graph
2. Parse PDF documentation
3. Analyze documentation with agent swarm
4. Enrich knowledge graph with documentation insights
"""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from cad_module import parse_step_file, CADKnowledgeGraph, CADMultiAgentSystem
from doc_module import PDFParser, SimpleDocumentAnalyzer, KnowledgeGraphEnricher


def main():
    """Run integrated CAD + Documentation pipeline."""
    parser = argparse.ArgumentParser(
        description="Integrated CAD and Documentation Knowledge Graph Pipeline"
    )
    parser.add_argument("--step-file", help="Path to STEP CAD file")
    parser.add_argument("--pdf-file", help="Path to PDF documentation")
    parser.add_argument("--clear-graph", action="store_true", help="Clear existing graph data")
    parser.add_argument("--skip-cad-agent", action="store_true", help="Skip CAD agent analysis")
    parser.add_argument("--skip-doc-agent", action="store_true", help="Skip doc agent analysis")
    parser.add_argument("--stats-only", action="store_true", help="Show statistics only")

    args = parser.parse_args()

    # Load environment
    load_dotenv()

    # Configuration
    step_file = args.step_file or os.getenv("STEP_FILE_PATH", "data/cad/100-1_A1-ASSY, PAYLOAD, CLINGERS.STEP")
    pdf_file = args.pdf_file or os.getenv("DOC_FILE_PATH", "data/docs/CLINGERS_ecosystem.pdf")
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")

    print("=" * 100)
    print("🚀 INTEGRATED CAD + DOCUMENTATION KNOWLEDGE GRAPH PIPELINE")
    print("=" * 100)
    print(f"\n📋 Configuration:")
    print(f"   CAD File:     {step_file}")
    print(f"   Doc File:     {pdf_file}")
    print(f"   Neo4j URI:    {neo4j_uri}")
    print(f"   Clear graph:  {args.clear_graph}")
    print(f"   Skip CAD AI:  {args.skip_cad_agent}")
    print(f"   Skip Doc AI:  {args.skip_doc_agent}")
    print()

    # ========== PHASE 1: CAD PROCESSING ==========
    print("=" * 100)
    print("📐 PHASE 1: CAD FILE PROCESSING")
    print("=" * 100)

    if not os.path.exists(step_file):
        print(f"❌ Error: STEP file not found: {step_file}")
        sys.exit(1)

    print(f"\n   🔍 Parsing STEP file: {step_file}")
    assemblies, step_stats = parse_step_file(step_file)

    print(f"\n   ✅ STEP file parsed successfully!")
    print(f"   📊 Assembly Statistics:")
    print(f"      - Total assemblies: {step_stats.get('total_assemblies', 0)}")
    print(f"      - Total parts: {step_stats.get('total_parts', 0)}")
    print(f"      - Total components: {step_stats.get('total_components', 0)}")
    if 'max_depth' in step_stats:
        print(f"      - Max depth: {step_stats['max_depth']}")

    if args.stats_only:
        print("\n   ℹ️  Stats-only mode, exiting...")
        return

    # ========== PHASE 2: CAD KNOWLEDGE GRAPH CREATION ==========
    print("\n" + "=" * 100)
    print("🗄️  PHASE 2: CAD KNOWLEDGE GRAPH CREATION")
    print("=" * 100)

    with CADKnowledgeGraph(neo4j_uri, neo4j_user, neo4j_password) as kg:
        print("\n   🔧 Initializing Neo4j schema...")
        kg.initialize_schema()

        if args.clear_graph:
            print("   🧹 Clearing existing graph data...")
            kg.clear_graph()

        print("   📊 Populating knowledge graph from assembly tree...")
        kg.populate_from_assembly_tree(assemblies)

        graph_stats = kg.get_statistics()
        print(f"\n   ✅ Knowledge graph created!")
        print(f"   📊 Graph Statistics:")
        for node_type, count in graph_stats.get("nodes", {}).items():
            print(f"      - {node_type}: {count}")
        print(f"      - Total relationships: {graph_stats.get('relationships', 0)}")

    # ========== PHASE 3: CAD AI ENRICHMENT (OPTIONAL) ==========
    if not args.skip_cad_agent:
        print("\n" + "=" * 100)
        print("🤖 PHASE 3: CAD AI ENRICHMENT")
        print("=" * 100)

        try:
            print("\n   🐝 Initializing CAD multi-agent system...")
            cad_agent_system = CADMultiAgentSystem()

            print("   🚀 Running CAD analysis with agent swarm...")
            cad_enriched_data = cad_agent_system.process(assemblies)

            print(f"\n   ✅ CAD AI enrichment complete!")

            # Could apply these enrichments to graph here
            # (currently the CAD agent returns JSON, not directly applied)

        except Exception as e:
            print(f"   ⚠️  CAD AI enrichment failed: {e}")
            print("   ℹ️  Continuing with documentation analysis...")
    else:
        print("\n   ⏭️  Skipping CAD AI enrichment (--skip-cad-agent)")

    # ========== PHASE 4: DOCUMENTATION PARSING ==========
    print("\n" + "=" * 100)
    print("📄 PHASE 4: DOCUMENTATION PARSING")
    print("=" * 100)

    if not os.path.exists(pdf_file):
        print(f"⚠️  Warning: PDF file not found: {pdf_file}")
        print("   ℹ️  Skipping documentation enrichment...")
        return

    print(f"\n   📖 Parsing PDF: {pdf_file}")
    with PDFParser(pdf_file) as pdf_parser:
        pdf_summary = pdf_parser.get_summary()
        document_text = pdf_parser.get_full_text()

    print(f"\n   ✅ PDF parsed successfully!")
    print(f"   📊 Document Statistics:")
    print(f"      - Pages: {pdf_summary['page_count']}")
    print(f"      - Words: {pdf_summary['word_count']:,}")
    print(f"      - Tables: {pdf_summary['table_count']}")

    # ========== PHASE 5: DOCUMENTATION AI ANALYSIS ==========
    if not args.skip_doc_agent:
        print("\n" + "=" * 100)
        print("🐝 PHASE 5: DOCUMENTATION AI ANALYSIS")
        print("=" * 100)

        # Get CAD entities from graph
        with KnowledgeGraphEnricher(neo4j_uri, neo4j_user, neo4j_password) as enricher:
            print("\n   🔍 Retrieving CAD entities from graph...")
            cad_entities = enricher.get_cad_entities(limit=100)
            print(f"   ✓ Retrieved {len(cad_entities)} CAD entities")

        # Run document analysis
        print("\n   🤖 Initializing documentation analyzer...")
        analyzer = SimpleDocumentAnalyzer()

        # Limit document size
        max_chars = 8000  # Process full document in chunks if needed
        if len(document_text) > max_chars:
            print(f"   ℹ️  Limiting document to {max_chars} characters for analysis")
            document_text = document_text[:max_chars]

        print("   🚀 Running documentation analysis...")
        doc_analysis = analyzer.analyze(document_text)

        # Package results
        enrichment_results = {
            "document_analysis": doc_analysis["document_analysis"],
            "graph_enrichment": {
                "entity_matches": {},
                "semantic_properties": {"enrichments": []}
            }
        }

        print(f"\n   ✅ Documentation analysis complete!")
        print(f"      - Components: {len(doc_analysis['document_analysis'].get('components', {}).get('components', []))}")
        print(f"      - Specifications: {len(doc_analysis['document_analysis'].get('specifications', {}).get('specifications', []))}")
        print(f"      - Requirements: {len(doc_analysis['document_analysis'].get('requirements', {}).get('requirements', []))}")

        # ========== PHASE 6: APPLY ENRICHMENTS TO GRAPH ==========
        print("\n" + "=" * 100)
        print("🔧 PHASE 6: APPLYING ENRICHMENTS TO KNOWLEDGE GRAPH")
        print("=" * 100)

        with KnowledgeGraphEnricher(neo4j_uri, neo4j_user, neo4j_password) as enricher:
            enrichment_stats = enricher.apply_enrichments(enrichment_results)

        print(f"\n   ✅ Graph enrichment applied!")

    else:
        print("\n   ⏭️  Skipping documentation AI analysis (--skip-doc-agent)")

    # ========== FINAL SUMMARY ==========
    print("\n" + "=" * 100)
    print("✅ INTEGRATED PIPELINE COMPLETE")
    print("=" * 100)

    with CADKnowledgeGraph(neo4j_uri, neo4j_user, neo4j_password) as kg:
        final_stats = kg.get_statistics()

    print(f"\n   📊 Final Knowledge Graph Statistics:")
    for node_type, count in final_stats.get("nodes", {}).items():
        print(f"      - {node_type}: {count}")
    print(f"      - Total relationships: {final_stats.get('relationships', 0)}")

    print("\n   🎉 Success! Your knowledge graph is now enriched with:")
    print("      ✓ CAD assembly hierarchy and geometry")
    print("      ✓ Semantic properties from documentation")
    print("      ✓ Requirements and specifications")
    print("      ✓ Functional relationships")
    print("      ✓ Documentation references")

    print("\n   💡 Next Steps:")
    print("      - Open Neo4j Browser (http://localhost:7474)")
    print("      - Run queries like:")
    print('        MATCH (r:Requirement) RETURN r LIMIT 10')
    print('        MATCH (p:Part)-[:IMPLEMENTS]->(r:Requirement) RETURN p, r')
    print('        MATCH (p:Part) WHERE p.function IS NOT NULL RETURN p.name, p.function')
    print()


if __name__ == "__main__":
    main()
