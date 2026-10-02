# Flashcards

Here are some hints for extraction (open in edit mode to see a real hack):

<details>
  <summary><b> <sd

 Use Markdown Preview for the best experience of`format`.
 </b></summary>

Use `backticks` for code, commands etc.

</details>

[In the summary block <sd followed by empty line allows the use if backticks]:#

## Spatial Flashcards

This folder contains a small Dash application for visualizing the learning flashcards. Flashcards are stored as markdown decks, watch out for the **Q/A** format. Decks are stored in `data/cards`, new decks can be added from there. The flashcards are shown as dots on on a rotating 3-D map. Coordinates are created at random and stored in `data/positions.json`, they are kept separate from the Markdown decks.

### Run locally

With Python 3.13 or newer:

```powershell
uv sync
uv run python app.py
```

Open the local URL printed by Dash.

### Quick start:

First use `"Add"` button in the DECK section to load flashcards. Select `"All"` or `"Focus"` to show only a specific deck. Select your first flashcard-dot on the 3D-map. Click on the question in the text box to flip to the answer.


### How to:

1. Select decks of flashcards. Multiple decks can be uploaded and you can select specific decks with the `"Focus"` button.
2. Hover mouse over a card-point to `preview` the question without selecting.
2. Use mouse on `3D map` space to drag move, rotate and zoom the map.
3. Click on a flashcard (represented as dots) to select a specific card. Alternativly use key arrows to `scroll` through the cards.
4. The automatic `camera` will center on the selected card and rotate around it like a satellite.
5. A selected card's question is shown in the text box. Click on it to `flip` to the answer.
6. For a flipped card the **learning progress** can be set with a `slider` above the text box. The progress is shown as a colore-coded `boarder` around the flashcards-dot on the 3D map space.
7. Assign cards to **groups**, apply group names and color-code the groups as you prefer. Use `"Focus"` button to see only the cards assigned to a specific group.
8. Connect specific cards with visual lines to visualize similar topics using the `"Connect"` button.
9. Change coordinates of cards (only flipped cards) to **arrange** their positions in the 3D space using the `"Change"` button.
10. The button `"Random card"` will only select flipped cards and will **prefer cards with low progress**.
11. The button `"Reset"` removes all settings for a fresh start.

### Tests

```powershell
uv run pytest
```

### Notes

Dash resolves assets_folder relative to wherever Dash(__name__) is instantiated — moving that call into a submodule silently breaks static assets with no error, so it needs an explicit assets_folder when the app isn't created at the project root.

### License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.