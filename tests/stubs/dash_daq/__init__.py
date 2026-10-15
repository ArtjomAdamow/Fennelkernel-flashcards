"""Minimal stand-in for `dash_daq` (see stubs/dash/__init__.py)."""

from dash import Node


def ColorPicker(*args, **props):
    return Node("daq.ColorPicker", args, props)
