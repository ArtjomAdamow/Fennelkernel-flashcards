# Flashcard Application
Components Index

## Overview

Agents: jump directly to the Agent Maintenance Trigger section for instructions without reading any text before it. Users: This index provides structured access to all application components with human-readable descriptions and anchor links as well as machine-readable metadata for efficient agent navigation.

<Details markdown="1">
<Summary><font color="green">User Guide for update_index.py script</font></Summary>

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
<Summary>YAML schema key representation</Summary>
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
<Summary><font color="red">Agent Maintenance Trigger</font></Summary>

**Agent instruction (when this index is in context, never ignore this, if you decided to ignore it, write this decision inside your response):** Never modify this index file.

Before any changes to the project are done, first find the prompted component in the index. Only read anchor links and YAML tags. Do not take any other text beyond this instruction into content.

```yaml
component_id: convention:example
file: index line convention
index_conventions:
  line_numbers: 1-based, inclusive, blank lines counted
  line_start: first decorator line (e.g. @dataclass) or def/class line
  line_end: last line of the body
```

If a task adds, changes, renames, or removes a project component, watch for explicit "validate index" prompt. If "validate index" prompt not given, respond with a question whether the index needs validation and from here jump to the relevant component in the Index section. Only If "validate index" prompt given:  

1. Cross-reference all `component_id` values with actual code going by the anchor links in the index.
2. Verify all `file` paths exist.
3. Do NOT verify any other yaml keys except for `component_id` and `file`.
4. For new components suggest, where you think it would be an appropriate section, to add a new entry into. Only suggest the **location and yaml key "tags"**, nothing else. Do not propose other YAML keys component_id, type, file, line_start, line_end.
5. Report any issues before finishing.

</Details>


## Index

### Core Data Models

The core data models define the primary entities used throughout the flashcards application, including flashcards, card positions, and card progress.

<Details markdown="1">
<Summary><sd

#### [`Flashcard:`](./flashcards_app/models.py#Class Flashcard:)

</Summary>
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
used_in: ["cards:adjacent_card", "cards:choose_random_card", "cards:pick_adjacent", "cards:pick_random", "map:make_figure", "panels:card_panel", "panels:connection_control", "panels:difficulty_control", "panels:group_control", "panels:position_control", "parser:deck_parser", "parser:load_decks", "runtime:visible_cards"]
```

</Details>
---

<Details markdown="1">
<Summary><sd

#### [`CardPosition:`](./flashcards_app/models.py#Class&nbspCardPosition:)

</Summary>
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
used_in: ["geometry:sphere_positions", "state:load_positions", "state:save_state"]
```

</Details>
---

<Details markdown="1">
<Summary><sd

#### [`CardProgress:`](./flashcards_app/models.py#Class&nbspCardProgress:)

</Summary>
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
used_in: ["cards:choose_random_card", "runtime:refresh_deck_state", "state:load_progress", "state:save_state"]
```

</Details>
---

<Details markdown="1">
<Summary><sd

#### [`CardGroup:`](./flashcards_app/models.py#Class&nbspCardGroup:)

</Summary>
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
used_in: ["groups:create_group", "state:load_groups", "state:save_state"]
```

</Details>
---

<Details markdown="1">
<Summary><sd

#### [`CardLink:`](./flashcards_app/models.py#Class&nbspCardLink:)

</Summary>
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
used_in: ["connections:create_link", "state:load_links", "state:save_state"]
```

</Details>
---

### Parsing System

The parsing system is responsible for extracting structured data from markdown deck files. It identifies specified blocks and converts them into objects.

<Details markdown="1">
<Summary><sd

#### [`parse_deck()`](./flashcards_app/parser.py#def&nbspparse_deck)

</Summary>
Extract flashcards from markdown deck files. Parses format markdown to structured Flashcard objects.

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

</Details>
---

<Details markdown="1">
<Summary><sd

#### [`_clean_question()`](./flashcards_app/parser.py#def _clean_question)

</Summary>
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

</Details>
---

<Details markdown="1">
<Summary><sd

#### [`_clean_answer()`](./flashcards_app/parser.py#def _clean_answer)

</Summary>
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

</Details>
---

<Details markdown="1">
<Summary><sd

#### [`format_technical_terms()`](./flashcards_app/parser.py#def&nbsps;format_technical_terms)

</Summary>
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

</Details>
---

<Details markdown="1">
<Summary><sd

#### [`load_decks()`](./flashcards_app/parser.py#def&nbspload_decks)

</Summary>
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
used_in: ["decks:add_enabled_deck", "decks:remove_enabled_deck"]
```

