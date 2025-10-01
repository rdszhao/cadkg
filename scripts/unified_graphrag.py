#!/usr/bin/env python3
"""Unified GraphRAG system for comprehensive Q&A across CAD, Documentation, and Code."""

import os
import sys
import argparse
import asyncio
from pathlib import Path
from typing import Dict, List
from dotenv import load_dotenv
from openai import AsyncOpenAI
from agents import Agent, Runner, OpenAIChatCompletionsModel, set_tracing_disabled
from neo4j import GraphDatabase

sys.path.insert(0, str(Path(__file__).parent))

load_dotenv()
set_tracing_disabled(True)


class UnifiedGraphRAG:
    """Unified GraphRAG system combining CAD, Documentation, and Code knowledge."""

    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        """Initialize unified RAG system.

        Args:
            neo4j_uri: Neo4j URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
        """
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

        self.client = AsyncOpenAI(
            base_url=os.getenv("OPENAI_API_BASE", "http://127.0.0.1:11435/v1"),
            api_key=os.getenv("OPENAI_API_KEY", "ollama")
        )

        # Use larger model for comprehensive reasoning
        self.model = OpenAIChatCompletionsModel(
            model=os.getenv("OPENAI_MODEL_MANAGER", "gpt-oss:120b"),
            openai_client=self.client
        )

        print(f"   ✓ Unified GraphRAG initialized with model: {os.getenv('OPENAI_MODEL_MANAGER', 'gpt-oss:120b')}")

    def close(self):
        """Close connections."""
        if self.driver:
            self.driver.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def get_system_overview(self) -> str:
        """Get comprehensive system overview from all data sources."""
        with self.driver.session() as session:
            # Get statistics
            stats_query = """
            MATCH (n)
            RETURN labels(n)[0] as type, count(n) as count
            ORDER BY count DESC
            """
            stats = session.run(stats_query)

            overview = ["=" * 80, "SYSTEM OVERVIEW", "=" * 80, ""]

            for record in stats:
                if record["type"]:
                    overview.append(f"{record['type']}: {record['count']}")

            return "\n".join(overview)

    def get_cad_context(self, query: str = None) -> str:
        """Get CAD assembly and part information."""
        with self.driver.session() as session:
            query_text = """
            MATCH (a:Assembly)
            OPTIONAL MATCH (a)-[:CONTAINS]->(p:Part)
            RETURN a.name as assembly, collect(DISTINCT p.name)[0..5] as sample_parts
            ORDER BY a.name
            LIMIT 10
            """

            result = session.run(query_text)
            context_parts = ["\n" + "=" * 80, "CAD ASSEMBLIES & PARTS", "=" * 80]

            for record in result:
                context_parts.append(f"\nAssembly: {record['assembly']}")
                if record['sample_parts'] and record['sample_parts'][0]:
                    context_parts.append(f"  Sample parts: {', '.join(record['sample_parts'][:3])}")

            return "\n".join(context_parts)

    def get_documentation_context(self, query: str = None) -> str:
        """Get requirements and specifications from documentation."""
        with self.driver.session() as session:
            # Get requirements
            req_query = """
            MATCH (r:Requirement)
            RETURN r.id, r.category, r.requirement, r.priority
            ORDER BY r.priority DESC, r.id
            LIMIT 15
            """

            context_parts = ["\n" + "=" * 80, "REQUIREMENTS", "=" * 80]

            reqs = session.run(req_query)
            for rec in reqs:
                context_parts.append(f"\n{rec[0]} [{rec[1]}] ({rec[3]})")
                context_parts.append(f"  {rec[2][:150]}...")

            # Get specifications
            spec_query = """
            MATCH (s:Specification)
            RETURN s.parameter, s.value, s.unit, s.category
            ORDER BY s.parameter
            LIMIT 15
            """

            context_parts.append("\n" + "=" * 80)
            context_parts.append("SPECIFICATIONS")
            context_parts.append("=" * 80)

            specs = session.run(spec_query)
            for rec in specs:
                context_parts.append(f"  {rec[0]}: {rec[1]} {rec[2] or ''}")

            return "\n".join(context_parts)

    def get_code_context(self, query: str = None) -> str:
        """Get code modules, classes, and functions."""
        with self.driver.session() as session:
            code_query = """
            MATCH (m:CodeModule)
            OPTIONAL MATCH (m)-[:CONTAINS_CLASS]->(c:CodeClass)
            RETURN m.name, m.purpose, m.domain, collect(DISTINCT c.name) as classes
            ORDER BY m.name
            """

            context_parts = ["\n" + "=" * 80, "CODE MODULES", "=" * 80]

            result = session.run(code_query)
            for rec in result:
                if rec[0]:
                    context_parts.append(f"\nModule: {rec[0]}")
                    if rec[2]:
                        context_parts.append(f"  Domain: {rec[2]}")
                    if rec[1]:
                        context_parts.append(f"  Purpose: {rec[1][:150]}...")
                    if rec[3] and rec[3][0]:
                        context_parts.append(f"  Classes: {', '.join(rec[3][:5])}")

            return "\n".join(context_parts)

    def get_comprehensive_context(self, query: str) -> str:
        """Get comprehensive context from all data sources.

        Args:
            query: User query

        Returns:
            Combined context from CAD, docs, and code
        """
        print(f"   🔍 Gathering context from knowledge graph...")

        context_parts = [
            self.get_system_overview(),
            self.get_cad_context(query),
            self.get_documentation_context(query),
            self.get_code_context(query)
        ]

        combined = "\n".join(context_parts)
        print(f"   📚 Retrieved {len(combined)} chars of context")

        return combined

    async def answer_question_async(self, question: str) -> str:
        """Answer a question using unified knowledge graph.

        Args:
            question: User question

        Returns:
            Comprehensive answer with cross-domain references
        """
        # Get comprehensive context
        context = self.get_comprehensive_context(question)

        print(f"   🤖 Generating comprehensive answer...")

        # Create unified RAG agent
        agent = Agent(
            name="Unified System Expert",
            model=self.model,
            instructions="""You are a system expert with comprehensive knowledge of:
- CAD assemblies and mechanical parts
- System requirements and specifications
- Software codebase and functionality

You have access to a complete knowledge graph integrating:
1. CAD geometry and assembly hierarchy
2. Requirements and specifications from documentation
3. Code modules, classes, and functions

GUIDELINES:
1. Answer holistically across all data sources
2. Make connections between CAD, docs, and code
3. Reference specific entities (parts, requirements, modules)
4. Explain how different aspects relate
5. Be specific with examples
6. If information is missing, say so

FORMAT:
- Start with direct answer
- Explain with cross-domain connections
- List relevant entities from CAD/docs/code
- Provide examples where helpful"""
        )

        prompt = f"""QUESTION: {question}

INTEGRATED SYSTEM KNOWLEDGE:
{context[:20000]}

Answer this question comprehensively using information from CAD models, documentation, and code."""

        result = await Runner.run(agent, prompt, max_turns=5)

        return result.final_output

    def answer_question(self, question: str) -> str:
        """Answer question (sync wrapper).

        Args:
            question: User question

        Returns:
            Answer
        """
        return asyncio.run(self.answer_question_async(question))

    async def ask_multiple_async(self, questions: List[str]) -> List[Dict[str, str]]:
        """Answer multiple questions.

        Args:
            questions: List of questions

        Returns:
            List of Q&A pairs
        """
        results = []

        for question in questions:
            print(f"\n{'='*100}")
            print(f"❓ {question}")
            print('='*100)

            answer = await self.answer_question_async(question)

            print(f"\n✅ Answer:\n{answer}\n")

            results.append({
                "question": question,
                "answer": answer
            })

        return results

    def ask_multiple(self, questions: List[str]) -> List[Dict[str, str]]:
        """Answer multiple questions (sync wrapper)."""
        return asyncio.run(self.ask_multiple_async(questions))


