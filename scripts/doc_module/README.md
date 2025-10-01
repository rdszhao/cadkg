# Documentation Analysis Swarm Module

A complex **swarm-of-specialists** multi-agent framework for analyzing technical documentation and enriching CAD knowledge graphs using the OpenAI Agents SDK with Ollama backend.

## Overview

This module implements a sophisticated agent swarm architecture with:

- **10 Specialist Agents** organized into two teams
- **2 Hub Orchestrators** managing the specialists
- **Parallel execution** using asyncio
- **Result caching** for performance
- **Performance monitoring** and metrics

## Architecture

### Document Analysis Specialists (6 agents)

1. **Document Structure Analyst** - Analyzes document organization, sections, TOC
2. **Technical Specifications Extractor** - Extracts specs, dimensions, materials
3. **Component Identifier** - Identifies parts, assemblies, components
4. **Functional Requirements Analyst** - Extracts requirements and capabilities
5. **Relationship Mapper** - Maps relationships between entities
6. **Metadata Curator** - Extracts metadata, glossary, acronyms

### Graph Enrichment Specialists (4 agents)

1. **Entity Matcher** - Matches doc components to CAD parts
2. **Semantic Enricher** - Adds semantic properties (function, purpose)
3. **Relationship Enricher** - Creates semantic relationships (IMPLEMENTS, SATISFIES)
4. **Context Augmenter** - Adds documentation references and context

### Hub Orchestrators (2 managers)

1. **Document Analysis Manager** - Orchestrates document analysis specialists
2. **Graph Enrichment Manager** - Orchestrates graph enrichment specialists

## Usage

### Standalone Documentation Enrichment

```bash
# Analyze PDF and enrich existing CAD knowledge graph
python scripts/doc_module/doc_enrichment_pipeline.py \
    --pdf data/docs/CLINGERS_ecosystem.pdf

# Analysis only (skip graph update)
python scripts/doc_module/doc_enrichment_pipeline.py \
    --pdf data/docs/CLINGERS_ecosystem.pdf \
    --skip-graph-update

# Save results to JSON
python scripts/doc_module/doc_enrichment_pipeline.py \
    --pdf data/docs/CLINGERS_ecosystem.pdf \
    --output results.json
```

### Integrated CAD + Documentation Pipeline

```bash
# Full pipeline: CAD + Documentation
python scripts/integrated_pipeline.py

# With custom files
python scripts/integrated_pipeline.py \
    --step-file data/cad/my_assembly.STEP \
    --pdf-file data/docs/my_docs.pdf

# Skip AI agents (just parse and build graph)
python scripts/integrated_pipeline.py \
    --skip-cad-agent \
    --skip-doc-agent
```

### Python API

```python
from doc_module import PDFParser, DocumentAnalysisSwarm, KnowledgeGraphEnricher

# Parse PDF
with PDFParser("data/docs/document.pdf") as parser:
    text = parser.get_full_text()
    summary = parser.get_summary()

# Analyze with agent swarm
swarm = DocumentAnalysisSwarm()
results = swarm.process(document_text, cad_entities)

# Apply enrichments to Neo4j
with KnowledgeGraphEnricher(uri, user, password) as enricher:
    stats = enricher.apply_enrichments(results)
```

## Agent Swarm Details

### Hub-and-Spoke Pattern

The system uses a hub-and-spoke architecture where:
- **Hub agents** (managers) orchestrate teams of specialists
- **Spoke agents** (specialists) perform focused analysis
- Specialists are called as **tools** by hub agents
- Hub agents synthesize results into unified outputs

### Parallel Execution

Specialist agents can execute in parallel when called by hub agents, maximizing throughput.

### Caching Strategy

- Results are cached using MD5 hashes of input data
- Avoids re-analyzing identical content
- Significantly improves performance on repeated runs

### Performance Monitoring

The system tracks:
- Agent execution times
- Cache hit/miss rates
- Parallel batch executions
- Per-agent statistics

