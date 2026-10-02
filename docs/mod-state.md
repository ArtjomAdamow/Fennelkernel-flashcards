# Current Mod State
This is version 1.0 of the project. It represents the initial stable release with core functionality for loading, displaying, and manually organizing flashcards in a three-dimensional space.


## Summary

- The app loads flashcards from Markdown files in `data/cards`. Each card is created from a `<details>` block with a `<summary>` question and the remaining block content as its answer.
- Cards are shown as points in a three-dimensional Plotly view. Their initial coordinates are generated inside a sphere; stored coordinates are reused when available.
- The app displays the card question on hover and lets the user select a card, reveal its answer, and navigate between visible cards with the arrow keys or the random-card control.
- Each card has a read state and a 1-100 progress/difficulty value. The progress control becomes available after the answer is revealed, and card colors communicate progress and manual group membership.
- The user can manually adjust a selected card's X, Y, and Z coordinates, create named and colored groups, assign or remove cards from groups, and manually connect pairs of cards.
- Deck and group filters control which cards are visible. These features organize and visualize user-created relationships; the app does not infer them from card meaning.
- Positions, progress, groups, links, and enabled decks are saved in `data/positions.json`, separately from the Markdown deck content.

## Description

I use the app to load flashcard decks written in a predefined Markdown format. The deck supplies the units of study: each unit has a question and an answer, and the app presents those units as points in a three-dimensional space. Their starting positions are generated automatically and can be adjusted by hand. I can also place cards into named groups and draw connections between selected cards.

The app reads the deck structure so it can extract and display each question and answer, but it does not interpret their meaning. It does not use the content to decide where cards belong, which cards should be grouped, or which cards should be connected. Those relationships and positions currently come from my manual choices, while the app provides controls to view and save them. In other words, the current mod is a spatial flashcard viewer and manual organization tool, not a content-aware mapping system.


## Current Behavior
Manual organization and spatial visualization are the primary modes of interaction.

### Decks and Cards

- Deck files are Markdown files stored in `data/cards`.
- The parser extracts a question from a `<summary>` element inside a `<details>` block and treats the remaining block content as the answer.
- Cards retain their source deck name. The user can enable decks and show all enabled decks, a selected deck, or cards assigned to a focused group.
- Hovering over a point previews its question. Selecting a point opens its card panel; clicking the panel reveals or hides the answer.
- The left and right arrow keys move to the previous or next visible card. Up and down follow the same previous/next mapping.

### Position, Groups, and Connections

- New card positions are generated as points inside a sphere. Existing saved coordinates are loaded for cards that already have positions.
- The user can adjust a selected card's X, Y, and Z coordinates with sliders and save the resulting state.
- Groups have a name, a color, and a list of card IDs. The user creates groups and assigns or removes cards manually; group focus filters the visible cards.
- Connections are manually created between two selected card IDs and displayed as lines. A connection can optionally refer to a group for its display color.
- Positions and links are spatial or visual data. They do not currently encode an automatically derived topic, semantic similarity, or other content relationship.

### Learning Progress and Persistence

- Each card has a read flag and a progress/difficulty value from 1 to 100. Revealing an answer marks the card as read.
- The progress slider is disabled until the card has been marked read. Its value affects the progress color shown around the card point.
- Random-card selection prefers read cards and weights selection toward lower progress/difficulty values. If no visible cards are read, it selects from all visible cards.
- The app saves positions, progress, groups, links, and enabled decks to `data/positions.json`. The Markdown files remain the source for card questions and answers.


## Limitations

- **Random-card selection:** The README says the control selects only flipped cards. In the implementation it prefers cards marked read, but falls back to any visible card if none are marked read.
- **Position editing:** The README says coordinates can be changed only for flipped cards. The implementation enables position editing for a selected card without checking whether it has been read or flipped.
- **Camera behavior:** The README says the camera automatically centers on the selected card and rotates around it. The implementation preserves the Plotly camera state supplied by the view; it does not automatically center on the selected card or orbit around it.


## Source Files


See [INDEX.md](./INDEX.md) for a complete list of source files and their descriptions.
This project also includes a standalone script, `update_index.py` that regenerates INDEX.md.


## Roadmap

Workflow Into RAG
(Map shows currently filtered/unfiltered context as dots)
parsed / preprocessed docs --> chunks --> Decks: filter by manual (selection) ingestion
assigning group, color, connection --> embedded --> Groups: similarity search, vectors
display question and answer --> context --> Card text: only answer is needed 