# cadKG - Integrated Knowledge Graph & GraphRAG System

multi-agent system for creating comprehensive knowledge graphs from CAD files, technical documentation, and source code, with powerful GraphRAG Q&A capabilities.

cadKG is a production-ready system that integrates three specialized analysis pipelines:

1. **CAD Analysis** - parses STEP CAD files to extract assembly hierarchies and geometric data
2. **Documentation Analysis** - analyzes technical PDFs to extract requirements and specifications
3. **Code Analysis** - parses Python codebases to extract modules, classes, functions, and dependencies
4. **Unified GraphRAG** - cross-domain question answering across all three knowledge sources

All data is unified into a single Neo4j knowledge graph, enabling comprehensive queries and AI-powered question answering that spans hardware, documentation, and software.

## setup

### prerequisites

- Python 3.10+
- Neo4j database (running on localhost:7687 or remote)
- Ollama with GPT-OSS models:
  - `gpt-oss:120b` (managers/orchestrators)
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
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Ollama Configuration
OPENAI_API_BASE=http://127.0.0.1:11435/v1
OPENAI_API_KEY=ollama
OPENAI_MODEL_MANAGER=gpt-oss:120b
OPENAI_MODEL_SPECIALIST=gpt-oss:20b

# Data Sources
STEP_FILE_PATH=data/cad/your-assembly.STEP
DOC_FILE_PATH=data/docs/your-documentation.pdf
CODEBASE_PATH=data/codebase
```

## usage

### complete pipeline (recommended)

run the entire pipeline with one command:

```bash
# Run complete pipeline
.venv/bin/python scripts/run_complete_pipeline.py

# Run and launch chat interface automatically
.venv/bin/python scripts/run_complete_pipeline.py --launch-chat

# Skip code analysis for faster execution (~2 minutes instead of ~7 minutes)
.venv/bin/python scripts/run_complete_pipeline.py --skip-code
```

### manual step-by-step pipeline

process CAD, documentation, and code separately:

```bash
# 1. Parse CAD and create initial graph
.venv/bin/python scripts/integrated_pipeline.py --clear-graph --skip-cad-agent

# 2. Enrich with documentation analysis
.venv/bin/python scripts/doc_module/doc_enrichment_pipeline.py

# 3. Enrich with code analysis
.venv/bin/python scripts/code_module/code_pipeline.py
```

### unified GraphRAG Q&A

ask questions across all three domains:

```bash
# Single question
.venv/bin/python scripts/unified_graphrag.py "What is the system architecture?"

# Interactive mode
.venv/bin/python scripts/unified_graphrag.py --interactive

# Demo mode with example questions
.venv/bin/python scripts/unified_graphrag.py --demo
```

### gradio chat interface

launch a web-based chat interface:

```bash
# Launch locally
.venv/bin/python scripts/chat_interface.py

# Launch with public sharing link
.venv/bin/python scripts/chat_interface.py --share

# Use different port
.venv/bin/python scripts/chat_interface.py --port 8080
```

Access at http://localhost:7860

### individual module pipelines

**CAD only:**
```bash
# Full CAD pipeline with AI enrichment
python scripts/grapher.py --clear-graph

# Faster processing without AI agents
python scripts/grapher.py --clear-graph --skip-agent

# Show STEP file statistics only
python scripts/grapher.py --stats-only
```

**documentation only:**
```bash
# Analyze PDF and enrich existing graph
.venv/bin/python scripts/doc_module/doc_enrichment_pipeline.py
```

**code only:**
```bash
# Analyze codebase and enrich existing graph
.venv/bin/python scripts/code_module/code_pipeline.py

