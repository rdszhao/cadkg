"""GraphRAG system for code Q&A using Neo4j knowledge graph."""

import os
import asyncio
from typing import Dict, List
from openai import AsyncOpenAI
from agents import Agent, Runner, OpenAIChatCompletionsModel, set_tracing_disabled
from dotenv import load_dotenv
from .code_graph_enricher import CodeKnowledgeGraphEnricher

load_dotenv()
set_tracing_disabled(True)


class CodeRAG:
    """GraphRAG system for answering questions about code using knowledge graph."""

    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        """Initialize RAG system.

        Args:
            neo4j_uri: Neo4j URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
        """
        self.enricher = CodeKnowledgeGraphEnricher(neo4j_uri, neo4j_user, neo4j_password)

        self.client = AsyncOpenAI(
            base_url=os.getenv("OPENAI_API_BASE", "http://127.0.0.1:11435/v1"),
            api_key=os.getenv("OPENAI_API_KEY", "ollama")
        )

        # Use larger model for better reasoning
        self.model = OpenAIChatCompletionsModel(
            model=os.getenv("OPENAI_MODEL_MANAGER", "gpt-oss:120b"),
            openai_client=self.client
        )

        print(f"   ✓ RAG system initialized with model: {os.getenv('OPENAI_MODEL_MANAGER', 'gpt-oss:120b')}")

    def close(self):
        """Close connections."""
        self.enricher.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def get_relevant_context(self, question: str) -> str:
        """Retrieve relevant context from knowledge graph.

        Args:
            question: User question

        Returns:
            Relevant code context
        """
        # For now, get all context
        # TODO: Implement semantic search/filtering based on question
        return self.enricher.get_all_code_context()

    async def answer_question_async(self, question: str) -> str:
        """Answer a question about the codebase.

        Args:
            question: User question

        Returns:
            Answer with code references
        """
        print(f"\n   🔍 Retrieving relevant code context...")

        # Get context from graph
        context = self.get_relevant_context(question)

        print(f"   📚 Context retrieved ({len(context)} chars)")
        print(f"   🤖 Generating answer...")

        # Create RAG agent
        agent = Agent(
            name="Code Q&A Agent",
            model=self.model,
            instructions="""You are a code expert answering questions about a codebase.

You have access to detailed information about code modules, functions, classes, and their purposes extracted from a knowledge graph.

GUIDELINES:
1. Answer based on the provided context
2. Be specific and reference actual code elements (modules, functions, classes)
3. Explain technical concepts clearly
4. If information is not in context, say so
5. Provide code examples or module names when relevant

FORMAT:
- Start with direct answer
- Provide details with code references
- List relevant modules/functions/classes
- Be concise but informative"""
        )

        prompt = f"""QUESTION: {question}

CODE CONTEXT:
{context[:15000]}

Please answer the question based on this codebase information."""

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
            print(f"\n{'='*80}")
            print(f"Q: {question}")
            print('='*80)

            answer = await self.answer_question_async(question)

            print(f"\nA: {answer}\n")

            results.append({
                "question": question,
                "answer": answer
            })

        return results

    def ask_multiple(self, questions: List[str]) -> List[Dict[str, str]]:
        """Answer multiple questions (sync wrapper).

        Args:
            questions: List of questions

        Returns:
            List of Q&A pairs
        """
        return asyncio.run(self.ask_multiple_async(questions))


def answer_code_question(
    question: str,
    neo4j_uri: str = "bolt://localhost:7687",
    neo4j_user: str = "neo4j",
    neo4j_password: str = "password"
) -> str:
    """Convenience function to answer a single question.

    Args:
        question: Question about the code
        neo4j_uri: Neo4j URI
        neo4j_user: Neo4j username
        neo4j_password: Neo4j password

    Returns:
        Answer
    """
    with CodeRAG(neo4j_uri, neo4j_user, neo4j_password) as rag:
        return rag.answer_question(question)
