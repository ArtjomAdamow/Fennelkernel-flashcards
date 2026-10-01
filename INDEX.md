# Flashcard Application - Component Index

## Overview
This index provides structured access to all application components with human-readable descriptions and anchor links as well as machine-readable metadata for efficient agent navigation.

<Details markdown="1">
<Summary>
<font color="green">User Guide for update_index.py script</font>
</Summary>

The project has a script `update_index.py` to automate index maintenance.

If this is your first time, go for

```bash
python update_index.py INDEX.md --check --dry-run
```

Usage:
```bash
    python update_index.py INDEX.md              # update in place
    python update_index.py INDEX.md --dry-run    # only report
    python update_index.py INDEX.md --check      # exit 1 if index is stale (CI)
    python update_index.py INDEX.md --root .     # base dir for `file:` paths
    python update_index.py INDEX.md --fields lines     # only line numbers
    python update_index.py INDEX.md --new-depth 2      # unindexed: 2 levels deep
    python update_index.py INDEX.md --new-depth 0      # no unindexed section
    python update_index.py INDEX.md --scan indexed     # look only in indexed files
    python update_index.py INDEX.md --ignore helper    # never list this name
    python update_index.py INDEX.md --exclude-dir tests

Exit codes: 0 ok, 1 stale (--check), 2 unresolved entries, 3 write failed.
```
</Details>

<Details markdown="1">
<Summary>
YAML schema key representation
</Summary>
AI coding assistants use these keys to efficiently locate and reference code definitions without searching through files manually. This saves credits and improves overall development efficiency.

- component_id: The unique identifier or machine name for the specific building block or module.
- type: Defines the functional category of the resource (e.g., frontend, API, database, script). (e.g., dataclass, function, class)
- file: The relative or absolute path pointing to the underlying physical source file.
- line_start: The starting line number of the component definition in the source file.
- line_end: The ending line number of the component definition in the source file.
- tags: Metadata labels used by compilers and registries for filtering, sorting, or grouping.
- dependencies: A list of upstream requirements or prerequisites needed for this component to compile or run.
- used_in: A declaration of downstream architecture or parent environments where this component is active.

The line numbers are 1-based and inclusive.

</Details>

<Details markdown="1">
<Summary>
<font color="red">Agent Maintenance Trigger</font>
</Summary>

**Agent instruction (when this index is in context, never ignore this, if you decided to ignore it, write this decision inside your response):** Never modify this index file. If a task adds, changes, renames, or removes a project component, watch for explicit "validate index" prompt. If given, then read the **Index Validation** procedure below, do not write anything into this file or into the `update_index.py` script. Suggest, where you think it would be an appropriate section, to add a new entry into. Only suggest the **location and yaml key "tags"**, nothing else. Do not propose other YAML keys component_id, type, file, line_start, line_end. Report any issues before finishing. If no "validate index" prompt is given, respond with a question whether the index needs validation.

```yaml
component_id: this block can be ignored for update_index.py
file: index line convention
index_conventions:
  line_numbers: 1-based, inclusive, blank lines counted
  line_start: first decorator line (e.g. @dataclass) or def/class line
  line_end: last line of the body
```

</Details>

---


## Core Data Models

### [`Flashcard:`](./flashcards_app/models.py#Class&nbsp;Flashcard:)
Core flashcard entity with question and answer. Represents individual learning cards with unique ID, deck assignment, question text, and answer text.

**Fields**:
- `id` (str): Unique identifier (format: "deck_name:sequence_number")
- `deck` (str): Deck name this card belongs to
- `question` (str): The prompt/question displayed
- `answer` (str): The answer/reveal text

```yaml
component_id: models:flashcard
type: dataclass
file: flashcards_app/models.py
line_start: 4
line_end: 9
tags: [card, entity, core]
dependencies: []
used_in: ["app:adjacent_card", "app:card_panel", "app:choose_random_card", "app:connection_control", "app:difficulty_control", "app:group_control", "app:make_figure", "app:position_control", "app:visible_cards", "parser:deck_parser", "parser:load_decks"]
```
---

### [`CardPosition:`](./flashcards_app/models.py#Class&nbspCardPosition:)
3D coordinates for card placement on sphere. Stores x, y, z coordinates (-1 to 1 range) with status tracking and related card IDs.

