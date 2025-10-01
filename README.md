# cadKG - CAD Knowledge Graph Constructor

multi-agent system for converting STEP CAD files into Neo4j knowledge graphs.

cadKG parses STEP CAD files and uses a team of specialized AI agents to analyze the data and construct detailed knowledge graphs in Neo4j. Each agent focuses on a specific aspect of the CAD data (geometry, hierarchy, classification, etc.), and a coordinator agent synthesizes their findings into a unified graph.

## setup

### prerequisites

- Python 3.10+
- Neo4j database
- Ollama with GPT-OSS models:
  - `gpt-oss:120b` (coordinator)
  - `gpt-oss:20b` (specialists)

### installation

1. **install dependencies**

```bash
cd cadkg

# Install uv package manager if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
```

2. **install ollama models**

```bash
ollama pull gpt-oss:120b
ollama pull gpt-oss:20b
```

3. **configure environment**

```bash
cp .env.example .env
# Edit .env with your settings
```

required environment variables:

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

## usage

### run the pipeline

process a STEP file and populate Neo4j:

```bash
python scripts/grapher.py --clear-graph
```

this will:
1. Parse the STEP file
2. Run multi-agent analysis
3. Create and populate the Neo4j knowledge graph

### skip AI analysis

for faster processing without agent enrichment:

```bash
python scripts/grapher.py --clear-graph --skip-agent
```

### view file statistics only

```bash
python scripts/grapher.py --stats-only
```

### test the multi-agent system

```bash
python scripts/test_multiagent.py
```

## how it works

### architecture

cadKG uses a **hub-and-spoke multi-agent architecture**:

```
                    ┌─────────────────────────┐
                    │   project manager       │
                    │   (gpt-oss:120b)        │
                    │   coordinates team      │
                    └───────────┬─────────────┘
                                │
            ┌───────────────────┼───────────────────┐
            │                   │                   │
    ┌───────▼───────┐   ┌──────▼──────┐   ┌───────▼───────┐
    │   geometry    │   │  hierarchy  │   │  component    │
    │   analyst     │   │   mapper    │   │  classifier   │
    └───────────────┘   └─────────────┘   └───────────────┘
    ┌───────────────┐   ┌─────────────┐
    │   spatial     │   │ properties  │
    │  relations    │   │  extractor  │
    └───────────────┘   └─────────────┘
```

**project manager (120B model)**
- coordinates all specialist agents
- synthesizes their findings
- produces final knowledge graph structure

**specialist agents (20B model)**
- geometry analyst: analyzes vertices, edges, faces, complexity
- hierarchy mapper: maps assembly structure and containment
- component classifier: categories parts (fasteners, structural, mechanical)
- spatial relations analyst: identifies connections (fastens, adjacent_to)
- properties extractor: extracts materials, vendors, sizes from labels

### pipeline flow

```
STEP File → Parser → Multi-Agent System → Knowledge Graph → Neo4j
```

**1. STEP parsing**

Uses cadquery-ocp to extract:
- assembly hierarchies
- part geometries (vertices, edges, faces)
- component metadata
- naming and labeling

**2. data preparation**

chunks data for each specialist agent:
- geometry: 30 most complex parts
- components: 50 representative items
- hierarchy: depth-limited to 3 levels
- spatial contexts: 15 assembly groups
- properties: 50 part labels

**3. multi-agent analysis**

each specialist receives focused data and analyzes independently:

- **geometry analyst**: returns `{id, vertex_count, complexity, shape_hint}`
- **hierarchy mapper**: returns `{source, relation: "CONTAINS", target, depth}`
- **component classifier**: returns `{part_id, category, subcategory, standard}`
- **spatial relations**: returns `{source, relation, target, confidence}`
- **properties extractor**: returns `{part_id: {material, vendor, size}}`

the project manager coordinates these analyses and produces a unified knowledge graph structure.

**4. Neo4j population**

creates graph with:
- **nodes**: assembly, part, vertex
- **relationships**: CONTAINS, HAS_GEOMETRY, HAS_VERTEX, FASTENS, etc.

### knowledge graph schema

**nodes**

```cypher
(:Assembly {id, name, shape_type, level})
(:Part {id, name, shape_type, level, vertex_count?, category?, material?})
(:Vertex:GeometricEntity {id, x, y, z})
```

**relationships**

```cypher
(:Assembly)-[:CONTAINS]->(:Assembly|Part)
(:Part)-[:HAS_GEOMETRY]->(:Part)
(:Part)-[:HAS_VERTEX]->(:Vertex)
(:Part)-[:FASTENS]->(:Part)
(:Part)-[:ADJACENT_TO]->(:Part)
```

### caching & optimization

- **result caching**: md5-based caching prevents redundant agent calls
- **progressive chunking**: limits context size per agent
- **multi-model strategy**: fast 20B for specialists, powerful 120B for coordination
- **performance monitoring**: tracks execution time and cache hits

## querying the knowledge graph

once populated, query Neo4j with Cypher:

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

## project structure

```
cadkg/
├── scripts/
│   ├── grapher.py           # main pipeline orchestrator
│   ├── agent.py             # multi-agent system
│   ├── step_parser.py       # STEP file parser
│   ├── neo4j_schema.py      # Neo4j schema & operations
│   └── test_multiagent.py   # test harness
├── data/
│   └── *.step               # cad files
├── .env                     # configuration
├── .env.example             # config template
├── pyproject.toml           # dependencies
└── README.md
```

## troubleshooting

**max turns exceeded**

the coordinator is making too many tool calls. reduce data limits in `agent.py` preparation methods or increase `max_turns` parameter.

**JSON extraction errors**

agent output isn't valid json. check agent instructions emphasize json-only responses.

**slow performance**

verify specialist agents use the 20b model. check cache hit rate with `--stats-only`.

**Neo4j connection errors**

Verify Neo4j is running and credentials in `.env` are correct.

## development

### Adding a new specialist agent

1. Create agent in `agent.py`:

```python
def _create_new_specialist(self) -> Agent:
    return Agent(
        name="new specialist",
        model=self.specialist_model,
        instructions="focus only on X. Return JSON: {...}"
    )
```

2. Add tool wrapper:

```python
@function_tool
async def analyze_new_aspect() -> str:
    """analyzes specific aspect of cad data."""
    return await self._run_specialist_with_monitoring(...)
```

3. add data preparation:

```python
def _prepare_new_data(self, step_data):
    # extract and limit relevant data
    return filtered_data[:limit]
```

4. Update Project Manager tools list

## Links

- [Neo4j Documentation](https://neo4j.com/docs/)
- [cadquery-ocp](https://github.com/CadQuery/cadquery-ocp)
- [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/)
- [Ollama](https://ollama.ai/)