</Details>
---

### State Management

All state components are persisted in [data/positions.json](./data/positions.json). The location is defined as [STATE_PATH](./flashcards_app/runtime.py#STATE_PATH).

<Details markdown="1">
<Summary><sd

#### [`load_enabled_decks()`](./flashcards_app/state.py#def&nbspload_enabled_decks)

</Summary>
Load the list of active flashcard decks. Reads saved preferences from JSON and validates them against available markdown files on disk.

**Algorithm**:

1. Check if JSON file exists
2. If not, or if no decks saved: return all `available_decks`
3. If yes: filter saved decks to ensure they still exist in `available_decks`

```yaml
component_id: state:load_enabled_decks
type: function
file: flashcards_app/state.py
line_start: 83
line_end: 96
tags: [loading, deck, persistence]
dependencies: []
used_in: []
```

</Details>
---

<Details markdown="1">
<Summary><sd

#### [`load_positions()`](./flashcards_app/state.py#def&nbspload_positions)

</Summary>
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
dependencies: ["geometry:sphere_positions", "models:card_position"]
used_in: []
```

</Details>
---

<Details markdown="1">
<Summary><sd

#### [`load_progress()`](./flashcards_app/state.py#def&nbspload_progress)

</Summary>
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
line_start: 25
line_end: 42
tags: [progress, persistence]
dependencies: ["models:card_progress"]
used_in: []
```

</Details>
---

<Details markdown="1">
<Summary><sd

#### [`load_groups()`](./flashcards_app/state.py#def&nbspload_groups)

</Summary>
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
line_start: 45
line_end: 61
tags: [groups, persistence]
dependencies: ["models:card_group"]
used_in: []
```

</Details>
---

<Details markdown="1">
<Summary><sd

#### [`load_links()`](./flashcards_app/state.py#def&nbspload_links)

</Summary>
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
line_start: 64
line_end: 80
tags: [links, persistence]
dependencies: ["models:card_link"]
used_in: []
```

</Details>
---

<Details markdown="1">
<Summary><sd

#### [`save_state()`](./flashcards_app/state.py#def&nbspsave_state)

</Summary>
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
line_start: 99
line_end: 120
tags: [persistence, state, json]
dependencies: ["models:card_group", "models:card_link", "models:card_position", "models:card_progress"]
used_in: ["callbacks:update_card", "server:main"]
```

</Details>
---

### Visualization of control elements (panels)

This section provides an overview and detailed descriptions of the various control elements (panels) used in the flashcards application. Each panel corresponds to a specific user interface component that allows interaction with flashcards.

<Details markdown="1">
<Summary><sd

#### [`deck_control()`](./flashcards_app/visualization/panels.py#def&nbspdeck_control)

</Summary>
The `deck_control()` function generates the user interface control for selecting the deck of a flashcard.

**Algorithm**:

1. Retrieve the current deck of the flashcard
2. Create the control layout with options for different decks
3. Handle user interactions to update the deck
4. Return the constructed control

```yaml
component_id: panels:deck_control
type: function
file: flashcards_app/visualization/panels.py
line_start: 156
line_end: 208
tags: []
dependencies: ["decks:deck_filter_options", "runtime:available_decks"]
used_in: ["callbacks:update_card"]
```

</Details>
---

<Details markdown="1">
<Summary><sd

#### [`card_panel()`](./flashcards_app/visualization/panels.py#def&nbspcard_panel)

</Summary>
The `card_panel()` function generates the user interface panel for displaying and interacting with a flashcard.

**Algorithm**:

1. Retrieve the flashcard data
2. Create the panel layout with the flashcard content
3. Include controls for interacting with the flashcard (e.g., reveal answer, navigate)
4. Return the constructed panel

```yaml
component_id: panels:card_panel
type: function
file: flashcards_app/visualization/panels.py
line_start: 9
line_end: 26
tags: []
dependencies: ["models:flashcard"]
used_in: ["callbacks:update_card"]
```

</Details>
---

<Details markdown="1">
<Summary><sd

#### [`difficulty_control()`](./flashcards_app/visualization/panels.py#def&nbspdifficulty_control)

</Summary>
The `difficulty_control()` function generates the user interface control for selecting the difficulty level of a flashcard.

**Algorithm**:

1. Retrieve the current difficulty level of the flashcard
2. Create the control layout with options for different difficulty levels
3. Handle user interactions to update the difficulty level
4. Return the constructed control

```yaml
component_id: panels:difficulty_control
type: function
file: flashcards_app/visualization/panels.py
line_start: 29
line_end: 55
tags: []
dependencies: ["models:flashcard"]
used_in: ["callbacks:update_card"]
```

</Details>
---

<Details markdown="1">
<Summary><sd

#### [`position_control()`](./flashcards_app/visualization/panels.py#def&nbspposition_control)

</Summary>
The `position_control()` function generates the user interface control for selecting the position of a flashcard.

**Algorithm**:

1. Retrieve the current position of the flashcard
2. Create the control layout with options for different positions
3. Handle user interactions to update the position
4. Return the constructed control

```yaml
component_id: panels:position_control
type: function
file: flashcards_app/visualization/panels.py
line_start: 58
line_end: 88
tags: []
dependencies: ["models:flashcard"]
used_in: ["callbacks:update_card"]
```

</Details>
---

<Details markdown="1">
<Summary><sd

#### [`group_control()`](./flashcards_app/visualization/panels.py#def&nbspgroup_control)

</Summary>
The `group_control()` function generates the user interface control for selecting the group of a flashcard.

**Algorithm**:

1. Retrieve the current group of the flashcard
2. Create the control layout with options for different groups
3. Handle user interactions to update the group
4. Return the constructed control

```yaml
component_id: panels:group_control
type: function
file: flashcards_app/visualization/panels.py
line_start: 91
line_end: 153
tags: []
dependencies: ["models:flashcard"]
used_in: ["callbacks:update_card"]
```

</Details>
---

<Details markdown="1">
<Summary><sd

#### [`connection_control()`](./flashcards_app/visualization/panels.py#def&nbspconnection_control)

</Summary>
The `connection_control()` function generates the user interface control for selecting the connection of a flashcard.

**Algorithm**:

1. Retrieve the current connection of the flashcard
2. Create the control layout with options for different connections
3. Handle user interactions to update the connection
4. Return the constructed control

```yaml
component_id: panels:connection_control
type: function
file: flashcards_app/visualization/panels.py
line_start: 211
line_end: 247
tags: []
dependencies: ["models:flashcard"]
used_in: ["callbacks:update_card"]
```

</Details>
---

### Visualization on 3D Sphere

The visualization on a 3D sphere helps users to understand the spatial relationships between flashcards, providing an intuitive way to explore the deck.

For new decks it generates reproducible random points inside a sphere. It ensues that all points stay inside the unit sphere. Framework: Dash (Plotly) with Flask for boot-id endpoint Visualization: Plotly 3D Scatter plots showing cards on a sphere.

The app uses an **extensive callback system for interactivity**.


<Details markdown="1">
<Summary><sd

#### [`sphere_positions()`](./flashcards_app/geometry.py#def&nbspsphere_positions)

</Summary>
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
used_in: ["runtime:refresh_deck_state", "runtime:reset_all_state", "state:load_positions"]
```

</Details>
---

<Details markdown="1">
<Summary><sd

#### [`make_figure()`](./flashcards_app/visualization/map.py#def&nbspmake_figure)

</Summary>
The `make_figure()` function generates a visual representation of the flashcards on a map, using colors to indicate progress and group membership.

**Algorithm**:

1. Initialize figure and axes
2. For each flashcard: determine color based on progress and group
3. Plot flashcard on map
4. Return the generated figure

```yaml
component_id: map:make_figure
type: function
file: flashcards_app/visualization/map.py
line_start: 9
line_end: 122
tags: []
dependencies: ["colors:group_color", "colors:progress_color", "models:flashcard"]
used_in: ["callbacks:update_card"]
```

</Details>
---

<Details markdown="1">
<Summary><sd

#### [`hex_to_rgb()`](./flashcards_app/visualization/colors.py#def&nbsphex_to_rgb)

</Summary>
The `hex_to_rgb()` function converts a hexadecimal color string to an RGB tuple.

**Algorithm**:

1. Remove the leading '#' from the hex string if present
2. Convert the hex string to an integer
3. Extract the red, green, and blue components
4. Return the RGB tuple

```yaml
component_id: colors:hex_to_rgb
type: function
file: flashcards_app/visualization/colors.py
line_start: 4
line_end: 6
tags: []
dependencies: []
used_in: ["colors:interpolate_color"]
```

</Details>
---

<Details markdown="1">
<Summary><sd

#### [`rgb_to_hex()`](./flashcards_app/visualization/colors.py#def&nbsprgb_to_hex)

</Summary>
The `rgb_to_hex()` function converts an RGB tuple to a hexadecimal color string.

**Algorithm**:

1. Extract the red, green, and blue components from the RGB tuple
2. Convert each component to a two-digit hexadecimal string
3. Concatenate the hexadecimal strings with a leading '#'
4. Return the hexadecimal color string

```yaml
component_id: colors:rgb_to_hex
type: function
file: flashcards_app/visualization/colors.py
line_start: 9
line_end: 10
tags: []
dependencies: []
used_in: ["colors:interpolate_color"]
```

</Details>
---

<Details markdown="1">
<Summary><sd

#### [`interpolate_color()`](./flashcards_app/visualization/colors.py#def&nbspinterpolate_color)

</Summary>
The `interpolate_color()` function calculates an intermediate color between two given colors based on a specified ratio.

**Algorithm**:

1. Convert the start and end colors from hex to RGB
2. Interpolate each RGB component based on the ratio
3. Convert the interpolated RGB color back to hex
4. Return the resulting color

```yaml
component_id: colors:interpolate_color
type: function
file: flashcards_app/visualization/colors.py
line_start: 13
line_end: 21
tags: []
dependencies: ["colors:hex_to_rgb", "colors:rgb_to_hex"]
used_in: ["colors:progress_color"]
```

</Details>
---

<Details markdown="1">
<Summary><sd

#### [`progress_color()`](./flashcards_app/visualization/colors.py#def&nbspprogress_color)

</Summary>
The `progress_color()` function determines the color representing the progress based on a given ratio.

**Algorithm**:

1. Define the start and end colors for the progress
2. Use the `interpolate_color()` function to calculate the intermediate color based on the ratio
3. Return the resulting color

```yaml
component_id: colors:progress_color
type: function
file: flashcards_app/visualization/colors.py
line_start: 24
line_end: 37
tags: []
dependencies: ["colors:interpolate_color"]
used_in: ["map:make_figure"]
```

</Details>
---

<Details markdown="1">
<Summary><sd

#### [`group_color()`](./flashcards_app/visualization/colors.py#def&nbspgroup_color)

</Summary>
The `group_color()` function determines the color associated with a specific group.

**Algorithm**:

1. Define a mapping of groups to colors
2. Look up the color for the given group
3. Return the corresponding color

```yaml
component_id: colors:group_color
type: function
file: flashcards_app/visualization/colors.py
line_start: 40
line_end: 44
tags: []
dependencies: []
used_in: ["map:make_figure"]
```

</Details>
---

### Interactive Features

The following section deals with interactive features that allow users to interact with the flashcards in various ways.

> The interactive features are planned as controls for tuning the model's behavior within the DS project. Without the model they provide a manual interface for navigating and managing flashcards.

### Decks

Selecting decks allows users to choose which decks they want to enable and interact with within the flashcards application. **This is the 1st and lowest level of detalisation**.

<Details markdown="1">
<Summary><sd

#### [`add_enabled_deck()`](./flashcards_app/services/decks.py#def&nbspadd_enabled_deck)

</Summary>
The `add_enabled_deck()` function adds a deck to the list of enabled decks.

**Algorithm**:

1. Load the current list of enabled decks
2. Add the specified deck to the list
3. Refresh the deck state to reflect the changes

```yaml
component_id: decks:add_enabled_deck
type: function
file: flashcards_app/services/decks.py
line_start: 12
line_end: 17
tags: []
dependencies: ["parser:load_decks", "runtime:available_decks", "runtime:refresh_deck_state"]
used_in: ["callbacks:update_card"]
```

</Details>
---

<Details markdown="1">
<Summary><sd

#### [`remove_enabled_deck()`](./flashcards_app/services/decks.py#def&nbspremove_enabled_deck)

</Summary>
The `remove_enabled_deck()` function removes a deck from the list of enabled decks.

**Algorithm**:

1. Load the current list of enabled decks
2. Remove the specified deck from the list
3. Refresh the deck state to reflect the changes

```yaml
component_id: decks:remove_enabled_deck
type: function
file: flashcards_app/services/decks.py
line_start: 20
line_end: 26
tags: []
dependencies: ["parser:load_decks", "runtime:refresh_deck_state"]
used_in: ["callbacks:update_card"]
```

</Details>
---

<Details markdown="1">
<Summary><sd

#### [`deck_filter_options()`](./flashcards_app/services/decks.py#def&nbspdeck_filter_options)

</Summary>
The `deck_filter_options()` function retrieves the available filter options for decks.

**Algorithm**:

1. Retrieve the list of available filter options for decks
2. Return the list of available filter options

```yaml
component_id: decks:deck_filter_options
type: function
file: flashcards_app/services/decks.py
line_start: 5
line_end: 9
tags: []
dependencies: []
used_in: ["callbacks:update_card", "panels:deck_control"]
```

</Details>
---

### Positions

The position of a flashcard within the sphere determines its vectorization. The spatial arrangement of flashcards shows the relative importance and relationships between different cards. It allows to establish a structured understanding of how individual flashcards relate to each other within the broader context of the knowledge sphere. **This is the 2nd level of detalisation**.

<Details markdown="1">
<Summary><sd

#### [`set_position()`](./flashcards_app/services/positions.py#def&nbspset_position)

</Summary>
The `set_position()` function sets the position of a flashcard within a group.

**Algorithm**:

1. Identify the flashcard and the target position
2. Update the flashcard's position

```yaml
component_id: positions:set_position
type: function
file: flashcards_app/services/positions.py
line_start: 4
line_end: 8
tags: []
dependencies: []
used_in: ["callbacks:update_card"]
```

</Details>
---

### Groups

Grouping flashcards into collections shows the relationships between different cards and allows users to organize their study material more effectively. **Together with connections this is the 3rd and intermediate level of detalisation**.

<Details markdown="1">
<Summary><sd

#### [`add_to_group()`](./flashcards_app/services/groups.py#def&nbspadd_to_group)

</Summary>
The `add_to_group()` function adds a flashcard to a specified group.

**Algorithm**:

1. Identify the flashcard and the target group
2. Add the flashcard to the group

```yaml
component_id: groups:add_to_group
type: function
file: flashcards_app/services/groups.py
line_start: 10
line_end: 13
tags: []
dependencies: []
used_in: []
```

</Details>
---

<Details markdown="1">
<Summary><sd

#### [`add_to_group()`](./flashcards_app/services/groups.py#def&nbspadd_to_group)

</Summary>
The `add_to_group()` function adds a flashcard to a specified group.

**Algorithm**:

1. Identify the flashcard and the target group
2. Add the flashcard to the group

```yaml
component_id: groups:add_to_group
type: function
file: flashcards_app/services/groups.py
line_start: 10
line_end: 13
tags: []
dependencies: []
used_in: ["callbacks:update_card"]
```

</Details>
---

<Details markdown="1">
<Summary><sd

#### [`remove_from_group()`](./flashcards_app/services/groups.py#def&nbspremove_from_group)

</Summary>
The `remove_from_group()` function removes a flashcard from a specified group.

**Algorithm**:

1. Identify the flashcard and the target group
2. Remove the flashcard from the group

```yaml
component_id: groups:remove_from_group
type: function
file: flashcards_app/services/groups.py
line_start: 16
line_end: 19
tags: []
dependencies: []
used_in: ["callbacks:update_card"]
```

</Details>
---

<Details markdown="1">
<Summary><sd

#### [`delete_group()`](./flashcards_app/services/groups.py#def&nbspdelete_group)

</Summary>
The `delete_group()` function deletes a specified group.

**Algorithm**:

1. Identify the target group
2. Delete the group

```yaml
component_id: groups:delete_group
type: function
file: flashcards_app/services/groups.py
line_start: 22
line_end: 24
tags: []
dependencies: []
used_in: ["callbacks:update_card"]
```

</Details>
---

<Details markdown="1">
<Summary><sd

#### [`create_group()`](./flashcards_app/services/groups.py#def&nbspcreate_group)

</Summary>
The `create_group()` function creates a new flashcard group.

**Algorithm**:

1. Define the new group attributes
2. Save the new group

```yaml
component_id: groups:create_group
type: function
file: flashcards_app/services/groups.py
line_start: 5
line_end: 7
tags: []
dependencies: ["models:card_group"]
used_in: ["callbacks:update_card"]
```

</Details>
---

### Connections

Connecting cards allows users to establish fixed relationships between different flashcards, enhancing the study experience by linking related concepts. **Together with grouping, this is the 3rd and intermediate level of detalisation**.

<Details markdown="1">
<Summary><sd

#### [`disconnect_link()`](./flashcards_app/services/connections.py#def&nbspdisconnect_link)

</Summary>
The `disconnect_link()` function removes an existing link between two flashcards.

**Algorithm**:

1. Identify the link between the specified flashcards
2. Remove the link

```yaml
component_id: connections:disconnect_link
type: function
file: flashcards_app/services/connections.py
line_start: 15
line_end: 22
tags: []
dependencies: []
used_in: ["callbacks:update_card"]
```

</Details>
---

<Details markdown="1">
<Summary><sd

#### [`create_link()`](./flashcards_app/services/connections.py#def&nbspcreate_link)

</Summary>
The `create_link()` function establishes a new link between two flashcards.

**Algorithm**:

1. Identify the flashcards to be linked
2. Create a link between the specified flashcards

```yaml
component_id: connections:create_link
type: function
file: flashcards_app/services/connections.py
line_start: 5
line_end: 12
tags: []
dependencies: ["models:card_link"]
used_in: ["callbacks:update_card"]
```

</Details>
---

### Cards

This last section covers navigating and selecting cards, revealing answers and tracking progress. It deals with the actual inner quality of the request. **This is the 4th and highest level of detalisation**.

<Details markdown="1">
<Summary><sd

#### [`choose_random_card()`](./flashcards_app/services/cards.py#def&nbspchoose_random_card)

</Summary>
The `choose_random_card()` function selects a random card from the available flashcards.

**Algorithm**:

1. Retrieve the list of all flashcards
2. Randomly select one card from the list
3. Return the selected card

```yaml
component_id: cards:choose_random_card
type: function
file: flashcards_app/services/cards.py
line_start: 5
line_end: 12
tags: []
dependencies: ["models:card_progress", "models:flashcard"]
used_in: ["cards:pick_random"] 
```

</Details>
---

<Details markdown="1">
<Summary><sd

#### [`pick_random()`](./flashcards_app/services/cards.py#def&nbsppick_random)

</Summary>
The `pick_random()` function selects a random flashcard using the `choose_random_card()` function and returns it.

**Algorithm**:

1. Call the `choose_random_card()` function to select a random card
2. Return the selected card

```yaml
component_id: cards:pick_random
type: function
file: flashcards_app/services/cards.py
line_start: 37
line_end: 39
tags: []
dependencies: ["cards:choose_random_card", "models:flashcard"]
used_in: ["callbacks:update_card"]
```

</Details>
---

<Details markdown="1">
<Summary><sd

#### [`adjacent_card()`](./flashcards_app/services/cards.py#def&nbspadjacent_card)

</Summary>
The `adjacent_card()` function retrieves the card adjacent to the currently selected card, either the previous or next one based on the specified direction.

**Algorithm**:

1. Determine the current card's position in the list of flashcards
2. Calculate the position of the adjacent card based on the direction
3. Return the adjacent card

```yaml
component_id: cards:adjacent_card
type: function
file: flashcards_app/services/cards.py
line_start: 15
line_end: 21
tags: []
dependencies: ["models:flashcard"]
used_in: ["cards:pick_adjacent"]
```

</Details>
---

<Details markdown="1">
<Summary><sd

#### [`pick_adjacent()`](./flashcards_app/services/cards.py#def&nbsppick_adjacent)

</Summary>
The `pick_adjacent()` function retrieves the flashcard adjacent to the currently selected one using the `adjacent_card()` function and returns it.

**Algorithm**:

1. Call the `adjacent_card()` function to get the adjacent card
2. Return the adjacent card

```yaml
component_id: cards:pick_adjacent
type: function
file: flashcards_app/services/cards.py
line_start: 42
line_end: 44
tags: []
dependencies: ["cards:adjacent_card", "models:flashcard"]
used_in: ["callbacks:update_card"]
```

</Details>
---

<Details markdown="1">
<Summary><sd

#### [`select_from_click()`](./flashcards_app/services/cards.py#def&nbspselect_from_click)

</Summary>
The `select_from_click()` function selects a flashcard based on a user's click input and returns it.

**Algorithm**:

1. Determine which card was clicked based on the input
2. Return the selected card

```yaml
component_id: cards:select_from_click
type: function
file: flashcards_app/services/cards.py
line_start: 24
line_end: 27
tags: []
dependencies: []
used_in: ["callbacks:update_card"]
```

</Details>
---

<Details markdown="1">
<Summary><sd

#### [`toggle_reveal()`](./flashcards_app/services/cards.py#def&nbsptoggle_reveal)

</Summary>
The `toggle_reveal()` function toggles the reveal state of the currently selected flashcard.

**Algorithm**:

1. Check the current reveal state of the flashcard
2. Toggle the reveal state

```yaml
component_id: cards:toggle_reveal
type: function
file: flashcards_app/services/cards.py
line_start: 30
line_end: 34
tags: []
dependencies: []
used_in: ["callbacks:update_card"]
```

</Details>
---

<Details markdown="1">
<Summary><sd

#### [`set_difficulty()`](./flashcards_app/services/progress.py#def&nbspset_difficulty)

</Summary>
Despite its name, the `set_difficulty()` function sets the learning progress of a flashcard. Given a time scale, slow progress indicates a higher difficulty.

> Regarding the model supported output this function can control the actual difficulty level of the output (e.g., how challenging the given exercise appears to the user)

**Algorithm**:

1. Identify the flashcard and the target difficulty level
2. Update the flashcard's difficulty level

```yaml
component_id: progress:set_difficulty
type: function
file: flashcards_app/services/progress.py
line_start: 4
line_end: 5
tags: []
dependencies: []
used_in: ["callbacks:update_card"]
```

</Details>
---

### Background functionalities

These background functionalities manage the overall state and visibility of decks and cards within the application. Functions are moved to this section if they primarily deal with maintaining or updating the application's state rather than direct user interactions.

<Details markdown="1">
<Summary><sd

#### [`refresh_deck_state()`](./flashcards_app/runtime.py#def&nbsprefresh_deck_state)

</Summary>
The `refresh_deck_state()` function updates the state of the deck, ensuring that the visibility and order of cards are consistent with the current application state.

**Algorithm**:

1. Retrieve the current state of the deck
2. Update the visibility and order of cards based on the current application state

```yaml
component_id: runtime:refresh_deck_state
type: function
file: flashcards_app/runtime.py
line_start: 43
line_end: 63
tags: []
dependencies: ["geometry:sphere_positions", "models:card_progress"]
used_in: ["decks:add_enabled_deck", "decks:remove_enabled_deck"]
```

</Details>
---

<Details markdown="1">
<Summary><sd

#### [`available_decks()`](./flashcards_app/runtime.py#def&nbspavailable_decks)

</Summary>
The `available_decks()` function retrieves the list of decks that are currently available in the application.

**Algorithm**:

1. Access the application's deck repository
2. Return the list of available decks

```yaml
component_id: runtime:available_decks
type: function
file: flashcards_app/runtime.py
line_start: 20
line_end: 25
tags: []
dependencies: []
used_in: ["decks:add_enabled_deck", "panels:deck_control"]
```

</Details>
---

<Details markdown="1">
<Summary><sd

#### [`visible_cards()`](./flashcards_app/runtime.py#def&nbspvisible_cards)

</Summary>
The `visible_cards()` function retrieves the list of cards that are currently visible to the user.

**Algorithm**:

1. Access the application's card repository
2. Filter the cards based on their visibility status
3. Return the list of visible cards

```yaml
component_id: runtime:visible_cards
type: function
file: flashcards_app/runtime.py
line_start: 66
line_end: 72
tags: []
dependencies: ["models:flashcard"]
used_in: ["callbacks:update_card"]
```

</Details>
---

<Details markdown="1">
<Summary><sd

#### [`reset_all_state()`](./flashcards_app/runtime.py#def&nbspreset_all_state)

</Summary>
The `reset_all_state()` function resets the entire application state, clearing all current data and returning the application to its initial state.

**Algorithm**:

1. Clear all current application data
2. Reset all state variables to their initial values
3. Ensure the application is in its initial state

```yaml
component_id: runtime:reset_all_state
type: function
file: flashcards_app/runtime.py
line_start: 75
line_end: 83
tags: []
dependencies: ["geometry:sphere_positions"]
used_in: ["callbacks:update_card"]
```

</Details>
---

<Details markdown="1">
<Summary><sd

#### [`update_card()`](./flashcards_app/callbacks.py#def&nbspupdate_card)

</Summary>
The `update_card()` function handles the logic for updating a card's state based on user interactions and application events.

**Algorithm**:

1. Identify the card to be updated based on user input or application events
2. Apply the necessary updates to the card's state
3. Trigger any dependent updates or callbacks
4. Ensure the application state remains consistent

```yaml
component_id: callbacks:update_card
type: function
file: flashcards_app/callbacks.py
line_start: 24
line_end: 233
tags: []
dependencies: ["cards:pick_adjacent", "cards:pick_random", "cards:select_from_click", "cards:toggle_reveal", "connections:create_link", "connections:disconnect_link", "decks:add_enabled_deck", "decks:deck_filter_options", "decks:remove_enabled_deck", "groups:add_to_group", "groups:create_group", "groups:delete_group", "groups:remove_from_group", "map:make_figure", "panels:card_panel", "panels:connection_control", "panels:deck_control", "panels:difficulty_control", "panels:group_control", "panels:position_control", "positions:set_position", "progress:set_difficulty", "runtime:reset_all_state", "runtime:visible_cards", "state:save_state"]
used_in: []
```

</Details>
---

<Details markdown="1">
<Summary><sd

#### [`boot_id()`](./flashcards_app/server.py#def&nbspboot_id)

</Summary>
The `boot_id()` function retrieves the unique boot identifier for the application instance.

**Algorithm**:

1. Access the system or application configuration for the boot ID
2. Return the boot ID to the caller

```yaml
component_id: server:boot_id
type: function
file: flashcards_app/server.py
line_start: 20
line_end: 22
tags: []
dependencies: []
used_in: []
```

</Details>
---

<Details markdown="1">
<Summary><sd

#### [`main()`](./flashcards_app/server.py#def&nbspmain)

</Summary>
The `main()` function serves as the entry point for the application, initializing necessary components and starting the application's main loop.

**Algorithm**:

1. Initialize application components and configurations
2. Start the main application loop
3. Handle any startup errors or exceptions
4. Ensure proper shutdown and cleanup of resources

```yaml
component_id: server:main
type: function
file: flashcards_app/server.py
line_start: 96
line_end: 98
tags: []
dependencies: ["state:save_state"]
used_in: []
```

</Details>
---

<font color="red">Agents instructions: do not read the following section.</font>



## Unindexed Components

<font color="green">If you see any components below, copy them manually into the appropriate section above and fill in their manual metadata. component_id and type are proposals. The ID is the snake_case of the code name (CardPosition becomes card_position), with a file prefix on collisions. type is dataclass, class, function or async_function. If you use other values, adjust them when you move the block.

Name collisions: the same file wins first, then the indexed component. Otherwise the name is skipped with a WARNING. Imports are not resolved, so two identically named unindexed functions can be ambiguous.

--check treats a changed section as stale and exits with 1. If you deliberately don't index something, use --ignore NAME (repeatable). --exclude-dir tests skips a folder while scanning, and --scan indexed looks only in files already in the index.

Once you placed the new components into the appropriate sections above, run the `update_index` script again to regenerate the index. The section below is regenerated on each run, from its title line to the end of the file. Don't add your own text or tags below it. They would be overwritten. </font>

**End of file**