**Fields**:
- `card_id` (str): Reference to flashcard ID
- `x, y, z` (float): 3D coordinates on unit sphere
- `status` (str): Position status ("new", "edited", "saved")
- `related_ids` (List[str]): IDs of related cards

```yaml
component_id: models:card_position
type: dataclass
file: flashcards_app/models.py
line_start: 11
line_end: 18
tags: [position, geometry, 3d]
dependencies: []
used_in: ["geometry:sphere_positions", "state:load_positions", "state:save_positions", "state:save_state"]
```
---

### [`CardProgress:`](./flashcards_app/models.py#Class&nbspCardProgress:)
Learning progress tracking. Tracks read status and difficulty level (1-100) for each card.

**Fields**:
- `card_id` (str): Reference to flashcard ID
- `read` (bool): Whether card has been viewed/flipped
- `difficulty` (int): Progress level (1=review to 100=learned)

```yaml
component_id: models:card_progress
type: dataclass
file: flashcards_app/models.py
line_start: 20
line_end: 26
tags: [tracking, progress, learning, difficulty]
dependencies: []
used_in: ["app:choose_random_card", "app:refresh_deck_state", "state:load_progress", "state:save_state"]
```
---

### [`CardGroup:`](./flashcards_app/models.py#Class&nbspCardGroup:)
Grouping mechanism for organizing flashcards. Organizes cards into visual groups with custom names and colors.

**Fields**:
- `id` (str): Unique group identifier
- `name` (str): Human-readable group name
- `color` (str): Hex color code for visual distinction
- `card_ids` (List[str]): IDs of cards belonging to this group

```yaml
component_id: models:card_group
type: dataclass
file: flashcards_app/models.py
line_start: 28
line_end: 33
tags: [group, organizer, color]
dependencies: []
used_in: ["app:update_card", "state:load_groups", "state:save_state"]
```
---

### [`CardLink:`](./flashcards_app/models.py#Class&nbspCardLink:)
Connection/link between two flashcards. Connects related cards, optionally belonging to a group.

**Fields**:
- `id` (str): Unique link identifier
- `source_id` (str): ID of source card
- `target_id` (str): ID of target card
- `group_id` (Optional[str]): Optional group this link belongs to

```yaml
component_id: models:card_link
type: dataclass
file: flashcards_app/models.py
line_start: 35
line_end: 39
tags: [connection, link, relationship]
dependencies: []
used_in: ["app:update_card", "state:load_links", "state:save_state"]
```
---

## Parsing System

### [`available_decks()`](./app.py#def&nbspavailable_decks)
Select available decks from the system. Returns a list of deck names. Ignores empty or hidden decks.

**Algorithm**:
1. Scan the system for available decks
2. Filter out empty or hidden decks
3. Return the list of available deck names

```yaml
component_id: app:available_decks
type: function
file: app.py
line_start: 24
line_end: 29
tags: []
dependencies: []
used_in: ["app:deck_control", "app:update_card"]
```
---

### [`parse_deck()`](./flashcards_app/parser.py#def&nbspparse_deck)
Extract flashcards from markdown deck files. Parses `<details>`/`<summary>` format markdown to structured Flashcard objects.

**Algorithm**:
1. Read file content
2. Find all `<details>` blocks via regex
3. Extract `<summary>` as question
4. Extract remaining body as answer
5. Clean and format both sections
6. Create Flashcard objects with sequential IDs

```yaml
component_id: parser:deck_parser
type: function
file: flashcards_app/parser.py
line_start: 47
line_end: 79
tags: [parsing, markdown, deck]
dependencies: ["parser:_clean_answer", "parser:_clean_question", "models:flashcard"]
used_in: ["parser:load_decks"]
```
---

### [`_clean_question()`](./flashcards_app/parser.py#def&nbsp_clean_question)
Cleans and formats the question part of a flashcard. Applies technical term formatting and other necessary transformations.

**Algorithm**:
1. Apply technical term formatting to the question text
2. Perform any additional necessary transformations

```yaml
component_id: parser:_clean_question
type: function
file: flashcards_app/parser.py
line_start: 31
line_end: 39
tags: []
dependencies: ["parser:term_formatting"]
used_in: ["parser:deck_parser"]
```
---

