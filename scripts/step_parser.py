"""STEP file parser using OpenCascade (OCP) to extract CAD entities."""

from typing import Any
from OCP.STEPControl import STEPControl_Reader
from OCP.IFSelect import IFSelect_ReturnStatus
from OCP.TopoDS import TopoDS_Shape, TopoDS_Compound
from OCP.TopAbs import TopAbs_ShapeEnum
from OCP.TopExp import TopExp_Explorer
from OCP.BRep import BRep_Tool
from OCP.TopLoc import TopLoc_Location
from OCP.gp import gp_Pnt
from OCP.TopoDS import TopoDS
from OCP.TDocStd import TDocStd_Document
from OCP.XCAFDoc import (
    XCAFDoc_DocumentTool,
    XCAFDoc_ShapeTool,
    XCAFDoc_ColorTool,
)
from OCP.XCAFApp import XCAFApp_Application
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDF import TDF_Label, TDF_LabelSequence


class STEPParser:
    """Parser for STEP files to extract assembly and geometric information."""

    def __init__(self, file_path: str):
        """Initialize the STEP parser with a file path.

        Args:
            file_path: Path to the STEP file to parse
        """
        self.file_path = file_path
        self.reader = STEPCAFControl_Reader()
        self.doc = None
        self.shape_tool = None
        self.color_tool = None
        self.root_shapes = []

    def load_file(self) -> bool:
        """Load and parse the STEP file.

        Returns:
            True if file loaded successfully, False otherwise
        """
        status = self.reader.ReadFile(self.file_path)

        if status != IFSelect_ReturnStatus.IFSelect_RetDone:
            print(f"Error reading STEP file: {self.file_path}")
            return False

        # Transfer the file content to the document
        app = XCAFApp_Application.GetApplication_s()
        self.doc = TDocStd_Document(TCollection_ExtendedString("XmlOcaf"))
        app.InitDocument(self.doc)

        if not self.reader.Transfer(self.doc):
            print("Error transferring STEP data to document")
            return False

        # Get shape and color tools
        self.shape_tool = XCAFDoc_DocumentTool.ShapeTool_s(self.doc.Main())
        self.color_tool = XCAFDoc_DocumentTool.ColorTool_s(self.doc.Main())

        # Get root shapes (assemblies)
        free_shapes = TDF_LabelSequence()
        self.shape_tool.GetFreeShapes(free_shapes)

        for i in range(1, free_shapes.Length() + 1):
            label = free_shapes.Value(i)
            self.root_shapes.append(label)

        return True

    def extract_assembly_structure(self) -> list[dict[str, Any]]:
        """Extract the assembly hierarchy from the STEP file.

        Returns:
            List of assembly/part dictionaries with hierarchy information
        """
        assemblies = []

        for root_label in self.root_shapes:
            assembly = self._extract_label_info(root_label, level=0)
            assemblies.append(assembly)

        return assemblies

    def _extract_label_info(self, label: TDF_Label, level: int = 0, parent_id: str = None) -> dict[str, Any]:
        """Recursively extract information from a label.

        Args:
            label: TDF_Label to extract information from
            level: Hierarchy level (0 = root)
            parent_id: ID of the parent component

        Returns:
            Dictionary containing label information
        """
        # Get shape using static method
        from OCP.XCAFDoc import XCAFDoc_ShapeTool as ShapeTool
        shape = ShapeTool.GetShape_s(label)

        # Get name
        name = self._get_label_name(label)

        # Generate unique ID
        label_id = f"label_{label.Tag()}"

        # Check if it's an assembly or a simple part (use static methods)
        is_assembly = ShapeTool.IsAssembly_s(label)
        is_simple_shape = ShapeTool.IsSimpleShape_s(label)
        is_component = ShapeTool.IsComponent_s(label)

        info = {
            "id": label_id,
            "name": name,
            "level": level,
            "parent_id": parent_id,
            "is_assembly": is_assembly,
            "is_simple_shape": is_simple_shape,
            "is_component": is_component,
            "shape_type": self._get_shape_type(shape),
            "children": [],
        }

        # If it's an assembly, get its components
        if is_assembly:
            components = TDF_LabelSequence()
            ShapeTool.GetComponents_s(label, components)

            for i in range(1, components.Length() + 1):
                component_label = components.Value(i)
                # Get the referred shape
                referred_label = TDF_Label()
                if ShapeTool.GetReferredShape_s(component_label, referred_label):
                    child_info = self._extract_label_info(referred_label, level + 1, label_id)
                    info["children"].append(child_info)

        # Extract geometric properties for simple shapes
        if is_simple_shape and not is_assembly:
            info["geometry"] = self._extract_geometry_info(shape)

        return info

    def _get_label_name(self, label: TDF_Label) -> str:
        """Get the name of a label.

        Args:
            label: TDF_Label to get name from

        Returns:
            Name string or "Unnamed" if no name is found
        """
        from OCP.TDataStd import TDataStd_Name

        # Try to find a name attribute
        name_attr = TDataStd_Name()
        if label.FindAttribute(TDataStd_Name.GetID_s(), name_attr):
            return name_attr.Get().ToExtString()

        return f"Unnamed_{label.Tag()}"

    def _get_shape_type(self, shape: TopoDS_Shape) -> str:
        """Get the type of a TopoDS_Shape.

        Args:
            shape: TopoDS_Shape to get type from

        Returns:
            String representation of the shape type
        """
        if shape.IsNull():
            return "NULL"

        shape_type = shape.ShapeType()
        type_map = {
            TopAbs_ShapeEnum.TopAbs_COMPOUND: "COMPOUND",
            TopAbs_ShapeEnum.TopAbs_COMPSOLID: "COMPSOLID",
            TopAbs_ShapeEnum.TopAbs_SOLID: "SOLID",
            TopAbs_ShapeEnum.TopAbs_SHELL: "SHELL",
            TopAbs_ShapeEnum.TopAbs_FACE: "FACE",
            TopAbs_ShapeEnum.TopAbs_WIRE: "WIRE",
            TopAbs_ShapeEnum.TopAbs_EDGE: "EDGE",
            TopAbs_ShapeEnum.TopAbs_VERTEX: "VERTEX",
        }
        return type_map.get(shape_type, "UNKNOWN")

    def _extract_geometry_info(self, shape: TopoDS_Shape) -> dict[str, Any]:
        """Extract geometric information from a shape.

        Args:
            shape: TopoDS_Shape to extract geometry from

        Returns:
            Dictionary containing geometric information
        """
        geometry = {
            "vertices": [],
            "edges": [],
            "faces": [],
            "volume_exists": False,
        }

        # Count and extract vertices
        vertex_explorer = TopExp_Explorer(shape, TopAbs_ShapeEnum.TopAbs_VERTEX)
        while vertex_explorer.More():
            vertex = TopoDS.Vertex_s(vertex_explorer.Current())
            point = BRep_Tool.Pnt_s(vertex)
            geometry["vertices"].append({
                "x": point.X(),
                "y": point.Y(),
                "z": point.Z(),
            })
            vertex_explorer.Next()

        # Count edges
        edge_explorer = TopExp_Explorer(shape, TopAbs_ShapeEnum.TopAbs_EDGE)
        edge_count = 0
        while edge_explorer.More():
            edge_count += 1
            edge_explorer.Next()
        geometry["edges"] = edge_count

        # Count faces
        face_explorer = TopExp_Explorer(shape, TopAbs_ShapeEnum.TopAbs_FACE)
        face_count = 0
        while face_explorer.More():
            face_count += 1
            face_explorer.Next()
        geometry["faces"] = face_count

        # Check for solids
        solid_explorer = TopExp_Explorer(shape, TopAbs_ShapeEnum.TopAbs_SOLID)
        if solid_explorer.More():
            geometry["volume_exists"] = True

        return geometry

    def get_statistics(self) -> dict[str, Any]:
        """Get overall statistics about the STEP file.

        Returns:
            Dictionary containing file statistics
        """
        stats = {
            "file_path": self.file_path,
            "root_shapes_count": len(self.root_shapes),
            "total_assemblies": 0,
            "total_parts": 0,
            "total_components": 0,
        }

        # Count assemblies and parts
        for root_label in self.root_shapes:
            self._count_shapes(root_label, stats)

        return stats

    def _count_shapes(self, label: TDF_Label, stats: dict[str, Any]):
        """Recursively count shapes in the assembly.

        Args:
            label: TDF_Label to count from
            stats: Statistics dictionary to update
        """
        from OCP.XCAFDoc import XCAFDoc_ShapeTool as ShapeTool

        if ShapeTool.IsAssembly_s(label):
            stats["total_assemblies"] += 1

            components = TDF_LabelSequence()
            ShapeTool.GetComponents_s(label, components)

            for i in range(1, components.Length() + 1):
                component_label = components.Value(i)
                stats["total_components"] += 1

                referred_label = TDF_Label()
                if ShapeTool.GetReferredShape_s(component_label, referred_label):
                    self._count_shapes(referred_label, stats)

        if ShapeTool.IsSimpleShape_s(label):
            stats["total_parts"] += 1


def parse_step_file(file_path: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Parse a STEP file and extract assembly and geometric information.

    Args:
        file_path: Path to the STEP file

    Returns:
        Tuple of (assembly structure list, statistics dictionary)
    """
    parser = STEPParser(file_path)

    if not parser.load_file():
        return [], {}

    assemblies = parser.extract_assembly_structure()
    stats = parser.get_statistics()

    return assemblies, stats
