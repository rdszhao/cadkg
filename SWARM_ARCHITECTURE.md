# Multi-Agent Swarm Architecture Documentation

## Overview

This project implements a sophisticated **swarm-of-specialists** multi-agent framework that combines CAD analysis and documentation processing to create enriched knowledge graphs. The system uses the OpenAI Agents SDK with Ollama backend for all LLM operations.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     INTEGRATED PIPELINE                              │
│                                                                       │
│  ┌────────────────────┐              ┌──────────────────────┐      │
│  │   CAD Processing   │              │ Documentation        │      │
│  │                    │              │ Processing           │      │
│  │  ┌──────────────┐  │              │  ┌────────────────┐  │      │
│  │  │ STEP Parser  │  │              │  │  PDF Parser    │  │      │
│  │  └──────┬───────┘  │              │  └────────┬───────┘  │      │
│  │         │          │              │           │          │      │
│  │         ▼          │              │           ▼          │      │
│  │  ┌──────────────┐  │              │  ┌────────────────┐  │      │
│  │  │ CAD Agent    │  │              │  │  Doc Analysis  │  │      │
│  │  │ Swarm        │  │              │  │  Swarm         │  │      │
│  │  │ (5 agents)   │  │              │  │  (10 agents)   │  │      │
│  │  └──────┬───────┘  │              │  └────────┬───────┘  │      │
│  │         │          │              │           │          │      │
│  └─────────┼──────────┘              └───────────┼──────────┘      │
│            │                                     │                 │
│            ▼                                     ▼                 │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │              Neo4j Knowledge Graph                           │  │
│  │                                                               │  │
│  │  Nodes: Assembly, Part, Requirement, Specification, Function │  │
│  │  Relationships: CONTAINS, IMPLEMENTS, SATISFIES, etc.        │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## Agent Swarm Composition

### CAD Analysis Swarm (5 Specialist Agents)

Located in: `scripts/cad_module/agent.py`

1. **Geometry Analyst**
   - Analyzes geometric properties (vertices, edges, faces)
   - Calculates complexity ratings
   - Identifies shape characteristics

2. **Hierarchy Mapper**
   - Maps parent-child relationships
   - Tracks assembly depth levels
   - Identifies component groupings

3. **Component Classifier**
   - Categorizes parts (fasteners, structural, mechanical)
   - Identifies standard parts
   - Recognizes vendor codes

4. **Spatial Relations Analyst**
   - Identifies connection relationships
   - Detects adjacency and mating relationships
   - Infers spatial connections

5. **Properties Extractor**
   - Extracts material hints from names
   - Identifies size specifications
   - Parses standard identifiers

**Hub Agent:** CAD Project Manager (orchestrates all 5 specialists)

**Model Configuration:**
- Specialist agents: `OPENAI_MODEL_SPECIALIST` (e.g., gpt-oss:20b)
- Manager agent: `OPENAI_MODEL_MANAGER` (e.g., gpt-oss:120b)

### Documentation Analysis Swarm (10 Specialist Agents)

Located in: `scripts/doc_module/doc_swarm_agents.py`

#### Document Analysis Team (6 agents)

1. **Document Structure Analyst**
   - Analyzes document organization
   - Extracts table of contents
   - Identifies sections, tables, figures

2. **Technical Specifications Extractor**
   - Extracts dimensions and measurements
   - Identifies materials and tolerances
   - Captures performance parameters

3. **Component Identifier**
   - Identifies components in documentation
   - Tracks part numbers and designators
   - Maps vendor parts and standards

4. **Functional Requirements Analyst**
   - Extracts functional requirements
   - Identifies capabilities
   - Categorizes requirements by priority

5. **Relationship Mapper**
   - Maps component-to-component relationships
   - Identifies requirement dependencies
   - Tracks interface connections

6. **Metadata Curator**
   - Extracts document metadata
   - Builds glossary and acronyms
   - Manages references and citations

**Hub Agent:** Document Analysis Manager

#### Graph Enrichment Team (4 agents)

1. **Entity Matcher**
   - Matches documentation components to CAD parts
   - Uses fuzzy matching for similar names
   - Provides confidence scores

