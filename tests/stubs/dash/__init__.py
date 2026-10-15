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
    if hasattr(value, "to_dict"):  # a recorded figure inside a component, e.g. dcc.Graph(figure=...)
        return value.to_dict()
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


# --- what the callback and server code needs: Input/Output/State, ctx and a Dash class -------------------------

class _Arg:
    def __init__(self, kind, component_id, component_property):
        self.kind, self.component_id, self.component_property = kind, component_id, component_property


def Input(component_id, component_property):
    return _Arg("Input", component_id, component_property)


def Output(component_id, component_property):
    return _Arg("Output", component_id, component_property)


def State(component_id, component_property):
    return _Arg("State", component_id, component_property)


class _Context:
    triggered_id = None  # the tests set this before calling a callback function


ctx = _Context()


class _Server:
    def __init__(self):
        self.routes = {}

    def route(self, path):
        def decorator(function):
            self.routes[path] = function
            return function
        return decorator


class Dash:
    def __init__(self, name=None, assets_folder=None, **kwargs):
        self.name, self.assets_folder = name, assets_folder
        self.title = None
        self.layout = None
        self.index_string = "<!DOCTYPE html><html><body>{%app_entry%}</body></html>"
        self.server = _Server()
        self.callbacks = []

    def callback(self, *args):
        def decorator(function):
            self.callbacks.append((args, function))
            return function
        return decorator

    def run(self, **kwargs):
        self.ran_with = kwargs
