# cadKG - CAD Knowledge Graph Constructor

Multi-agent system for converting STEP CAD files into Neo4j knowledge graphs.

## What is cadKG?

cadKG parses STEP CAD files and uses a team of specialized AI agents to analyze the data and construct detailed knowledge graphs in Neo4j. Each agent focuses on a specific aspect of the CAD data (geometry, hierarchy, classification, etc.), and a coordinator agent synthesizes their findings into a unified graph.

## Setup

### Prerequisites

- Python 3.10+
- Neo4j database
- Ollama with GPT-OSS models:
  - `gpt-oss:120b` (coordinator)
  - `gpt-oss:20b` (specialists)

### Installation

1. **Install dependencies**

```bash
cd cadkg

# Install uv package manager if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
```

2. **Install Ollama models**

```bash
ollama pull gpt-oss:120b
ollama pull gpt-oss:20b
```

3. **Configure environment**

```bash
cp .env.example .env
# Edit .env with your settings
```

Required environment variables:

```bash
# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Ollama
OPENAI_API_BASE=http://127.0.0.1:11435/v1
OPENAI_API_KEY=ollama
OPENAI_MODEL_MANAGER=gpt-oss:120b
OPENAI_MODEL_SPECIALIST=gpt-oss:20b

# STEP file
STEP_FILE_PATH=data/your-file.STEP
```

## Usage

### Run the pipeline

Process a STEP file and populate Neo4j:

```bash
python scripts/grapher.py --clear-graph
```

This will:
1. Parse the STEP file
2. Run multi-agent analysis
3. Create and populate the Neo4j knowledge graph

### Skip AI analysis

For faster processing without agent enrichment:

```bash
python scripts/grapher.py --clear-graph --skip-agent
```

### View file statistics only

```bash
python scripts/grapher.py --stats-only
```

### Test the multi-agent system

```bash
python scripts/test_multiagent.py
```

## How It Works

### Architecture

cadKG uses a **hub-and-spoke multi-agent architecture**:

```
                    ┌─────────────────────────┐
                    │   Project Manager       │
                    │   (gpt-oss:120b)        │
                    │   Coordinates team      │
                    └───────────┬─────────────┘
                                │
            ┌───────────────────┼───────────────────┐
            │                   │                   │
    ┌───────▼───────┐   ┌──────▼──────┐   ┌───────▼───────┐
    │   Geometry    │   │  Hierarchy  │   │  Component    │
    │   Analyst     │   │   Mapper    │   │  Classifier   │
    └───────────────┘   └─────────────┘   └───────────────┘
    ┌───────────────┐   ┌─────────────┐
    │   Spatial     │   │ Properties  │
    │  Relations    │   │  Extractor  │
    └───────────────┘   └─────────────┘
```

**Project Manager (120B model)**
- Coordinates all specialist agents
- Synthesizes their findings
- Produces final knowledge graph structure

**Specialist Agents (20B model)**
- Geometry Analyst: Analyzes vertices, edges, faces, complexity
- Hierarchy Mapper: Maps assembly structure and containment
- Component Classifier: Categories parts (fasteners, structural, mechanical)
- Spatial Relations Analyst: Identifies connections (FASTENS, ADJACENT_TO)
- Properties Extractor: Extracts materials, vendors, sizes from labels

### Pipeline Flow

```
STEP File → Parser → Multi-Agent System → Knowledge Graph → Neo4j
```

**1. STEP Parsing**

Uses cadquery-ocp to extract:
- Assembly hierarchies
- Part geometries (vertices, edges, faces)
- Component metadata
- Naming and labeling

**2. Data Preparation**

Chunks data for each specialist agent:
- Geometry: 30 most complex parts
- Components: 50 representative items
- Hierarchy: Depth-limited to 3 levels
- Spatial contexts: 15 assembly groups
- Properties: 50 part labels

**3. Multi-Agent Analysis**

Each specialist receives focused data and analyzes independently:

- **Geometry Analyst**: Returns `{id, vertex_count, complexity, shape_hint}`
- **Hierarchy Mapper**: Returns `{source, relation: "CONTAINS", target, depth}`
- **Component Classifier**: Returns `{part_id, category, subcategory, standard}`
- **Spatial Relations**: Returns `{source, relation, target, confidence}`
- **Properties Extractor**: Returns `{part_id: {material, vendor, size}}`