2. **Semantic Enricher**
   - Adds functional purpose properties
   - Enriches with design intent
   - Adds performance characteristics

3. **Relationship Enricher**
   - Creates IMPLEMENTS relationships
   - Adds SATISFIES connections
   - Establishes FUNCTIONS_AS links

4. **Context Augmenter**
   - Adds documentation references
   - Includes design rationale
   - Provides usage scenarios

**Hub Agent:** Graph Enrichment Manager

**Model Configuration:**
- Specialist agents: `OPENAI_MODEL_SPECIALIST` (e.g., gpt-oss:20b)
- Manager agents: `OPENAI_MODEL_MANAGER` (e.g., gpt-oss:120b)

## Technical Stack

### Core Technologies

- **Python**: 3.12+
- **Package Manager**: `uv` (modern Python package management)
- **LLM Framework**: OpenAI Agents SDK (v0.3.2+)
- **LLM Backend**: Ollama (local inference)
- **Database**: Neo4j (graph database)
- **PDF Processing**: PyMuPDF (pymupdf)
- **CAD Processing**: cadquery-ocp (OpenCascade bindings)

### Agent Framework Features

- **Hub-and-Spoke Pattern**: Hierarchical orchestration
- **Parallel Execution**: asyncio-based concurrent processing
- **Result Caching**: MD5-based content hashing
- **Performance Monitoring**: Detailed metrics and statistics
- **Error Handling**: Graceful fallbacks and recovery

## Knowledge Graph Schema

### Node Types

**Original (CAD-derived):**
- `Assembly` - CAD assemblies with hierarchy
- `Part` - Individual CAD parts with geometry
- `Vertex` - 3D geometric points
- `GeometricEntity` - Base geometric type

**Enriched (Documentation-derived):**
- `Requirement` - Functional/performance requirements
- `Specification` - Technical specifications
- `Function` - Functional capabilities

### Relationship Types

**Original:**
- `CONTAINS` - Hierarchical containment
- `HAS_GEOMETRY` - Part-to-geometry links

**Enriched:**
- `IMPLEMENTS` - Component implements requirement
- `SATISFIES` - Part satisfies specification
- `FUNCTIONS_AS` - Part functions as X
- `INTERFACES_WITH` - Part-to-part interfaces
- `DEPENDS_ON` - Dependencies
- `SUPPORTS` - Supports function

### Enriched Properties

Properties added to existing nodes:
- `function` - Functional purpose
- `purpose` - Design intent
- `role` - Operational role
- `material` - Material properties (from docs)
- `criticality` - Importance level
- `documentation_refs` - Page references
- `design_rationale` - Design reasoning
- `usage_scenarios` - Use cases
- `operational_context` - Operational info

## Data Flow

### Phase 1: CAD Processing

```
STEP File → Parser → Assembly Tree → CAD Agent Swarm → Enriched Data → Neo4j
```

1. Parse STEP file with OpenCascade
2. Extract assembly hierarchy and geometry
3. Analyze with CAD agent swarm (optional)
4. Create nodes and relationships in Neo4j

### Phase 2: Documentation Processing

```
PDF → Parser → Text Extraction → Doc Analysis Swarm → Enrichment Data
```

1. Parse PDF with PyMuPDF
2. Extract text, tables, structure
3. Analyze with document analysis swarm
4. Generate enrichment data

### Phase 3: Graph Enrichment

```
Enrichment Data + CAD Entities → Graph Enrichment Swarm → Neo4j Updates
```

1. Retrieve CAD entities from Neo4j
2. Match documentation entities to CAD entities
3. Add semantic properties
4. Create new relationships
5. Add documentation references

## Performance Characteristics

### Optimization Strategies

1. **Parallel Execution**
   - Specialist agents run concurrently when possible
   - Managed by asyncio.gather()

2. **Result Caching**
   - MD5 hash-based cache keys
   - Avoids redundant analysis
   - Significant speedup on repeated runs

3. **Progressive Chunking**
   - Large documents limited to manageable sizes
   - Entity sets limited to prevent token overflow
   - Prioritization of most relevant data

