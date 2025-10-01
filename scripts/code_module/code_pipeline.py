#!/usr/bin/env python3
"""Pipeline for analyzing codebase and creating GraphRAG system."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

from code_module.code_parser import CodebaseParser
from code_module.code_analyzer import CodebaseAnalyzer
from code_module.code_graph_enricher import CodeKnowledgeGraphEnricher

load_dotenv()


def main():
    """Run code analysis pipeline."""
    # Configuration
    codebase_path = os.getenv("CODEBASE_PATH", "data/codebase")
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")

    print("=" * 100)
    print("💻 CODEBASE ANALYSIS & GRAPHRAG PIPELINE")
    print("=" * 100)
    print(f"\n📋 Configuration:")
    print(f"   Codebase: {codebase_path}")
    print(f"   Neo4j URI: {neo4j_uri}")
    print()

    # ========== PHASE 1: PARSE CODEBASE ==========
    print("=" * 100)
    print("📄 PHASE 1: PARSING CODEBASE")
    print("=" * 100)

    parser = CodebaseParser(codebase_path)
    modules = parser.parse_all()
    summary = parser.get_codebase_summary()

    print(f"\n   ✅ Parsed {summary['module_count']} modules")
    print(f"   📊 Codebase Statistics:")
    print(f"      - Total lines: {summary['total_lines']:,}")
    print(f"      - Total functions: {summary['total_functions']}")
    print(f"      - Total classes: {summary['total_classes']}")

    print(f"\n   📦 Modules:")
    for mod in summary['modules']:
        print(f"      - {mod['name']}: {mod['lines']} lines, {mod['functions']} funcs, {mod['classes']} classes")

    # ========== PHASE 2: ANALYZE CODE WITH AI ==========
    print("\n" + "=" * 100)
    print("🤖 PHASE 2: AI-POWERED CODE ANALYSIS")
    print("=" * 100)

    # Load code contents
    code_contents = {}
    for module_data in modules:
        module_name = module_data.get('module_name')
        file_path = module_data.get('file_path')
        try:
            with open(file_path, 'r') as f:
                code_contents[module_name] = f.read()
        except Exception as e:
            print(f"   ⚠️  Could not read {file_path}: {e}")
            code_contents[module_name] = ""

    # Analyze with AI
    analyzer = CodebaseAnalyzer()
    analyses = analyzer.analyze_codebase(modules, code_contents)

    print(f"\n   ✅ Analysis complete for {len(analyses)} modules")

    # ========== PHASE 3: ENRICH KNOWLEDGE GRAPH ==========
    print("\n" + "=" * 100)
    print("🔧 PHASE 3: ENRICHING KNOWLEDGE GRAPH")
    print("=" * 100)

    with CodeKnowledgeGraphEnricher(neo4j_uri, neo4j_user, neo4j_password) as enricher:
        stats = enricher.enrich_graph_with_code(analyses)

    # ========== SUMMARY ==========
    print("\n" + "=" * 100)
    print("✅ CODEBASE ANALYSIS COMPLETE")
    print("=" * 100)

    print(f"\n   📊 Final Statistics:")
    print(f"      - Code Modules: {stats['modules_created']}")
    print(f"      - Functions: {stats['functions_created']}")
    print(f"      - Classes: {stats['classes_created']}")
    print(f"      - Dependencies: {stats['dependencies_created']}")

    print(f"\n   🎉 GraphRAG system ready for code Q&A!")
    print(f"\n   💡 Try asking questions:")
    print(f"      python scripts/code_module/ask_question.py \"What does the PNP module do?\"")
    print(f"      python scripts/code_module/ask_question.py \"How does the motor control work?\"")
    print()


if __name__ == "__main__":
    main()
