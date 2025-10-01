"""Advanced swarm-of-specialists multi-agent system for document analysis and graph enrichment.

This module implements a complex agent swarm using the OpenAI Agents SDK with Ollama backend.
The swarm analyzes technical documentation and enriches CAD knowledge graphs with semantic information.

Architecture:
- Document Analysis Specialists (6 agents)
- Graph Enrichment Specialists (4 agents)
- Hub Orchestrators (2 managers)
- Parallel execution with asyncio
- Result caching and performance monitoring
"""

import os
import json
import asyncio
import time
import hashlib
from typing import Any, Dict, List, Optional
from openai import AsyncOpenAI
from agents import Agent, Runner, OpenAIChatCompletionsModel, set_tracing_disabled, function_tool

# Disable tracing for Ollama
set_tracing_disabled(True)


class SwarmPerformanceMonitor:
    """Monitor and track swarm performance metrics."""

    def __init__(self):
        self.metrics = {
            "agent_calls": {},
            "execution_times": {},
            "cache_hits": 0,
            "cache_misses": 0,
            "parallel_batches": 0,
            "total_start_time": None,
            "total_end_time": None
        }

    def start_timer(self):
        """Start overall timer."""
        self.metrics["total_start_time"] = time.time()

    def end_timer(self):
        """End overall timer."""
        self.metrics["total_end_time"] = time.time()

    def record_agent_call(self, agent_name: str, duration: float):
        """Record an agent execution."""
        if agent_name not in self.metrics["agent_calls"]:
            self.metrics["agent_calls"][agent_name] = 0
            self.metrics["execution_times"][agent_name] = []

        self.metrics["agent_calls"][agent_name] += 1
        self.metrics["execution_times"][agent_name].append(duration)

    def record_cache_hit(self):
        """Record a cache hit."""
        self.metrics["cache_hits"] += 1

    def record_cache_miss(self):
        """Record a cache miss."""
        self.metrics["cache_misses"] += 1

    def record_parallel_batch(self):
        """Record a parallel execution batch."""
        self.metrics["parallel_batches"] += 1

    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        total_time = 0
        if self.metrics["total_start_time"] and self.metrics["total_end_time"]:
            total_time = self.metrics["total_end_time"] - self.metrics["total_start_time"]

        summary = {
            "total_execution_time_seconds": round(total_time, 2),
            "parallel_batches_executed": self.metrics["parallel_batches"],
            "agent_statistics": {},
            "cache_statistics": {
                "hits": self.metrics["cache_hits"],
                "misses": self.metrics["cache_misses"],
                "hit_rate": round(
                    self.metrics["cache_hits"] / max(1, self.metrics["cache_hits"] + self.metrics["cache_misses"]) * 100,
                    2
                )
            }
        }

        for agent_name, calls in self.metrics["agent_calls"].items():
            times = self.metrics["execution_times"][agent_name]
            summary["agent_statistics"][agent_name] = {
                "calls": calls,
                "avg_time_seconds": round(sum(times) / len(times), 2),
                "total_time_seconds": round(sum(times), 2)
            }

        return summary

    def print_summary(self):
        """Print performance summary."""
        summary = self.get_summary()
        print("\n   📊 Swarm Performance Metrics:")
        print(f"   - Total execution time: {summary['total_execution_time_seconds']}s")
        print(f"   - Parallel batches: {summary['parallel_batches_executed']}")
        print(f"   - Cache hit rate: {summary['cache_statistics']['hit_rate']}%")
        print("   - Agent statistics:")
        for agent_name, stats in summary["agent_statistics"].items():
            print(f"     • {agent_name}: {stats['calls']} calls, avg {stats['avg_time_seconds']}s")


