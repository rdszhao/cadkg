#!/usr/bin/env python3
"""Simple test of a single agent to verify the framework works."""

import os
import asyncio
from dotenv import load_dotenv
from openai import AsyncOpenAI
from agents import Agent, Runner, OpenAIChatCompletionsModel, set_tracing_disabled

load_dotenv()
set_tracing_disabled(True)

async def test_single_agent():
    """Test a single specialist agent."""

    # Create client
    client = AsyncOpenAI(
        base_url=os.getenv("OPENAI_API_BASE", "http://127.0.0.1:11435/v1"),
        api_key=os.getenv("OPENAI_API_KEY", "ollama")
    )

    # Create model
    model = OpenAIChatCompletionsModel(
        model=os.getenv("OPENAI_MODEL_SPECIALIST", "gpt-oss:20b"),
        openai_client=client
    )

    # Create simple agent
    agent = Agent(
        name="Test Analyst",
        model=model,
        instructions="""You are a test analyst.

Analyze the provided text and return a JSON summary.

Output ONLY valid JSON in this format:
{
  "word_count": <number>,
  "summary": "<brief summary>",
  "key_topics": ["topic1", "topic2"]
}"""
    )

    # Test text
    test_text = """
    CLINGERS stands for Compliant Low-profile Independent Non-protruding Genderless Electronic
    Rendezvous System. CLINGERS is a genderless docking system with a mission to enable
    cooperative and communicative RPO.
    """

    print("🧪 Testing single agent...")
    print(f"📝 Input text: {test_text[:100]}...")
    print("\n🤖 Running agent...")

    result = await Runner.run(
        agent,
        f"Analyze this text:\n{test_text}",
        max_turns=5
    )

    print(f"\n✅ Agent completed!")
    print(f"📄 Output:\n{result.final_output}\n")

    return result.final_output

if __name__ == "__main__":
    output = asyncio.run(test_single_agent())
