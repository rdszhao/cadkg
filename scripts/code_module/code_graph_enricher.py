"""Knowledge graph enricher for code analysis - adds code structure and functionality to Neo4j."""

from typing import Any, Dict, List
from neo4j import GraphDatabase


class CodeKnowledgeGraphEnricher:
    """Enrich Neo4j knowledge graph with code structure and functionality."""

    def __init__(self, uri: str, user: str, password: str):
        """Initialize enricher.

        Args:
            uri: Neo4j connection URI
            user: Neo4j username
            password: Neo4j password
        """
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        """Close Neo4j connection."""
        if self.driver:
            self.driver.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def initialize_code_schema(self):
        """Initialize schema for code entities."""
        with self.driver.session() as session:
            # Create constraints
            constraints = [
                "CREATE CONSTRAINT code_module_id IF NOT EXISTS FOR (m:CodeModule) REQUIRE m.id IS UNIQUE",
                "CREATE CONSTRAINT code_function_id IF NOT EXISTS FOR (f:CodeFunction) REQUIRE f.id IS UNIQUE",
                "CREATE CONSTRAINT code_class_id IF NOT EXISTS FOR (c:CodeClass) REQUIRE c.id IS UNIQUE",
            ]

            for constraint in constraints:
                try:
                    session.run(constraint)
                    print(f"   ✓ Created code constraint")
                except Exception:
                    pass

            # Create indexes
            indexes = [
                "CREATE INDEX code_module_name IF NOT EXISTS FOR (m:CodeModule) ON (m.name)",
                "CREATE INDEX code_function_name IF NOT EXISTS FOR (f:CodeFunction) ON (f.name)",
                "CREATE INDEX code_class_name IF NOT EXISTS FOR (c:CodeClass) ON (c.name)",
                "CREATE INDEX code_domain IF NOT EXISTS FOR (m:CodeModule) ON (m.domain)",
            ]

            for index in indexes:
                try:
                    session.run(index)
                    print(f"   ✓ Created code index")
                except Exception:
                    pass

    def create_module_node(self, analysis: Dict) -> str:
        """Create CodeModule node.

        Args:
            analysis: Module analysis data

        Returns:
            Module ID
        """
        with self.driver.session() as session:
            module_name = analysis.get("module")
            purpose_data = analysis.get("purpose", {})

            query = """
            MERGE (m:CodeModule {id: $id})
            ON CREATE SET
                m.name = $name,
                m.file_path = $file_path,
                m.purpose = $purpose,
                m.domain = $domain,
                m.key_functionality = $key_functionality,
                m.algorithms = $algorithms
            ON MATCH SET
                m.name = $name,
                m.file_path = $file_path,
                m.purpose = $purpose,
                m.domain = $domain,
                m.key_functionality = $key_functionality,
                m.algorithms = $algorithms
            RETURN m.id as id
            """

            try:
                result = session.run(
                    query,
                    id=f"CODE_MODULE_{module_name}",
                    name=module_name,
                    file_path=analysis.get("file_path", ""),
                    purpose=purpose_data.get("purpose", ""),
                    domain=purpose_data.get("domain", ""),
                    key_functionality=str(purpose_data.get("key_functionality", [])),
                    algorithms=str(purpose_data.get("algorithms", []))
                )
                return result.single()["id"]
            except Exception as e:
                print(f"   ⚠️  Error creating module {module_name}: {e}")
                return ""

    def create_function_nodes(self, module_id: str, functions_data: Dict) -> int:
        """Create CodeFunction nodes.

        Args:
            module_id: Parent module ID
            functions_data: Functions analysis data

        Returns:
            Number of functions created
        """
        count = 0
        functions = functions_data.get("functions", [])

        with self.driver.session() as session:
            for func in functions:
                func_name = func.get("name")
                func_id = f"{module_id}_FUNC_{func_name}"

                query = """
                MERGE (f:CodeFunction {id: $id})
                ON CREATE SET
                    f.name = $name,
                    f.purpose = $purpose,
                    f.parameters = $parameters,
                    f.returns = $returns,
                    f.algorithm = $algorithm
                ON MATCH SET
                    f.name = $name,
                    f.purpose = $purpose,
                    f.parameters = $parameters,
                    f.returns = $returns,
                    f.algorithm = $algorithm
                WITH f
                MATCH (m:CodeModule {id: $module_id})
                MERGE (m)-[:CONTAINS_FUNCTION]->(f)
                RETURN f.id as id
                """

                try:
                    result = session.run(
                        query,
                        id=func_id,
                        name=func_name,
                        purpose=func.get("purpose", ""),
                        parameters=str(func.get("parameters", {})),
                        returns=func.get("returns", ""),
                        algorithm=func.get("algorithm", ""),
                        module_id=module_id
                    )
                    if result.single():
                        count += 1
                except Exception as e:
                    print(f"   ⚠️  Error creating function {func_name}: {e}")

        return count

    def create_class_nodes(self, module_id: str, classes_data: Dict) -> int:
        """Create CodeClass nodes.

        Args:
            module_id: Parent module ID
            classes_data: Classes analysis data

        Returns:
            Number of classes created
        """
        count = 0
        classes = classes_data.get("classes", [])

        with self.driver.session() as session:
            for cls in classes:
                class_name = cls.get("name")
                class_id = f"{module_id}_CLASS_{class_name}"

                query = """
                MERGE (c:CodeClass {id: $id})
                ON CREATE SET
                    c.name = $name,
                    c.purpose = $purpose,
                    c.key_methods = $key_methods,
                    c.state = $state,
                    c.pattern = $pattern
                ON MATCH SET
                    c.name = $name,
                    c.purpose = $purpose,
                    c.key_methods = $key_methods,
                    c.state = $state,
                    c.pattern = $pattern
                WITH c
                MATCH (m:CodeModule {id: $module_id})
                MERGE (m)-[:CONTAINS_CLASS]->(c)
                RETURN c.id as id
                """

                try:
                    result = session.run(
                        query,
                        id=class_id,
                        name=class_name,
                        purpose=cls.get("purpose", ""),
                        key_methods=str(cls.get("key_methods", {})),
                        state=str(cls.get("state", "")),
                        pattern=cls.get("pattern", ""),
                        module_id=module_id
                    )
                    if result.single():
                        count += 1
                except Exception as e:
                    print(f"   ⚠️  Error creating class {class_name}: {e}")

        return count

    def create_dependency_relationships(self, module_id: str, dependencies_data: Dict) -> int:
        """Create DEPENDS_ON relationships.

        Args:
            module_id: Module ID
            dependencies_data: Dependencies analysis

        Returns:
            Number of relationships created
        """
        count = 0
        deps = dependencies_data.get("dependencies", {})

        with self.driver.session() as session:
            # Create relationships for key dependencies
            key_deps = dependencies_data.get("key_dependencies", [])

            for dep in key_deps:
                query = """
                MATCH (m:CodeModule {id: $module_id})
                MERGE (d:CodeModule {name: $dep_name})
                MERGE (m)-[r:DEPENDS_ON]->(d)
                SET r.type = $dep_type
                RETURN id(r) as rel_id
                """

                # Determine dependency type
                dep_type = "unknown"
                if dep in deps.get("third_party", []):
                    dep_type = "third_party"
                elif dep in deps.get("standard_library", []):
                    dep_type = "standard_library"
                elif dep in deps.get("local", []):
                    dep_type = "local"

                try:
                    result = session.run(
                        query,
                        module_id=module_id,
                        dep_name=dep,
                        dep_type=dep_type
                    )
                    if result.single():
                        count += 1
                except Exception as e:
                    print(f"   ⚠️  Error creating dependency {dep}: {e}")

        return count

    def enrich_graph_with_code(self, analysis_results: List[Dict]) -> Dict[str, int]:
        """Enrich graph with code analysis.

        Args:
            analysis_results: List of module analyses

        Returns:
            Statistics dictionary
        """
        stats = {
            "modules_created": 0,
            "functions_created": 0,
            "classes_created": 0,
            "dependencies_created": 0
        }

        print("   🔧 Enriching knowledge graph with code analysis...")

        # Initialize schema
        self.initialize_code_schema()

        # Process each module
        for analysis in analysis_results:
            # Create module node
            module_id = self.create_module_node(analysis)
            if module_id:
                stats["modules_created"] += 1

            # Create function nodes
            if analysis.get("functions"):
                func_count = self.create_function_nodes(module_id, analysis["functions"])
                stats["functions_created"] += func_count

            # Create class nodes
            if analysis.get("classes"):
                class_count = self.create_class_nodes(module_id, analysis["classes"])
                stats["classes_created"] += class_count

            # Create dependencies
            if analysis.get("dependencies"):
                dep_count = self.create_dependency_relationships(module_id, analysis["dependencies"])
                stats["dependencies_created"] += dep_count

        print(f"\n   ✅ Code enrichment complete!")
        print(f"      - Modules: {stats['modules_created']}")
        print(f"      - Functions: {stats['functions_created']}")
        print(f"      - Classes: {stats['classes_created']}")
        print(f"      - Dependencies: {stats['dependencies_created']}")

        return stats

    def get_all_code_context(self) -> str:
        """Get all code information as context for RAG.

        Returns:
            Formatted text with all code information
        """
        with self.driver.session() as session:
            # Get all modules with their functions and classes
            query = """
            MATCH (m:CodeModule)
            OPTIONAL MATCH (m)-[:CONTAINS_FUNCTION]->(f:CodeFunction)
            OPTIONAL MATCH (m)-[:CONTAINS_CLASS]->(c:CodeClass)
            RETURN m, collect(DISTINCT f) as functions, collect(DISTINCT c) as classes
            ORDER BY m.name
            """

            result = session.run(query)
            context_parts = []

            for record in result:
                module = record["m"]
                functions = record["functions"]
                classes = record["classes"]

                # Module section
                context_parts.append(f"\n{'='*80}")
                context_parts.append(f"MODULE: {module['name']}")
                context_parts.append(f"{'='*80}")
                context_parts.append(f"Purpose: {module.get('purpose', 'N/A')}")
                context_parts.append(f"Domain: {module.get('domain', 'N/A')}")
                context_parts.append(f"File: {module.get('file_path', 'N/A')}")

                # Functions
                if functions and functions[0]:
                    context_parts.append(f"\nFunctions:")
                    for func in functions:
                        if func:
                            context_parts.append(f"  - {func['name']}: {func.get('purpose', 'N/A')}")
                            if func.get('algorithm'):
                                context_parts.append(f"    Algorithm: {func.get('algorithm')}")

                # Classes
                if classes and classes[0]:
                    context_parts.append(f"\nClasses:")
                    for cls in classes:
                        if cls:
                            context_parts.append(f"  - {cls['name']}: {cls.get('purpose', 'N/A')}")
                            if cls.get('pattern'):
                                context_parts.append(f"    Pattern: {cls.get('pattern')}")

            return "\n".join(context_parts)
