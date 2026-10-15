# Flashcards v2.0

<details>
<summary>The magic has not arrived yet</summary>

... but the manual experience is as cool as it gets. All decks can be added from the app, just click the `"Add"` button in the DECK section. No input files needed, all flashcards and quizzes are included. **Quizes are flattened and represented with the correct answer only**. Flashcards are shown as dots on on a rotating 3-D map and coordinates for cards from new loaded decks are still created at random.

</details>

[The quiz content was not hidden that well to prevent accidental exposure]:#


## Run locally

```powershell
uv sync
uv run python app.py
```

Open the **local URL** printed by Dash.


## Quick start:

1. Flashcards content is loaded in `data/cards.json`. Only Version 2 data is supported. **Important: ask for permission for content, it may not be shared in public.**

2. Use `"Add"` button in the DECK section to load flashcards. Select `"All"` or `"Focus"` to show only a specific deck. Select your first flashcard-dot on the 3D-map. Click on the question in the text box to flip to the answer.

3. States and progress are stored in `data/user_state.json`.


## Spatial Study

1. Select decks of flashcards. Multiple decks can be loaded and you can select specific decks with the `"Focus"` button. Loaded decks can be removed to clean up the workspace.
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


### Improvements

- workflow
  - state management cleaned of transitive shared mutable globals
  - mutation authority centralized in user_state_service
  - read models/snapshots feed other consumers
  - ownership boundaries separate source / state / persistence / UI
  - deck scope is properly first-class
  - no more duplicate id's
- usability 
  - deck state is saved, at startup only added decks are loaded
  - groups are ranked, group color is updated when focused on a group
  - connections only visible for visible cards
- connectivity
  - the app is now evolving modular
  - interfaces for recommender system are prepared
  - RAG-state -> own states 
  - RAG-comprehension -> shared state with user state
  - scripted self updating indexing tool for backend development
