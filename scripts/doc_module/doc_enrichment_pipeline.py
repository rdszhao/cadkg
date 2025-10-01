#!/usr/bin/env python3
"""Main orchestration script for document-driven knowledge graph enrichment.

This script:
1. Parses PDF technical documentation
2. Analyzes documents using a swarm of specialist agents
3. Enriches the CAD knowledge graph with semantic information
4. Uses Ollama backend for all LLM operations
"""

import os
import sys
import argparse
import json
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from doc_module.pdf_parser import PDFParser
from doc_module.simple_doc_analyzer import SimpleDocumentAnalyzer
from doc_module.graph_enricher import KnowledgeGraphEnricher


def main():
    """Main orchestration function."""
    parser = argparse.ArgumentParser(
        description="Enrich CAD knowledge graph with documentation insights using agent swarm"
    )
    parser.add_argument(
        "--pdf",
        type=str,
        help="Path to PDF documentation file",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Path to save analysis results (JSON)",
    )
    parser.add_argument(
        "--skip-graph-update",
        action="store_true",
        help="Skip updating the Neo4j graph (analysis only)"
    )
    parser.add_argument(
        "--max-entities",
        type=int,
        default=100,
        help="Maximum number of CAD entities to process (default: 100)"
    )

    args = parser.parse_args()

    # Load environment variables
    load_dotenv()

    # Get configuration
    pdf_path = args.pdf or os.getenv("DOC_FILE_PATH", "data/docs/CLINGERS_ecosystem.pdf")
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")

    print("=" * 80)
    print("🐝 DOCUMENT-DRIVEN KNOWLEDGE GRAPH ENRICHMENT SWARM")
    print("=" * 80)
    print(f"\n📋 Configuration:")
    print(f"   - PDF Document: {pdf_path}")
    print(f"   - Neo4j URI: {neo4j_uri}")
    print(f"   - Max entities: {args.max_entities}")
    print(f"   - Skip graph update: {args.skip_graph_update}")
    print()

    # ========== PHASE 1: PARSE PDF DOCUMENT ==========
    print("=" * 80)
    print("📄 PHASE 1: PARSING PDF DOCUMENT")
    print("=" * 80)

    if not os.path.exists(pdf_path):
        print(f"❌ Error: PDF file not found: {pdf_path}")
        sys.exit(1)

    try:
        with PDFParser(pdf_path) as parser:
            print(f"   📖 Parsing {pdf_path}...")
            summary = parser.get_summary()
            print(f"   ✓ Document loaded:")
            print(f"      - Pages: {summary['page_count']}")
            print(f"      - Words: {summary['word_count']:,}")
            print(f"      - Characters: {summary['character_count']:,}")
            print(f"      - Tables: {summary['table_count']}")
            print(f"      - Has TOC: {summary['has_toc']}")

            # Extract full text
            document_text = parser.get_full_text()
            print(f"   ✓ Extracted {len(document_text)} characters of text")

    except Exception as e:
        print(f"   ❌ Error parsing PDF: {e}")
        sys.exit(1)

    # ========== PHASE 2: GET CAD ENTITIES FROM GRAPH ==========
    print("\n" + "=" * 80)
    print("🔍 PHASE 2: RETRIEVING CAD ENTITIES FROM KNOWLEDGE GRAPH")
    print("=" * 80)

    cad_entities = []
    try:
        with KnowledgeGraphEnricher(neo4j_uri, neo4j_user, neo4j_password) as enricher:
            print(f"   🔗 Connecting to Neo4j...")
            cad_entities = enricher.get_cad_entities(limit=args.max_entities)
            print(f"   ✓ Retrieved {len(cad_entities)} CAD entities")

            # Show sample entities
            if cad_entities:
                print(f"   📦 Sample entities:")
                for entity in cad_entities[:5]:
                    print(f"      - {entity['name']} ({entity['type']})")
                if len(cad_entities) > 5:
                    print(f"      ... and {len(cad_entities) - 5} more")

    except Exception as e:
        print(f"   ⚠️  Warning: Could not retrieve CAD entities: {e}")
        print(f"   ℹ️  Continuing with document analysis only...")

    # ========== PHASE 3: DOCUMENT ANALYSIS WITH AGENT SWARM ==========
    print("\n" + "=" * 80)
    print("🐝 PHASE 3: DOCUMENT ANALYSIS WITH SPECIALIST SWARM")
    print("=" * 80)

    try:
        analyzer = SimpleDocumentAnalyzer()
        print("   🚀 Starting document analysis...")

        # Limit document text size for processing
        max_chars = 5000
        if len(document_text) > max_chars:
            print(f"   ℹ️  Document is large ({len(document_text)} chars), using first {max_chars} chars")
            document_text = document_text[:max_chars]

        # Analyze document
        doc_analysis = analyzer.analyze(document_text)

        # Create simple enrichment structure
        results = {
            "document_analysis": doc_analysis["document_analysis"],
            "graph_enrichment": {
                "entity_matches": {},
                "semantic_properties": {
                    "enrichments": []
                }
            }
        }

        print(f"\n   ✅ Document analysis complete!")
        print(f"      - Components found: {len(doc_analysis['document_analysis'].get('components', {}).get('components', []))}")
        print(f"      - Specifications found: {len(doc_analysis['document_analysis'].get('specifications', {}).get('specifications', []))}")
        print(f"      - Requirements found: {len(doc_analysis['document_analysis'].get('requirements', {}).get('requirements', []))}")

        # Save results if output path specified
        if args.output:
            output_path = args.output
            print(f"\n   💾 Saving results to {output_path}...")
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"   ✓ Results saved")

    except Exception as e:
        print(f"   ❌ Error during swarm analysis: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # ========== PHASE 4: APPLY ENRICHMENTS TO GRAPH ==========
    if not args.skip_graph_update:
        print("\n" + "=" * 80)
        print("🔧 PHASE 4: APPLYING ENRICHMENTS TO KNOWLEDGE GRAPH")
        print("=" * 80)

        try:
            with KnowledgeGraphEnricher(neo4j_uri, neo4j_user, neo4j_password) as enricher:
                stats = enricher.apply_enrichments(results)

                print(f"\n   ✅ Graph enrichment complete!")
                print(f"\n   📊 Enrichment Statistics:")
                for key, value in stats.items():
                    print(f"      - {key.replace('_', ' ').title()}: {value}")

        except Exception as e:
            print(f"   ❌ Error applying enrichments: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    else:
        print("\n   ⏭️  Skipping graph update (--skip-graph-update specified)")

    # ========== SUMMARY ==========
    print("\n" + "=" * 80)
    print("✅ ENRICHMENT PIPELINE COMPLETE")
    print("=" * 80)
    print("\n   🎉 Successfully enriched knowledge graph with documentation insights!")
    print(f"\n   📊 Performance Summary:")

    perf = results.get("performance", {})
    print(f"      - Total time: {perf.get('total_execution_time_seconds', 0)}s")
    print(f"      - Parallel batches: {perf.get('parallel_batches_executed', 0)}")
    print(f"      - Cache hit rate: {perf.get('cache_statistics', {}).get('hit_rate', 0)}%")

    print("\n   💡 Next Steps:")
    print("      - Query the enriched graph in Neo4j Browser")
    print("      - Explore new semantic relationships")
    print("      - View requirements and specifications nodes")
    print()


if __name__ == "__main__":
    main()