# Ask questions about code specifically
.venv/bin/python scripts/code_module/ask_question.py "How does the control system work?"
```

## system architecture

### complete pipeline flow

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  STEP File  │────▶│   CAD Parser     │────▶│                 │
└─────────────┘     └──────────────────┘     │                 │
                                              │                 │
┌─────────────┐     ┌──────────────────┐     │   Neo4j         │
│  PDF Docs   │────▶│  Doc Analyzer    │────▶│   Knowledge     │
└─────────────┘     └──────────────────┘     │   Graph         │
                                              │                 │
┌─────────────┐     ┌──────────────────┐     │                 │
│  Codebase   │────▶│  Code Analyzer   │────▶│                 │
└─────────────┘     └──────────────────┘     └────────┬────────┘
                                                       │
                                              ┌────────▼────────┐
                                              │  Unified        │
                                              │  GraphRAG       │
                                              │  Q&A System     │
                                              └─────────────────┘
```

### multi-agent architecture

each module uses a **hub-and-spoke multi-agent architecture** with specialized agents:

**CAD module agents:**
```
                    ┌─────────────────────────┐
                    │   CAD Project Manager   │
                    │   (gpt-oss:120b)        │
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

**documentation module agents (parallel execution):**
```
    ┌────────────────────┐
    │  Component         │
    │  Identifier        │────┐
    └────────────────────┘    │
                              │
    ┌────────────────────┐    │    ┌─────────────────┐
    │  Specifications    │────┼───▶│  Doc Analyzer   │
    │  Extractor         │    │    │  (orchestrator) │
    └────────────────────┘    │    └─────────────────┘
                              │
    ┌────────────────────┐    │
    │  Requirements      │────┘
    │  Analyst           │
    └────────────────────┘
```

**code module agents (parallel execution):**
```
    ┌────────────────────┐
    │  Module Purpose    │
    │  Analyzer          │────┐
    └────────────────────┘    │
                              │
    ┌────────────────────┐    │    ┌─────────────────┐
    │  Function/Class    │────┼───▶│  Code Analyzer  │
    │  Analyzer          │    │    │  (orchestrator) │
    └────────────────────┘    │    └─────────────────┘
                              │
    ┌────────────────────┐    │
    │  Dependency        │────┘
    │  Analyzer          │
    └────────────────────┘
```

### knowledge graph schema

**node types:**

**CAD domain:**
```cypher
(:Assembly {id, name, shape_type, level})
(:Part {id, name, shape_type, level, vertex_count, edge_count, face_count, category?, material?})
(:Vertex:GeometricEntity {id, x, y, z})
```

**documentation domain:**
```cypher
(:Requirement {id, category, requirement, rationale, priority, source_page})
(:Specification {parameter, value, unit, tolerance, category, source_page})
```

**code domain:**
```cypher
(:CodeModule {id, name, file_path, purpose, domain, key_functionality, algorithms})
(:CodeClass {id, name, purpose, key_methods, state, pattern})
(:CodeFunction {id, name, purpose, parameters, returns, algorithm})
```

**relationships:**

```cypher
# CAD relationships
(:Assembly)-[:CONTAINS]->(:Assembly|Part)
(:Part)-[:HAS_GEOMETRY]->(:Vertex)
(:Part)-[:FASTENS]->(:Part)
(:Part)-[:ADJACENT_TO]->(:Part)

# Code relationships
(:CodeModule)-[:CONTAINS_CLASS]->(:CodeClass)
(:CodeModule)-[:DEPENDS_ON]->(:CodeModule)
(:CodeClass)-[:CONTAINS_FUNCTION]->(:CodeFunction)

