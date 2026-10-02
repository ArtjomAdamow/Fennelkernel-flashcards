from flashcards_app.visualization.panels import deck_control, group_control


def test_deck_and_group_actions_are_single_rows():
    def nodes(component):
        node = component.to_plotly_json()
        yield node
        children = node.get("props", {}).get("children", [])
        if not isinstance(children, list):
            children = [children]
        for child in children:
            if hasattr(child, "to_plotly_json"):
                yield from nodes(child)

    deck_nodes = list(nodes(deck_control()))
    group_nodes = list(nodes(group_control(None)))
    deck_ids = {node.get("props", {}).get("id") for node in deck_nodes}
    group_ids = {node.get("props", {}).get("id") for node in group_nodes}

    def action_ids(component_nodes):
        action_row = next(
            node
            for node in component_nodes
            if node.get("props", {}).get("className") == "tool-row control-actions"
        )
        return [
            child.to_plotly_json()["props"]["id"]
            for child in action_row["props"]["children"]
        ]

    assert sum(node.get("props", {}).get("className") == "tool-row control-actions" for node in deck_nodes) == 1
    assert sum(node.get("props", {}).get("className") == "tool-row control-actions" for node in group_nodes) == 1
    assert action_ids(deck_nodes) == ["add-deck", "remove-deck", "focus-deck", "all-decks", "reset-cards"]
    assert action_ids(group_nodes) == ["new-group", "delete-group", "add-group", "remove-group", "focus-group", "all-groups"]
    assert {"add-deck", "remove-deck", "focus-deck", "all-decks", "reset-cards"} <= deck_ids
    assert {"new-group", "add-group", "remove-group", "delete-group", "focus-group", "all-groups"} <= group_ids