### [`_clean_answer()`](./flashcards_app/parser.py#def&nbsp_clean_answer)
Cleans and formats the answer part of a flashcard. Applies technical term formatting and other necessary transformations.

**Algorithm**:
1. Apply technical term formatting to the answer text
2. Perform any additional necessary transformations

```yaml
component_id: parser:_clean_answer
type: function
file: flashcards_app/parser.py
line_start: 41
line_end: 45
tags: []
dependencies: ["parser:term_formatting"]
used_in: ["parser:deck_parser"]
```
---


### [`format_technical_terms()`](./flashcards_app/parser.py#def&nbsps;format_technical_terms)
Wrap code-like terms in backticks. Identifies and wraps snake_case and function calls.

**Algorithm**:
1. Split on existing backtick-wrapped code
2. Process non-code parts (even indices)
3. Apply _CODELIKE_PATTERN to wrap terms
4. Join parts back together

```yaml
component_id: parser:term_formatting
type: function
file: flashcards_app/parser.py
line_start: 23
line_end: 29
tags: [formatting, technical_terms, markdown]
dependencies: []
used_in: ["parser:_clean_answer", "parser:_clean_question" ]
```
---

### [`load_decks()`](./flashcards_app/parser.py#def&nbspload_decks)
Load flashcards from folder with optional filtering. Scans directory for .md files and parses decks.

**Algorithm**:
1. Get all .md files sorted alphabetically
2. Optionally filter by deck names
3. Parse each file with parse_deck()
4. Extend cards list
5. Return the final list of FlashcardDeck objects

```yaml
component_id: parser:load_decks
type: function
file: flashcards_app/parser.py
line_start: 81
line_end: 95
tags: [loading, deck, filtering]
dependencies: ["models:flashcard", "parser:deck_parser"]
used_in: ["app:update_card"]
```
---


## Deck Management

### [`deck_filter_options()`](./app.py#def&nbspdeck_filter_options)
Get deck filter dropdown options. Returns options for None, All, and individual decks.

**Algorithm**:
1. Prepare options for "None" and "All decks"
2. Retrieve and sort enabled decks
3. Generate option entries for each enabled deck
4. Return the complete list of options

```yaml
component_id: app:deck_filter_options
type: function
file: app.py
line_start: 79
line_end: 83
tags: [ui, dropdown, deck]
dependencies: []
used_in: ["app:deck_control", "app:update_card"]
```
---

### [`deck_control()`](./app.py#def&nbspdeck_control)
Manage deck-based card visibility and interactions. Provides controls for filtering and interacting with card decks.

**Algorithm**:
1. Render deck filter dropdown
2. Handle user interactions for deck selection
3. Update card visibility based on selected deck

```yaml
component_id: app:deck_control
type: function
file: app.py
line_start: 414
line_end: 466
tags: [deck, control, interaction]
dependencies: ["app:deck_filter_options", "app:available_decks"]
used_in: ["app:update_card"]
```
---