## Graph Enrichment

### New Node Types Created

- **Requirement** - Functional and performance requirements
- **Specification** - Technical specifications and parameters
- **Function** - Functional capabilities

### New Relationship Types

- `IMPLEMENTS` - Component implements requirement
- `SATISFIES` - Part satisfies specification
- `FUNCTIONS_AS` - Part functions as X
- `INTERFACES_WITH` - Part interfaces with other part
- `DEPENDS_ON` - Part depends on other part
- `SUPPORTS` - Part supports function

### Properties Added to Existing Nodes

- `function` - Functional purpose
- `purpose` - Design intent
- `role` - Operational role
- `material` - Material properties
- `criticality` - Importance level
- `documentation_refs` - Documentation page references
- `design_rationale` - Design reasoning
- `usage_scenarios` - Use cases
- `operational_context` - Operational information

## Configuration

Set in `.env` file:

```bash
# Ollama Configuration
OPENAI_API_BASE=http://127.0.0.1:11435/v1
OPENAI_API_KEY=ollama
OPENAI_MODEL_MANAGER=gpt-oss:120b      # Larger model for orchestration
OPENAI_MODEL_SPECIALIST=gpt-oss:20b    # Smaller model for specialists

# Files
DOC_FILE_PATH=data/docs/CLINGERS_ecosystem.pdf
STEP_FILE_PATH=data/cad/100-1_A1-ASSY, PAYLOAD, CLINGERS.STEP

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password_here
```

## Module Structure

```
doc_module/
├── __init__.py                      # Module exports
├── pdf_parser.py                    # PDF parsing with PyMuPDF
├── doc_swarm_agents.py              # Agent swarm implementation
├── graph_enricher.py                # Neo4j enrichment operations
├── doc_enrichment_pipeline.py       # Main pipeline script
└── README.md                        # This file
```

## Example Queries

After enrichment, query the enhanced graph:

```cypher
# View requirements
MATCH (r:Requirement) RETURN r LIMIT 10

# Find parts implementing requirements
MATCH (p:Part)-[:IMPLEMENTS]->(r:Requirement)
RETURN p.name, r.requirement

# View parts with functional descriptions
MATCH (p:Part)
WHERE p.function IS NOT NULL
RETURN p.name, p.function, p.purpose

# Find specifications
MATCH (s:Specification)
WHERE s.category = 'performance'
RETURN s.parameter, s.value, s.unit

# View parts with documentation references
MATCH (p:Part)
WHERE p.documentation_refs IS NOT NULL
RETURN p.name, p.documentation_refs, p.design_rationale
```

## Performance Optimization

### Document Size Limiting

Large documents are automatically truncated to 50,000 characters for processing to avoid token limits and improve performance.

### Entity Limiting

CAD entities are limited to 100 by default when passing to enrichment agents.

### Progressive Summarization

The system uses progressive summarization techniques to handle large datasets efficiently.

## Dependencies

- `pymupdf` (PyMuPDF) - PDF parsing
- `openai-agents` - OpenAI Agents SDK
- `neo4j` - Neo4j Python driver
- `python-dotenv` - Environment configuration

## Troubleshooting

### Ollama Connection Issues

```bash
# Verify Ollama is running
curl http://127.0.0.1:11435/v1/models

# Check model availability
ollama list
```

### Large Document Processing

For very large documents, consider:
- Splitting into sections
- Processing key sections only
- Increasing character limit in code

### Neo4j Connection

```bash
# Test connection
cypher-shell -u neo4j -p password

# Verify database is running
systemctl status neo4j  # Linux
```

## Future Enhancements

- [ ] Support for multiple document formats (Word, Markdown)
- [ ] Image and diagram analysis
- [ ] Table extraction and structured data parsing
- [ ] Cross-document relationship mapping
- [ ] Version control integration for documentation
- [ ] Automated requirement traceability matrix

## License

Part of the Caddie project - CAD Knowledge Graph Construction System
