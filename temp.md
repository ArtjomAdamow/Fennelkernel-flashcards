# Flashcard Application - Component Index

## Overview
This index provides structured access to all application components with human-readable descriptions and anchor links as well as machine-readable metadata for efficient agent navigation.

## Agent Maintenance Trigger
**Agent instruction (when this index is in context):** If a task adds, changes, renames, or removes a project component, watch for explicit "validate index" prompt, then update this index. Follow the **Index Validation** procedure below and fix any reported issues before finishing.

---

## Core Data Models

### [`Flashcard:`](./flashcards_app/models.py#Flashcard:)
Core flashcard entity with question and answer. Represents individual learning cards with unique ID, deck assignment, question text, and answer text.

```yaml
component_id: flashcard:core
type: dataclass
file: flashcards_app/models.py
line_start: 4
line_end: 9
tags: [card, entity, core]
dependencies: []
used_in: [app, parser, state, tests]
```

**Fields**:
- `id` (str): Unique identifier (format: "deck_name:sequence_number")
- `deck` (str): Deck name this card belongs to
- `question` (str): The prompt/question displayed
- `answer` (str): The answer/reveal text

**Related Components**:
- Used by: `app.py` callbacks, `parser.py` parse_deck(), `state.py` load_progress()
- Depends on: None (base component)
---

### [`CardPosition:`](./flashcards_app/models.py#CardPosition:)
3D coordinates for card placement on sphere. Stores x, y, z coordinates (-1 to 1 range) with status tracking and related card IDs.

```yaml
component_id: card_position:3d
type: dataclass
file: flashcards_app/models.py
line_start: 12
line_end: 19
tags: [position, geometry, 3d]
dependencies: [flashcard:core]
used_in: [app, geometry, state]
```

**Fields**:
- `card_id` (str): Reference to flashcard ID
- `x, y, z` (float): 3D coordinates on unit sphere
- `status` (str): Position status ("new", "edited", "saved")
- `related_ids` (List[str]): IDs of related cards

**Related Components**:
- Used by: `app.py` make_figure(), `geometry.py` sphere_positions()
- Depends on: flashcard:core
---

### [`CardProgress:`](./flashcards_app/models.py#CardProgress:)
Learning progress tracking. Tracks read status and difficulty level (1-100) for each card.

```yaml
component_id: card_progress:tracking
type: dataclass
file: flashcards_app/models.py
line_start: 22
line_end: 29
tags: [progress, learning, difficulty]
dependencies: [flashcard:core]
used_in: [app, state]
```

**Fields**:
- `card_id` (str): Reference to flashcard ID
- `read` (bool): Whether card has been viewed/flipped
- `difficulty` (int): Progress level (1=review to 100=learned)

**Related Components**:
- Used by: `app.py` progress_color(), difficulty_control()
- Depends on: flashcard:core
---

### [`CardGroup:`](./flashcards_app/models.py#CardGroup:)
Grouping mechanism for organizing flashcards. Organizes cards into visual groups with custom names and colors.

```yaml
component_id: card_group:organizer
type: dataclass
file: flashcards_app/models.py
line_start: 32
line_end: 38
tags: [group, organization, color]
dependencies: [flashcard:core]
used_in: [app, state]
```

**Fields**:
- `id` (str): Unique group identifier
- `name` (str): Human-readable group name
- `color` (str): Hex color code for visual distinction
- `card_ids` (List[str]): IDs of cards belonging to this group

**Related Components**:
- Used by: `app.py` group_control(), deck_filter_options()
- Depends on: flashcard:core
---

### [`CardLink:`](./flashcards_app/models.py#CardLink:)
Connection/link between two flashcards. Connects related cards, optionally belonging to a group.

```yaml
component_id: card_link:connection
type: dataclass
file: flashcards_app/models.py
line_start: 40
line_end: 44
tags: [connection, link, relationship]
dependencies: [flashcard:core]
used_in: [app, state]
```

**Fields**:
- `id` (str): Unique link identifier
- `source_id` (str): ID of source card
- `target_id` (str): ID of target card
- `group_id` (Optional[str]): Optional group this link belongs to