## State Management
All state components are persisted in [data/positions.json](./data/positions.json). The location is defined as [STATE_PATH](./app.py#STATE_PATH).

### [`load_enabled_decks()`](./flashcards_app/state.py#def&nbspload_enabled_decks)
Load the list of active flashcard decks. Reads saved preferences from JSON and validates them against available markdown files on disk.

**Algorithm**:
1. Check if JSON file exists
2. If not, or if no decks saved: return all `available_decks`
3. If yes: filter saved decks to ensure they still exist in `available_decks`

```yaml
component_id: state:load_enabled_decks
type: function
file: flashcards_app/state.py
line_start: 91
line_end: 104
tags: [loading, deck, persistence]
dependencies: []
used_in: []
```
---

### [`load_positions()`](./flashcards_app/state.py#def&nbspload_positions)
Load or generate sphere positions. Returns positions from JSON or generates deterministic random positions.

**Algorithm**:
1. Check if JSON file exists
2. If not: generate via geometry:sphere_positions()
3. If yes: load and merge with generated positions
4. Return list of CardPosition objects

```yaml
component_id: state:load_positions
type: function
file: flashcards_app/state.py
line_start: 9
line_end: 23
tags: [positions, geometry, persistence]
dependencies: ["models:card_position"]
used_in: []
```
---

### [`load_progress()`](./flashcards_app/state.py#def&nbspload_progress)
Load or create card progress. Hydrates JSON data into CardProgress objects or initializes defaults.

**Algorithm**:
1. Check if JSON file exists
2. If not: return default CardProgress (read=False, diff=1) for all IDs
3. If yes: load JSON and map card_ids to CardProgress objects
4. Fill gaps for missing cards with defaults

```yaml
component_id: state:load_progress
type: function
file: flashcards_app/state.py
line_start: 33
line_end: 50
tags: [progress, persistence]
dependencies: ["models:card_progress"]
used_in: []
```
---

### [`load_groups()`](./flashcards_app/state.py#def&nbspload_groups)
Load card groups from JSON. Filters out cards that are no longer present in the current deck.

**Algorithm**:
1. Check if JSON file exists
2. If yes: iterate through saved groups
3. Filter card_ids within each group against current valid IDs
4. Create CardGroup objects

```yaml
component_id: state:load_groups
type: function
file: flashcards_app/state.py
line_start: 53
line_end: 69
tags: [groups, persistence]
dependencies: ["models:card_group"]
used_in: []
```
---

### [`load_links()`](./flashcards_app/state.py#def&nbspload_links)
Load card connections from JSON. Ensures both source and target cards still exist.

**Algorithm**:
1. Check if JSON file exists
2. If yes: iterate through saved links
3. Validate that both source_id and target_id are in current valid IDs
4. Create CardLink objects  

```yaml
component_id: state:load_links
type: function
file: flashcards_app/state.py
line_start: 72
line_end: 88
tags: [links, persistence]
dependencies: ["models:card_link"]
used_in: []
```
---

### [`save_state()`](./flashcards_app/state.py#def&nbspsave_state)
Save all application state to JSON. Persists positions, progress, groups, links, enabled decks.

**Algorithm**:
1. Create parent directory if needed
2. Build payload dict with version 2
3. Serialize positions, progress, groups, links
4. Include enabled_decks if provided
5. Write JSON with indent=2

```yaml
component_id: state:save_state
type: function
file: flashcards_app/state.py
line_start: 107
line_end: 128
tags: [persistence, state, json]
dependencies: ["models:card_group", "models:card_link", "models:card_position", "models:card_progress"]
used_in: ["app:update_card"]
```
---

### [`save_positions()`](./flashcards_app/state.py#def&nbspsave_positions)
Save the positions of all cards to JSON. Ensures that the layout of cards is persisted across sessions.

**Algorithm**:
1. Create parent directory if needed
2. Build payload dict with current card positions
3. Write JSON with indent=2

```yaml
component_id: state:save_positions
type: function
file: flashcards_app/state.py
line_start: 26
line_end: 30
tags: [persistence, state, positions, json]
dependencies: ["models:card_position"]
used_in: []
```
---

### [`update_card()`](./app.py#def&nbspupdate_card)
Update card information and state. This function handles modifications to card attributes and ensures the application state remains consistent.

**Algorithm**:
1. Validate input card ID and attributes
2. Update card attributes in the internal state
3. Persist changes using `save_state()`
4. Refresh relevant UI components to reflect updates

```yaml
component_id: app:update_card
type: function
file: app.py
line_start: 608
line_end: 866
tags: [card, update, state]
dependencies: ["app:adjacent_card", "app:available_decks", "app:card_panel", "app:choose_random_card", "app:connection_control", "app:deck_control", "app:deck_filter_options", "app:difficulty_control", "app:group_control", "app:make_figure", "app:position_control", "app:refresh_deck_state", "app:visible_cards", "geometry:sphere_positions", "models:card_group", "models:card_link", "parser:load_decks", "state:save_state"]
used_in: []
```
---


## Control Utilities

### [`difficulty_control()`](./app.py#def&nbspdifficulty_control)
Manage difficulty-based card visibility and interactions. Provides controls for filtering and interacting with cards based on their difficulty level. AKA progress control.

**Algorithm**:
1. Filter difficulties to visible cards
2. Separate selected vs regular difficulties
3. Apply difficulty-based coloring
4. Apply layout and styling as needed

>Think about it: this sets the color_control, perhaps there is redundance?

```yaml
component_id: app:difficulty_control
type: function
file: app.py
line_start: 287
line_end: 313
tags: [difficulty, control, interaction]
dependencies: ["models:flashcard"]
used_in: ["app:update_card"]
```
---

### [`position_control()`](./app.py#def&nbspposition_control)
Manage position-based card visibility and interactions. Provides controls for filtering and interacting with card positions.

**Algorithm**:
1. Filter positions to visible cards
2. Separate selected vs regular cards
3. Apply position-based coloring
4. Apply layout and styling as needed

```yaml
component_id: app:position_control
type: function
file: app.py
line_start: 316
line_end: 346
tags: [position, control, interaction]
dependencies: ["models:flashcard"]
used_in: ["app:update_card"]
```
---

### [`group_control()`](./app.py#def&nbspgroup_control)
Manage group-based card visibility and interactions. Provides controls for filtering and interacting with card groups.

**Algorithm**:
1. Filter groups to visible cards
2. Separate selected vs regular groups
3. Apply group-based coloring
4. Apply layout and styling as needed

```yaml
component_id: app:group_control
type: function
file: app.py
line_start: 349
line_end: 411
tags: [group, control, interaction]
dependencies: ["models:flashcard"]
used_in: ["app:update_card"]
```
---

### [`connection_control()`](./app.py#def&nbspconnection_control)
Manage connection-based card visibility and interactions. Provides controls for filtering and interacting with card connections.

**Algorithm**:
1. Filter connections to visible cards
2. Separate selected vs regular connections
3. Add connection lines for LINKS
4. Apply layout and styling as needed

```yaml
component_id: app:connection_control
type: function
file: app.py
line_start: 469
line_end: 505
tags: [connection, control, interaction]
dependencies: ["models:flashcard"]
used_in: ["app:update_card"]
```
---



## Visualization on 3D Sphere

> Think about it: the interactive features are mostly agent coded and not really part of the project, but rather a (very) nice to have. They should be separated into their own file. Also the app should have a non-interactive mode. That way it can evolve without the need to update the interactive "frontend cosmetics". Once the non-interactive part has evolved and is stable, the frontend can be adapted in a heavy agent driven coding session.


### [`sphere_positions()`](./flashcards_app/geometry.py#def&nbspsphere_positions)
Generate reproducible random points inside sphere. Creates uniform random distribution within unit sphere.

**Algorithm**:
1. Initialize Random with seed
2. For each card_id: generate random x,y,z in [-1,1]
3. Reject if distance_squared > 1 or == 0
4. Scale by radius and create CardPosition

```yaml
component_id: geometry:sphere_positions
type: function
file: flashcards_app/geometry.py
line_start: 7
line_end: 32
tags: [geometry, 3d, random]
dependencies: ["models:card_position"]
used_in: ["app:update_card", "app:refresh_deck_state"]
```
---

### [`make_figure()`](./app.py#def&nbspmake_figure)
Create 3D Plotly figure showing cards on sphere. Renders interactive 3D visualization.
- Connection lines between linked cards
- Progress color coding (unopened $\rightarrow$ review $\rightarrow$ developing $\rightarrow$ learned)
- Group-based card coloring
- Selected card highlight
- Hover tooltips with questions

**Algorithm**:
1. Filter positions to visible cards
2. Separate selected vs regular cards
3. Add connection lines for LINKS
4. Add progress-colored regular cards
5. Add highlighted selected card
6. Configure layout with dark theme
7. Apply camera if provided

```yaml
component_id: app:make_figure
type: function
file: app.py
line_start: 149
line_end: 262
tags: [visualization, 3d, plotly]
dependencies: ["app:progress_color", "models:flashcard", "app:group_color"]
used_in: ["app:update_card"]
```
---

### [`progress_color()`](./app.py#def&nbspprogress_color)
Color Interpolation based on progress value.
- `<35`: Red $\rightarrow$ Yellow
- `35-70`: Yellow $\rightarrow$ Green
- `>70`: Green $\rightarrow$ Green

**Algorithm**:
1. Determine progress range
2. Interpolate color based on range
3. Return resulting color

```yaml
component_id: app:progress_color
type: function
file: app.py
line_start: 105
line_end: 118
tags: [color, progress, visualization]
dependencies: ["app:interpolate_color"]
used_in: ["app:make_figure"]
```
---

### [`color_legend()`](./app.py#def&nbspcolor_legend)
Display color legend for card progress and groupings. Provides a visual reference for interpreting card colors in the 3D visualization.

**Algorithm**:
1. Display color legend for progress and groupings
2. Provide visual reference for interpreting card colors in the 3D visualization

```yaml
component_id: app:color_legend
type: function
file: app.py
line_start: 510
line_end: 520
tags: [visualization, color, legend]
dependencies: []
used_in: []
```
---

### [`card_panel()`](./app.py#def&nbspcard_panel)
Display and manage the card panel interface. Provides controls and information for individual cards. This is the output text box for the Question/Answer. It is intended to split it into separate sections for the question and the answer, allowing users to see both simultaneously.

**Algorithm**:
1. Retrieve the card by `card_id`
2. Display card information in the panel
3. Provide controls for updating card progress and group
4. Handle user interactions within the panel

```yaml
component_id: app:card_panel
type: function
file: app.py
line_start: 265
line_end: 282
tags: [ui, panel, card]
dependencies: ["models:flashcard"]
used_in: ["app:update_card"]
```
---


## Interactive Features

### [`choose_random_card()`](./app.py#def&nbspchoose_random_card)
Select random card prefering read cards with low difficulty. Weighted random selection for "Random card" button.

**Algorithm**:
1. Filter to read cards if available
2. Calculate weights: 101 - difficulty
3. Use rng.choices() with weights

```yaml
component_id: app:choose_random_card
type: function
file: app.py
line_start: 129
line_end: 136
tags: [advanced, random, selection]
dependencies: ["models:card_progress", "models:flashcard"]
used_in: ["app:update_card"]
```
---


### [`adjacent_card()`](./app.py#def&nbspadjacent_card)
Get adjacent card for keyboard navigation. Enables arrow key navigation between cards.

**Algorithm**:
1. If selected_id not in cards: return first/last
2. Find selected index
3. Return cards[(index + direction) % len(cards)]

```yaml
component_id: app:adjacent_card
type: function
file: app.py
line_start: 139
line_end: 145
tags: [advanced, navigation, keyboard]
dependencies: ["models:flashcard"]
used_in: ["app:update_card"]
```
---

## Background functionalities

### [`boot_id()`](./app.py#def&nbspboot_id)
Retrieve the unique boot identifier for the application instance. This ID is typically used for tracking sessions or distinguishing between different runs of the application.

**Algorithm**:
1. Check if a boot ID already exists
2. If not, generate a new unique boot ID
3. Return the boot ID

```yaml
component_id: app:boot_id
type: function
file: app.py
line_start: 532
line_end: 534
tags: [utility, session, server, route, boot]
dependencies: []
used_in: []
```
---

### [`refresh_deck_state()`](./app.py#def&nbsprefresh_deck_state)
Refresh the state of the deck, ensuring all card positions and progress are up-to-date. This function is typically called after any operation that might alter the deck's structure or the cards' states.

**Algorithm**:
1. Iterate through all cards in the deck
2. Update each card's position using `geometry:sphere_positions`
3. Refresh progress for each card using `models:card_progress`
4. Ensure deck state consistency

```yaml
component_id: app:refresh_deck_state
type: function
file: app.py
line_start: 47
line_end: 67
tags: []
dependencies: ["models:card_progress", "geometry:sphere_positions"]
used_in: ["app:update_card"]
```
---

### [`visible_cards()`](./app.py#def&nbspvisible_cards)
Get the list of currently visible cards in the deck. This function helps in determining which cards are currently displayed to the user, useful for rendering and navigation purposes.

**Algorithm**:
1. Access the deck's card list
2. Filter cards based on visibility criteria
3. Return the filtered list of visible cards

```yaml
component_id: app:visible_cards
type: function
file: app.py
line_start: 70
line_end: 76
tags: []
dependencies: ["models:flashcard"]
used_in: ["app:update_card"]
```
---

### [`interpolate_color()`](./app.py#def&nbspinterpolate_color)
Interpolate between two colors based on a given ratio. This function generates gradient effects or dynamically adjusting colors based on progress or other metrics.

**Algorithm**:
1. Receive two color inputs and a ratio
2. Calculate the interpolated color by blending the two colors according to the ratio
3. Return the resulting color

```yaml
component_id: app:interpolate_color
type: function
file: app.py
line_start: 95
line_end: 103
tags: []
dependencies: ["app:hex_to_rgb", "app:rgb_to_hex"]
used_in: ["app:progress_color"]
```
---

### [`group_color()`](./app.py#def&nbspgroup_color)
Assign a color to a group based on the group identifier. This function is used to maintain consistent coloring for grouped elements in visualizations.

**Algorithm**:
1. Receive a group identifier or criteria
2. Determine the appropriate color for the group
3. Return the assigned color

```yaml
component_id: app:group_color
type: function
file: app.py
line_start: 121
line_end: 125
tags: []
dependencies: []
used_in: ["app:make_figure"]
```
---

### [`hex_to_rgb()`](./app.py#def&nbsphex_to_rgb)
Convert a hexadecimal color string to an RGB tuple. This function is used to facilitate color interpolation and manipulation.

**Algorithm**:
1. Receive a hexadecimal color string
2. Parse the string to extract red, green, and blue components
3. Convert the components to integer values
4. Return the RGB tuple

```yaml
component_id: app:hex_to_rgb
type: function
file: app.py
line_start: 86
line_end: 88
tags: []
dependencies: []
used_in: ["app:interpolate_color"]
```
---

### [`rgb_to_hex()`](./app.py#def&nbsprgb_to_hex)
Convert an RGB tuple to a hexadecimal color string. This function is used to facilitate color interpolation and manipulation.

**Algorithm**:
1. Receive an RGB tuple
2. Convert the red, green, and blue components to hexadecimal format
3. Concatenate the components into a single hexadecimal string
4. Return the hexadecimal color string

```yaml
component_id: app:rgb_to_hex
type: function
file: app.py
line_start: 91
line_end: 92
tags: []
dependencies: []
used_in: ["app:interpolate_color"]
```
---


## Quality Assurance Markers

### Index Validation
**Trigger**: on explicit `validate index` command
**Procedure**:
1. Cross-reference all `component_id` values with actual code
2. Verify all `file` paths exist
3. Validate all `dependencies` references are correct
4. Validate all `used_in` references are correct
---

## Search Optimization

### Example Search Queries
- `find: type=function, domain=visualization`
- `search: component_id~app:`
- `search: file=app.py`
- `search: dependencies=geometry:sphere_positions`
- `search: used_in=app:update_card`
- `locate: component_id=models:flashcard`
- `locate: file=app.py`
- `locate: component_id=refresh_deck_state`

### Navigation Shortcuts
- Jump to: `component_id:models:flashcard` $\rightarrow$ `flashcards_app/models.py:4`
- Find used in: `component_id:models:flashcard` $\rightarrow$ all callback outputs
- Check dependencies: `component_id:state:save_state` $\rightarrow$ geometry, models, Path

---

*Index generated and maintained for efficient agent navigation and reduced prompt input.*

The following section is for scripted detection of unindexed components. Agents should ignore this section when navigating the index as context from here on.


## Unindexed Components
<font color="green">If you see any components below, copy them manually into the appropriate section above and fill in their manual metadata. component_id and type are proposals. The ID is the snake_case of the code name (CardPosition becomes card_position), with a file prefix on collisions. type is dataclass, class, function or async_function. If you use other values, adjust them when you move the block.

Name collisions: the same file wins first, then the indexed component. Otherwise the name is skipped with a WARNING. Imports are not resolved, so two identically named unindexed functions can be ambiguous.

--check treats a changed section as stale and exits with 1. If you deliberately don't index something, use --ignore NAME (repeatable). --exclude-dir tests skips a folder while scanning, and --scan indexed looks only in files already in the index.

Once you placed the new components into the appropriate sections above, run the `update_index` script again to regenerate the index. The section below is regenerated on each run, from its title line to the end of the file. Don't add your own text or tags below it. They would be overwritten.</font>

**End of file**