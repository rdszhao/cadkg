"""Neo4j knowledge graph enrichment from document analysis results.

This module takes the output from the document analysis swarm and applies
enrichments to the Neo4j knowledge graph.
"""

from typing import Any, Dict, List
from neo4j import GraphDatabase


class KnowledgeGraphEnricher:
    """Enrich Neo4j knowledge graph with documentation insights."""

    def __init__(self, uri: str, user: str, password: str):
        """Initialize the graph enricher.

        Args:
            uri: Neo4j connection URI
            user: Neo4j username
            password: Neo4j password
        """
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        """Close the Neo4j connection."""
        if self.driver:
            self.driver.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def initialize_enrichment_schema(self):
        """Initialize schema for enrichment (new node types, relationships)."""
        with self.driver.session() as session:
            # Create constraints for new node types
            constraints = [
                "CREATE CONSTRAINT requirement_id IF NOT EXISTS FOR (r:Requirement) REQUIRE r.id IS UNIQUE",
                "CREATE CONSTRAINT specification_id IF NOT EXISTS FOR (s:Specification) REQUIRE s.id IS UNIQUE",
                "CREATE CONSTRAINT function_id IF NOT EXISTS FOR (f:Function) REQUIRE f.id IS UNIQUE",
            ]

            for constraint in constraints:
                try:
                    session.run(constraint)
                    print(f"   ✓ Created enrichment constraint")
                except Exception as e:
                    # Constraint may already exist
                    pass

            # Create indexes for enrichment properties
            indexes = [
                "CREATE INDEX part_function IF NOT EXISTS FOR (p:Part) ON (p.function)",
                "CREATE INDEX part_material IF NOT EXISTS FOR (p:Part) ON (p.material)",
                "CREATE INDEX requirement_category IF NOT EXISTS FOR (r:Requirement) ON (r.category)",
            ]

            for index in indexes:
                try:
                    session.run(index)
                    print(f"   ✓ Created enrichment index")
                except Exception as e:
                    pass

    def add_semantic_properties(self, enrichments: List[Dict[str, Any]]) -> int:
        """Add semantic properties to existing entities.

        Args:
            enrichments: List of entity enrichments with properties

        Returns:
            Number of entities enriched
        """
        count = 0
        with self.driver.session() as session:
            for enrichment in enrichments:
                entity_id = enrichment.get("entity_id")
                properties = enrichment.get("properties", {})

                if not entity_id or not properties:
                    continue

                # Build SET clause dynamically
                set_clauses = []
                params = {"entity_id": entity_id}

                for key, value in properties.items():
                    if value and key != "source_pages":
                        param_name = f"prop_{key}"
                        set_clauses.append(f"e.{key} = ${param_name}")
                        params[param_name] = value

                if not set_clauses:
                    continue

                query = f"""
                MATCH (e {{id: $entity_id}})
                SET {", ".join(set_clauses)}
                RETURN e.id as id
                """

                try:
                    result = session.run(query, **params)
                    if result.single():
                        count += 1
                except Exception as e:
                    print(f"   ⚠️  Failed to enrich {entity_id}: {e}")

        return count

    def create_requirement_nodes(self, requirements: List[Dict[str, Any]]) -> int:
        """Create Requirement nodes.

        Args:
            requirements: List of requirement data

        Returns:
            Number of requirements created
        """
        count = 0
        with self.driver.session() as session:
            for req in requirements:
                req_id = req.get("id")
                if not req_id:
                    continue

                query = """
                MERGE (r:Requirement {id: $id})
                ON CREATE SET
                    r.category = $category,
                    r.requirement = $requirement,
                    r.rationale = $rationale,
                    r.priority = $priority,
                    r.source_page = $source_page
                ON MATCH SET
                    r.category = $category,
                    r.requirement = $requirement,
                    r.rationale = $rationale,
                    r.priority = $priority,
                    r.source_page = $source_page
                RETURN r.id as id
                """

                try:
                    result = session.run(
                        query,
                        id=req_id,
                        category=req.get("category", ""),
                        requirement=req.get("requirement", ""),
                        rationale=req.get("rationale", ""),
                        priority=req.get("priority", ""),
                        source_page=req.get("source_page", 0)
                    )
                    if result.single():
                        count += 1
                except Exception as e:
                    print(f"   ⚠️  Failed to create requirement {req_id}: {e}")

        return count

    def create_specification_nodes(self, specifications: List[Dict[str, Any]]) -> int:
        """Create Specification nodes.

        Args:
            specifications: List of specification data

        Returns:
            Number of specifications created
        """
        count = 0
        with self.driver.session() as session:
            for spec in specifications:
                spec_id = f"SPEC-{spec.get('category', 'UNK')}-{count}"

                query = """
                MERGE (s:Specification {id: $id})
                ON CREATE SET
                    s.category = $category,
                    s.parameter = $parameter,
                    s.value = $value,
                    s.unit = $unit,
                    s.tolerance = $tolerance,
                    s.source_page = $source_page
                ON MATCH SET
                    s.category = $category,
                    s.parameter = $parameter,
                    s.value = $value,
                    s.unit = $unit,
                    s.tolerance = $tolerance,
                    s.source_page = $source_page
                RETURN s.id as id
                """

                try:
                    result = session.run(
                        query,
                        id=spec_id,
                        category=spec.get("category", ""),
                        parameter=spec.get("parameter", ""),
                        value=str(spec.get("value", "")),
                        unit=spec.get("unit", ""),
                        tolerance=spec.get("tolerance", ""),
                        source_page=spec.get("source_page", 0)
                    )
                    if result.single():
                        count += 1
                except Exception as e:
                    print(f"   ⚠️  Failed to create specification: {e}")

        return count

    def create_function_nodes(self, capabilities: List[Dict[str, Any]]) -> int:
        """Create Function nodes from capabilities.

        Args:
            capabilities: List of functional capability data

        Returns:
            Number of functions created
        """
        count = 0
        with self.driver.session() as session:
            for cap in capabilities:
                func_name = cap.get("name")
                if not func_name:
                    continue

                func_id = f"FUNC-{func_name.replace(' ', '_')}"

                query = """
                MERGE (f:Function {id: $id})
                ON CREATE SET
                    f.name = $name,
                    f.description = $description,
                    f.parameters = $parameters
                ON MATCH SET
                    f.name = $name,
                    f.description = $description,
                    f.parameters = $parameters
                RETURN f.id as id
                """

                try:
                    result = session.run(
                        query,
                        id=func_id,
                        name=func_name,
                        description=cap.get("description", ""),
                        parameters=str(cap.get("parameters", {}))
                    )
                    if result.single():
                        count += 1
                except Exception as e:
                    print(f"   ⚠️  Failed to create function {func_id}: {e}")

        return count

    def create_semantic_relationships(self, relationships: List[Dict[str, Any]]) -> int:
        """Create semantic relationships between entities.

        Args:
            relationships: List of relationship data

        Returns:
            Number of relationships created
        """
        count = 0
        with self.driver.session() as session:
            for rel in relationships:
                source_id = rel.get("source_id")
                target_id = rel.get("target_id")
                relation_type = rel.get("relation_type", "RELATED_TO")

                if not source_id or not target_id:
                    continue

                # Build properties
                properties = rel.get("properties", {})
                prop_clauses = []
                params = {
                    "source_id": source_id,
                    "target_id": target_id
                }

                for key, value in properties.items():
                    if value:
                        param_name = f"prop_{key}"
                        prop_clauses.append(f"r.{key} = ${param_name}")
                        params[param_name] = value

                prop_set = f"SET {', '.join(prop_clauses)}" if prop_clauses else ""

                query = f"""
                MATCH (source {{id: $source_id}})
                MATCH (target {{id: $target_id}})
                MERGE (source)-[r:{relation_type}]->(target)
                {prop_set}
                RETURN id(r) as rel_id
                """

                try:
                    result = session.run(query, **params)
                    if result.single():
                        count += 1
                except Exception as e:
                    print(f"   ⚠️  Failed to create relationship {source_id}-[{relation_type}]->{target_id}: {e}")

        return count

    def add_documentation_references(self, augmentations: List[Dict[str, Any]]) -> int:
        """Add documentation references to entities.

        Args:
            augmentations: List of context augmentations

        Returns:
            Number of entities augmented
        """
        count = 0
        with self.driver.session() as session:
            for aug in augmentations:
                entity_id = aug.get("entity_id")
                context = aug.get("context", {})

                if not entity_id or not context:
                    continue

                query = """
                MATCH (e {id: $entity_id})
                SET e.documentation_refs = $doc_refs,
                    e.design_rationale = $rationale,
                    e.usage_scenarios = $scenarios,
                    e.operational_context = $op_context,
                    e.doc_notes = $notes
                RETURN e.id as id
                """

                try:
                    result = session.run(
                        query,
                        entity_id=entity_id,
                        doc_refs=str(context.get("documentation_refs", [])),
                        rationale=context.get("design_rationale", ""),
                        scenarios=str(context.get("usage_scenarios", [])),
                        op_context=context.get("operational_context", ""),
                        notes=context.get("notes", "")
                    )
                    if result.single():
                        count += 1
                except Exception as e:
                    print(f"   ⚠️  Failed to augment {entity_id}: {e}")

        return count

    def apply_enrichments(self, enrichment_results: Dict[str, Any]) -> Dict[str, int]:
        """Apply all enrichments from analysis results.

        Args:
            enrichment_results: Results from document analysis swarm

        Returns:
            Statistics on enrichments applied
        """
        stats = {
            "semantic_properties_added": 0,
            "requirements_created": 0,
            "specifications_created": 0,
            "functions_created": 0,
            "relationships_created": 0,
            "documentation_refs_added": 0
        }

        print("   🔧 Applying enrichments to knowledge graph...")

        # Initialize schema
        self.initialize_enrichment_schema()

        # Extract enrichment data
        graph_enrichment = enrichment_results.get("graph_enrichment", {})
        doc_analysis = enrichment_results.get("document_analysis", {})

        # Apply semantic properties
        semantic_props = graph_enrichment.get("semantic_properties", {})
        if isinstance(semantic_props, dict):
            enrichments = semantic_props.get("enrichments", [])
            if enrichments:
                stats["semantic_properties_added"] = self.add_semantic_properties(enrichments)

        # Create requirement nodes
        requirements_data = doc_analysis.get("requirements", {})
        if isinstance(requirements_data, dict):
            req_list = requirements_data.get("requirements", [])
            if req_list:
                # Auto-generate IDs for requirements
                for idx, req in enumerate(req_list):
                    if "id" not in req or not req["id"]:
                        req["id"] = f"REQ-{idx+1:03d}"
                stats["requirements_created"] = self.create_requirement_nodes(req_list)

        # Create specification nodes
        specifications_data = doc_analysis.get("specifications", {})
        if isinstance(specifications_data, dict):
            spec_list = specifications_data.get("specifications", [])
            if spec_list:
                stats["specifications_created"] = self.create_specification_nodes(spec_list)

        # Create function nodes
        requirements = doc_analysis.get("requirements", {})
        if isinstance(requirements, dict):
            capabilities = requirements.get("capabilities", [])
            if capabilities:
                stats["functions_created"] = self.create_function_nodes(capabilities)

        # Create semantic relationships
        new_relationships = graph_enrichment.get("new_relationships", {})
        if isinstance(new_relationships, dict):
            rel_list = new_relationships.get("relationships", [])
            if rel_list:
                stats["relationships_created"] = self.create_semantic_relationships(rel_list)

        # Add documentation references
        context_augs = graph_enrichment.get("context_augmentations", {})
        if isinstance(context_augs, dict):
            aug_list = context_augs.get("augmentations", [])
            if aug_list:
                stats["documentation_refs_added"] = self.add_documentation_references(aug_list)

        print(f"   ✅ Enrichments applied:")
        print(f"      - Semantic properties: {stats['semantic_properties_added']}")
        print(f"      - Requirements: {stats['requirements_created']}")
        print(f"      - Specifications: {stats['specifications_created']}")
        print(f"      - Functions: {stats['functions_created']}")
        print(f"      - Relationships: {stats['relationships_created']}")
        print(f"      - Documentation refs: {stats['documentation_refs_added']}")

        return stats

    def get_cad_entities(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve CAD entities from the knowledge graph.

        Args:
            limit: Maximum number of entities to retrieve

        Returns:
            List of CAD entities
        """
        with self.driver.session() as session:
            query = """
            MATCH (e)
            WHERE e:Assembly OR e:Part
            RETURN e.id as id, e.name as name, labels(e) as labels,
                   e.shape_type as shape_type, e.level as level
            LIMIT $limit
            """
            result = session.run(query, limit=limit)

            entities = []
            for record in result:
                entities.append({
                    "id": record["id"],
                    "name": record["name"],
                    "type": record["labels"][0] if record["labels"] else "Unknown",
                    "shape_type": record.get("shape_type", ""),
                    "level": record.get("level", 0)
                })

            return entities
