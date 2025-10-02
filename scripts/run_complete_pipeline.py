#!/usr/bin/env python3
"""Complete pipeline orchestrator - runs CAD, Documentation, and Code analysis end-to-end."""

import os
import sys
import time
import subprocess
import argparse
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()


class CompletePipelineRunner:
    """Orchestrates the complete CAD + Docs + Code pipeline."""

    def __init__(self, skip_cad: bool = False, skip_docs: bool = False, skip_code: bool = False,
                 clear_graph: bool = True, launch_chat: bool = False):
        """Initialize pipeline runner.

        Args:
            skip_cad: Skip CAD analysis
            skip_docs: Skip documentation analysis
            skip_code: Skip code analysis
            clear_graph: Clear existing graph before starting
            launch_chat: Launch chat interface after completion
        """
        self.skip_cad = skip_cad
        self.skip_docs = skip_docs
        self.skip_code = skip_code
        self.clear_graph = clear_graph
        self.launch_chat = launch_chat

        self.scripts_dir = Path(__file__).parent
        self.venv_python = self.scripts_dir.parent / ".venv" / "bin" / "python"

        # Configuration
        self.neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD", "password")

        # Pipeline statistics
        self.stats = {
            "total_time": 0,
            "cad_time": 0,
            "docs_time": 0,
            "code_time": 0,
            "nodes_created": 0,
            "relationships_created": 0
        }

    def print_header(self, title: str):
        """Print formatted section header."""
        print("\n" + "=" * 100)
        print(f"🚀 {title}")
        print("=" * 100 + "\n")

    def print_step(self, step_num: int, total_steps: int, description: str):
        """Print step information."""
        print(f"\n{'─' * 100}")
        print(f"📍 STEP {step_num}/{total_steps}: {description}")
        print("─" * 100 + "\n")

    def run_command(self, cmd: list, description: str) -> bool:
        """Run a command and track execution time.

        Args:
            cmd: Command to run as list
            description: Description of the command

        Returns:
            True if successful, False otherwise
        """
        print(f"▶️  {description}...")
        start_time = time.time()

        try:
            result = subprocess.run(
                cmd,
                cwd=self.scripts_dir.parent,
                check=True,
                capture_output=False,
                text=True
            )

            elapsed = time.time() - start_time
            print(f"✅ {description} completed in {elapsed:.1f}s\n")
            return True

        except subprocess.CalledProcessError as e:
            elapsed = time.time() - start_time
            print(f"❌ {description} failed after {elapsed:.1f}s")
            print(f"Error: {e}")
            return False

    def verify_neo4j_connection(self) -> bool:
        """Verify Neo4j is accessible."""
        try:
            driver = GraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password)
            )
            driver.verify_connectivity()
            driver.close()
            print("✅ Neo4j connection verified\n")
            return True
        except Exception as e:
            print(f"❌ Cannot connect to Neo4j: {e}")
            print(f"\nPlease ensure:")
            print(f"  1. Neo4j is running")
            print(f"  2. Connection details in .env are correct:")
            print(f"     NEO4J_URI={self.neo4j_uri}")
            print(f"     NEO4J_USER={self.neo4j_user}")
            return False

    def get_graph_statistics(self) -> dict:
        """Get current graph statistics."""
        try:
            driver = GraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password)
            )

            with driver.session() as session:
                # Get node counts
                node_result = session.run("""
                    MATCH (n)
                    RETURN labels(n)[0] as type, count(n) as count
                    ORDER BY count DESC
                """)

                nodes = {}
                total_nodes = 0
                for record in node_result:
                    if record["type"]:
                        nodes[record["type"]] = record["count"]
                        total_nodes += record["count"]

                # Get relationship count
                rel_result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
                total_rels = rel_result.single()["count"]

            driver.close()

            return {
                "nodes": nodes,
                "total_nodes": total_nodes,
                "total_relationships": total_rels
            }

        except Exception as e:
            print(f"Warning: Could not get graph statistics: {e}")
            return {"nodes": {}, "total_nodes": 0, "total_relationships": 0}

    def print_statistics(self):
        """Print pipeline statistics."""
        self.print_header("PIPELINE STATISTICS")

        # Get final graph statistics
        graph_stats = self.get_graph_statistics()

        print(f"⏱️  Execution Times:")
        if not self.skip_cad:
            print(f"   CAD Analysis:     {self.stats['cad_time']:.1f}s")
        if not self.skip_docs:
            print(f"   Doc Analysis:     {self.stats['docs_time']:.1f}s")
        if not self.skip_code:
            print(f"   Code Analysis:    {self.stats['code_time']:.1f}s")
        print(f"   ─────────────────────────────")
        print(f"   Total Time:       {self.stats['total_time']:.1f}s ({self.stats['total_time']/60:.1f} minutes)")

        print(f"\n📊 Knowledge Graph Contents:")
        if graph_stats["nodes"]:
            for node_type, count in graph_stats["nodes"].items():
                print(f"   {node_type:20s} {count:4d}")
            print(f"   ─────────────────────────────")
            print(f"   Total Nodes:      {graph_stats['total_nodes']:4d}")
            print(f"   Total Relationships: {graph_stats['total_relationships']:4d}")
        else:
            print("   No statistics available")

    def run_pipeline(self) -> bool:
        """Run the complete pipeline.

        Returns:
            True if successful, False otherwise
        """
        pipeline_start = time.time()

        self.print_header("COMPLETE CADKG PIPELINE")

        print(f"📋 Configuration:")
        print(f"   CAD Analysis:     {'❌ SKIPPED' if self.skip_cad else '✅ ENABLED'}")
        print(f"   Doc Analysis:     {'❌ SKIPPED' if self.skip_docs else '✅ ENABLED'}")
        print(f"   Code Analysis:    {'❌ SKIPPED' if self.skip_code else '✅ ENABLED'}")
        print(f"   Clear Graph:      {'✅ YES' if self.clear_graph else '❌ NO'}")
        print(f"   Launch Chat:      {'✅ YES' if self.launch_chat else '❌ NO'}")

        # Calculate total steps
        total_steps = 1  # Neo4j verification
        if not self.skip_cad:
            total_steps += 1
        if not self.skip_docs:
            total_steps += 1
        if not self.skip_code:
            total_steps += 1
        total_steps += 1  # Statistics
        if self.launch_chat:
            total_steps += 1

        current_step = 0

        # Step: Verify Neo4j connection
        current_step += 1
        self.print_step(current_step, total_steps, "Verifying Neo4j Connection")
        if not self.verify_neo4j_connection():
            return False

        # Step 1: CAD Analysis
        if not self.skip_cad:
            current_step += 1
            self.print_step(current_step, total_steps, "CAD Analysis & Graph Creation")

            cad_start = time.time()
            cmd = [str(self.venv_python), "scripts/integrated_pipeline.py"]
            if self.clear_graph:
                cmd.append("--clear-graph")
            cmd.append("--skip-cad-agent")

            if not self.run_command(cmd, "Running CAD pipeline"):
                print("❌ CAD pipeline failed. Aborting.")
                return False

            self.stats['cad_time'] = time.time() - cad_start

        # Step 2: Documentation Analysis
        if not self.skip_docs:
            current_step += 1
            self.print_step(current_step, total_steps, "Documentation Analysis & Graph Enrichment")

            docs_start = time.time()
            cmd = [str(self.venv_python), "scripts/doc_module/doc_enrichment_pipeline.py"]

            if not self.run_command(cmd, "Running documentation pipeline"):
                print("❌ Documentation pipeline failed. Aborting.")
                return False

            self.stats['docs_time'] = time.time() - docs_start

        # Step 3: Code Analysis
        if not self.skip_code:
            current_step += 1
            self.print_step(current_step, total_steps, "Code Analysis & Graph Enrichment")

            code_start = time.time()
            cmd = [str(self.venv_python), "scripts/code_module/code_pipeline.py"]

            if not self.run_command(cmd, "Running code pipeline"):
                print("❌ Code pipeline failed. Aborting.")
                return False

            self.stats['code_time'] = time.time() - code_start

        # Calculate total time
        self.stats['total_time'] = time.time() - pipeline_start

        # Step: Print Statistics
        current_step += 1
        self.print_step(current_step, total_steps, "Pipeline Statistics")
        self.print_statistics()

        # Success message
        print("\n" + "=" * 100)
        print("🎉 PIPELINE COMPLETED SUCCESSFULLY!")
        print("=" * 100 + "\n")

        # Step: Launch Chat Interface
        if self.launch_chat:
            current_step += 1
            self.print_step(current_step, total_steps, "Launching Chat Interface")
            print("\n🚀 Starting Gradio chat interface...")
            print("   Press Ctrl+C to stop the server\n")

            cmd = [str(self.venv_python), "scripts/chat_interface.py"]
            subprocess.run(cmd, cwd=self.scripts_dir.parent)
        else:
            print("\n💡 Next Steps:")
            print("   • Launch chat interface:")
            print("     .venv/bin/python scripts/chat_interface.py")
            print("\n   • Query GraphRAG directly:")
            print("     .venv/bin/python scripts/unified_graphrag.py \"Your question here\"")
            print("\n   • Interactive mode:")
            print("     .venv/bin/python scripts/unified_graphrag.py --interactive\n")

        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run complete cadKG pipeline (CAD + Docs + Code)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run complete pipeline
  python scripts/run_complete_pipeline.py

  # Run without clearing graph
  python scripts/run_complete_pipeline.py --no-clear

  # Skip code analysis (faster)
  python scripts/run_complete_pipeline.py --skip-code

  # Run and launch chat interface
  python scripts/run_complete_pipeline.py --launch-chat

  # Only CAD and docs
  python scripts/run_complete_pipeline.py --skip-code
        """
    )

    parser.add_argument(
        "--skip-cad",
        action="store_true",
        help="Skip CAD analysis"
    )
    parser.add_argument(
        "--skip-docs",
        action="store_true",
        help="Skip documentation analysis"
    )
    parser.add_argument(
        "--skip-code",
        action="store_true",
        help="Skip code analysis"
    )
    parser.add_argument(
        "--no-clear",
        action="store_true",
        help="Don't clear existing graph (append instead)"
    )
    parser.add_argument(
        "--launch-chat",
        action="store_true",
        help="Launch chat interface after completion"
    )

    args = parser.parse_args()

    # Validation
    if args.skip_cad and args.skip_docs and args.skip_code:
        print("❌ Error: Cannot skip all modules. At least one must be enabled.")
        sys.exit(1)

    # Create and run pipeline
    runner = CompletePipelineRunner(
        skip_cad=args.skip_cad,
        skip_docs=args.skip_docs,
        skip_code=args.skip_code,
        clear_graph=not args.no_clear,
        launch_chat=args.launch_chat
    )

    success = runner.run_pipeline()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
