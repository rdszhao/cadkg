#!/usr/bin/env python3
"""Ask questions about the codebase using GraphRAG."""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

from code_module.code_rag import CodeRAG

load_dotenv()


def main():
    """Answer questions about code."""
    parser = argparse.ArgumentParser(description="Ask questions about the codebase")
    parser.add_argument("question", type=str, help="Question to ask")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")

    args = parser.parse_args()

    # Configuration
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")

    if args.interactive:
        # Interactive mode
        print("=" * 80)
        print("💬 INTERACTIVE CODE Q&A (type 'exit' to quit)")
        print("=" * 80)

        with CodeRAG(neo4j_uri, neo4j_user, neo4j_password) as rag:
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

    else:
        # Single question mode
        print("\n" + "=" * 80)
        print(f"❓ Question: {args.question}")
        print("=" * 80)

        with CodeRAG(neo4j_uri, neo4j_user, neo4j_password) as rag:
            answer = rag.answer_question(args.question)

        print(f"\n✅ Answer:\n{answer}\n")


if __name__ == "__main__":
    main()
