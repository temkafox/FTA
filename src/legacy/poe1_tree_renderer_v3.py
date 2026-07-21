"""Clean passive renderer with complete bidirectional edge reconstruction."""

from poe1_tree_renderer_v2 import CleanPassiveTreeCanvas


class ConnectedPassiveTreeCanvas(CleanPassiveTreeCanvas):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._rebuild_complete_edges()

    def _rebuild_complete_edges(self):
        edges = set()
        for node_id, node in self.nodes.items():
            first = str(node_id)
            if first not in self.positions:
                continue
            for other in node.get("out", []) + node.get("in", []):
                second = str(other)
                if second not in self.positions or second == first:
                    continue
                edges.add(tuple(sorted((first, second))))
        self.edges = sorted(edges)