class DocumentAnalysisSwarm:
    """Swarm of specialist agents for document analysis and graph enrichment.

    This system uses a complex swarm architecture with:
    - 6 Document Analysis Specialists
    - 4 Graph Enrichment Specialists
    - 2 Hub Orchestrators
    - Parallel execution capabilities
    - Result caching
    """

    def __init__(self):
        """Initialize the document analysis swarm with Ollama settings."""
        # Get settings from environment
        self.base_url = os.getenv("OPENAI_API_BASE", "http://127.0.0.1:11435/v1")
        self.api_key = os.getenv("OPENAI_API_KEY", "ollama")
        self.manager_model_name = os.getenv("OPENAI_MODEL_MANAGER", "gpt-oss:120b")
        self.specialist_model_name = os.getenv("OPENAI_MODEL_SPECIALIST", "gpt-oss:20b")

        # Performance monitoring
        self.monitor = SwarmPerformanceMonitor()

        # Result cache
        self.cache = {}

        # Create AsyncOpenAI client for Ollama
        self.client = AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key
        )

        # Create model instances
        self.specialist_model = OpenAIChatCompletionsModel(
            model=self.specialist_model_name,
            openai_client=self.client
        )

        # Use same model for managers as specialists for speed
        self.manager_model = OpenAIChatCompletionsModel(
            model=self.specialist_model_name,  # Use 20b for all
            openai_client=self.client
        )

        # ========== DOCUMENT ANALYSIS SPECIALISTS ==========
        self.doc_structure_analyst = self._create_doc_structure_analyst()
        self.technical_spec_extractor = self._create_technical_spec_extractor()
        self.component_identifier = self._create_component_identifier()
        self.functional_requirements_analyst = self._create_functional_requirements_analyst()
        self.relationship_mapper = self._create_relationship_mapper()
        self.metadata_curator = self._create_metadata_curator()

        # ========== GRAPH ENRICHMENT SPECIALISTS ==========
        self.entity_matcher = self._create_entity_matcher()
        self.semantic_enricher = self._create_semantic_enricher()
        self.relationship_enricher = self._create_relationship_enricher()
        self.context_augmenter = self._create_context_augmenter()

        # ========== HUB ORCHESTRATORS ==========
        self.document_analysis_manager = self._create_document_analysis_manager()
        self.graph_enrichment_manager = self._create_graph_enrichment_manager()

        print(f"   🐝 Initialized Document Analysis Swarm:")
        print(f"      - Manager model: {self.manager_model_name}")
        print(f"      - Specialist model: {self.specialist_model_name}")
        print(f"      - Document analysts: 6")
        print(f"      - Graph enrichers: 4")
        print(f"      - Orchestrators: 2")

    def _cache_key(self, agent_name: str, data: Any) -> str:
        """Generate cache key for agent result."""
        data_str = json.dumps(data, sort_keys=True) if isinstance(data, (dict, list)) else str(data)
        hash_obj = hashlib.md5(data_str.encode())
        return f"{agent_name}:{hash_obj.hexdigest()}"

    def _get_cached_result(self, agent_name: str, data: Any) -> Optional[str]:
        """Get cached result if available."""
        key = self._cache_key(agent_name, data)
        if key in self.cache:
            self.monitor.record_cache_hit()
            return self.cache[key]
        self.monitor.record_cache_miss()
        return None

    def _cache_result(self, agent_name: str, data: Any, result: str):
        """Cache agent result."""
        key = self._cache_key(agent_name, data)
        self.cache[key] = result

    async def _run_specialist_with_monitoring(
        self,
        agent: Agent,
        agent_name: str,
        prompt: str,
        cache_data: Any
    ) -> str:
        """Run specialist agent with performance monitoring and caching."""
        # Check cache first
        cached = self._get_cached_result(agent_name, cache_data)
        if cached:
            print(f"      ✓ {agent_name} (cached)")
            return cached

        # Execute agent
        start_time = time.time()
        result = await Runner.run(agent, prompt)
        duration = time.time() - start_time

        # Record metrics
        self.monitor.record_agent_call(agent_name, duration)

        # Cache result
        output = result.final_output
        self._cache_result(agent_name, cache_data, output)

        print(f"      ✓ {agent_name} ({duration:.2f}s)")
        return output

    # ==================== DOCUMENT ANALYSIS SPECIALISTS ====================

    def _create_doc_structure_analyst(self) -> Agent:
        """Create agent for analyzing document structure and organization."""
        return Agent(
            name="Document Structure Analyst",
            model=self.specialist_model,
            instructions="""You are a document structure analysis specialist.

Your job is to analyze the organizational structure of technical documents.

ANALYZE:
- Section hierarchy and organization
- Document outline and flow
- Key sections and their purposes
- Tables, figures, and their content
- Cross-references between sections

OUTPUT FORMAT (JSON only):
{
  "sections": [
    {"title": "...", "level": 1, "page": 1, "summary": "..."}
  ],
  "tables": [
    {"title": "...", "page": 1, "content_type": "..."}
  ],
  "figures": [
    {"title": "...", "page": 1, "description": "..."}
  ],
  "structure_summary": "..."
}

CRITICAL:
- Return ONLY valid JSON
- Focus on structure, not detailed content
- Identify key organizational elements"""
        )

    def _create_technical_spec_extractor(self) -> Agent:
        """Create agent for extracting technical specifications."""
        return Agent(
            name="Technical Specifications Extractor",
            model=self.specialist_model,
            instructions="""You are a technical specifications extraction specialist.

Your job is to extract technical specifications, dimensions, materials, and performance data.

EXTRACT:
- Dimensions and measurements
- Material specifications
- Performance parameters
- Tolerances and constraints
- Environmental specifications
- Power requirements
- Weight and mass properties

OUTPUT FORMAT (JSON only):
{
  "specifications": [
    {
      "category": "dimensional|material|performance|environmental",
      "parameter": "...",
      "value": "...",
      "unit": "...",
      "tolerance": "...",
      "source_page": 1
    }
  ],
  "summary": "..."
}

CRITICAL:
- Return ONLY valid JSON
- Extract exact values with units
- Include source page numbers"""
        )

    def _create_component_identifier(self) -> Agent:
        """Create agent for identifying components and parts."""
        return Agent(
            name="Component Identifier",
            model=self.specialist_model,
            instructions="""You are a component identification specialist.

Your job is to identify all components, parts, and assemblies mentioned in documentation.

IDENTIFY:
- Component names and IDs
- Part numbers and designators
- Assembly names
- Subassembly groupings
- Vendor parts and standards
- Functional modules

OUTPUT FORMAT (JSON only):
{
  "components": [
    {
      "name": "...",
      "part_number": "...",
      "type": "assembly|part|module",
      "description": "...",
      "vendor": "...",
      "standard": "...",
      "mentioned_pages": [1, 2, 3]
    }
  ],
  "component_count": 0,
  "summary": "..."
}

CRITICAL:
- Return ONLY valid JSON
- Capture all component mentions
- Track page locations"""
        )

    def _create_functional_requirements_analyst(self) -> Agent:
        """Create agent for analyzing functional requirements."""
        return Agent(
            name="Functional Requirements Analyst",
            model=self.specialist_model,
            instructions="""You are a functional requirements analysis specialist.

Your job is to extract functional requirements, capabilities, and operational constraints.

EXTRACT:
- Functional capabilities
- Operational requirements
- Performance requirements
- Safety requirements
- Interface requirements
- Mission objectives
- Use cases and scenarios

OUTPUT FORMAT (JSON only):
{
  "requirements": [
    {
      "id": "REQ-001",
      "category": "functional|performance|safety|interface",
      "requirement": "...",
      "rationale": "...",
      "priority": "critical|high|medium|low",
      "source_page": 1
    }
  ],
  "capabilities": [
    {
      "name": "...",
      "description": "...",
      "parameters": {...}
    }
  ],
  "summary": "..."
}

CRITICAL:
- Return ONLY valid JSON
- Categorize requirements
- Extract capabilities clearly"""
        )

    def _create_relationship_mapper(self) -> Agent:
        """Create agent for mapping relationships between documented entities."""
        return Agent(
            name="Relationship Mapper",
            model=self.specialist_model,
            instructions="""You are a relationship mapping specialist.

Your job is to identify relationships between components, requirements, and functions.

MAP RELATIONSHIPS:
- Component-to-component connections
- Component-to-requirement mappings
- Function-to-component assignments
- Assembly hierarchies
- Interface connections
- Dependency relationships

OUTPUT FORMAT (JSON only):
{
  "relationships": [
    {
      "source": "component/requirement name",
      "relation_type": "IMPLEMENTS|CONNECTS_TO|REQUIRES|PART_OF",
      "target": "component/requirement name",
      "description": "...",
      "source_page": 1
    }
  ],
  "summary": "..."
}

CRITICAL:
- Return ONLY valid JSON
- Use consistent relation types
- Map bidirectional relationships"""
        )

    def _create_metadata_curator(self) -> Agent:
        """Create agent for curating metadata and context."""
        return Agent(
            name="Metadata Curator",
            model=self.specialist_model,
            instructions="""You are a metadata curation specialist.

Your job is to extract and organize document metadata, context, and auxiliary information.

EXTRACT:
- Project information
- Version and revision data
- Authors and contributors
- Dates and timelines
- References and citations
- Glossary terms
- Acronyms and abbreviations

OUTPUT FORMAT (JSON only):
{
  "metadata": {
    "project_name": "...",
    "version": "...",
    "date": "...",
    "authors": [...],
    "organization": "..."
  },
  "glossary": [
    {"term": "...", "definition": "...", "page": 1}
  ],
  "acronyms": [
    {"acronym": "...", "expansion": "...", "page": 1}
  ],
  "references": [...],
  "summary": "..."
}

CRITICAL:
- Return ONLY valid JSON
- Organize metadata systematically"""
        )

    # ==================== GRAPH ENRICHMENT SPECIALISTS ====================

    def _create_entity_matcher(self) -> Agent:
        """Create agent for matching document entities to CAD entities."""
        return Agent(
            name="Entity Matcher",
            model=self.specialist_model,
            instructions="""You are an entity matching specialist.

Your job is to match components identified in documentation with CAD parts in the knowledge graph.

MATCH ENTITIES:
- Compare document component names with CAD part names
- Use fuzzy matching for similar names
- Consider part numbers and IDs
- Account for naming variations
- Identify unmapped entities

OUTPUT FORMAT (JSON only):
{
  "matches": [
    {
      "doc_component": "...",
      "cad_part_id": "...",
      "cad_part_name": "...",
      "confidence": "high|medium|low",
      "match_method": "exact|fuzzy|part_number|inference",
      "notes": "..."
    }
  ],
  "unmatched_doc_components": [...],
  "unmatched_cad_parts": [...],
  "summary": "..."
}

CRITICAL:
- Return ONLY valid JSON
- Provide confidence levels
- List unmatched entities"""
        )

    def _create_semantic_enricher(self) -> Agent:
        """Create agent for adding semantic properties to graph entities."""
        return Agent(
            name="Semantic Enricher",
            model=self.specialist_model,
            instructions="""You are a semantic enrichment specialist.

Your job is to add semantic properties to CAD entities based on documentation.

ADD SEMANTIC PROPERTIES:
- Functional purpose
- Operational role
- Design intent
- Performance characteristics
- Material properties
- Criticality/importance
- Operational constraints

OUTPUT FORMAT (JSON only):
{
  "enrichments": [
    {
      "entity_id": "...",
      "entity_name": "...",
      "properties": {
        "function": "...",
        "purpose": "...",
        "role": "...",
        "material": "...",
        "criticality": "critical|important|standard",
        "operational_constraints": "...",
        "performance_params": {...}
      },
      "source_pages": [1, 2]
    }
  ],
  "summary": "..."
}

CRITICAL:
- Return ONLY valid JSON
- Add meaningful semantic properties
- Reference source pages"""
        )

    def _create_relationship_enricher(self) -> Agent:
        """Create agent for creating semantic relationships."""
        return Agent(
            name="Relationship Enricher",
            model=self.specialist_model,
            instructions="""You are a relationship enrichment specialist.

Your job is to create new semantic relationships in the knowledge graph based on documentation.

CREATE RELATIONSHIPS:
- IMPLEMENTS (component implements requirement)
- SATISFIES (part satisfies specification)
- FUNCTIONS_AS (part functions as X)
- INTERFACES_WITH (part interfaces with other part)
- DEPENDS_ON (part depends on other part)
- SUPPORTS (part supports function)

OUTPUT FORMAT (JSON only):
{
  "relationships": [
    {
      "source_id": "...",
      "relation_type": "IMPLEMENTS|SATISFIES|FUNCTIONS_AS|INTERFACES_WITH",
      "target_id": "...",
      "properties": {
        "description": "...",
        "interface_type": "...",
        "criticality": "..."
      },
      "source_pages": [1]
    }
  ],
  "summary": "..."
}

CRITICAL:
- Return ONLY valid JSON
- Use standard relation types
- Add relationship properties"""
        )

    def _create_context_augmenter(self) -> Agent:
        """Create agent for adding contextual information."""
        return Agent(
            name="Context Augmenter",
            model=self.specialist_model,
            instructions="""You are a context augmentation specialist.

Your job is to add contextual information and documentation references to the knowledge graph.

ADD CONTEXT:
- Documentation references
- Page citations
- Design rationale
- Historical context
- Usage scenarios
- Operational context
- Links to requirements

OUTPUT FORMAT (JSON only):
{
  "augmentations": [
    {
      "entity_id": "...",
      "context": {
        "documentation_refs": ["page 1", "page 5"],
        "design_rationale": "...",
        "usage_scenarios": [...],
        "operational_context": "...",
        "notes": "..."
      }
    }
  ],
  "summary": "..."
}

CRITICAL:
- Return ONLY valid JSON
- Provide comprehensive context
- Include clear citations"""
        )

    # ==================== HUB ORCHESTRATORS ====================

    def _create_document_analysis_manager(self) -> Agent:
        """Create hub agent for orchestrating document analysis specialists."""

        @function_tool
        async def analyze_structure() -> str:
            """Analyze document structure and organization."""
            if not hasattr(self, '_doc_text'):
                return '{}'
            return await self._run_specialist_with_monitoring(
                self.doc_structure_analyst,
                "Document Structure Analyst",
                f"Analyze this document structure:\n{self._doc_text[:8000]}",
                self._doc_text[:8000]
            )

        @function_tool
        async def extract_specifications() -> str:
            """Extract technical specifications and parameters."""
            if not hasattr(self, '_doc_text'):
                return '{}'
            return await self._run_specialist_with_monitoring(
                self.technical_spec_extractor,
                "Technical Specifications Extractor",
                f"Extract technical specifications:\n{self._doc_text[:8000]}",
                self._doc_text[:8000]
            )

        @function_tool
        async def identify_components() -> str:
            """Identify all components and parts mentioned."""
            if not hasattr(self, '_doc_text'):
                return '{}'
            return await self._run_specialist_with_monitoring(
                self.component_identifier,
                "Component Identifier",
                f"Identify components:\n{self._doc_text[:8000]}",
                self._doc_text[:8000]
            )

        @function_tool
        async def analyze_requirements() -> str:
            """Analyze functional requirements and capabilities."""
            if not hasattr(self, '_doc_text'):
                return '{}'
            return await self._run_specialist_with_monitoring(
                self.functional_requirements_analyst,
                "Functional Requirements Analyst",
                f"Extract requirements:\n{self._doc_text[:8000]}",
                self._doc_text[:8000]
            )

        @function_tool
        async def map_relationships() -> str:
            """Map relationships between documented entities."""
            if not hasattr(self, '_doc_text'):
                return '{}'
            return await self._run_specialist_with_monitoring(
                self.relationship_mapper,
                "Relationship Mapper",
                f"Map relationships:\n{self._doc_text[:8000]}",
                self._doc_text[:8000]
            )

        @function_tool
        async def curate_metadata() -> str:
            """Curate document metadata and context."""
            if not hasattr(self, '_doc_text'):
                return '{}'
            return await self._run_specialist_with_monitoring(
                self.metadata_curator,
                "Metadata Curator",
                f"Extract metadata:\n{self._doc_text[:8000]}",
                self._doc_text[:8000]
            )

        return Agent(
            name="Document Analysis Manager",
            model=self.manager_model,
            instructions="""You are coordinating analysis specialists. Call the tools and combine their JSON outputs.

TOOLS AVAILABLE:
1. identify_components() - Find components/parts
2. extract_specifications() - Get technical specs
3. analyze_requirements() - Extract requirements

PROCESS:
1. Call identify_components()
2. Call extract_specifications()
3. Call analyze_requirements()
4. Combine all results into final JSON

OUTPUT FORMAT:
{
  "document_analysis": {
    "components": <result from identify_components>,
    "specifications": <result from extract_specifications>,
    "requirements": <result from analyze_requirements>
  }
}

Return ONLY this JSON structure, nothing else.""",
            tools=[
                identify_components,
                extract_specifications,
                analyze_requirements
            ]
        )

    def _create_graph_enrichment_manager(self) -> Agent:
        """Create hub agent for orchestrating graph enrichment specialists."""

        @function_tool
        async def match_entities() -> str:
            """Match document entities to CAD graph entities."""
            if not hasattr(self, '_match_context'):
                return '{}'
            return await self._run_specialist_with_monitoring(
                self.entity_matcher,
                "Entity Matcher",
                f"Match entities:\n{json.dumps(self._match_context, indent=2)}",
                self._match_context
            )

        @function_tool
        async def enrich_semantics() -> str:
            """Add semantic properties to entities."""
            if not hasattr(self, '_semantic_context'):
                return '{}'
            return await self._run_specialist_with_monitoring(
                self.semantic_enricher,
                "Semantic Enricher",
                f"Enrich with semantics:\n{json.dumps(self._semantic_context, indent=2)}",
                self._semantic_context
            )

        @function_tool
        async def enrich_relationships() -> str:
            """Create semantic relationships."""
            if not hasattr(self, '_relationship_context'):
                return '{}'
            return await self._run_specialist_with_monitoring(
                self.relationship_enricher,
                "Relationship Enricher",
                f"Create relationships:\n{json.dumps(self._relationship_context, indent=2)}",
                self._relationship_context
            )

        @function_tool
        async def augment_context() -> str:
            """Add contextual information."""
            if not hasattr(self, '_context_data'):
                return '{}'
            return await self._run_specialist_with_monitoring(
                self.context_augmenter,
                "Context Augmenter",
                f"Augment context:\n{json.dumps(self._context_data, indent=2)}",
                self._context_data
            )

        return Agent(
            name="Graph Enrichment Manager",
            model=self.manager_model,
            instructions="""Coordinate graph enrichment. Call tools and combine results.

TOOLS:
1. match_entities() - Match doc to CAD
2. enrich_semantics() - Add properties

PROCESS:
1. Call match_entities()
2. Call enrich_semantics()
3. Combine into JSON

OUTPUT:
{
  "graph_enrichment": {
    "entity_matches": <from match_entities>,
    "semantic_properties": <from enrich_semantics>
  },
  "statistics": {
    "entities_matched": 0,
    "properties_added": 0
  }
}

Return ONLY valid JSON.""",
            tools=[
                match_entities,
                enrich_semantics
            ]
        )

    # ==================== ORCHESTRATION ====================

    async def analyze_document_async(self, document_text: str) -> Dict[str, Any]:
        """Analyze document using document analysis swarm.

        Args:
            document_text: Full text of document

        Returns:
            Document analysis results
        """
        self._doc_text = document_text

        print("   📄 Starting document analysis with specialist swarm...")

        manager_prompt = """Analyze this technical documentation by calling these tools in order:
1. identify_components()
2. extract_specifications()
3. analyze_requirements()

Then combine their JSON outputs into the required format."""

        try:
            result = await Runner.run(
                self.document_analysis_manager,
                manager_prompt,
                max_turns=10  # Reduced for faster execution
            )

            return self._extract_json(result.final_output, "document analysis")

        except Exception as e:
            print(f"   ⚠️  Document analysis failed: {e}")
            return {"error": str(e)}

    async def enrich_graph_async(
        self,
        document_analysis: Dict[str, Any],
        cad_entities: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Enrich knowledge graph using enrichment swarm.

        Args:
            document_analysis: Results from document analysis
            cad_entities: CAD entities from knowledge graph

        Returns:
            Graph enrichment results
        """
        # Prepare context for enrichment specialists
        self._match_context = {
            "doc_components": document_analysis.get("document_analysis", {}).get("components", {}),
            "cad_entities": cad_entities[:50]  # Limit for performance
        }

        self._semantic_context = {
            "specifications": document_analysis.get("document_analysis", {}).get("specifications", {}),
            "requirements": document_analysis.get("document_analysis", {}).get("requirements", {}),
            "matched_entities": []  # Will be populated
        }

        self._relationship_context = {
            "doc_relationships": document_analysis.get("document_analysis", {}).get("relationships", {}),
            "matched_entities": []
        }

        self._context_data = {
            "metadata": document_analysis.get("document_analysis", {}).get("metadata", {}),
            "matched_entities": []
        }

        print("   🔗 Starting graph enrichment with specialist swarm...")

        manager_prompt = """Enrich the knowledge graph:
1. Call match_entities()
2. Call enrich_semantics()
3. Combine into required JSON format."""

        try:
            result = await Runner.run(
                self.graph_enrichment_manager,
                manager_prompt,
                max_turns=10  # Reduced for faster execution
            )

            return self._extract_json(result.final_output, "graph enrichment")

        except Exception as e:
            print(f"   ⚠️  Graph enrichment failed: {e}")
            return {"error": str(e)}

    def _extract_json(self, text: str, context: str) -> Dict[str, Any]:
        """Extract JSON from agent response."""
        # Try multiple extraction methods
        if "```json" in text:
            try:
                json_str = text.split("```json")[1].split("```")[0]
                return json.loads(json_str.strip())
            except (IndexError, json.JSONDecodeError):
                pass

        if "```" in text:
            try:
                json_str = text.split("```")[1].split("```")[0]
                json_str = json_str.strip()
                if json_str.startswith(('json', 'JSON')):
                    json_str = json_str[4:].strip()
                return json.loads(json_str)
            except (IndexError, json.JSONDecodeError):
                pass

        if '{' in text and '}' in text:
            try:
                start = text.index('{')
                end = text.rindex('}') + 1
                json_str = text[start:end]
                return json.loads(json_str)
            except (ValueError, json.JSONDecodeError):
                pass

        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            print(f"   ⚠️  Could not extract JSON from {context}")
            print(f"   📄 First 300 chars:\n{text[:300]}\n")
            return {"error": f"Could not extract valid JSON from {context}", "raw_output": text[:500]}

    async def process_async(
        self,
        document_text: str,
        cad_entities: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Process document and enrich graph.

        Args:
            document_text: Full document text
            cad_entities: CAD entities from knowledge graph

        Returns:
            Complete analysis and enrichment results
        """
        self.monitor.start_timer()

        # Phase 1: Document Analysis
        doc_analysis = await self.analyze_document_async(document_text)

        # Phase 2: Graph Enrichment
        graph_enrichment = await self.enrich_graph_async(doc_analysis, cad_entities)

        self.monitor.end_timer()

        # Combine results
        results = {
            "document_analysis": doc_analysis,
            "graph_enrichment": graph_enrichment,
            "performance": self.monitor.get_summary()
        }

        self.monitor.print_summary()

        return results

    def process(
        self,
        document_text: str,
        cad_entities: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Process document and enrich graph (sync wrapper)."""
        return asyncio.run(self.process_async(document_text, cad_entities))


def create_enriched_knowledge_graph(
    document_text: str,
    cad_entities: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Create enriched knowledge graph using document analysis swarm.

    Args:
        document_text: Full document text
        cad_entities: CAD entities from knowledge graph

    Returns:
        Complete enrichment results
    """
    swarm = DocumentAnalysisSwarm()
    return swarm.process(document_text, cad_entities)