**Related Components**:
- Used by: `app.py` connection_control(), make_figure() (draws lines)
- Depends on: flashcard:core
---

## Parsing System

### [`parse_deck()`](./flashcards_app/parser.py#parse_deck)
Extract flashcards from markdown deck files. Parses `<details>`/`<summary>` format markdown to structured Flashcard objects.

```yaml
component_id: parser:deck_parser
type: function
file: flashcards_app/parser.py
line_start: 35
line_end: 59
tags: [parsing, markdown, deck]
dependencies: [flashcard:core, models]
used_in: [app, tests]
```

**Parameters**:
- `path` (Path): Path to markdown deck file
- `Returns` (List[Flashcard]): List of parsed flashcards

**Algorithm**:
1. Read file content
2. Find all `<details>` blocks via regex
3. Extract `<summary>` as question
4. Extract remaining body as answer
5. Clean and format both sections
6. Create Flashcard objects with sequential IDs

**Regex Patterns**:
- `_DETAILS_PATTERN`: Matches `<details>...</details>` blocks
- `_SUMMARY_PATTERN`: Matches `<summary>...</summary>` within details
- `_PLACEHOLDER_PATTERN`: Filters placeholder content like `[...]: `

**Related Components**:
- Used by: `app.py` AVAILABLE_DECKS, ENABLED_DECKS
- Depends on: flashcard:core, format_technical_terms()
---

### [`format_technical_terms()`](./flashcards_app/parser.py#format_technical_terms)
Wrap code-like terms in backticks. Identifies and wraps snake_case and function calls.

```yaml
component_id: parser:term_formatting
type: function
file: flashcards_app/parser.py
line_start: 15
line_end: 20
tags: [formatting, technical_terms, markdown]
dependencies: []
used_in: [parser]
```

**Algorithm**:
1. Split on existing backtick-wrapped code
2. Process non-code parts (even indices)
3. Apply _CODELIKE_PATTERN to wrap terms
4. Join parts back together

