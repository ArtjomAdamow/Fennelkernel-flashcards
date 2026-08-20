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

### Run locally

With Python 3.13 or newer:

```powershell
cd "c:\Users\artjo\Projekte\Poster\flashcards"
uv sync
uv run python app.py
```

Open the local URL printed by Dash. Drag the 3D space to rotate it, hover over a point for a preview, and click a point to select its card. Click the question frame to reveal the answer. The **Random card** action provides a second way to study.

Coordinates are stored in `data/positions.json` and are kept separate from the Markdown decks so later versions can support manual rearrangement, highlighting, and visual connections.

### Tests

```powershell
uv run pytest
```
