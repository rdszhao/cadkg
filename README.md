# Caddie

A Python-based system that extracts information from STEP CAD files and constructs a knowledge graph in Neo4j using OpenAI-powered agents.

## Features

- **STEP File Parsing**: Extracts geometric and assembly information from STEP (ISO 10303) files using OpenCascade
- **AI-Powered Analysis**: Uses OpenAI Agents SDK to analyze and structure CAD data with specialized agents
- **Knowledge Graph Construction**: Automatically builds a hierarchical knowledge graph in Neo4j
- **Rich Schema**: Captures assemblies, parts, geometric entities, and their relationships

## Prerequisites

- Python 3.12+
- Neo4j database (local or remote)
- OpenAI API key

## Installation

1. Clone the repository and navigate to the project directory

2. Install dependencies using uv:
```bash
uv sync
```

3. Create a `.env` file based on `.env.example`:
```bash
cp .env.example .env
```

4. Configure your `.env` file:
```bash
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# STEP File Configuration
STEP_FILE_PATH=data/100-1_A1-ASSY, PAYLOAD, CLINGERS.STEP
```

## Usage

### Basic Usage

Process a STEP file and create a knowledge graph:

```bash
python scripts/grapher.py
```

### Command Line Options

```bash
# Use a different STEP file
python scripts/grapher.py --step-file path/to/your/file.STEP

# Clear existing graph data before loading
python scripts/grapher.py --clear-graph

# Skip AI agent enrichment (faster, direct mapping)
python scripts/grapher.py --skip-agent

# Use a different OpenAI model
python scripts/grapher.py --model gpt-4o

# Only show statistics without populating graph
python scripts/grapher.py --stats-only

# Override Neo4j connection
python scripts/grapher.py --neo4j-uri bolt://localhost:7687 --neo4j-user neo4j --neo4j-password password
```

### Example Workflow

1. **Start Neo4j** (if running locally):
```bash
# Using Docker
docker run -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:latest

# Or use Neo4j Desktop
```

2. **Run the pipeline**:
```bash
# First time: clear any existing data and use AI agent
python scripts/grapher.py --clear-graph

# Subsequent runs: just add new data
python scripts/grapher.py
```

3. **Explore the graph**:
- Open Neo4j Browser: http://localhost:7474
- Run sample queries (see below)

## Neo4j Queries

### View Assembly Hierarchy
```cypher
MATCH p=(a:Assembly)-[:CONTAINS*]->(child)
RETURN p LIMIT 50
```

### Find All Parts with Geometry
```cypher
MATCH (p:Part)-[:HAS_GEOMETRY]->(v:Vertex)
RETURN p.name, p.edge_count, p.face_count, count(v) as vertex_count
ORDER BY vertex_count DESC
```

### Find Top-Level Assemblies
```cypher
MATCH (a:Assembly)
WHERE NOT (()-[:CONTAINS]->(a))
RETURN a.name, a.id
```

### Get Full Part Details
```cypher
MATCH (p:Part {name: 'YourPartName'})
OPTIONAL MATCH (p)-[:HAS_GEOMETRY]->(v:Vertex)
RETURN p, collect(v) as vertices
```

### Find Components by Level
```cypher
MATCH (n)
WHERE n.level = 2
RETURN n.name, labels(n), n.shape_type
```

## Architecture

### Modules

- **`step_parser.py`**: STEP file parser using OpenCascade (OCP)
  - Extracts assembly hierarchy
  - Parses geometric entities (vertices, edges, faces, solids)
  - Generates structured data

- **`agent.py`**: OpenAI Agents SDK system with specialized agents
  - Analyzes assembly structure
  - Extracts entities and relationships
  - Enriches data with AI-powered insights
  - Uses Agent/Runner pattern with fallback mechanisms

- **`neo4j_schema.py`**: Neo4j knowledge graph schema and operations
  - Defines node types (Assembly, Part, Vertex, etc.)
  - Creates relationships (CONTAINS, HAS_GEOMETRY, etc.)
  - Provides query utilities

- **`grapher.py`**: Main orchestration script
  - Coordinates the full pipeline
  - Handles configuration and CLI arguments
  - Reports statistics and results

### Knowledge Graph Schema

**Node Types:**
- `Assembly`: Top-level assemblies and sub-assemblies
- `Part`: Individual CAD parts
- `Vertex`: Geometric vertices (3D points)
- `GeometricEntity`: Base type for geometric elements

**Relationships:**
- `CONTAINS`: Hierarchical parent-child relationship
- `HAS_GEOMETRY`: Links parts to their geometric entities

**Properties:**
- Name, ID, level in hierarchy
- Shape type (SOLID, SHELL, FACE, etc.)
- Geometric counts (edges, faces, vertices)
- 3D coordinates for vertices

## Development

### Running Tests
```bash
# Add test dependencies
uv add --dev pytest

# Run tests
pytest
```

### Adding New Features

The modular architecture makes it easy to extend:

1. **New STEP entity types**: Update `step_parser.py`
2. **New relationship types**: Update `neo4j_schema.py`
3. **Enhanced AI analysis**: Update `agent.py`

## Troubleshooting

### OpenCascade Import Errors
If you see import errors for OCP:
```bash
uv add OCP --force-reinstall
```

### Neo4j Connection Issues
- Verify Neo4j is running: `neo4j status`
- Check connection details in `.env`
- Ensure ports 7474 (HTTP) and 7687 (Bolt) are accessible

### Large STEP Files
For very large files:
- Use `--skip-agent` to avoid LLM token limits
- Consider processing in chunks
- Increase Neo4j memory configuration

## License

MIT

## Contributing

Contributions welcome! Please open an issue or submit a PR.