**Code Pattern**: `(?<![`\w])(?:[A-Za-z_][A-Za-z0-9_]*\(\)|[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]+)(?![`\w])`

**Related Components**:
- Used by: `_clean_question()`, `_clean_answer()`
- Depends on: None
---

### [`load_decks()`](./flashcards_app/parser.py#load_decks)
Load flashcards from folder with optional filtering. Scans directory for .md files and parses decks.

```yaml
component_id: parser:load_decks
type: function
file: flashcards_app/parser.py
line_start: 62
line_end: 70
tags: [loading, deck, filtering]
dependencies: [parser:deck_parser, Path]
used_in: [app, state]
```

**Parameters**:
- `folder` (Path): Directory containing markdown files
- `deck_names` (Optional[List[str]]): Filter specific decks
- `Returns` (List[FlashcardDeck]): List of parsed flashcard decks

**Algorithm**:
1. Get all .md files sorted alphabetically
2. Optionally filter by deck names
3. Parse each file with parse_deck()
4. Extend cards list
5. Return the final list of FlashcardDeck objects

**Related Components**:
- Used by: `app.py` CARDS loading, `state.py` load_enabled_decks()
- Depends on: parser:deck_parser
---


## Deck Management

### [`deck_filter_options()`](./app.py#deck_filter_options)
Get deck filter dropdown options. Returns options for None, All, and individual decks.

```yaml
component_id: app:deck_filter_options
type: function
file: app.py
line_start: 78
line_end: 82
tags: [ui, dropdown, deck]
dependencies: [app:AVAILABLE_DECKS, ENABLED_DECKS]
used_in: [app.callback]
```

**Returns**:
```python
[
    {"label": "None", "value": NONE_DECK},
    {"label": "All decks", "value": "all"},
    ...deck options from sorted(ENABLED_DECKS)
]
```

**Related Components**:
- Used by: app.callback deck-filter trigger
- Depends on: AVAILABLE_DECKS, ENABLED_DECKS
---

### [`deck_control()`](./app.py#deck_control)
Manage deck-based card visibility and interactions. Provides controls for filtering and interacting with card decks.

```yaml
component_id: app:deck_control
type: function
file: app.py
line_start: 128
line_end: 136
tags: [deck, control, interaction]
dependencies: [models:CardDeck]
used_in: [app, make_figure]
```

**Parameters**:
- `deck` (str): Deck value to control

**Returns**:
- `None`

**Related Components**:
- Used by: make_figure() card rendering, card_panel()
- Depends on: models:CardDeck
---


## State Management
All state components are persisted in [data/positions.json](./data/positions.json). The location is defined as [STATE_PATH](./app.py#STATE_PATH).

### [load_enabled_decks()](./flashcards_app/state.py#load_enabled_decks)
Load the list of active flashcard decks. Reads saved preferences from JSON and validates them against available markdown files on disk.

```yaml
component_id: state:load_enabled_decks
type: function
file: flashcards_app/state.py
line_start: 147
line_end: 177
tags: [loading, deck, persistence]
dependencies: [Path]
used_in: [app]
```

**Parameters**:
- `path` (Path): Path to the state JSON file
- `available_decks` (List[str]): List of all decks found on disk
- `Returns` (List[str]): The subset (list) of decks to be enabled

**Algorithm**:
1. Check if JSON file exists
2. If not, or if no decks saved: return all `available_decks`
3. If yes: filter saved decks to ensure they still exist in `available_decks`

**Related Components**: 
- Used by: `app.py` ENABLED_DECKS initialization
- Depends on: None
---

### [`load_positions()`](./flashcards_app/state.py#load_positions)
Load or generate sphere positions. Returns positions from JSON or generates deterministic random positions.

```yaml
component_id: state:load_positions
type: function
file: flashcards_app/state.py
line_start: 8
line_end: 17
tags: [positions, geometry, persistence]
dependencies: [geometry:sphere_positions, Path]
used_in: [app]
```

**Parameters**:
- `path` (Path): Path to the state JSON file
- `seed` (int): Reproducibility seed (default: 42)

**Algorithm**:
1. Check if JSON file exists
2. If not: generate via geometry:sphere_positions()
3. If yes: load and merge with generated positions
4. Return list of CardPosition objects

**Returns**:
- List[CardPosition]: List of positions for each card

**Related Components**:
- Used by: `app.py` POSITIONS initialization
- Depends on: geometry:sphere_positions
---

### [load_progress()](./flashcards_app/state.py#load_progress)
Load or create card progress. Hydrates JSON data into CardProgress objects or initializes defaults.

```yaml
component_id: state:load_progress
type: function
file: flashcards_app/state.py
line_start: 33
line_end: 62
tags: [progress, persistence]
dependencies: [models:CardProgress, Path]
used_in: [app, app:progress_color]
```

**Parameters**:
- `path` (Path): Path to the state JSON file
- `card_ids` (List[str]): List of all current card IDs
- `Returns` (Dict[str, CardProgress]): Mapping of card IDs to their progress

**Algorithm**:
1. Check if JSON file exists
2. If not: return default CardProgress (read=False, diff=1) for all IDs
3. If yes: load JSON and map card_ids to CardProgress objects
4. Fill gaps for missing cards with defaults

**Related Components**: 
- Used by: `app.py` PROGRESS initialization, `app:progress_color`
- Depends on: models:CardProgress
---

### [load_groups()](./flashcards_app/state.py#load_groups)
Load card groups from JSON. Filters out cards that are no longer present in the current deck.

```yaml
component_id: state:load_groups
type: function
file: flashcards_app/state.py
line_start: 65
line_end: 91
tags: [groups, persistence]
dependencies: [models:CardGroup, Path]
used_in: [app, app:make_figure]
```

**Parameters**:
- `path` (Path): Path to the state JSON file
- `card_ids` (List[str]): List of all current card IDs
- `Returns` (List[CardGroup]): List of card groups

**Algorithm**:
1. Check if JSON file exists
2. If yes: iterate through saved groups
3. Filter card_ids within each group against current valid IDs
4. Create CardGroup objects

**Related Components**: 
- Used by: `app.py` GROUPS initialization, `app:make_figure`
- Depends on: models:CardGroup
---

### [load_links()](./flashcards_app/state.py#load_links)
Load card connections from JSON. Ensures both source and target cards still exist.

```yaml
component_id: state:load_links
type: function
file: flashcards_app/state.py
line_start: 94
line_end: 120
tags: [links, persistence]
dependencies: [models:CardLink, Path]
used_in: [app, app:make_figure]
```
**Parameters**:
- `path` (Path): Path to the state JSON file
- `card_ids` (List[str]): List of all current card IDs
- `Returns` (List[CardLink]): List of card links

**Algorithm**:
1. Check if JSON file exists
2. If yes: iterate through saved links
3. Validate that both source_id and target_id are in current valid IDs
4. Create CardLink objects

**Related Components**: 
- Used by: `app.py` LINKS initialization, `app:make_figure`
- Depends on: models:CardLink
---

### [`save_state()`](./flashcards_app/state.py#save_state)
Save all application state to JSON. Persists positions, progress, groups, links, enabled decks.

```yaml
component_id: state:save_state
type: function
file: flashcards_app/state.py
line_start: 88
line_end: 106
tags: [persistence, state, json]
dependencies: [dataclasses, Path]
used_in: [app]
```

**Algorithm**:
1. Create parent directory if needed
2. Build payload dict with version 2
3. Serialize positions, progress, groups, links
4. Include enabled_decks if provided
5. Write JSON with indent=2

**Returns**:
- None

**Related Components**:
- Used by: `app.py` __main__ callback, all callback returns
- Depends on: all state component loaders
---

### [`update_card()`](./app.py#update_card)
Update card information and state. This function handles modifications to card attributes and ensures the application state remains consistent.

```yaml
component_id: app:update_card
type: function
file: app.py
line_start: 146
line_end: 154
tags: [card, update, state]
dependencies: [models:Card]
used_in: [app, make_figure]
```

**Parameters**:
- `card_id` (str): ID of the card to update
- `attributes` (dict): Dictionary of attributes to update

**Returns**:
- `None`

**Related Components**:
- Used by: make_figure() card rendering, card_panel()
- Depends on: models:Card
---


## Control Utilities

### [`difficulty_control()`](./app.py#difficulty_control)
Manage difficulty-based card visibility and interactions. Provides controls for filtering and interacting with cards based on their difficulty level. AKA progress control.

>Think about it: this sets the color_control, perhaps there is redundance?

```yaml
component_id: app:difficulty_control
type: function
file: app.py
line_start: 100
line_end: 104
tags: [difficulty, control, interaction]
dependencies: [models:CardDifficulty]
used_in: [app, make_figure]
```

**Parameters**:
- `difficulty` (str): Difficulty value to control

**Returns**:
- `None`

**Related Components**:
- Used by: make_figure() card rendering, card_panel()
- Depends on: models:CardDifficulty
---

### [`position_control()`](./app.py#position_control)
Manage position-based card visibility and interactions. Provides controls for filtering and interacting with card positions.

```yaml
component_id: app:position_control
type: function
file: app.py
line_start: 110
line_end: 118
tags: [position, control, interaction]
dependencies: [models:CardPosition]
used_in: [app, make_figure]
```

**Parameters**:
- `position` (str): Position value to control

**Returns**:
- `None`

**Related Components**:
- Used by: make_figure() card rendering, card_panel()
- Depends on: models:CardPosition
---

### [`group_control()`](./app.py#group_control)
Manage group-based card visibility and interactions. Provides controls for filtering and interacting with card groups.

```yaml
component_id: app:group_control
type: function
file: app.py
line_start: 119
line_end: 127
tags: [group, control, interaction]
dependencies: [models:CardGroup]
used_in: [app, make_figure]
```

**Parameters**:
- `group` (str): Group value to control

**Returns**:
- `None`

**Related Components**:
- Used by: make_figure() card rendering, card_panel()
- Depends on: models:CardGroup
---

### [`connection_control()`](./app.py#connection_control)
Manage connection-based card visibility and interactions. Provides controls for filtering and interacting with card connections.

```yaml
component_id: app:connection_control
type: function
file: app.py
line_start: 137
line_end: 145
tags: [connection, control, interaction]
dependencies: [models:CardConnection]
used_in: [app, make_figure]
```

**Parameters**:
- `connection` (str): Connection value to control

**Returns**:
- `None`

**Related Components**:
- Used by: make_figure() card rendering, card_panel()
- Depends on: models:CardConnection
---



## Visualization on 3D Sphere

> Think about it: the interactive features are mostly agent coded and not really part of the project, but rather a (very) nice to have. They should be separated into their own file. Also the app should have a non-interactive mode. That way it can evolve without the need to update the interactive "frontend cosmetics". Once the non-interactive part has evolved and is stable, the frontend can be adapted in a heavy agent driven coding session.


### [`sphere_positions()`](./flashcards_app/geometry.py#sphere_positions)
Generate reproducible random points inside sphere. Creates uniform random distribution within unit sphere.

```yaml
component_id: geometry:sphere_positions
type: function
file: flashcards_app/geometry.py
line_start: 6
line_end: 28
tags: [geometry, 3d, random]
dependencies: [random, models:CardPosition]
used_in: [state:load_positions]
```

**Algorithm**:
1. Initialize Random with seed
2. For each card_id: generate random x,y,z in [-1,1]
3. Reject if distance_squared > 1 or == 0
4. Scale by radius and create CardPosition

**Parameters**:
- `card_ids` (List[str]): Cards to position
- `seed` (int): Reproducibility seed (default: 42)
- `radius` (float): Sphere radius (default: 1.0)

**Returns**:
- List[CardPosition]: List of generated card positions within the sphere

**Related Components**:
- Used by: `state:load_positions()`, app.py refresh_deck_state()
- Depends on: random.Random, models:CardPosition

---

### [`make_figure()`](./app.py#make_figure)
Create 3D Plotly figure showing cards on sphere. Renders interactive 3D visualization with progress coloring and connections.

```yaml
component_id: app:make_figure
type: function
file: app.py
line_start: 147
line_end: 254
tags: [visualization, 3d, plotly]
dependencies: [models, state, geometry]
used_in: [app.callback]
```

**Algorithm**:
1. Filter positions to visible cards
2. Separate selected vs regular cards
3. Add connection lines for LINKS
4. Add progress-colored regular cards
5. Add highlighted selected card
6. Configure layout with dark theme
7. Apply camera if provided

**Returns**:
- Plotly Figure object representing the 3D card visualization

**Visual Elements**:
- Connection lines between linked cards
- Progress color coding (unopened $\rightarrow$ review $\rightarrow$ developing $\rightarrow$ learned)
- Group-based card coloring
- Selected card highlight
- Hover tooltips with questions

**Related Components**:
- Used by: `app.callback` Output("sphere", "figure")
- Depends on: models, state, geometry, LINKS, PROGRESS, GROUPS
---

### [`progress_color()`](./app.py#progress_color)
Get color based on progress value. Interpolates colors from red $\rightarrow$ yellow $\rightarrow$ green based on difficulty.

```yaml
component_id: app:progress_color
type: function
file: app.py
line_start: 105
line_end: 118
tags: [color, progress, visualization]
dependencies: [models:CardProgress, math]
used_in: [app, make_figure]
```

**Parameters**:
- `progress` (int): Progress value of the card (0-100)

**Returns**:
- `str`: Hex color code corresponding to the progress value

**Color Interpolation**:
- <35: Red (#e76f51) $\rightarrow$ Yellow (#f5b942)
- 35-70: Yellow $\rightarrow$ Green (#69c6a5)
- `>70`: Green $\rightarrow$ Green (#69c6a5)

**Related Components**:
- Used by: make_figure() card rendering, card_panel()
- Depends on: models:CardProgress
---

### [`color_legend()`](./app.py#color_legend)
Display color legend for card progress and groupings. Provides a visual reference for interpreting card colors in the 3D visualization.

```yaml
component_id: app:color_legend
type: function
file: app.py
line_start: 119
line_end: 127
tags: [visualization, color, legend]
dependencies: [models:CardProgress, models:CardGroup]
used_in: [app, make_figure]
```

**Parameters**:
- None

**Returns**:
- `None`

**Related Components**:
- Used by: make_figure() card rendering, card_panel()
- Depends on: models:CardProgress, models:CardGroup
---

### [`card_panel()`](./app.py#card_panel)
Display and manage the card panel interface. Provides controls and information for individual cards. This is the output text box for the Question/Answer. It is intended to split it into separate sections for the question and the answer, allowing users to see both simultaneously.

```yaml
component_id: app:card_panel
type: function
file: app.py
line_start: 155
line_end: 165
tags: [ui, panel, card]
dependencies: [models:Card, models:CardProgress, models:CardGroup]
used_in: [app, make_figure]
```

**Parameters**:
- `card_id` (str): ID of the card to display in the panel

**Returns**:
- `None`

**Related Components**:
- Used by: make_figure() card rendering, app.callback
- Depends on: models:Card, models:CardProgress, models:CardGroup
---


## Interactive Features

### [`choose_random_card()`](./app.py#choose_random_card)
Select random card prefering read cards with low difficulty. Weighted random selection for "Random card" button.

```yaml
component_id: app:choose_random_card
type: function
file: app.py
line_start: 128
line_end: 135
tags: [advanced, random, selection]
dependencies: [models:Flashcard, models:CardProgress, random]
used_in: [app.callback]
```

**Algorithm**:
1. Filter to read cards if available
2. Calculate weights: 101 - difficulty
3. Use rng.choices() with weights

**Related Components**:
- Used by: app.callback random-card trigger
- Depends on: models, random module
---

### [`adjacent_card()`](./app.py#adjacent_card)
Get adjacent card for keyboard navigation. Enables arrow key navigation between cards.

```yaml
component_id: app:adjacent_card
type: function
file: app.py
line_start: 138
line_end: 144
tags: [advanced, navigation, keyboard]
dependencies: [models:Flashcard]
used_in: [app.callback]
```

**Algorithm**:
1. If selected_id not in cards: return first/last
2. Find selected index
3. Return cards[(index + direction) % len(cards)]

**Related Components**:
- Used by: app.callback keyboard-nav trigger
- Depends on: models:Flashcard
---


## Quality Assurance Markers

### Index Validation
**Trigger**: on explicit `validate_index` command
**Procedure**:
1. Cross-reference all `component_id` values with actual code
2. Verify all `file` paths exist
3. Check all `used_in` references are valid
4. Validate YAML frontmatter syntax
5. Search test all component IDs can be located
---

## Update Procedure

### When to Update Index
1. **Class/Method Renames**: Always update component_id
2. **New Files Added**: Add new entries with full metadata
3. **Dependency Changes**: Update dependencies/used_in arrays
4. **API Changes**: Update function signatures and parameters
5. **Feature Additions**: Add new component entries

### Update Commands
- `update_index --component flashcard:core --rename new_flashcard:core`
- `update_index --add --type dataclass --file flashcards_app/new_module.py`
- `update_index --validate` - Run QA checks
- `update_index --search term`

---

## Search Optimization

### Tag-Based Search
- **Component Type**: `dataclass`, `function`, `class`
- **Domain**: `card`, `position`, `progress`, `group`, `connection`, `parsing`, `state`, `visualization`, `ui`, `advanced`
- **Feature**: `3d`, `random`, `keyboard`, `color`, `filter`, `connection`, `persistance`

### Example Search Queries
- `find: type=function, domain=visualization`
- `search: tag=progress, component_id~app:`
- `locate: component_id=flashcard:core`

### Navigation Shortcuts
- Jump to: `component_id:flashcard:core` $\rightarrow$ `flashcards_app/models.py:4`
- Find used in: `component_id:make_figure` $\rightarrow$ all callback outputs
- Check dependencies: `component_id:state:save_state` $\rightarrow$ geometry, models, Path

---

*Index generated and maintained for efficient agent navigation and reduced prompt input.*