The Project Manager coordinates these analyses and produces a unified knowledge graph structure.

**4. Neo4j Population**

Creates graph with:
- **Nodes**: Assembly, Part, Vertex
- **Relationships**: CONTAINS, HAS_GEOMETRY, HAS_VERTEX, FASTENS, etc.
- Batch operations for efficiency
- Idempotent MERGE operations

### Knowledge Graph Schema

**Nodes**

```cypher
(:Assembly {id, name, shape_type, level})
(:Part {id, name, shape_type, level, vertex_count?, category?, material?})
(:Vertex:GeometricEntity {id, x, y, z})
```

**Relationships**

```cypher
(:Assembly)-[:CONTAINS]->(:Assembly|Part)
(:Part)-[:HAS_GEOMETRY]->(:Part)
(:Part)-[:HAS_VERTEX]->(:Vertex)
(:Part)-[:FASTENS]->(:Part)
(:Part)-[:ADJACENT_TO]->(:Part)
```

### Caching & Optimization

- **Result Caching**: MD5-based caching prevents redundant agent calls
- **Progressive Chunking**: Limits context size per agent
- **Multi-Model Strategy**: Fast 20B for specialists, powerful 120B for coordination
- **Performance Monitoring**: Tracks execution time and cache hits

## Querying the Knowledge Graph

Once populated, query Neo4j with Cypher:

```cypher
// View all assemblies
MATCH (a:Assembly) RETURN a LIMIT 25

// View assembly hierarchy
MATCH p=(a:Assembly)-[:CONTAINS*]->(child)
RETURN p LIMIT 50

// Find parts with geometry
MATCH (p:Part)-[:HAS_GEOMETRY]->(g)
RETURN p.name, p.vertex_count
ORDER BY p.vertex_count DESC

// Find fastening relationships
MATCH (p1:Part)-[r:FASTENS]->(p2:Part)
RETURN p1.name, p2.name, r.confidence

// Find standard parts by vendor
MATCH (p:Part)
WHERE p.vendor = 'McMaster-Carr'
RETURN p.name, p.standard
```

## Project Structure

```
cadkg/
├── scripts/
│   ├── grapher.py           # Main pipeline orchestrator
│   ├── agent.py             # Multi-agent system
│   ├── step_parser.py       # STEP file parser
│   ├── neo4j_schema.py      # Neo4j schema & operations
│   └── test_multiagent.py   # Test harness
├── data/
│   └── *.STEP               # CAD files
├── .env                     # Configuration
├── .env.example             # Config template
├── pyproject.toml           # Dependencies
└── README.md
```

## Troubleshooting

**Max turns exceeded**

The coordinator is making too many tool calls. Reduce data limits in `agent.py` preparation methods or increase `max_turns` parameter.

**JSON extraction errors**

Agent output isn't valid JSON. Check agent instructions emphasize JSON-only responses.

**Slow performance**

Verify specialist agents use the 20B model. Check cache hit rate with `--stats-only`.

**Neo4j connection errors**

Verify Neo4j is running and credentials in `.env` are correct.

## Development

### Adding a new specialist agent

1. Create agent in `agent.py`:

```python
def _create_new_specialist(self) -> Agent:
    return Agent(
        name="New Specialist",
        model=self.specialist_model,
        instructions="Focus only on X. Return JSON: {...}"
    )
```

2. Add tool wrapper:

```python
@function_tool
async def analyze_new_aspect() -> str:
    """Analyzes specific aspect of CAD data."""
    return await self._run_specialist_with_monitoring(...)
```

3. Add data preparation:

```python
def _prepare_new_data(self, step_data):
    # Extract and limit relevant data
    return filtered_data[:limit]
```

4. Update Project Manager tools list

## Links

- [Neo4j Documentation](https://neo4j.com/docs/)
- [cadquery-ocp](https://github.com/CadQuery/cadquery-ocp)
- [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/)
- [Ollama](https://ollama.ai/)
