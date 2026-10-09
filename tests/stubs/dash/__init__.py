"""Minimal stand-in for `dash`, used only by the visualization equivalence test.

It records what the code builds (component type, children, properties) instead of rendering it,
so old and new code can be compared without the real library. It shadows a real Dash install
because the test puts this folder first on PYTHONPATH.
"""


class Node:
    def __init__(self, kind, args, props):
        self.kind, self.args, self.props = kind, args, props

    def to_json(self):
        return {"type": self.kind, "args": [to_json(a) for a in self.args], "props": {k: to_json(v) for k, v in self.props.items()}}


def to_json(value):
    if isinstance(value, Node):
        return value.to_json()
    if isinstance(value, dict):
        return {str(k): to_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_json(v) for v in value]
    return value


class _Namespace:
    def __init__(self, name):
        self._name = name

    def __getattr__(self, attr):
        if attr.startswith("__"):
            raise AttributeError(attr)
        return lambda *args, **props: Node(f"{self._name}.{attr}", args, props)


html = _Namespace("html")
dcc = _Namespace("dcc")
