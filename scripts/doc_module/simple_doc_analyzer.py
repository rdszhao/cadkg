"""Simplified document analyzer - direct specialist calls without complex orchestration."""

import os
import json
import asyncio
from typing import Dict, List, Any
from openai import AsyncOpenAI
from agents import Agent, Runner, OpenAIChatCompletionsModel, set_tracing_disabled
from dotenv import load_dotenv

load_dotenv()
set_tracing_disabled(True)


class SimpleDocumentAnalyzer:
    """Simplified document analyzer with direct agent calls."""

    def __init__(self):
        self.client = AsyncOpenAI(
            base_url=os.getenv("OPENAI_API_BASE", "http://127.0.0.1:11435/v1"),
            api_key=os.getenv("OPENAI_API_KEY", "ollama")
        )

        self.model = OpenAIChatCompletionsModel(
            model=os.getenv("OPENAI_MODEL_SPECIALIST", "gpt-oss:20b"),
            openai_client=self.client
        )

        print(f"   ✓ Initialized with model: {os.getenv('OPENAI_MODEL_SPECIALIST', 'gpt-oss:20b')}")

    async def analyze_components(self, text: str) -> Dict:
        """Extract components from documentation."""
        agent = Agent(
            name="Component Identifier",
            model=self.model,
            instructions="""Extract components/parts from technical documentation.

Return JSON:
{
  "components": [
    {"name": "...", "type": "...", "description": "..."}
  ]
}"""
        )

        print("      🔍 Analyzing components...")
        result = await Runner.run(agent, f"Extract components from:\n{text}", max_turns=3)
        return self._extract_json(result.final_output)

    async def extract_specs(self, text: str) -> Dict:
        """Extract technical specifications."""
        agent = Agent(
            name="Spec Extractor",
            model=self.model,
            instructions="""Extract technical specifications.

Return JSON:
{
  "specifications": [
    {"parameter": "...", "value": "...", "unit": "..."}
  ]
}"""
        )

        print("      📐 Extracting specifications...")
        result = await Runner.run(agent, f"Extract specs from:\n{text}", max_turns=3)
        return self._extract_json(result.final_output)

    async def extract_requirements(self, text: str) -> Dict:
        """Extract requirements."""
        agent = Agent(
            name="Requirements Analyst",
            model=self.model,
            instructions="""Extract functional requirements.

Return JSON:
{
  "requirements": [
    {"requirement": "...", "category": "...", "priority": "..."}
  ]
}"""
        )

        print("      📋 Extracting requirements...")
        result = await Runner.run(agent, f"Extract requirements from:\n{text}", max_turns=3)
        return self._extract_json(result.final_output)

    def _extract_json(self, text: str) -> Dict:
        """Extract JSON from text."""
        try:
            if "```json" in text:
                json_str = text.split("```json")[1].split("```")[0]
                return json.loads(json_str.strip())
            if '{' in text:
                start = text.index('{')
                end = text.rindex('}') + 1
                return json.loads(text[start:end])
            return json.loads(text.strip())
        except:
            return {"error": "Could not parse JSON", "raw": text[:200]}

    async def analyze_async(self, text: str) -> Dict:
        """Analyze document with all specialists in parallel."""
        print("   🚀 Running analysis with specialists...")

        # Run all in parallel
        components_task = self.analyze_components(text)
        specs_task = self.extract_specs(text)
        reqs_task = self.extract_requirements(text)

        components, specs, reqs = await asyncio.gather(
            components_task,
            specs_task,
            reqs_task
        )

        return {
            "document_analysis": {
                "components": components,
                "specifications": specs,
                "requirements": reqs
            }
        }

    def analyze(self, text: str) -> Dict:
        """Analyze document (sync wrapper)."""
        return asyncio.run(self.analyze_async(text))


def analyze_document_simple(text: str) -> Dict:
    """Simple document analysis function."""
    analyzer = SimpleDocumentAnalyzer()
    return analyzer.analyze(text)