def main():
    """Interactive unified GraphRAG Q&A."""
    parser = argparse.ArgumentParser(description="Ask questions about the complete system")
    parser.add_argument("question", nargs='?', type=str, help="Question to ask")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")
    parser.add_argument("--demo", action="store_true", help="Run demo questions")

    args = parser.parse_args()

    # Configuration
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")

    if args.demo:
        # Demo mode with example questions
        print("=" * 100)
        print("🎯 UNIFIED GRAPHRAG DEMO")
        print("=" * 100)

        demo_questions = [
            "What is the CLINGERS system and how does it work?",
            "How do the PNP algorithm and the CAD parts relate?",
            "What requirements does the motor assembly satisfy?"
        ]

        with UnifiedGraphRAG(neo4j_uri, neo4j_user, neo4j_password) as rag:
            rag.ask_multiple(demo_questions)

    elif args.interactive:
        # Interactive mode
        print("=" * 100)
        print("💬 UNIFIED SYSTEM Q&A (type 'exit' to quit)")
        print("=" * 100)
        print("\n💡 Ask about CAD parts, requirements, code modules, or how they relate!")

        with UnifiedGraphRAG(neo4j_uri, neo4j_user, neo4j_password) as rag:
            while True:
                question = input("\n❓ Question: ").strip()

                if question.lower() in ['exit', 'quit', 'q']:
                    print("\n👋 Goodbye!")
                    break

                if not question:
                    continue

                try:
                    answer = rag.answer_question(question)
                    print(f"\n✅ Answer:\n{answer}\n")
                except Exception as e:
                    print(f"\n❌ Error: {e}\n")

    elif args.question:
        # Single question mode
        print("\n" + "=" * 100)
        print(f"❓ Question: {args.question}")
        print("=" * 100)

        with UnifiedGraphRAG(neo4j_uri, neo4j_user, neo4j_password) as rag:
            answer = rag.answer_question(args.question)

        print(f"\n✅ Answer:\n{answer}\n")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