# Cross-domain relationships (inferred by GraphRAG)
# These are identified dynamically through semantic matching:
# - Parts ↔ CodeModules (by name matching)
# - Requirements ↔ CodeModules (by functionality)
# - Specifications ↔ Parts (by parameters)
```

## module details

### 1. CAD analysis module

**location:** `scripts/cad_module/`

**components:**
- `step_parser.py` - OpenCascade-based STEP file parser
- `agent.py` - 5-agent CAD analysis swarm
- `neo4j_schema.py` - Neo4j graph operations
- `grapher.py` - Main pipeline orchestrator

**what it extracts:**
- assembly hierarchy (assemblies → subassemblies → parts)
- geometric data (vertices, edges, faces)
- topology (shape types, complexity)
- spatial relationships
- component classifications

**typical output:**
- Assemblies: 10-50 nodes
- Parts: 50-200 nodes
- Vertices: 500-1000 nodes
- Relationships: 500-1500

**performance:** ~30-60 seconds depending on STEP file size

### 2. documentation analysis module

**location:** `scripts/doc_module/`

**components:**
- `pdf_parser.py` - PyMuPDF-based PDF extraction
- `simple_doc_analyzer.py` - 3-agent parallel analysis swarm
- `graph_enricher.py` - Neo4j enrichment logic
- `doc_enrichment_pipeline.py` - Main orchestrator

**agents:**
- **component identifier** - identifies hardware/software components mentioned
- **specifications extractor** - extracts technical specs (parameters, values, units, tolerances)
- **requirements analyst** - extracts functional requirements (with priority, rationale)

**what it extracts:**
- requirements (functional, performance, safety)
- specifications (dimensions, tolerances, materials)
- component identifications
- page references

**typical output:**
- Requirements: 10-30 nodes
- Specifications: 15-40 nodes
- high accuracy and detail

**performance:** ~40-45 seconds for typical technical PDF

### 3. code analysis module

**location:** `scripts/code_module/`

**components:**
- `code_parser.py` - AST-based Python parser
- `code_analyzer.py` - 3-agent code analysis swarm
- `code_graph_enricher.py` - Neo4j enrichment
- `code_rag.py` - Code-specific RAG Q&A
- `code_pipeline.py` - Main orchestrator
- `ask_question.py` - Q&A interface

**agents:**
- **module purpose analyzer** - determines what each module does
- **function/class analyzer** - analyzes methods and classes
- **dependency analyzer** - maps module dependencies

**what it extracts:**
- module purposes and domains
- class definitions and patterns
- function signatures and algorithms
- import dependencies
- code structure

**typical output:**
- CodeModules: 5-20 nodes
- CodeClasses: 10-50 nodes
- Dependencies: 10-40 relationships
- algorithm identification

**performance:** ~60 seconds per module

### 4. unified GraphRAG system

**location:** `scripts/unified_graphrag.py`

**capabilities:**
- queries across CAD, documentation, and code simultaneously
- cross-domain entity linking (e.g., hardware part → control code → functional requirements)
- comprehensive context retrieval from all three domains
- holistic question answering with cross-references

**features:**
- hardware-to-software mapping
- requirements traceability
- CAD-to-code connections
- multi-domain reasoning

**example usage:**

```
Question: "How does the system architecture integrate hardware and software?"

Answer:
The system integrates hardware and software through the following mappings:

| Hardware Component    | Software Module      | Requirements         |
|-----------------------|----------------------|----------------------|
| Actuator Assembly     | Control Module       | REQ-001: Motion      |
| Sensor Housing        | Processing Module    | REQ-002: Sensing     |
| Communication Unit    | Network Module       | REQ-003: Telemetry   |
| Main Housing          | Orchestrator         | REQ-004: Integration |

System Flow:
1. Initialization: Main orchestrator initializes subsystems
2. Operation: Control modules interface with hardware
3. Processing: Sensor data processed in real-time
4. Communication: Status reported via network module
5. Monitoring: System health tracked continuously

[Cross-references include assemblies, requirements, specifications, and code modules]
```

**performance:** ~25-45 seconds per question

## STEP parsing technical details

STEP (STandard for the Exchange of Product model data) files are ISO 10303 format files that contain complete 3D CAD model information including geometry, topology, assembly structure, and metadata. cadKG uses cadquery-ocp (Python bindings for OpenCascade Technology) to parse these files.

the parsing process (`scripts/cad_module/step_parser.py`):

### a. file loading
```python
# read STEP file using OpenCascade XCAF (Extended CAF) framework
doc = TDocStd_Document(TCollection_ExtendedString("XmlOcaf"))
shape_tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
STEPCAFControl_Reader().ReadFile(step_file_path)
```

### b. assembly tree extraction

STEP files organize CAD data in a hierarchical tree structure. the parser walks this tree using OpenCascade's label system:

- each node is a "label" in the XCAF document
- labels can be assemblies (containers) or parts (leaf nodes)
- labels reference shapes (geometric data) and have attributes (names, properties)

```python
# check if label is an assembly or simple shape
is_assembly = ShapeTool.IsAssembly_s(label)
is_simple = ShapeTool.IsSimpleShape_s(label)

