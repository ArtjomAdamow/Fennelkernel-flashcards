# Flashcards

Here are some hints for extraction (open in edit mode to see a real hack):

<details>
  <summary><b> <sd

 Use Markdown Preview for the best experience of`format`.
 </b></summary>

Use `backticks` for code, commands etc.
</details>

[In the summary block <sd followed by empty line allows the use if backticks]:#

[suggest a python program for learning from flashcards. there should be a 3d (array?) structure with each question belonging to a randomly assigned coordinate within a sphere. the user should be able to rotate the structure interactivly and select the questions (suggest selecting method). The question should be then displayed in a frame. clicking on the frame with the quastion the answer is displayed. In future (just keep in mind for now) the coordinates should be able to reassign and be highlighted, visual connections between the coordinates should be possible. The user is going to order the coordinates during the learning game to connect and gather related questions closer to eachother. ]:#

## Spatial Flashcards

This folder now contains a small Dash application for learning from the Markdown decks.
Coordinates are stored in `data/positions.json` and are kept separate from the Markdown decks.

### Run locally

With Python 3.13 or newer:

```powershell
uv sync
uv run python app.py
```

Open the local URL printed by Dash.

### Howto:

1. Select deck of flashcards. Hover over a card-point to preview the question.
2. Use mouse to drag the 3D space to rotate, zoom and select cards (dots).
3. Alternativly use key arrows to scroll through the cards.
4. A selected card can be flipped by clicking on it.
5. For a flipped card the learning progress can be set with a slider.
6. The button "Random card" will only select flipped cards and will prefer cards with low progress.
7. Change coordinates of cards (only flipped cards) to arrange in the 3D space.
8. Assign cards to groups, apply names and color code.
9. Focus on groups to see only assigned cards.
10. Connect cards with visual lines.
11. Reset removes all settings.



### Tests

```powershell
uv run pytest
```
