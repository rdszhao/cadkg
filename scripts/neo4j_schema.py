"""Neo4j schema definition and initialization for CAD knowledge graph."""

from typing import Any
from neo4j import GraphDatabase, Driver


class CADKnowledgeGraph:
    """Knowledge graph schema and operations for CAD assembly data."""

    def __init__(self, uri: str, user: str, password: str):
        """Initialize the Neo4j connection.

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

    def initialize_schema(self):
        """Initialize the Neo4j schema with constraints and indexes."""
        with self.driver.session() as session:
            # Create constraints for unique IDs
            constraints = [
                "CREATE CONSTRAINT assembly_id IF NOT EXISTS FOR (a:Assembly) REQUIRE a.id IS UNIQUE",
                "CREATE CONSTRAINT part_id IF NOT EXISTS FOR (p:Part) REQUIRE p.id IS UNIQUE",
                "CREATE CONSTRAINT component_id IF NOT EXISTS FOR (c:Component) REQUIRE c.id IS UNIQUE",
                "CREATE CONSTRAINT vertex_id IF NOT EXISTS FOR (v:Vertex) REQUIRE v.id IS UNIQUE",
            ]

            for constraint in constraints:
                try:
                    session.run(constraint)
                    print(f"✓ Created constraint")
                except Exception as e:
                    print(f"Note: Constraint may already exist - {str(e)[:50]}")

            # Create indexes for performance
            indexes = [
                "CREATE INDEX assembly_name IF NOT EXISTS FOR (a:Assembly) ON (a.name)",
                "CREATE INDEX part_name IF NOT EXISTS FOR (p:Part) ON (p.name)",
                "CREATE INDEX shape_type IF NOT EXISTS FOR (n:GeometricEntity) ON (n.shape_type)",
            ]

            for index in indexes:
                try:
                    session.run(index)
                    print(f"✓ Created index")
                except Exception as e:
                    print(f"Note: Index may already exist - {str(e)[:50]}")

    def clear_graph(self):
        """Clear all nodes and relationships from the graph (use with caution!)."""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            print("✓ Graph cleared")

    def create_assembly_node(self, assembly_data: dict[str, Any]) -> str:
        """Create an assembly node in the graph.

        Args:
            assembly_data: Dictionary containing assembly information

        Returns:
            ID of the created assembly node
        """
        with self.driver.session() as session:
            query = """
            MERGE (a:Assembly {id: $id})
            ON CREATE SET
                a.name = $name,
                a.level = $level,
                a.shape_type = $shape_type
            ON MATCH SET
                a.name = $name,
                a.level = $level,
                a.shape_type = $shape_type
            RETURN a.id as id
            """
            result = session.run(
                query,
                id=assembly_data["id"],
                name=assembly_data["name"],
                level=assembly_data["level"],
                shape_type=assembly_data["shape_type"],
            )
            return result.single()["id"]

    def create_part_node(self, part_data: dict[str, Any]) -> str:
        """Create a part node in the graph.

        Args:
            part_data: Dictionary containing part information

        Returns:
            ID of the created part node
        """
        with self.driver.session() as session:
            # Base properties
            props = {
                "id": part_data["id"],
                "name": part_data["name"],
                "level": part_data["level"],
                "shape_type": part_data.get("shape_type", "UNKNOWN"),
            }

            # Add geometric properties if available
            if "geometry" in part_data:
                geom = part_data["geometry"]
                props["edge_count"] = geom.get("edges", 0)
                props["face_count"] = geom.get("faces", 0)
                props["vertex_count"] = len(geom.get("vertices", []))
                props["has_volume"] = geom.get("volume_exists", False)
            else:
                # Set defaults if no geometry
                props["edge_count"] = 0
                props["face_count"] = 0
                props["vertex_count"] = 0
                props["has_volume"] = False

            query = """
            MERGE (p:Part {id: $id})
            ON CREATE SET
                p.name = $name,
                p.level = $level,
                p.shape_type = $shape_type,
                p.edge_count = $edge_count,
                p.face_count = $face_count,
                p.vertex_count = $vertex_count,
                p.has_volume = $has_volume
            ON MATCH SET
                p.name = $name,
                p.level = $level,
                p.shape_type = $shape_type,
                p.edge_count = $edge_count,
                p.face_count = $face_count,
                p.vertex_count = $vertex_count,
                p.has_volume = $has_volume
            RETURN p.id as id
            """
            result = session.run(query, **props)
            return result.single()["id"]

    def create_vertices(self, part_id: str, vertices: list[dict[str, float]]) -> list[str]:
        """Create vertex nodes for a part.

        Args:
            part_id: ID of the parent part
            vertices: List of vertex coordinates

        Returns:
            List of created vertex IDs
        """
        # Skip if too many vertices to avoid slowdown
        if len(vertices) > 100:
            return []

        with self.driver.session() as session:
            # Prepare batch data
            vertex_data = []
            vertex_ids = []
            for idx, vertex in enumerate(vertices):
                vertex_id = f"{part_id}_vertex_{idx}"
                vertex_ids.append(vertex_id)
                vertex_data.append({
                    "id": vertex_id,
                    "x": vertex["x"],
                    "y": vertex["y"],
                    "z": vertex["z"]
                })

            # Create all vertices in a single query using UNWIND
            query = """
            UNWIND $vertices AS v
            MERGE (vertex:Vertex:GeometricEntity {id: v.id})
            ON CREATE SET vertex.x = v.x, vertex.y = v.y, vertex.z = v.z
            ON MATCH SET vertex.x = v.x, vertex.y = v.y, vertex.z = v.z
            """
            session.run(query, vertices=vertex_data)
            return vertex_ids

    def create_contains_relationship(self, parent_id: str, child_id: str):
        """Create a CONTAINS relationship between parent and child nodes.

        Args:
            parent_id: ID of the parent node
            child_id: ID of the child node
        """
        with self.driver.session() as session:
            query = """
            MATCH (parent {id: $parent_id})
            MATCH (child {id: $child_id})
            MERGE (parent)-[:CONTAINS]->(child)
            """
            session.run(query, parent_id=parent_id, child_id=child_id)

    def create_has_geometry_relationship(self, part_id: str, vertex_id: str):
        """Create a HAS_GEOMETRY relationship between part and vertex.

        Args:
            part_id: ID of the part node
            vertex_id: ID of the vertex node
        """
        with self.driver.session() as session:
            query = """
            MATCH (part:Part {id: $part_id})
            MATCH (vertex:Vertex {id: $vertex_id})
            MERGE (part)-[:HAS_GEOMETRY]->(vertex)
            """
            session.run(query, part_id=part_id, vertex_id=vertex_id)

    def _batch_create_geometry_relationships(self, part_id: str, vertex_ids: list[str]):
        """Batch create HAS_GEOMETRY relationships between part and vertices.

        Args:
            part_id: ID of the part node
            vertex_ids: List of vertex IDs
        """
        with self.driver.session() as session:
            query = """
            MATCH (part:Part {id: $part_id})
            UNWIND $vertex_ids AS vid
            MATCH (vertex:Vertex {id: vid})
            MERGE (part)-[:HAS_GEOMETRY]->(vertex)
            """
            session.run(query, part_id=part_id, vertex_ids=vertex_ids)

    def populate_from_assembly_tree(self, assembly_tree: list[dict[str, Any]]):
        """Recursively populate the graph from an assembly tree structure.

        Args:
            assembly_tree: List of assembly dictionaries from STEP parser
        """
        for assembly in assembly_tree:
            self._process_node(assembly)

    def _process_node(self, node: dict[str, Any], parent_id: str = None):
        """Recursively process a node and its children.

        Args:
            node: Node dictionary from STEP parser
            parent_id: ID of the parent node (None for root)
        """
        # Determine node type and create appropriate node
        if node["is_assembly"]:
            node_id = self.create_assembly_node(node)
        else:
            node_id = self.create_part_node(node)

            # Create vertex nodes if geometry exists
            if "geometry" in node and node["geometry"]["vertices"]:
                vertex_ids = self.create_vertices(node_id, node["geometry"]["vertices"])
                # Batch create relationships
                if vertex_ids:
                    self._batch_create_geometry_relationships(node_id, vertex_ids)

        # Create relationship to parent if exists
        if parent_id:
            self.create_contains_relationship(parent_id, node_id)

        # Process children recursively
        for child in node.get("children", []):
            self._process_node(child, parent_id=node_id)

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about the knowledge graph.

        Returns:
            Dictionary containing graph statistics
        """
        with self.driver.session() as session:
            # Count nodes by type
            node_counts = session.run("""
                MATCH (n)
                RETURN labels(n)[0] as label, count(n) as count
            """)

            stats = {"nodes": {}}
            for record in node_counts:
                if record["label"]:
                    stats["nodes"][record["label"]] = record["count"]

            # Count relationships
            rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            stats["relationships"] = rel_count.single()["count"]

            return stats

    def query_assembly_hierarchy(self, root_name: str = None) -> list[dict[str, Any]]:
        """Query the assembly hierarchy.

        Args:
            root_name: Name of root assembly (optional)

        Returns:
            List of assembly paths
        """
        with self.driver.session() as session:
            if root_name:
                query = """
                MATCH path = (root:Assembly {name: $root_name})-[:CONTAINS*]->(child)
                RETURN root.name as root, child.name as child, length(path) as depth
                ORDER BY depth
                """
                result = session.run(query, root_name=root_name)
            else:
                query = """
                MATCH path = (root)-[:CONTAINS*]->(child)
                WHERE NOT (()-[:CONTAINS]->(root))
                RETURN root.name as root, child.name as child, length(path) as depth
                ORDER BY depth
                LIMIT 100
                """
                result = session.run(query)

            return [dict(record) for record in result]

    def find_parts_with_geometry(self) -> list[dict[str, Any]]:
        """Find all parts that have geometric entities.

        Returns:
            List of parts with their geometry counts
        """
        with self.driver.session() as session:
            query = """
            MATCH (p:Part)-[:HAS_GEOMETRY]->(v:Vertex)
            WITH p, count(v) as vertex_count
            RETURN p.name as part_name, p.id as part_id,
                   p.edge_count as edges, p.face_count as faces,
                   vertex_count
            ORDER BY vertex_count DESC
            """
            result = session.run(query)
            return [dict(record) for record in result]
