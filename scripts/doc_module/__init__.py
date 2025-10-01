"""Document analysis and knowledge graph enrichment module.

This module provides tools for:
- Parsing PDF technical documentation
- Analyzing documents with a swarm of specialist AI agents
- Enriching CAD knowledge graphs with semantic information
- Using Ollama backend for LLM operations
"""

from .pdf_parser import PDFParser, parse_pdf
from .simple_doc_analyzer import SimpleDocumentAnalyzer
from .doc_swarm_agents import DocumentAnalysisSwarm, create_enriched_knowledge_graph
from .graph_enricher import KnowledgeGraphEnricher

__all__ = [
    "PDFParser",
    "parse_pdf",
    "SimpleDocumentAnalyzer",
    "DocumentAnalysisSwarm",
    "create_enriched_knowledge_graph",
    "KnowledgeGraphEnricher",
]