# get children for assemblies
if is_assembly:
    components = ShapeTool.GetComponents_s(label)
```

### c. geometry extraction

for each part with geometry, the parser extracts topological data:

- **vertices**: 3D points (x, y, z coordinates)
- **edges**: curves connecting vertices (lines, arcs, splines)
- **faces**: surfaces bounded by edges (planes, cylinders, spheres)

```python
# get the shape geometry
shape = ShapeTool.GetShape_s(label)

# extract topological elements
vertices = []
for vertex in TopologyExplorer(shape).vertices():
    point = BRep_Tool.Pnt_s(vertex)
    vertices.append([point.X(), point.Y(), point.Z()])

edges = list(TopologyExplorer(shape).edges())
faces = list(TopologyExplorer(shape).faces())
```

### d. metadata extraction

part names and labels are stored as attributes on labels:

```python
# get name attribute
name_attr = TDataStd_Name()
if label.FindAttribute(TDataStd_Name.GetID_s(), name_attr):
    name = name_attr.Get().ToExtString()
```

### e. assembly tree construction

the parser recursively traverses the label tree and builds a nested dictionary structure:

```python
{
    "id": "label_1",
    "name": "Main Assembly",
    "is_assembly": True,
    "shape_type": "Assembly",
    "level": 0,
    "children": [
        {
            "id": "label_2",
            "name": "SubAssembly A",
            "is_assembly": False,
            "shape_type": "Part",
            "level": 1,
            "geometry": {
                "vertices": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], ...],
                "edges": 36,
                "faces": 9
            },
            "children": []
        },
        ...
    ]
}
```

### f. key OpenCascade classes used

- `TDocStd_Document`: XCAF document container
- `XCAFDoc_DocumentTool`: provides access to shape tools
- `XCAFDoc_ShapeTool`: manages shapes and assemblies
- `STEPCAFControl_Reader`: reads STEP files into XCAF
- `TDataStd_Name`: attribute storing part names
- `TopoDS_Shape`: base class for all geometric shapes
- `TopologyExplorer`: iterates over topological entities
- `BRep_Tool`: provides access to geometric data

## querying the knowledge graph

### cross-domain queries

```cypher
// Hardware implementing requirements
MATCH (p:Part), (r:Requirement)
WHERE p.name CONTAINS 'Motor' AND r.category = 'Control'
RETURN p, r

// Code modules related to assemblies (by name matching)
MATCH (m:CodeModule), (a:Assembly)
WHERE m.name = a.name OR a.name CONTAINS m.name
RETURN m, a

// Specifications with corresponding parts
MATCH (s:Specification), (p:Part)
WHERE p.name CONTAINS s.parameter
RETURN s, p
```

### domain-specific queries

**CAD queries:**
```cypher
// View assembly hierarchy
MATCH p=(a:Assembly)-[:CONTAINS*]->(child)
RETURN p LIMIT 50

// Find parts with most geometry
MATCH (p:Part)-[:HAS_GEOMETRY]->(v:Vertex)
RETURN p.name, count(v) as vertices
ORDER BY vertices DESC

// Find fastening relationships
MATCH (p1:Part)-[r:FASTENS]->(p2:Part)
RETURN p1.name, p2.name, r.confidence
```

**documentation queries:**
```cypher
// Requirements by priority
MATCH (r:Requirement)
WHERE r.priority = 'critical'
RETURN r.id, r.requirement

