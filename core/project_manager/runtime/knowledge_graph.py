"""
P14 — Engineering Knowledge Graph.

Deterministic project knowledge graph.
NOT semantic AI graph hallucinations — only verified facts.

Graph stores:
- Modules and their relationships
- Symbols and their usage
- Workflows and their outcomes
- Architectural decisions
- Ownership information
- Historical changes
- Risk zones
"""

import time
import threading
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict


class NodeType(Enum):
    MODULE = "module"
    SYMBOL = "symbol"
    WORKFLOW = "workflow"
    DECISION = "decision"
    OWNER = "owner"
    CHANGE = "change"
    RISK_ZONE = "risk_zone"
    FILE = "file"


class EdgeType(Enum):
    DEPENDS_ON = "depends_on"
    IMPORTS = "imports"
    EXPORTS = "exports"
    CALLS = "calls"
    OWNS = "owns"
    CHANGED_BY = "changed_by"
    DECIDED_BY = "decided_by"
    RISK_IN = "risk_in"
    CONTAINS = "contains"
    USED_BY = "used_by"


@dataclass
class GraphNode:
    """A node in the knowledge graph."""
    id: str
    node_type: NodeType
    label: str
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0
    updated_at: float = 0.0


@dataclass
class GraphEdge:
    """An edge in the knowledge graph."""
    source_id: str
    target_id: str
    edge_type: EdgeType
    properties: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0


class EngineeringKnowledgeGraph:
    """
    Deterministic engineering knowledge graph.
    Only verified facts from actual code analysis.
    """

    def __init__(self):
        self._nodes: Dict[str, GraphNode] = {}
        self._edges: List[GraphEdge] = []
        self._adjacency: Dict[str, List[GraphEdge]] = defaultdict(list)  # source -> edges
        self._reverse_adj: Dict[str, List[GraphEdge]] = defaultdict(list)  # target -> edges
        self._lock = threading.Lock()

    def add_node(self, node_type: NodeType, label: str,
                 node_id: str = "",
                 properties: Dict[str, Any] = None) -> GraphNode:
        """Add a node to the graph."""
        import uuid
        nid = node_id or f"{node_type.value}:{label}"
        node = GraphNode(
            id=nid,
            node_type=node_type,
            label=label,
            properties=properties or {},
            created_at=time.time(),
            updated_at=time.time(),
        )
        self._nodes[nid] = node
        return node

    def add_edge(self, source_id: str, target_id: str,
                 edge_type: EdgeType,
                 properties: Dict[str, Any] = None,
                 weight: float = 1.0) -> Optional[GraphEdge]:
        """Add an edge between two nodes."""
        if source_id not in self._nodes or target_id not in self._nodes:
            return None

        edge = GraphEdge(
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            properties=properties or {},
            weight=weight,
        )
        self._edges.append(edge)
        self._adjacency[source_id].append(edge)
        self._reverse_adj[target_id].append(edge)
        return edge

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Get a node by ID."""
        return self._nodes.get(node_id)

    def get_neighbors(self, node_id: str,
                      edge_type: EdgeType = None,
                      direction: str = "outgoing") -> List[GraphNode]:
        """Get neighboring nodes."""
        if direction == "outgoing":
            edges = self._adjacency.get(node_id, [])
        else:
            edges = self._reverse_adj.get(node_id, [])

        if edge_type:
            edges = [e for e in edges if e.edge_type == edge_type]

        result = []
        for edge in edges:
            target = edge.target_id if direction == "outgoing" else edge.source_id
            node = self._nodes.get(target)
            if node:
                result.append(node)
        return result

    def get_risk_zones(self) -> List[Dict[str, Any]]:
        """Get all risk zones in the graph."""
        risk_nodes = [n for n in self._nodes.values() if n.node_type == NodeType.RISK_ZONE]
        results = []
        for node in risk_nodes:
            # Find modules in this risk zone
            modules = self.get_neighbors(node.id, EdgeType.RISK_IN, direction="incoming")
            results.append({
                'zone': node.label,
                'risk_level': node.properties.get('level', 'medium'),
                'modules': [m.label for m in modules],
                'reason': node.properties.get('reason', ''),
            })
        return results

    def get_module_dependencies(self, module_id: str) -> Dict[str, List[str]]:
        """Get all dependencies of a module."""
        deps = {"imports": [], "depends_on": [], "used_by": []}
        for edge in self._adjacency.get(module_id, []):
            target = self._nodes.get(edge.target_id)
            if target:
                if edge.edge_type == EdgeType.IMPORTS:
                    deps["imports"].append(target.label)
                elif edge.edge_type == EdgeType.DEPENDS_ON:
                    deps["depends_on"].append(target.label)
        for edge in self._reverse_adj.get(module_id, []):
            source = self._nodes.get(edge.source_id)
            if source and edge.edge_type in (EdgeType.IMPORTS, EdgeType.DEPENDS_ON):
                deps["used_by"].append(source.label)
        return deps

    def get_architectural_decisions(self) -> List[Dict[str, Any]]:
        """Get all architectural decisions."""
        decision_nodes = [n for n in self._nodes.values() if n.node_type == NodeType.DECISION]
        results = []
        for node in decision_nodes:
            # Find what this decision affects
            affected = self.get_neighbors(node.id, direction="outgoing")
            results.append({
                'decision': node.label,
                'rationale': node.properties.get('rationale', ''),
                'date': node.properties.get('date', ''),
                'affected_modules': [n.label for n in affected if n.node_type == NodeType.MODULE],
            })
        return results

    def find_path(self, source_id: str, target_id: str,
                  max_depth: int = 10) -> Optional[List[str]]:
        """Find a path between two nodes using BFS."""
        if source_id not in self._nodes or target_id not in self._nodes:
            return None

        visited = {source_id}
        queue = [(source_id, [source_id])]

        while queue:
            current, path = queue.pop(0)
            if current == target_id:
                return path
            if len(path) >= max_depth:
                continue
            for edge in self._adjacency.get(current, []):
                if edge.target_id not in visited:
                    visited.add(edge.target_id)
                    queue.append((edge.target_id, path + [edge.target_id]))

        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        by_type = defaultdict(int)
        for node in self._nodes.values():
            by_type[node.node_type.value] += 1

        by_edge_type = defaultdict(int)
        for edge in self._edges:
            by_edge_type[edge.edge_type.value] += 1

        return {
            'total_nodes': len(self._nodes),
            'total_edges': len(self._edges),
            'by_node_type': dict(by_type),
            'by_edge_type': dict(by_edge_type),
        }
