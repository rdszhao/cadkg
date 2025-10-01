#!/usr/bin/env python3
"""Test script for multi-agent system with minimal data."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from agent import CADMultiAgentSystem

# Create minimal test data
test_data = {
    "id": "assembly_1",
    "name": "Test Assembly",
    "is_assembly": True,
    "shape_type": "Assembly",
    "level": 0,
    "children": [
        {
            "id": "part_1",
            "name": "92196A191-18-8 SS SHCS, McMASTER CARR",
            "is_assembly": False,
            "shape_type": "Part",
            "level": 1,
            "geometry": {
                "vertices": [[0, 0, 0], [1, 0, 0], [1, 1, 0]],
                "edges": 3,
                "faces": 1
            },
            "children": []
        },
        {
            "id": "part_2",
            "name": "091-1_A1-FRONT PANEL",
            "is_assembly": False,
            "shape_type": "Part",
            "level": 1,
            "geometry": {
                "vertices": [[0, 0, 0]] * 72,
                "edges": 36,
                "faces": 9
            },
            "children": []
        }
    ]
}

print("Testing Multi-Agent System with minimal data...")
print("=" * 70)

agent_system = CADMultiAgentSystem()
result = agent_system.process(test_data)

print("\n" + "=" * 70)
print("RESULT:")
print("=" * 70)
import json
print(json.dumps(result, indent=2))
