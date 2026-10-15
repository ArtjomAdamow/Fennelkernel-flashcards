"""Minimal stand-in for `plotly.graph_objects` (see stubs/dash/__init__.py): records traces and layout."""


class Scatter3d(dict):
    def __init__(self, **kwargs):
        super().__init__(kwargs)


class Figure:
    def __init__(self):
        self.data = []
        self.layout = {}

    def add_trace(self, trace):
        self.data.append(trace)

    def update_layout(self, **kwargs):
        self.layout.update(kwargs)

    def to_dict(self):
        return {"data": [dict(trace) for trace in self.data], "layout": dict(self.layout)}