// Specifications with tolerances
MATCH (s:Specification)
WHERE s.tolerance IS NOT NULL
RETURN s.parameter, s.value, s.unit, s.tolerance
```

**code queries:**
```cypher
// Module dependencies
MATCH (m1:CodeModule)-[:DEPENDS_ON]->(m2:CodeModule)
RETURN m1.name, m2.name

// Classes by design pattern
MATCH (c:CodeClass)
WHERE c.pattern IS NOT NULL
RETURN c.name, c.pattern, c.purpose
```

## performance & statistics

### typical knowledge graph contents

after processing a complete engineering system:

```
Node counts:
- Assembly: 10-50
- Part: 50-200
- Vertex: 500-1000
- Requirement: 10-30
- Specification: 15-40
- CodeModule: 5-20
- CodeClass: 10-50

Total relationships: 500-1500+
```

### execution times

- **CAD parsing:** ~30-60s (depends on file size)
- **CAD graph creation:** ~10s
- **Documentation analysis:** ~40-45s per PDF
- **Code analysis:** ~60s per module
- **GraphRAG query:** ~25-45s per question
- **Complete pipeline:** ~7-8 minutes (or ~2 minutes with --skip-code)

### data quality

**requirements extraction:**
- accuracy: high
- detail: excellent (category, priority, rationale)
- coverage: comprehensive extraction from technical documents

**specifications extraction:**
- accuracy: high
- detail: excellent (parameter, value, unit, tolerance)
- coverage: comprehensive technical parameter extraction

**code analysis:**
- accuracy: excellent
- detail: very detailed (purpose, algorithms, patterns)
- coverage: all modules and classes analyzed

## project structure

```
cadkg/
├── scripts/
│   ├── cad_module/              # CAD processing
│   │   ├── step_parser.py       # STEP file parser
│   │   ├── neo4j_schema.py      # Neo4j schema & operations
│   │   ├── agent.py             # 5-agent CAD swarm
│   │   └── grapher.py           # CAD pipeline orchestrator
│   │
│   ├── doc_module/              # Documentation processing
│   │   ├── pdf_parser.py        # PDF text extraction
│   │   ├── simple_doc_analyzer.py    # 3-agent doc swarm
│   │   ├── graph_enricher.py    # Neo4j enrichment
│   │   └── doc_enrichment_pipeline.py # Doc pipeline orchestrator
│   │
│   ├── code_module/             # Code processing
│   │   ├── code_parser.py       # AST-based Python parser
│   │   ├── code_analyzer.py     # 3-agent code swarm
│   │   ├── code_graph_enricher.py    # Neo4j enrichment
│   │   ├── code_rag.py          # Code-specific RAG
│   │   ├── code_pipeline.py     # Code pipeline orchestrator
│   │   └── ask_question.py      # Q&A CLI
│   │
│   ├── integrated_pipeline.py   # CAD + Docs pipeline
│   ├── unified_graphrag.py      # Unified cross-domain Q&A
│   ├── chat_interface.py        # Gradio web chat UI
│   └── run_complete_pipeline.py # Complete pipeline orchestrator
│
├── data/
│   ├── cad/                     # STEP CAD files
│   ├── docs/                    # PDF documentation
│   └── codebase/                # Python source code
│
├── .env                         # Configuration (git-ignored)
├── .env.example                 # Config template
├── pyproject.toml               # Dependencies
├── uv.lock                      # Locked versions
└── README.md                    # This file
```

## troubleshooting

### CAD module issues

**OCP import errors**
```bash
uv add cadquery-ocp --force-reinstall
```

**large STEP files**
Use `--skip-agent` to avoid LLM token limits, or increase data limits in `agent.py`.

### documentation module issues

**PDF extraction errors**
Ensure PDFs are text-based (not scanned images). For scanned PDFs, OCR preprocessing is needed.

**slow analysis**
The 3-agent system is optimized for speed. If still slow, check Ollama model availability.

### code module issues

**import errors**
Ensure target codebase is valid Python that can be parsed by AST.

**None docstring errors**
Recent fix handles missing docstrings gracefully. Update to latest version.

### GraphRAG issues

**poor answer quality**
Ensure all three modules have been run to populate the graph. Check graph contents with:
```bash
.venv/bin/python -c "
from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'password'))
with driver.session() as s:
    result = s.run('MATCH (n) RETURN labels(n)[0] as type, count(n) as count ORDER BY count DESC')
    for r in result:
        print(f'{r[\"type\"]}: {r[\"count\"]}')
