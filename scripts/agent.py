"""Multi-agent system for CAD knowledge graph construction using hub-and-spoke pattern with Ollama/GPT-OSS.

Optimizations:
- Parallel agent execution with asyncio.gather()
- Multi-model support (faster 20B for specialists, 120B for manager)
- Result caching to avoid re-analysis
- Progressive summarization for large datasets
- Performance monitoring and metrics
"""

import os
import json
import asyncio
import time
import hashlib
from typing import Any, Dict, List, Optional
from openai import AsyncOpenAI
from agents import Agent, Runner, OpenAIChatCompletionsModel, set_tracing_disabled, function_tool

# Disable tracing since we're using Ollama, not OpenAI
set_tracing_disabled(True)


class PerformanceMonitor:
    """Monitor and track agent performance metrics."""

    def __init__(self):
        self.metrics = {
            "agent_calls": {},
            "execution_times": {},
            "cache_hits": 0,
            "cache_misses": 0,
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

    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        total_time = 0
        if self.metrics["total_start_time"] and self.metrics["total_end_time"]:
            total_time = self.metrics["total_end_time"] - self.metrics["total_start_time"]

        summary = {
            "total_execution_time_seconds": round(total_time, 2),
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
        print("\n   📊 Performance Metrics:")
        print(f"   - Total execution time: {summary['total_execution_time_seconds']}s")
        print(f"   - Cache hit rate: {summary['cache_statistics']['hit_rate']}%")
        print("   - Agent statistics:")
        for agent_name, stats in summary["agent_statistics"].items():
            print(f"     • {agent_name}: {stats['calls']} calls, avg {stats['avg_time_seconds']}s")


class CADMultiAgentSystem:
    """Hub-and-spoke multi-agent system for CAD analysis with specialized agents.

    Optimizations:
    - Parallel specialist execution
    - Multi-model support (20B for specialists, 120B for manager)
    - Result caching
    - Progressive data chunking
    """

    def __init__(self):
        """Initialize the multi-agent system with Ollama settings."""
        # Get settings from environment
        self.base_url = os.getenv("OPENAI_API_BASE", "http://127.0.0.1:11435/v1")
        self.api_key = os.getenv("OPENAI_API_KEY", "ollama")
        self.manager_model_name = os.getenv("OPENAI_MODEL_MANAGER", "gpt-oss:120b")
        self.specialist_model_name = os.getenv("OPENAI_MODEL_SPECIALIST", "gpt-oss:20b")
        self.step_data = None

        # Performance monitoring
        self.monitor = PerformanceMonitor()

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

        self.manager_model = OpenAIChatCompletionsModel(
            model=self.manager_model_name,
            openai_client=self.client
        )

        # Create specialized agents (spokes) - use faster 20B model
        self.geometry_analyst = self._create_geometry_analyst()
        self.hierarchy_mapper = self._create_hierarchy_mapper()
        self.component_classifier = self._create_component_classifier()
        self.spatial_relations_analyst = self._create_spatial_relations_analyst()
        self.properties_extractor = self._create_properties_extractor()

        # Create hub agent (project manager) - use larger 120B model
        self.project_manager = self._create_project_manager()

        print(f"   🤖 Initialized multi-agent system:")
        print(f"      - Manager model: {self.manager_model_name}")
        print(f"      - Specialist model: {self.specialist_model_name}")

    def _cache_key(self, agent_name: str, data: Any) -> str:
        """Generate cache key for agent result."""
        data_str = json.dumps(data, sort_keys=True)
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

    # ==================== SPECIALIST AGENTS (SPOKES) ====================

    def _create_geometry_analyst(self) -> Agent:
        """Create ultra-focused agent for geometric analysis only."""
        return Agent(
            name="Geometry Analyst",
            model=self.specialist_model,
            instructions="""You are a geometric analysis specialist. Your ONLY job is to analyze geometric properties.

Given a part with geometry data, extract and report:
- Number of vertices, edges, faces
- Complexity rating (simple/moderate/complex based on vertex count: <10=simple, 10-50=moderate, >50=complex)
- Shape characteristics (if obvious from counts)

CRITICAL RULES:
- Focus ONLY on geometric metrics
- Do NOT analyze relationships, classifications, or hierarchies
- Keep responses concise and data-focused
- Return ONLY a JSON array of geometric analyses

Example output:
[
  {
    "id": "part_1",
    "vertex_count": 72,
    "edge_count": 36,
    "face_count": 9,
    "complexity": "complex",
    "shape_hint": "cylindrical"
  }
]"""
        )

    def _create_hierarchy_mapper(self) -> Agent:
        """Create agent focused solely on assembly hierarchy."""
        return Agent(
            name="Hierarchy Mapper",
            model=self.specialist_model,
            instructions="""You are an assembly structure specialist. Your ONLY job is to map parent-child relationships.

Given assembly tree data, identify:
- Parent-child containment relationships (A CONTAINS B)
- Assembly depth levels
- Component groupings

CRITICAL RULES:
- Focus ONLY on hierarchical structure
- Do NOT analyze geometry, classifications, or properties
- Return ONLY a JSON array of relationships

Example output:
[
  {"source": "assembly_1", "relation": "CONTAINS", "target": "part_1", "depth": 1},
  {"source": "assembly_1", "relation": "CONTAINS", "target": "subassembly_2", "depth": 1}
]"""
        )

    def _create_component_classifier(self) -> Agent:
        """Create agent for component classification only."""
        return Agent(
            name="Component Classifier",
            model=self.specialist_model,
            instructions="""You are a component classification specialist. Your ONLY job is to categorize CAD parts.

Given part names and shape types, classify into categories:
- Fasteners (screws, bolts, washers, nuts)
- Structural (plates, frames, brackets, panels)
- Mechanical (gears, bearings, shafts)
- Standard parts (identify vendor codes like McMaster-Carr)

CRITICAL RULES:
- Focus ONLY on classification
- Do NOT analyze geometry, relationships, or hierarchies
- Use common engineering categories
- Return ONLY a JSON array of classifications

Example output:
[
  {"part_id": "part_1", "category": "fastener", "subcategory": "washer", "standard": "McMaster-Carr 98689A111"}
]"""
        )

    def _create_spatial_relations_analyst(self) -> Agent:
        """Create agent for spatial relationship detection."""
        return Agent(
            name="Spatial Relations Analyst",
            model=self.specialist_model,
            instructions="""You are a spatial relationship specialist. Your ONLY job is to identify how parts relate spatially.

Given multiple parts with positions and assembly context, identify:
- Connection relationships (CONNECTED_TO, FASTENS)
- Adjacency (ADJACENT_TO)
- Mating relationships (MATES_WITH)

CRITICAL RULES:
- Focus ONLY on spatial relationships
- Do NOT classify parts, analyze geometry details, or map hierarchies
- Infer relationships from assembly structure
- Return ONLY a JSON array of relationships

Example output:
[
  {"source": "washer_1", "relation": "FASTENS", "target": "panel_1", "confidence": "high"}
]"""
        )

    def _create_properties_extractor(self) -> Agent:
        """Create agent for extracting metadata and properties."""
        return Agent(
            name="Properties Extractor",
            model=self.specialist_model,
            instructions="""You are a metadata extraction specialist. Your ONLY job is to extract properties and metadata.

Given part labels and attributes, extract:
- Material hints from names (stainless steel, aluminum, acrylic)
- Size specifications (dimensions in part names)
- Standard identifiers (part numbers, vendor codes)
- Naming patterns and conventions

CRITICAL RULES:
- Focus ONLY on extracting existing properties
- Do NOT classify, analyze geometry, or map relationships
- Pull information directly from names and attributes
- Return ONLY a JSON object with extracted properties

Example output:
{
  "part_1": {
    "material_hint": "stainless_steel",
    "standard_id": "SS SHCS 91292A831",
    "vendor": "McMaster-Carr",
    "size_hint": "18-8"
  }
}"""
        )

    # ==================== HUB AGENT (PROJECT MANAGER) ====================

    def _create_project_manager(self) -> Agent:
        """Create the hub agent that orchestrates specialist agents."""

        # Create tool wrappers for each specialist agent
        @function_tool
        async def analyze_geometry() -> str:
            """Analyze geometric properties of all CAD parts with geometry.

            Returns:
                Geometric analysis results in JSON format
            """
            if not hasattr(self, '_cached_geometry_data'):
                return '[]'

            return await self._run_specialist_with_monitoring(
                self.geometry_analyst,
                "Geometry Analyst",
                f"Analyze these part geometries:\n{json.dumps(self._cached_geometry_data, indent=2)}",
                self._cached_geometry_data
            )

        @function_tool
        async def map_hierarchy() -> str:
            """Map assembly hierarchy and parent-child containment relationships.

            Returns:
                Hierarchy mapping results in JSON format
            """
            if not hasattr(self, '_cached_hierarchy_data'):
                return '[]'

            return await self._run_specialist_with_monitoring(
                self.hierarchy_mapper,
                "Hierarchy Mapper",
                f"Map the hierarchy of this assembly structure:\n{json.dumps(self._cached_hierarchy_data, indent=2)}",
                self._cached_hierarchy_data
            )

        @function_tool
        async def classify_components() -> str:
            """Classify CAD components by type (fasteners, structural, mechanical, etc).

            Returns:
                Component classifications in JSON format
            """
            if not hasattr(self, '_cached_component_list'):
                return '[]'

            return await self._run_specialist_with_monitoring(
                self.component_classifier,
                "Component Classifier",
                f"Classify these components:\n{json.dumps(self._cached_component_list, indent=2)}",
                self._cached_component_list
            )

        @function_tool
        async def analyze_spatial_relations() -> str:
            """Identify spatial relationships between parts (FASTENS, ADJACENT_TO, etc).

            Returns:
                Spatial relationship analysis in JSON format
            """
            if not hasattr(self, '_cached_spatial_context'):
                return '[]'

            return await self._run_specialist_with_monitoring(
                self.spatial_relations_analyst,
                "Spatial Relations Analyst",
                f"Identify spatial relationships in these assemblies:\n{json.dumps(self._cached_spatial_context, indent=2)}",
                self._cached_spatial_context
            )

        @function_tool
        async def extract_properties() -> str:
            """Extract properties and metadata from part labels (materials, sizes, vendors).

            Returns:
                Extracted properties in JSON format
            """
            if not hasattr(self, '_cached_property_labels'):
                return '{}'

            return await self._run_specialist_with_monitoring(
                self.properties_extractor,
                "Properties Extractor",
                f"Extract properties from these part labels:\n{json.dumps(self._cached_property_labels, indent=2)}",
                self._cached_property_labels
            )

        return Agent(
            name="CAD Project Manager",
            model=self.manager_model,
            instructions="""You are the CAD Project Manager coordinating a team of specialist agents.

Your job is to orchestrate analysis of CAD assembly data for knowledge graph construction.

YOUR TEAM:
1. Geometry Analyst - analyzes vertices, edges, faces, complexity
2. Hierarchy Mapper - maps parent-child assembly relationships
3. Component Classifier - categorizes parts (fasteners, structural, etc.)
4. Spatial Relations Analyst - identifies how parts connect spatially
5. Properties Extractor - extracts metadata from part labels

PROCESS:
1. Call specialist tools to gather their analyses
2. Combine outputs into final knowledge graph JSON
3. Return ONLY the JSON, nothing else

CRITICAL RULES:
- Call specialist tools to gather data
- Synthesize results into unified knowledge graph
- Return ONLY valid JSON - no explanations, no markdown, no text
- Do NOT generate code or scripts
- Output must be parseable JSON

OUTPUT FORMAT (return ONLY this JSON):
{
  "entities": [
    {"id": "...", "type": "Assembly|Part", "name": "...", "properties": {...}}
  ],
  "relationships": [
    {"source_id": "...", "relation": "CONTAINS|CONNECTED_TO|etc", "target_id": "...", "properties": {...}}
  ],
  "metadata": {
    "total_entities": N,
    "total_relationships": M,
    "analysis_summary": "..."
  }
}""",
            tools=[
                analyze_geometry,
                map_hierarchy,
                classify_components,
                analyze_spatial_relations,
                extract_properties
            ]
        )

    # ==================== DATA PREPARATION ====================

    def _chunk_data(self, data: List[Any], chunk_size: int) -> List[List[Any]]:
        """Split data into chunks for progressive processing."""
        return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]

    def _prepare_geometry_data(self, step_data: Any) -> list[dict]:
        """Prepare focused geometry data for Geometry Analyst."""
        geometry_parts = []

        def extract_geometry(node: dict):
            if "geometry" in node:
                geometry_parts.append({
                    "id": node.get("id"),
                    "name": node.get("name"),
                    "vertices": len(node["geometry"].get("vertices", [])),
                    "edges": node["geometry"].get("edges", 0),
                    "faces": node["geometry"].get("faces", 0)
                })
            for child in node.get("children", []):
                extract_geometry(child)

        if isinstance(step_data, list):
            for item in step_data:
                extract_geometry(item)
        else:
            extract_geometry(step_data)

        # Progressive chunking: limit to 30 most complex parts
        geometry_parts.sort(key=lambda x: x["vertices"], reverse=True)
        return geometry_parts[:30]

    def _prepare_hierarchy_data(self, step_data: Any) -> dict:
        """Prepare focused hierarchy data for Hierarchy Mapper."""
        def simplify_node(node: dict, max_depth: int = 3, current_depth: int = 0) -> dict:
            """Recursively simplify node with depth limit."""
            if current_depth >= max_depth:
                return {
                    "id": node.get("id"),
                    "name": node.get("name"),
                    "is_assembly": node.get("is_assembly", False),
                    "children": []  # Truncate at max depth
                }

            return {
                "id": node.get("id"),
                "name": node.get("name"),
                "is_assembly": node.get("is_assembly", False),
                "children": [simplify_node(child, max_depth, current_depth + 1) for child in node.get("children", [])]
            }

        if isinstance(step_data, list):
            return {"assemblies": [simplify_node(item) for item in step_data[:5]]}
        else:
            return simplify_node(step_data)

    def _prepare_component_list(self, step_data: Any) -> list[dict]:
        """Prepare focused component list for Component Classifier."""
        components = []

        def extract_components(node: dict):
            components.append({
                "id": node.get("id"),
                "name": node.get("name"),
                "shape_type": node.get("shape_type"),
                "is_assembly": node.get("is_assembly", False)
            })
            for child in node.get("children", []):
                extract_components(child)

        if isinstance(step_data, list):
            for item in step_data:
                extract_components(item)
        else:
            extract_components(step_data)

        # Sample representative components
        return components[:50]

    def _prepare_spatial_context(self, step_data: Any) -> list[dict]:
        """Prepare spatial context for Spatial Relations Analyst."""
        assemblies = []

        def extract_assembly_group(node: dict):
            if node.get("is_assembly") and node.get("children"):
                assemblies.append({
                    "assembly_id": node.get("id"),
                    "assembly_name": node.get("name"),
                    "parts": [
                        {"id": child.get("id"), "name": child.get("name"), "type": child.get("shape_type")}
                        for child in node.get("children", [])[:10]  # Limit children per assembly
                    ]
                })
            for child in node.get("children", []):
                extract_assembly_group(child)

        if isinstance(step_data, list):
            for item in step_data:
                extract_assembly_group(item)
        else:
            extract_assembly_group(step_data)

        return assemblies[:15]

    def _prepare_property_labels(self, step_data: Any) -> list[dict]:
        """Prepare part labels for Properties Extractor."""
        labels = []

        def extract_labels(node: dict):
            labels.append({
                "id": node.get("id"),
                "name": node.get("name"),
                "shape_type": node.get("shape_type"),
                "level": node.get("level")
            })
            for child in node.get("children", []):
                extract_labels(child)

        if isinstance(step_data, list):
            for item in step_data:
                extract_labels(item)
        else:
            extract_labels(step_data)

        return labels[:50]

    # ==================== ORCHESTRATION ====================

    async def process_async(self, step_data: Any) -> dict[str, Any]:
        """Process STEP data through the multi-agent system with parallel execution.

        Args:
            step_data: Assembly data from STEP parser

        Returns:
            Enriched data ready for knowledge graph construction
        """
        self.step_data = step_data
        self.monitor.start_timer()

        print("   🎯 Preparing specialized data for agent team...")

        # Prepare focused data for each specialist and cache for tool access
        self._cached_geometry_data = self._prepare_geometry_data(step_data)
        self._cached_hierarchy_data = self._prepare_hierarchy_data(step_data)
        self._cached_component_list = self._prepare_component_list(step_data)
        self._cached_spatial_context = self._prepare_spatial_context(step_data)
        self._cached_property_labels = self._prepare_property_labels(step_data)

        print(f"   📊 Data prepared:")
        print(f"      - {len(self._cached_geometry_data)} geometries")
        print(f"      - {len(self._cached_component_list)} components")
        print(f"      - {len(self._cached_spatial_context)} assembly contexts")

        # Create prompt for project manager
        manager_prompt = f"""Coordinate your specialist team to build a comprehensive knowledge graph.

AVAILABLE SPECIALISTS:
1. analyze_geometry() - Analyzes {len(self._cached_geometry_data)} parts with geometric data
2. map_hierarchy() - Maps the assembly structure hierarchy
3. classify_components() - Classifies {len(self._cached_component_list)} components by type
4. analyze_spatial_relations() - Identifies spatial relationships in {len(self._cached_spatial_context)} assembly contexts
5. extract_properties() - Extracts metadata from {len(self._cached_property_labels)} part labels

TASK:
Call each specialist tool and synthesize their outputs into a unified knowledge graph JSON.

IMPORTANT:
- Call all specialist tools (no parameters needed)
- Combine results into final JSON structure
- Return ONLY valid JSON, no explanations

Begin coordinating your team now."""

        print("   🤝 Project Manager orchestrating specialists in parallel...")

        try:
            result = await Runner.run(
                self.project_manager,
                manager_prompt,
                max_turns=20  # Allow more turns for complex orchestration
            )

            self.monitor.end_timer()

            # Parse the final output
            final_output = result.final_output

            # Try to extract JSON from the response
            enriched_data = None

            # Try multiple extraction methods
            if "```json" in final_output:
                try:
                    json_str = final_output.split("```json")[1].split("```")[0]
                    enriched_data = json.loads(json_str.strip())
                except (IndexError, json.JSONDecodeError):
                    pass

            if not enriched_data and "```" in final_output:
                try:
                    json_str = final_output.split("```")[1].split("```")[0]
                    json_str = json_str.strip()
                    if json_str.startswith(('json', 'JSON')):
                        json_str = json_str[4:].strip()
                    enriched_data = json.loads(json_str)
                except (IndexError, json.JSONDecodeError):
                    pass

            if not enriched_data and '{' in final_output and '}' in final_output:
                try:
                    start = final_output.index('{')
                    end = final_output.rindex('}') + 1
                    json_str = final_output[start:end]
                    enriched_data = json.loads(json_str)
                except (ValueError, json.JSONDecodeError):
                    pass

            if not enriched_data:
                try:
                    enriched_data = json.loads(final_output.strip())
                except json.JSONDecodeError:
                    print(f"   ⚠️  Could not extract JSON from response")
                    print(f"   📄 First 300 chars:\n{final_output[:300]}\n")
                    raise Exception("Could not extract valid JSON from agent response")

            print(f"   ✅ Multi-agent analysis complete")

            # Add performance metrics to metadata
            if "metadata" not in enriched_data:
                enriched_data["metadata"] = {}
            enriched_data["metadata"]["performance"] = self.monitor.get_summary()

            # Print performance summary
            self.monitor.print_summary()

            return enriched_data

        except Exception as e:
            self.monitor.end_timer()
            print(f"   ⚠️  Multi-agent processing failed: {e}")
            print("   📋 Falling back to direct mapping...")
            return self._fallback_mapping(step_data)

    def _fallback_mapping(self, step_data: Any) -> dict[str, Any]:
        """Fallback method for direct mapping if agent processing fails."""
        entities = []
        relationships = []

        def traverse(node: dict, parent_id: str = None):
            entity = {
                "id": node.get("id"),
                "type": "Assembly" if node.get("is_assembly") else "Part",
                "name": node.get("name"),
                "properties": {
                    "shape_type": node.get("shape_type"),
                    "level": node.get("level")
                }
            }

            if "geometry" in node:
                entity["properties"]["vertex_count"] = len(node["geometry"].get("vertices", []))

            entities.append(entity)

            if parent_id:
                relationships.append({
                    "source_id": parent_id,
                    "relation": "CONTAINS",
                    "target_id": node.get("id"),
                    "properties": {}
                })

            for child in node.get("children", []):
                traverse(child, node.get("id"))

        if isinstance(step_data, list):
            for item in step_data:
                traverse(item)
        else:
            traverse(step_data)

        return {
            "entities": entities,
            "relationships": relationships,
            "metadata": {
                "analysis_summary": "Direct mapping (fallback mode)",
                "total_entities": len(entities),
                "total_relationships": len(relationships),
                "performance": self.monitor.get_summary()
            }
        }

    def process(self, step_data: Any) -> dict[str, Any]:
        """Process STEP data through the multi-agent system (sync wrapper)."""
        return asyncio.run(self.process_async(step_data))


def create_knowledge_graph_with_agent(step_data: Any) -> dict[str, Any]:
    """Create enriched knowledge graph data using multi-agent system with Ollama.

    Args:
        step_data: Assembly data from STEP parser

    Returns:
        Enriched data ready for Neo4j population
    """
    agent_system = CADMultiAgentSystem()
    enriched_data = agent_system.process(step_data)

    return enriched_data