4. **Multi-Model Strategy**
   - Smaller, faster models for specialists
   - Larger, more capable models for managers
   - Optimizes cost/performance tradeoff

### Performance Metrics

The system tracks:
- Total execution time
- Per-agent execution times
- Cache hit/miss rates
- Parallel batch executions
- Agent call counts

## Usage Examples

### Standalone CAD Analysis

```bash
python scripts/cad_module/grapher.py \
    --step-file data/cad/assembly.STEP \
    --clear-graph
```

### Standalone Documentation Enrichment

```bash
python scripts/doc_module/doc_enrichment_pipeline.py \
    --pdf data/docs/documentation.pdf
```

### Integrated Pipeline

```bash
python scripts/integrated_pipeline.py \
    --step-file data/cad/assembly.STEP \
    --pdf-file data/docs/documentation.pdf \
    --clear-graph
```

## Configuration

All configuration via `.env` file:

```bash
# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Ollama
OPENAI_API_BASE=http://127.0.0.1:11435/v1
OPENAI_API_KEY=ollama
OPENAI_MODEL_MANAGER=gpt-oss:120b
OPENAI_MODEL_SPECIALIST=gpt-oss:20b

# Files
STEP_FILE_PATH=data/cad/100-1_A1-ASSY, PAYLOAD, CLINGERS.STEP
DOC_FILE_PATH=data/docs/CLINGERS_ecosystem.pdf
```

## File Structure

```
cadkg/
├── scripts/
│   ├── cad_module/
│   │   ├── __init__.py
│   │   ├── agent.py                    # CAD agent swarm (5 agents)
│   │   ├── step_parser.py              # STEP file parser
│   │   ├── neo4j_schema.py             # Graph schema & operations
│   │   └── grapher.py                  # CAD pipeline script
│   │
│   ├── doc_module/
│   │   ├── __init__.py
│   │   ├── pdf_parser.py               # PDF parsing
│   │   ├── doc_swarm_agents.py         # Doc swarm (10 agents)
│   │   ├── graph_enricher.py           # Graph enrichment ops
│   │   ├── doc_enrichment_pipeline.py  # Doc pipeline script
│   │   └── README.md                   # Module documentation
│   │
│   └── integrated_pipeline.py          # Full integrated pipeline
│
├── data/
│   ├── cad/                            # STEP files
│   └── docs/                           # PDF documentation
│
├── .env.example                        # Configuration template
├── pyproject.toml                      # Project dependencies
└── README.md                           # Project documentation
```

## Key Design Patterns

### Hub-and-Spoke Architecture

- **Hub agents** (managers) orchestrate specialist teams
- **Spoke agents** (specialists) perform focused tasks
- Specialists exposed as function tools to hub agents
- Hub agents synthesize specialist outputs

### Agent-as-Tool Pattern

Specialist agents are wrapped as function tools:

```python
@function_tool
async def analyze_geometry() -> str:
    """Analyze geometric properties."""
    return await self._run_specialist_with_monitoring(
        self.geometry_analyst,
        "Geometry Analyst",
        prompt,
        cache_data
    )
```

### Progressive Data Preparation

Each specialist receives custom-prepared data:

```python
# Prepare focused data for each specialist
self._cached_geometry_data = self._prepare_geometry_data(step_data)
self._cached_hierarchy_data = self._prepare_hierarchy_data(step_data)
self._cached_component_list = self._prepare_component_list(step_data)
```

## Future Enhancements

- [ ] Real-time agent collaboration visualization
- [ ] Multi-document cross-referencing
- [ ] Version control for knowledge graph changes
- [ ] Automated requirement traceability matrices
- [ ] Image and diagram analysis
- [ ] Voice-based query interface
- [ ] Export to standard formats (OSLC, ReqIF)

## References

- [OpenAI Agents SDK](https://github.com/openai/openai-agents-python)
- [Ollama](https://ollama.ai/)
- [Neo4j](https://neo4j.com/)
- [cadquery-ocp](https://github.com/CadQuery/cadquery-ocp)
- [PyMuPDF](https://pymupdf.readthedocs.io/)
