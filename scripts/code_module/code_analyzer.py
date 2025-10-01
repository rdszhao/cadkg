"""Code analysis agents for extracting functionality and creating knowledge graph data."""

import os
import json
import asyncio
from typing import Dict, List, Any
from openai import AsyncOpenAI
from agents import Agent, Runner, OpenAIChatCompletionsModel, set_tracing_disabled
from dotenv import load_dotenv

load_dotenv()
set_tracing_disabled(True)


class CodeAnalyzer:
    """Analyze code to extract functionality, purpose, and relationships."""

    def __init__(self):
        self.client = AsyncOpenAI(
            base_url=os.getenv("OPENAI_API_BASE", "http://127.0.0.1:11435/v1"),
            api_key=os.getenv("OPENAI_API_KEY", "ollama")
        )

        self.model = OpenAIChatCompletionsModel(
            model=os.getenv("OPENAI_MODEL_SPECIALIST", "gpt-oss:20b"),
            openai_client=self.client
        )

        print(f"   ✓ Code analyzer initialized with model: {os.getenv('OPENAI_MODEL_SPECIALIST', 'gpt-oss:20b')}")

    async def analyze_module_purpose(self, module_data: Dict, code_snippet: str) -> Dict:
        """Analyze module's purpose and functionality."""
        agent = Agent(
            name="Module Purpose Analyzer",
            model=self.model,
            instructions="""Analyze this Python module and describe its purpose and functionality.

Given the module structure and code, explain:
- What this module does
- Key algorithms/logic implemented
- Main responsibilities

Return JSON:
{
  "module_name": "...",
  "purpose": "concise description of what module does",
  "key_functionality": ["func1", "func2", ...],
  "algorithms": ["algorithm1", "algorithm2", ...],
  "domain": "technical domain (e.g., computer_vision, control_systems, communication)"
}"""
        )

        prompt = f"""Analyze this module:

Module: {module_data.get('module_name')}
Functions: {[f['name'] for f in module_data.get('functions', [])]}
Classes: {[c['name'] for c in module_data.get('classes', [])]}

Code snippet (first 2000 chars):
{code_snippet[:2000]}

Docstring: {module_data.get('docstring', 'None')}"""

        print(f"      📝 Analyzing {module_data.get('module_name')}...")
        result = await Runner.run(agent, prompt, max_turns=3)
        return self._extract_json(result.final_output)

    async def analyze_functions(self, functions: List[Dict], code_snippet: str) -> Dict:
        """Analyze what each function does."""
        agent = Agent(
            name="Function Analyzer",
            model=self.model,
            instructions="""Analyze Python functions and describe what they do.

For each function, explain:
- Purpose/what it does
- Key parameters
- Return value meaning
- Any algorithms used

Return JSON:
{
  "functions": [
    {
      "name": "function_name",
      "purpose": "what it does",
      "parameters": {"param": "description"},
      "returns": "what it returns",
      "algorithm": "algorithm used if any"
    }
  ]
}"""
        )

        func_list = "\n".join([
            f"- {f['name']}({', '.join(f['args'])})"
            for f in functions
        ])

        prompt = f"""Analyze these functions:

{func_list}

Code context:
{code_snippet[:2000]}"""

        print(f"      🔍 Analyzing {len(functions)} functions...")
        result = await Runner.run(agent, prompt, max_turns=3)
        return self._extract_json(result.final_output)

    async def analyze_classes(self, classes: List[Dict], code_snippet: str) -> Dict:
        """Analyze what each class does."""
        agent = Agent(
            name="Class Analyzer",
            model=self.model,
            instructions="""Analyze Python classes and describe their purpose and responsibilities.

For each class, explain:
- Purpose/what it represents
- Key methods and their roles
- State it maintains
- Design patterns used

Return JSON:
{
  "classes": [
    {
      "name": "ClassName",
      "purpose": "what it does/represents",
      "key_methods": {"method": "what it does"},
      "state": "what state/data it manages",
      "pattern": "design pattern if any"
    }
  ]
}"""
        )

        class_list = "\n".join([
            f"- {c['name']}: methods={[m['name'] for m in c.get('methods', [])]}, docstring={(c.get('docstring') or 'none')[:100]}"
            for c in classes
        ])

        prompt = f"""Analyze these classes:

{class_list}

Code context:
{code_snippet[:2000]}"""

        print(f"      📦 Analyzing {len(classes)} classes...")
        result = await Runner.run(agent, prompt, max_turns=3)
        return self._extract_json(result.final_output)

    async def analyze_dependencies(self, imports: List[Dict], module_name: str) -> Dict:
        """Analyze module dependencies and how they're used."""
        agent = Agent(
            name="Dependency Analyzer",
            model=self.model,
            instructions="""Analyze module dependencies and categorize them.

Categorize imports as:
- standard_library: Python standard libs
- third_party: External packages
- local: Local project modules

Return JSON:
{
  "dependencies": {
    "standard_library": ["module1", ...],
    "third_party": ["package1", ...],
    "local": ["module1", ...]
  },
  "key_dependencies": ["most important dependencies"]
}"""
        )

        imports_list = "\n".join([
            f"- {imp.get('module', '')}.{imp.get('name', '')}" if imp['type'] == 'from_import'
            else f"- {imp.get('module', '')}"
            for imp in imports
        ])

        prompt = f"""Module: {module_name}

Imports:
{imports_list}"""

        print(f"      🔗 Analyzing dependencies...")
        result = await Runner.run(agent, prompt, max_turns=3)
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

    async def analyze_module_async(self, module_data: Dict, code_content: str) -> Dict:
        """Analyze a complete module."""
        print(f"   🚀 Analyzing module: {module_data.get('module_name')}")

        # Run all analyses in parallel
        tasks = [
            self.analyze_module_purpose(module_data, code_content)
        ]

        if module_data.get('functions'):
            tasks.append(self.analyze_functions(module_data['functions'], code_content))

        if module_data.get('classes'):
            tasks.append(self.analyze_classes(module_data['classes'], code_content))

        if module_data.get('imports'):
            tasks.append(self.analyze_dependencies(module_data['imports'], module_data.get('module_name')))

        results = await asyncio.gather(*tasks)

        # Combine results
        analysis = {
            "module": module_data.get('module_name'),
            "file_path": module_data.get('file_path'),
            "purpose": results[0] if results else {},
            "functions": {},
            "classes": {},
            "dependencies": {}
        }

        idx = 1
        if module_data.get('functions') and idx < len(results):
            analysis["functions"] = results[idx]
            idx += 1

        if module_data.get('classes') and idx < len(results):
            analysis["classes"] = results[idx]
            idx += 1

        if module_data.get('imports') and idx < len(results):
            analysis["dependencies"] = results[idx]

        return analysis

    def analyze_module(self, module_data: Dict, code_content: str) -> Dict:
        """Analyze module (sync wrapper)."""
        return asyncio.run(self.analyze_module_async(module_data, code_content))


class CodebaseAnalyzer:
    """Analyze entire codebase."""

    def __init__(self):
        self.analyzer = CodeAnalyzer()

    async def analyze_codebase_async(self, modules_data: List[Dict], code_contents: Dict[str, str]) -> List[Dict]:
        """Analyze all modules in codebase."""
        print(f"\n   📊 Analyzing {len(modules_data)} modules...")

        analyses = []
        for module_data in modules_data:
            module_name = module_data.get('module_name')
            code_content = code_contents.get(module_name, '')

            analysis = await self.analyzer.analyze_module_async(module_data, code_content)
            analyses.append(analysis)

        return analyses

    def analyze_codebase(self, modules_data: List[Dict], code_contents: Dict[str, str]) -> List[Dict]:
        """Analyze codebase (sync wrapper)."""
        return asyncio.run(self.analyze_codebase_async(modules_data, code_contents))


def analyze_code_module(module_data: Dict, code_content: str) -> Dict:
    """Convenience function to analyze a single module."""
    analyzer = CodeAnalyzer()
    return analyzer.analyze_module(module_data, code_content)