"
```

**slow query responses**
Increase Ollama model performance by allocating more GPU memory or using faster models.

### general issues

**Neo4j connection errors**
Verify Neo4j is running and credentials in `.env` are correct:
```bash
# Check Neo4j status
systemctl status neo4j  # Linux
# or open http://localhost:7474 in browser
```

**agent timeout errors**
Reduce `max_turns` in agent creation or limit input data size in preparation methods.

**JSON extraction errors**
Agent output isn't valid JSON. This is usually transient; retry the operation.

## optimization & caching

### result caching
- **md5-based caching** prevents redundant agent calls for identical inputs
- cache files stored in `cache/` directory
- clear cache with `rm -rf cache/` if results become stale

### performance strategies
- **progressive chunking** limits context size per agent (prevents token limit errors)
- **multi-model strategy** uses fast 20B for specialists, powerful 120B for coordination
- **parallel execution** runs independent agents concurrently with asyncio.gather()
- **performance monitoring** tracks execution time and cache hit rate

### data limits
adjust in each module's code if needed:
- CAD: 30 most complex parts for geometry analysis
- Docs: 5,000-8,000 char chunks
- Code: all modules (typically 5-10 per codebase)

## development

### adding a new CAD specialist agent

1. create agent in `scripts/cad_module/agent.py`:

```python
def _create_new_specialist(self) -> Agent:
    return Agent(
        name="new specialist",
        model=self.specialist_model,
        instructions="focus only on X. Return JSON: {...}"
    )
```

2. add tool wrapper:

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

4. update Project Manager tools list

### extending to other languages

the code module currently supports Python only. to add support for other languages:

1. create new parser (e.g., `java_parser.py`) using language-specific AST library
2. adapt `code_analyzer.py` agents for language specifics
3. update `code_graph_enricher.py` schema if needed
4. extend `code_pipeline.py` to detect and route file types

### adding new node types

to add new node types to the knowledge graph:

1. define schema in appropriate `neo4j_schema.py` or `graph_enricher.py`
2. create agent to extract that information
3. update GraphRAG context retrieval in `unified_graphrag.py`

## future enhancements

### near-term
- [ ] entity matching (fuzzy name matching CAD ↔ Code ↔ Docs)
- [ ] explicit semantic relationships (IMPLEMENTS, SATISFIES, CONTROLS)
- [ ] function node creation (currently only classes)
- [ ] incremental updates (vs full rebuild)

### long-term
- [ ] multi-language code support (C++, Java, JavaScript)
- [ ] image/diagram analysis from PDFs
- [ ] version control integration (track changes over time)
- [ ] automated testing integration
- [ ] web UI for graph exploration
- [ ] real-time code-to-CAD synchronization

## links & references

- [Neo4j Documentation](https://neo4j.com/docs/)
- [cadquery-ocp](https://github.com/CadQuery/cadquery-ocp) - OpenCascade Python bindings
- [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/) - Multi-agent framework
- [Ollama](https://ollama.ai/) - Local LLM inference
- [PyMuPDF](https://pymupdf.readthedocs.io/) - PDF processing
- [STEP ISO 10303](https://www.iso.org/standard/63141.html) - CAD file format standard

## license

This project is provided as-is for research and development purposes.

## status

**production-ready** ✅

the system is fully functional, tested, and ready for use on complex engineering projects involving CAD models, technical documentation, and software codebases.

all three modules integrate seamlessly, and the unified GraphRAG system provides accurate, detailed cross-domain question answering.
