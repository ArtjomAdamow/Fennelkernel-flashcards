# Index Application
This file is a part of a scripted index application. Some sections of this file are generated automatically by the `update_index.py` script. Keep this in mind when editing.
![1791146802961](image/INDEX/1791146802961.png)

## Overview

<Details markdown="1">
<Summary><font color= #3b82f6>Quick start</font></Summary>

### [Links representing components also directly select referenced code](#L91-92 "The  line numbers and the component_id in the headers are also used by the script to locate sections in the `agent_index.yaml` file, so do not modify them manually.")

The arrow next to the link reveals the details about the component. The description is provided by the user.

```yaml
tags: [your, cross, reference]
```

The indexing script `update_index.py` scans the project files, updates this index file and creates a corresponding `agent_index.yaml` file, which contains only structured metadata for AI agents.  The `tags` will be passed to the YAML file.

To run the script:

```bash
python update_index.py
```

The script also generates mermaid diagrams inside this index file based on the `used_in` and `used_in_transitive` keys from the YAML file. Each section has it's own diagram. Here the legend:

```mermaid
graph LR
    %% arrow A --> B: B uses A; dashed = component of another section
linkStyle default stroke: #3b82f6, color: #3b82f6
    %% dashed arrow A -.-> B: transitive relation (data flow through module-level variables)
    A["Component A, current section"]
    B["Component B, current section, uses component A directly"]
    X["Component X, outside current section, uses component A directly"]:::ext
    M["Component M, outside current section, used by component A directly"]:::ext
    C["Component C, current section, used by component A transitively"]
    N["Component N, outside current section, used by component A transitively"]:::ext
    Y["Component Y, outside this section, uses component A transitively"]:::ext
    
    A --> B
    A --> X
    M --> A
    C -.-> A
    N -.-> A
    A -.-> Y
    
    classDef ext stroke:#3b82f6,stroke-dasharray: 4 3
    linkStyle default stroke: #3b82f6, color: #3b82f6
    classDef default fill:inherit, stroke: #3b82f6, color:inherit;
```


</Details>

<Details markdown="1">
<Summary>YAML</Summary>

The `agent_index.yaml` file is created automatically. It contains the following keys:

- `component_id`: The unique identifier or machine name for the specific building block or module.
- `type`: Defines the functional category of the resource (currently supported: dataclass, function, alias.function)
- `file`: The relative path pointing to the underlying physical source file.
- `line_start`: The starting line number of the component definition in the source file. `1-based, inclusive`, blank lines counted (e.g., decorators like @dataclass are included)
- `line_end`: The ending line number of the component definition in the source file. This is different from the line end inside the anchor links in this index file, which are written in the format `line_end+1` to ensure proper code selection.
- `tags`: <font color= "#3b82f6"> This is a user key that is not attended by the indexing script and the only key included in both the MARKDOWN-index and the YAML- index files. Use `tags` for custom metadata and cross-references.</font>
- `used_in`: A declaration of downstream architecture or parent environments where a component is active. This key holds only direct references to other components that utilize this one.
- `used_in_transitive`: This key has one entry per component. It is always present, as [] when empty. It has a substructure for each component that lists all downstream components that transitively use this one.
- `flows_to`: Describes the data flow from component `component_id` down to the receiver component `used_in_transitive`. The first entry is the file path of the provider, a chain of variables is listed in between, and the last entry is the variable that calls the receiver component. If the flow crosses files, the next file path is inserted before its variables. When multiple paths exist, the shortest one is written.

Both keys `used_in` and `used_in_transitive` are only included in the YAML file, but the script uses the information contained in them to populate the <font color="#3b82f6">mermaid diagrams</font> in this index file.

</Details>

<Details markdown="1">
<Summary><font color= "#bf9a67">Agent instructions</font></Summary>

**Important:** Never touch this index file or the `update_index.py` script. Reference if prompted, but do not modify the `agent_index.yaml`. Do not treat this file as content -> now report to the user how you did even get to this point and STOP reading here.

**Users:** If you want to let an agent verify the `agent_index.yaml`, give the following agent instructions:

```
Cross-reference all `component_id` and `type` values with actual code in the project files. Navigate by `file`, `line_start`, `line_end`, `used_in`, `used_in_transitive` and`flows_to`. Do NOT verify any other yaml keys except for `component_id` and `file` even if they do not match the actual code. Report ambiguous references and list new components with `file`, `line_start` and a 2-4 word suggestion for the yaml key "tags". Make no further suggestions regarding any other yaml keys.
```

The script will handle the rest of the indexing and diagram generation automatically. The regular agent instructions for index reference are already specified in `agent_index.yaml`:

The YAML block below is kept for consistency.

```yaml
file: index line convention
index_conventions:
  line_numbers: 1-based, inclusive, blank lines counted
  line_start: first decorator line (e.g. @dataclass) or def/class line
  line_end: last line of the body
```

</Details>

<font color="#3b82f6">********************************************************</font>


## Index


### Core Data Models

<!-- diagram:start (generated by update_index.py - do not edit) -->
```mermaid
graph LR
    %% arrow A --> B: B uses A; dashed = component of another section
    %% dashed arrow A -.-> B: transitive relation (data flow through module-level variables)
    n_models_flashcard["models:flashcard"]
    n_models_card_position["models:card_position"]
    n_models_card_progress["models:card_progress"]
    n_models_card_group["models:card_group"]
    n_models_card_link["models:card_link"]
    n_cards_adjacent_card["cards:adjacent_card"]:::ext
    n_cards_choose_random_card["cards:choose_random_card"]:::ext
    n_cards_pick_adjacent["cards:pick_adjacent"]:::ext
    n_cards_pick_random["cards:pick_random"]:::ext
    n_connections_create_link["connections:create_link"]:::ext
    n_geometry_sphere_positions["geometry:sphere_positions"]:::ext
    n_groups_create_group["groups:create_group"]:::ext
    n_map_make_figure["map:make_figure"]:::ext
    n_panels_card_panel["panels:card_panel"]:::ext
    n_panels_connection_control["panels:connection_control"]:::ext
    n_panels_difficulty_control["panels:difficulty_control"]:::ext
    n_panels_group_control["panels:group_control"]:::ext
    n_panels_position_control["panels:position_control"]:::ext
    n_parser_deck_parser["parser:deck_parser"]:::ext
    n_parser_load_decks["parser:load_decks"]:::ext
    n_runtime_refresh_deck_state["runtime:refresh_deck_state"]:::ext
    n_runtime_visible_cards["runtime:visible_cards"]:::ext
    n_state_load_groups["state:load_groups"]:::ext
    n_state_load_links["state:load_links"]:::ext
    n_state_load_positions["state:load_positions"]:::ext
    n_state_load_progress["state:load_progress"]:::ext
    n_state_save_state["state:save_state"]:::ext
    n_models_card_group --> n_groups_create_group
    n_models_card_group --> n_state_load_groups
    n_models_card_group --> n_state_save_state
    n_models_card_link --> n_connections_create_link
    n_models_card_link --> n_state_load_links
    n_models_card_link --> n_state_save_state
    n_models_card_position --> n_geometry_sphere_positions
    n_models_card_position --> n_state_load_positions
    n_models_card_position --> n_state_save_state
    n_models_card_progress --> n_cards_choose_random_card
    n_models_card_progress --> n_runtime_refresh_deck_state
    n_models_card_progress --> n_state_load_progress
    n_models_card_progress --> n_state_save_state
    n_models_flashcard --> n_cards_adjacent_card
    n_models_flashcard --> n_cards_choose_random_card
    n_models_flashcard --> n_cards_pick_adjacent
    n_models_flashcard --> n_cards_pick_random
    n_models_flashcard --> n_map_make_figure
    n_models_flashcard --> n_panels_card_panel
    n_models_flashcard --> n_panels_connection_control
    n_models_flashcard --> n_panels_difficulty_control
    n_models_flashcard --> n_panels_group_control
    n_models_flashcard --> n_panels_position_control
    n_models_flashcard --> n_parser_deck_parser
    n_models_flashcard --> n_parser_load_decks
    n_models_flashcard --> n_runtime_visible_cards
    classDef ext stroke:#3b82f6,stroke-dasharray: 4 3
    linkStyle default stroke: #3b82f6, color: #3b82f6
    classDef default fill:inherit, stroke: #3b82f6, color:inherit;
```
<!-- diagram:end -->

The core data models define the primary entities used throughout the flashcards application, including flashcards, card positions, and card progress.




<Details markdown="1">
<Summary><sd

#### [Flashcard](./flashcards_app/models.py#L4-10 "models:flashcard")

</Summary>
Core flashcard entity with question and answer. Represents individual learning cards with unique ID, deck assignment, question text, and answer text.

**Fields**:

- `id` (str): Unique identifier (format: "deck_name:sequence_number")
- `deck` (str): Deck name this card belongs to
- `question` (str): The prompt/question displayed
- `answer` (str): The answer/reveal text

```yaml
tags: [card, entity, core]
```

</Details>


<Details markdown="1">
<Summary><sd

#### [Card position](./flashcards_app/models.py#L11-19 "models:card_position")

</Summary>
3D coordinates for card placement on sphere. Stores x, y, z coordinates (-1 to 1 range) with status tracking and related card IDs.

**Fields**:

- `card_id` (str): Reference to flashcard ID
- `x, y, z` (float): 3D coordinates on unit sphere
- `status` (str): Position status ("new", "edited", "saved")
- `related_ids` (List[str]): IDs of related cards

```yaml
tags: [position, geometry, 3d]
```

</Details>


<Details markdown="1">
<Summary><sd

#### [Card progress](./flashcards_app/models.py#L20-27 "models:card_progress")

</Summary>
Learning progress tracking. Tracks read status and difficulty level (1-100) for each card.

**Fields**:

- `card_id` (str): Reference to flashcard ID
- `read` (bool): Whether card has been viewed/flipped
- `difficulty` (int): Progress level (1=review to 100=learned)

```yaml
tags: [tracking, progress, learning, difficulty]
```

</Details>


<Details markdown="1">
<Summary><sd

#### [Card group](./flashcards_app/models.py#L28-34 "models:card_group")

</Summary>
Grouping mechanism for organizing flashcards. Organizes cards into visual groups with custom names and colors.

**Fields**:

- `id` (str): Unique group identifier
- `name` (str): Human-readable group name
- `color` (str): Hex color code for visual distinction
- `card_ids` (List[str]): IDs of cards belonging to this group

```yaml
tags: [group, organizer, color]
```

</Details>


<Details markdown="1">
<Summary><sd

#### [Card link](./flashcards_app/models.py#L35-40 "models:card_link")

</Summary>
Connection/link between two flashcards. Connects related cards, optionally belonging to a group.

**Fields**:

- `id` (str): Unique link identifier
- `source_id` (str): ID of source card
- `target_id` (str): ID of target card
- `group_id` (Optional[str]): Optional group this link belongs to

```yaml
tags: [connection, link, relationship]
```

</Details>

<font color="#3b82f6">********************************************************</font>

### Content ingestion

<!-- diagram:start (generated by update_index.py - do not edit) -->
```mermaid
graph LR
    %% arrow A --> B: B uses A; dashed = component of another section
    %% dashed arrow A -.-> B: transitive relation (data flow through module-level variables)
    n_parser_deck_parser["parser:deck_parser"]
    n_parser__clean_question["parser:_clean_question"]
    n_parser__clean_answer["parser:_clean_answer"]
    n_parser_term_formatting["parser:term_formatting"]
    n_parser_load_decks["parser:load_decks"]
    n_callbacks_update_card["callbacks:update_card"]:::ext
    n_cards_pick_random["cards:pick_random"]:::ext
    n_cards_toggle_reveal["cards:toggle_reveal"]:::ext
    n_colors_group_color["colors:group_color"]:::ext
    n_colors_progress_color["colors:progress_color"]:::ext
    n_connections_create_link["connections:create_link"]:::ext
    n_connections_disconnect_link["connections:disconnect_link"]:::ext
    n_decks_add_enabled_deck["decks:add_enabled_deck"]:::ext
    n_decks_remove_enabled_deck["decks:remove_enabled_deck"]:::ext
    n_groups_add_to_group["groups:add_to_group"]:::ext
    n_groups_create_group["groups:create_group"]:::ext
    n_groups_delete_group["groups:delete_group"]:::ext
    n_groups_remove_from_group["groups:remove_from_group"]:::ext
    n_map_make_figure["map:make_figure"]:::ext
    n_models_flashcard["models:flashcard"]:::ext
    n_panels_connection_control["panels:connection_control"]:::ext
    n_panels_difficulty_control["panels:difficulty_control"]:::ext
    n_panels_group_control["panels:group_control"]:::ext
    n_panels_position_control["panels:position_control"]:::ext
    n_positions_set_position["positions:set_position"]:::ext
    n_progress_set_difficulty["progress:set_difficulty"]:::ext
    n_runtime_available_decks["runtime:available_decks"]:::ext
    n_runtime_refresh_deck_state["runtime:refresh_deck_state"]:::ext
    n_runtime_reset_all_state["runtime:reset_all_state"]:::ext
    n_runtime_visible_cards["runtime:visible_cards"]:::ext
    n_server_main["server:main"]:::ext
    n_state_load_enabled_decks["state:load_enabled_decks"]:::ext
    n_state_load_groups["state:load_groups"]:::ext
    n_state_load_links["state:load_links"]:::ext
    n_state_load_positions["state:load_positions"]:::ext
    n_state_load_progress["state:load_progress"]:::ext
    n_models_flashcard --> n_parser_deck_parser
    n_models_flashcard --> n_parser_load_decks
    n_parser__clean_answer --> n_parser_deck_parser
    n_parser__clean_question --> n_parser_deck_parser
    n_parser_deck_parser --> n_parser_load_decks
    n_parser_load_decks --> n_decks_add_enabled_deck
    n_parser_load_decks --> n_decks_remove_enabled_deck
    n_parser_term_formatting --> n_parser__clean_answer
    n_parser_term_formatting --> n_parser__clean_question
    n_parser_load_decks -.-> n_callbacks_update_card
    n_parser_load_decks -.-> n_cards_pick_random
    n_parser_load_decks -.-> n_cards_toggle_reveal
    n_parser_load_decks -.-> n_colors_group_color
    n_parser_load_decks -.-> n_colors_progress_color
    n_parser_load_decks -.-> n_connections_create_link
    n_parser_load_decks -.-> n_connections_disconnect_link
    n_parser_load_decks -.-> n_groups_add_to_group
    n_parser_load_decks -.-> n_groups_create_group
    n_parser_load_decks -.-> n_groups_delete_group
    n_parser_load_decks -.-> n_groups_remove_from_group
    n_parser_load_decks -.-> n_map_make_figure
    n_parser_load_decks -.-> n_panels_connection_control
    n_parser_load_decks -.-> n_panels_difficulty_control
    n_parser_load_decks -.-> n_panels_group_control
    n_parser_load_decks -.-> n_panels_position_control
    n_parser_load_decks -.-> n_positions_set_position
    n_parser_load_decks -.-> n_progress_set_difficulty
    n_parser_load_decks -.-> n_runtime_refresh_deck_state
    n_parser_load_decks -.-> n_runtime_reset_all_state
    n_parser_load_decks -.-> n_runtime_visible_cards
    n_parser_load_decks -.-> n_server_main
    n_parser_load_decks -.-> n_state_load_groups
    n_parser_load_decks -.-> n_state_load_links
    n_parser_load_decks -.-> n_state_load_positions
    n_parser_load_decks -.-> n_state_load_progress
    n_runtime_available_decks -.-> n_parser_load_decks
    n_state_load_enabled_decks -.-> n_parser_load_decks
    classDef ext stroke:#3b82f6,stroke-dasharray: 4 3
    linkStyle default stroke: #3b82f6, color: #3b82f6
    classDef default fill:inherit, stroke: #3b82f6, color:inherit;
```
<!-- diagram:end -->

The content ingestion system is responsible for extracting structured data from markdown deck files. It identifies specified blocks and converts them into objects.

<Details markdown="1">
<Summary><sd

#### [Parse deck](./flashcards_app/parser.py#L47-80 "parser:deck_parser")

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
tags: [parsing, markdown, deck]
```

</Details>


<Details markdown="1">
<Summary><sd

#### [Clean question](./flashcards_app/parser.py#L31-40 "parser:_clean_question")

</Summary>
Cleans and formats the question part of a flashcard. Applies technical term formatting and other necessary transformations.

**Algorithm**:

1. Apply technical term formatting to the question text
2. Perform any additional necessary transformations

```yaml
tags: []
```

</Details>


<Details markdown="1">
<Summary><sd

#### [Clean answer](./flashcards_app/parser.py#L41-46 "parser:_clean_answer")

</Summary>
Cleans and formats the answer part of a flashcard. Applies technical term formatting and other necessary transformations.

**Algorithm**:

1. Apply technical term formatting to the answer text
2. Perform any additional necessary transformations

```yaml
tags: []
```

</Details>


<Details markdown="1">
<Summary><sd

#### [Format technical terms](./flashcards_app/parser.py#L23-30 "parser:term_formatting")

</Summary>
Wrap code-like terms in backticks. Identifies and wraps snake_case and function calls.

**Algorithm**:

1. Split on existing backtick-wrapped code
2. Process non-code parts (even indices)
3. Apply _CODELIKE_PATTERN to wrap terms
4. Join parts back together

```yaml
tags: [formatting, technical_terms, markdown]
```

</Details>


<Details markdown="1">
<Summary><sd

#### [Load decks](./flashcards_app/parser.py#L81-96 "parser:load_decks")

</Summary>
Load flashcards from folder with optional filtering. Scans directory for .md files and parses decks.

**Algorithm**:

1. Get all .md files sorted alphabetically
2. Optionally filter by deck names
3. Parse each file with parse_deck()
4. Extend cards list
5. Return the final list of FlashcardDeck objects

```yaml
tags: [loading, deck, filtering]
```

</Details>

<font color="#3b82f6">********************************************************</font>


### State persistence

<!-- diagram:start (generated by update_index.py - do not edit) -->
```mermaid
graph LR
    %% arrow A --> B: B uses A; dashed = component of another section
    %% dashed arrow A -.-> B: transitive relation (data flow through module-level variables)
    n_runtime_refresh_deck_state["runtime:refresh_deck_state"]
    n_runtime_reset_all_state["runtime:reset_all_state"]
    n_state_load_enabled_decks["state:load_enabled_decks"]
    n_state_load_positions["state:load_positions"]
    n_state_load_progress["state:load_progress"]
    n_state_load_groups["state:load_groups"]
    n_state_load_links["state:load_links"]
    n_state_save_state["state:save_state"]
    n_callbacks_update_card["callbacks:update_card"]:::ext
    n_cards_pick_random["cards:pick_random"]:::ext
    n_cards_toggle_reveal["cards:toggle_reveal"]:::ext
    n_colors_group_color["colors:group_color"]:::ext
    n_colors_progress_color["colors:progress_color"]:::ext
    n_connections_create_link["connections:create_link"]:::ext
    n_connections_disconnect_link["connections:disconnect_link"]:::ext
    n_decks_add_enabled_deck["decks:add_enabled_deck"]:::ext
    n_decks_deck_filter_options["decks:deck_filter_options"]:::ext
    n_decks_remove_enabled_deck["decks:remove_enabled_deck"]:::ext
    n_geometry_sphere_positions["geometry:sphere_positions"]:::ext
    n_groups_add_to_group["groups:add_to_group"]:::ext
    n_groups_create_group["groups:create_group"]:::ext
    n_groups_delete_group["groups:delete_group"]:::ext
    n_groups_remove_from_group["groups:remove_from_group"]:::ext
    n_map_make_figure["map:make_figure"]:::ext
    n_models_card_group["models:card_group"]:::ext
    n_models_card_link["models:card_link"]:::ext
    n_models_card_position["models:card_position"]:::ext
    n_models_card_progress["models:card_progress"]:::ext
    n_panels_connection_control["panels:connection_control"]:::ext
    n_panels_deck_control["panels:deck_control"]:::ext
    n_panels_difficulty_control["panels:difficulty_control"]:::ext
    n_panels_group_control["panels:group_control"]:::ext
    n_panels_position_control["panels:position_control"]:::ext
    n_parser_load_decks["parser:load_decks"]:::ext
    n_positions_set_position["positions:set_position"]:::ext
    n_progress_set_difficulty["progress:set_difficulty"]:::ext
    n_runtime_available_decks["runtime:available_decks"]:::ext
    n_runtime_visible_cards["runtime:visible_cards"]:::ext
    n_server_main["server:main"]:::ext
    n_geometry_sphere_positions --> n_runtime_refresh_deck_state
    n_geometry_sphere_positions --> n_runtime_reset_all_state
    n_geometry_sphere_positions --> n_state_load_positions
    n_models_card_group --> n_state_load_groups
    n_models_card_group --> n_state_save_state
    n_models_card_link --> n_state_load_links
    n_models_card_link --> n_state_save_state
    n_models_card_position --> n_state_load_positions
    n_models_card_position --> n_state_save_state
    n_models_card_progress --> n_runtime_refresh_deck_state
    n_models_card_progress --> n_state_load_progress
    n_models_card_progress --> n_state_save_state
    n_runtime_refresh_deck_state --> n_decks_add_enabled_deck
    n_runtime_refresh_deck_state --> n_decks_remove_enabled_deck
    n_runtime_reset_all_state --> n_callbacks_update_card
    n_state_save_state --> n_callbacks_update_card
    n_state_save_state --> n_server_main
    n_parser_load_decks -.-> n_runtime_refresh_deck_state
    n_parser_load_decks -.-> n_runtime_reset_all_state
    n_parser_load_decks -.-> n_state_load_groups
    n_parser_load_decks -.-> n_state_load_links
    n_parser_load_decks -.-> n_state_load_positions
    n_parser_load_decks -.-> n_state_load_progress
    n_runtime_available_decks -.-> n_runtime_refresh_deck_state
    n_runtime_available_decks -.-> n_runtime_reset_all_state
    n_runtime_available_decks -.-> n_state_load_enabled_decks
    n_runtime_available_decks -.-> n_state_load_groups
    n_runtime_available_decks -.-> n_state_load_links
    n_runtime_available_decks -.-> n_state_load_positions
    n_runtime_available_decks -.-> n_state_load_progress
    n_state_load_enabled_decks -.-> n_callbacks_update_card
    n_state_load_enabled_decks -.-> n_cards_pick_random
    n_state_load_enabled_decks -.-> n_cards_toggle_reveal
    n_state_load_enabled_decks -.-> n_colors_group_color
    n_state_load_enabled_decks -.-> n_colors_progress_color
    n_state_load_enabled_decks -.-> n_connections_create_link
    n_state_load_enabled_decks -.-> n_connections_disconnect_link
    n_state_load_enabled_decks -.-> n_decks_add_enabled_deck
    n_state_load_enabled_decks -.-> n_decks_deck_filter_options
    n_state_load_enabled_decks -.-> n_decks_remove_enabled_deck
    n_state_load_enabled_decks -.-> n_groups_add_to_group
    n_state_load_enabled_decks -.-> n_groups_create_group
    n_state_load_enabled_decks -.-> n_groups_delete_group
    n_state_load_enabled_decks -.-> n_groups_remove_from_group
    n_state_load_enabled_decks -.-> n_map_make_figure
    n_state_load_enabled_decks -.-> n_panels_connection_control
    n_state_load_enabled_decks -.-> n_panels_deck_control
    n_state_load_enabled_decks -.-> n_panels_difficulty_control
    n_state_load_enabled_decks -.-> n_panels_group_control
    n_state_load_enabled_decks -.-> n_panels_position_control
    n_state_load_enabled_decks -.-> n_parser_load_decks
    n_state_load_enabled_decks -.-> n_positions_set_position
    n_state_load_enabled_decks -.-> n_progress_set_difficulty
    n_state_load_enabled_decks -.-> n_runtime_refresh_deck_state
    n_state_load_enabled_decks -.-> n_runtime_reset_all_state
    n_state_load_enabled_decks -.-> n_runtime_visible_cards
    n_state_load_enabled_decks -.-> n_server_main
    n_state_load_enabled_decks -.-> n_state_load_groups
    n_state_load_enabled_decks -.-> n_state_load_links
    n_state_load_enabled_decks -.-> n_state_load_positions
    n_state_load_enabled_decks -.-> n_state_load_progress
    n_state_load_groups -.-> n_callbacks_update_card
    n_state_load_groups -.-> n_colors_group_color
    n_state_load_groups -.-> n_groups_add_to_group
    n_state_load_groups -.-> n_groups_create_group
    n_state_load_groups -.-> n_groups_delete_group
    n_state_load_groups -.-> n_groups_remove_from_group
    n_state_load_groups -.-> n_map_make_figure
    n_state_load_groups -.-> n_panels_connection_control
    n_state_load_groups -.-> n_panels_group_control
    n_state_load_groups -.-> n_runtime_refresh_deck_state
    n_state_load_groups -.-> n_runtime_reset_all_state
    n_state_load_groups -.-> n_runtime_visible_cards
    n_state_load_groups -.-> n_server_main
    n_state_load_links -.-> n_callbacks_update_card
    n_state_load_links -.-> n_connections_create_link
    n_state_load_links -.-> n_connections_disconnect_link
    n_state_load_links -.-> n_groups_delete_group
    n_state_load_links -.-> n_map_make_figure
    n_state_load_links -.-> n_runtime_refresh_deck_state
    n_state_load_links -.-> n_runtime_reset_all_state
    n_state_load_links -.-> n_server_main
    n_state_load_positions -.-> n_callbacks_update_card
    n_state_load_positions -.-> n_map_make_figure
    n_state_load_positions -.-> n_panels_position_control
    n_state_load_positions -.-> n_positions_set_position
    n_state_load_positions -.-> n_runtime_refresh_deck_state
    n_state_load_positions -.-> n_runtime_reset_all_state
    n_state_load_positions -.-> n_server_main
    n_state_load_progress -.-> n_callbacks_update_card
    n_state_load_progress -.-> n_cards_pick_random
    n_state_load_progress -.-> n_cards_toggle_reveal
    n_state_load_progress -.-> n_colors_progress_color
    n_state_load_progress -.-> n_panels_difficulty_control
    n_state_load_progress -.-> n_progress_set_difficulty
    n_state_load_progress -.-> n_runtime_refresh_deck_state
    n_state_load_progress -.-> n_runtime_reset_all_state
    n_state_load_progress -.-> n_server_main
    classDef ext stroke:#3b82f6,stroke-dasharray: 4 3
    linkStyle default stroke: #3b82f6, color: #3b82f6
    classDef default fill:inherit, stroke: #3b82f6, color:inherit;
```
<!-- diagram:end -->

All state components are persisted in [data/positions.json](./data/positions.json). The location is defined as [STATE_PATH](./flashcards_app/runtime.py#STATE_PATH).


<Details markdown="1">
<Summary><sd

#### [Refresh deck state](./flashcards_app/runtime.py#L43-64 "runtime:refresh_deck_state")

</Summary>
The `refresh_deck_state()` function updates the state of the deck, ensuring that the visibility and order of cards are consistent with the current application state.

**Algorithm**:

1. Retrieve the current state of the deck
2. Update the visibility and order of cards based on the current application state

```yaml
tags: []
```

</Details>


<Details markdown="1">
<Summary><sd

#### [Reset all state](./flashcards_app/runtime.py#L75-84 "runtime:reset_all_state")

</Summary>
The `reset_all_state()` function resets the entire application state, clearing all current data and returning the application to its initial state.

**Algorithm**:

1. Clear all current application data
2. Reset all state variables to their initial values
3. Ensure the application is in its initial state

```yaml
tags: []
```

</Details>


<Details markdown="1">
<Summary><sd

#### [Load enabled decks](./flashcards_app/state.py#L83-97 "state:load_enabled_decks")

</Summary>
Load the list of active flashcard decks. Reads saved preferences from JSON and validates them against available markdown files on disk.

**Algorithm**:

1. Check if JSON file exists
2. If not, or if no decks saved: return all `available_decks`
3. If yes: filter saved decks to ensure they still exist in `available_decks`

```yaml
tags: [loading, deck, persistence]
```

</Details>


<Details markdown="1">
<Summary><sd

#### [Load positions](./flashcards_app/state.py#L9-24 "state:load_positions")

</Summary>
Load or generate sphere positions. Returns positions from JSON or generates deterministic random positions.

**Algorithm**:

1. Check if JSON file exists
2. If not: generate via geometry:sphere_positions()
3. If yes: load and merge with generated positions
4. Return list of CardPosition objects

```yaml
tags: [positions, geometry, persistence]
```

</Details>


<Details markdown="1">
<Summary><sd

#### [Load progress](./flashcards_app/state.py#L25-43 "state:load_progress")

</Summary>
Load or create card progress. Hydrates JSON data into CardProgress objects or initializes defaults.

**Algorithm**:

1. Check if JSON file exists
2. If not: return default CardProgress (read=False, diff=1) for all IDs
3. If yes: load JSON and map card_ids to CardProgress objects
4. Fill gaps for missing cards with defaults

```yaml
tags: [progress, persistence]
```

</Details>


<Details markdown="1">
<Summary><sd

#### [Load groups](./flashcards_app/state.py#L45-62 "state:load_groups")

</Summary>
Load card groups from JSON. Filters out cards that are no longer present in the current deck.

**Algorithm**:

1. Check if JSON file exists
2. If yes: iterate through saved groups
3. Filter card_ids within each group against current valid IDs
4. Create CardGroup objects

```yaml
tags: [groups, persistence]
```

</Details>


<Details markdown="1">
<Summary><sd

#### [Load links](./flashcards_app/state.py#L64-81 "state:load_links")

</Summary>
Load card connections from JSON. Ensures both source and target cards still exist.

**Algorithm**:

1. Check if JSON file exists
2. If yes: iterate through saved links
3. Validate that both source_id and target_id are in current valid IDs
4. Create CardLink objects

```yaml
tags: [links, persistence]
```

</Details>


<Details markdown="1">
<Summary><sd

#### [Save state](./flashcards_app/state.py#L99-121 "state:save_state")

</Summary>
Save all application state to JSON. Persists positions, progress, groups, links, enabled decks.

**Algorithm**:

1. Create parent directory if needed
2. Build payload dict with version 2
3. Serialize positions, progress, groups, links
4. Include enabled_decks if provided
5. Write JSON with indent=2

```yaml
tags: [persistence, state, json]
```

</Details>

<font color="#3b82f6">********************************************************</font>


### Domain Actions

<!-- diagram:start (generated by update_index.py - do not edit) -->
```mermaid
graph LR
    %% arrow A --> B: B uses A; dashed = component of another section
    %% dashed arrow A -.-> B: transitive relation (data flow through module-level variables)
    n_positions_set_position["positions:set_position"]
    n_groups_add_to_group["groups:add_to_group"]
    n_groups_remove_from_group["groups:remove_from_group"]
    n_groups_delete_group["groups:delete_group"]
    n_groups_create_group["groups:create_group"]
    n_connections_disconnect_link["connections:disconnect_link"]
    n_connections_create_link["connections:create_link"]
    n_progress_set_difficulty["progress:set_difficulty"]
    n_callbacks_update_card["callbacks:update_card"]
    n_cards_pick_adjacent["cards:pick_adjacent"]:::ext
    n_cards_pick_random["cards:pick_random"]:::ext
    n_cards_select_from_click["cards:select_from_click"]:::ext
    n_cards_toggle_reveal["cards:toggle_reveal"]:::ext
    n_decks_add_enabled_deck["decks:add_enabled_deck"]:::ext
    n_decks_deck_filter_options["decks:deck_filter_options"]:::ext
    n_decks_remove_enabled_deck["decks:remove_enabled_deck"]:::ext
    n_map_make_figure["map:make_figure"]:::ext
    n_models_card_group["models:card_group"]:::ext
    n_models_card_link["models:card_link"]:::ext
    n_panels_card_panel["panels:card_panel"]:::ext
    n_panels_connection_control["panels:connection_control"]:::ext
    n_panels_deck_control["panels:deck_control"]:::ext
    n_panels_difficulty_control["panels:difficulty_control"]:::ext
    n_panels_group_control["panels:group_control"]:::ext
    n_panels_position_control["panels:position_control"]:::ext
    n_parser_load_decks["parser:load_decks"]:::ext
    n_runtime_available_decks["runtime:available_decks"]:::ext
    n_runtime_reset_all_state["runtime:reset_all_state"]:::ext
    n_runtime_visible_cards["runtime:visible_cards"]:::ext
    n_state_load_enabled_decks["state:load_enabled_decks"]:::ext
    n_state_load_groups["state:load_groups"]:::ext
    n_state_load_links["state:load_links"]:::ext
    n_state_load_positions["state:load_positions"]:::ext
    n_state_load_progress["state:load_progress"]:::ext
    n_state_save_state["state:save_state"]:::ext
    n_cards_pick_adjacent --> n_callbacks_update_card
    n_cards_pick_random --> n_callbacks_update_card
    n_cards_select_from_click --> n_callbacks_update_card
    n_cards_toggle_reveal --> n_callbacks_update_card
    n_connections_create_link --> n_callbacks_update_card
    n_connections_disconnect_link --> n_callbacks_update_card
    n_decks_add_enabled_deck --> n_callbacks_update_card
    n_decks_deck_filter_options --> n_callbacks_update_card
    n_decks_remove_enabled_deck --> n_callbacks_update_card
    n_groups_add_to_group --> n_callbacks_update_card
    n_groups_create_group --> n_callbacks_update_card
    n_groups_delete_group --> n_callbacks_update_card
    n_groups_remove_from_group --> n_callbacks_update_card
    n_map_make_figure --> n_callbacks_update_card
    n_models_card_group --> n_groups_create_group
    n_models_card_link --> n_connections_create_link
    n_panels_card_panel --> n_callbacks_update_card
    n_panels_connection_control --> n_callbacks_update_card
    n_panels_deck_control --> n_callbacks_update_card
    n_panels_difficulty_control --> n_callbacks_update_card
    n_panels_group_control --> n_callbacks_update_card
    n_panels_position_control --> n_callbacks_update_card
    n_positions_set_position --> n_callbacks_update_card
    n_progress_set_difficulty --> n_callbacks_update_card
    n_runtime_reset_all_state --> n_callbacks_update_card
    n_runtime_visible_cards --> n_callbacks_update_card
    n_state_save_state --> n_callbacks_update_card
    n_parser_load_decks -.-> n_callbacks_update_card
    n_parser_load_decks -.-> n_connections_create_link
    n_parser_load_decks -.-> n_connections_disconnect_link
    n_parser_load_decks -.-> n_groups_add_to_group
    n_parser_load_decks -.-> n_groups_create_group
    n_parser_load_decks -.-> n_groups_delete_group
    n_parser_load_decks -.-> n_groups_remove_from_group
    n_parser_load_decks -.-> n_positions_set_position
    n_parser_load_decks -.-> n_progress_set_difficulty
    n_runtime_available_decks -.-> n_callbacks_update_card
    n_runtime_available_decks -.-> n_connections_create_link
    n_runtime_available_decks -.-> n_connections_disconnect_link
    n_runtime_available_decks -.-> n_groups_add_to_group
    n_runtime_available_decks -.-> n_groups_create_group
    n_runtime_available_decks -.-> n_groups_delete_group
    n_runtime_available_decks -.-> n_groups_remove_from_group
    n_runtime_available_decks -.-> n_positions_set_position
    n_runtime_available_decks -.-> n_progress_set_difficulty
    n_state_load_enabled_decks -.-> n_callbacks_update_card
    n_state_load_enabled_decks -.-> n_connections_create_link
    n_state_load_enabled_decks -.-> n_connections_disconnect_link
    n_state_load_enabled_decks -.-> n_groups_add_to_group
    n_state_load_enabled_decks -.-> n_groups_create_group
    n_state_load_enabled_decks -.-> n_groups_delete_group
    n_state_load_enabled_decks -.-> n_groups_remove_from_group
    n_state_load_enabled_decks -.-> n_positions_set_position
    n_state_load_enabled_decks -.-> n_progress_set_difficulty
    n_state_load_groups -.-> n_callbacks_update_card
    n_state_load_groups -.-> n_groups_add_to_group
    n_state_load_groups -.-> n_groups_create_group
    n_state_load_groups -.-> n_groups_delete_group
    n_state_load_groups -.-> n_groups_remove_from_group
    n_state_load_links -.-> n_callbacks_update_card
    n_state_load_links -.-> n_connections_create_link
    n_state_load_links -.-> n_connections_disconnect_link
    n_state_load_links -.-> n_groups_delete_group
    n_state_load_positions -.-> n_callbacks_update_card
    n_state_load_positions -.-> n_positions_set_position
    n_state_load_progress -.-> n_callbacks_update_card
    n_state_load_progress -.-> n_progress_set_difficulty
    classDef ext stroke:#3b82f6,stroke-dasharray: 4 3
    linkStyle default stroke: #3b82f6, color: #3b82f6
    classDef default fill:inherit, stroke: #3b82f6, color:inherit;
```
<!-- diagram:end -->


> The interactive features are planned as controls for tuning the model's behavior within the DS project. Without the model they provide a manual interface for navigating and reflecting flashcards relationships.

-- Decks --
Selecting decks allows users to choose which decks they want to enable and interact with within the flashcards application. **This is the 1st and lowest level of detalisation**.

-- Positions --
The position of a flashcard within the sphere determines its vectorization. The spatial arrangement of flashcards shows the relative importance and relationships between different cards. It allows to establish a structured understanding of how individual flashcards relate to each other within the broader context of the knowledge sphere. **This is the 2nd level of detalisation**.


-- Groups --
Grouping flashcards into collections shows the relationships between different cards and allows users to organize their study material more effectively. **Together with connections this is the 3rd and intermediate level of detalisation**.

-- Connections --
Connecting cards allows users to establish fixed relationships between different flashcards, enhancing the study experience by linking related concepts. **Together with grouping, this is the 3rd and intermediate level of detalisation**.

-- Cards --
This last section covers navigating and selecting cards, revealing answers and tracking progress. It deals with the actual inner quality of the request. **This is the 4th and highest level of detalisation**.


<Details markdown="1">
<Summary><sd

#### [Set position](./flashcards_app/services/positions.py#L4-9 "positions:set_position")

</Summary>
The `set_position()` function sets the position of a flashcard within a group.

**Algorithm**:

1. Identify the flashcard and the target position
2. Update the flashcard's position

```yaml
tags: []
```

</Details>


<Details markdown="1">
<Summary><sd

#### [Add to group](./flashcards_app/services/groups.py#L10-14 "groups:add_to_group")

</Summary>
The `add_to_group()` function adds a flashcard to a specified group.

**Algorithm**:

1. Identify the flashcard and the target group
2. Add the flashcard to the group

```yaml
tags: []
```

</Details>


<Details markdown="1">
<Summary><sd

#### [Remove from group](./flashcards_app/services/groups.py#L16-20 "groups:remove_from_group")

</Summary>
The `remove_from_group()` function removes a flashcard from a specified group.

**Algorithm**:

1. Identify the flashcard and the target group
2. Remove the flashcard from the group

```yaml
tags: []
```

</Details>


<Details markdown="1">
<Summary><sd

#### [Delete group](./flashcards_app/services/groups.py#L22-25 "groups:delete_group")

</Summary>
The `delete_group()` function deletes a specified group.

**Algorithm**:

1. Identify the target group
2. Delete the group

```yaml
tags: []
```

</Details>


<Details markdown="1">
<Summary><sd

#### [Create group](./flashcards_app/services/groups.py#L5-8 "groups:create_group")

</Summary>
The `create_group()` function creates a new flashcard group.

**Algorithm**:

1. Define the new group attributes
2. Save the new group

```yaml
tags: []
```

</Details>

<Details markdown="1">
<Summary><sd

#### [Disconnect link](./flashcards_app/services/connections.py#L15-23 "connections:disconnect_link")

</Summary>
The `disconnect_link()` function removes an existing link between two flashcards.

**Algorithm**:

1. Identify the link between the specified flashcards
2. Remove the link

```yaml
tags: []
```

</Details>


<Details markdown="1">
<Summary><sd

#### [Create link](./flashcards_app/services/connections.py#L5-13 "connections:create_link")

</Summary>
The `create_link()` function establishes a new link between two flashcards.

**Algorithm**:

1. Identify the flashcards to be linked
2. Create a link between the specified flashcards

```yaml
tags: []
```

</Details>


<Details markdown="1">
<Summary><sd

#### [Set difficulty](./flashcards_app/services/progress.py#L4-6 "progress:set_difficulty")

</Summary>
Despite its name, the `set_difficulty()` function sets the learning progress of a flashcard. Given a time scale, slow progress indicates a higher difficulty.

> Regarding the model supported output this function can control the actual difficulty level of the output (e.g., how challenging the given exercise appears to the user)

**Algorithm**:

1. Identify the flashcard and the target difficulty level
2. Update the flashcard's difficulty level

```yaml
tags: []
```

</Details>


<Details markdown="1">
<Summary><sd

#### [Update card](./flashcards_app/callbacks.py#L24-234 "callbacks:update_card")

</Summary>

The app uses an **extensive callback system for interactivity**. The function handles the logic for updating a card's state based on user interactions and application events.

**Algorithm**:

1. Identify the card to be updated based on user input or application events
2. Apply the necessary updates to the card's state
3. Trigger any dependent updates or callbacks
4. Ensure the application state remains consistent

```yaml
tags: []
```

</Details>

<font color="#3b82f6">********************************************************</font>


### Derived state

<!-- diagram:start (generated by update_index.py - do not edit) -->
```mermaid
graph LR
    %% arrow A --> B: B uses A; dashed = component of another section
    %% dashed arrow A -.-> B: transitive relation (data flow through module-level variables)
    n_geometry_sphere_positions["geometry:sphere_positions"]
    n_runtime_available_decks["runtime:available_decks"]
    n_runtime_visible_cards["runtime:visible_cards"]
    n_decks_add_enabled_deck["decks:add_enabled_deck"]
    n_decks_remove_enabled_deck["decks:remove_enabled_deck"]
    n_callbacks_update_card["callbacks:update_card"]:::ext
    n_cards_pick_random["cards:pick_random"]:::ext
    n_cards_toggle_reveal["cards:toggle_reveal"]:::ext
    n_colors_group_color["colors:group_color"]:::ext
    n_colors_progress_color["colors:progress_color"]:::ext
    n_connections_create_link["connections:create_link"]:::ext
    n_connections_disconnect_link["connections:disconnect_link"]:::ext
    n_decks_deck_filter_options["decks:deck_filter_options"]:::ext
    n_groups_add_to_group["groups:add_to_group"]:::ext
    n_groups_create_group["groups:create_group"]:::ext
    n_groups_delete_group["groups:delete_group"]:::ext
    n_groups_remove_from_group["groups:remove_from_group"]:::ext
    n_map_make_figure["map:make_figure"]:::ext
    n_models_card_position["models:card_position"]:::ext
    n_models_flashcard["models:flashcard"]:::ext
    n_panels_connection_control["panels:connection_control"]:::ext
    n_panels_deck_control["panels:deck_control"]:::ext
    n_panels_difficulty_control["panels:difficulty_control"]:::ext
    n_panels_group_control["panels:group_control"]:::ext
    n_panels_position_control["panels:position_control"]:::ext
    n_parser_load_decks["parser:load_decks"]:::ext
    n_positions_set_position["positions:set_position"]:::ext
    n_progress_set_difficulty["progress:set_difficulty"]:::ext
    n_runtime_refresh_deck_state["runtime:refresh_deck_state"]:::ext
    n_runtime_reset_all_state["runtime:reset_all_state"]:::ext
    n_server_main["server:main"]:::ext
    n_state_load_enabled_decks["state:load_enabled_decks"]:::ext
    n_state_load_groups["state:load_groups"]:::ext
    n_state_load_links["state:load_links"]:::ext
    n_state_load_positions["state:load_positions"]:::ext
    n_state_load_progress["state:load_progress"]:::ext
    n_decks_add_enabled_deck --> n_callbacks_update_card
    n_decks_remove_enabled_deck --> n_callbacks_update_card
    n_geometry_sphere_positions --> n_runtime_refresh_deck_state
    n_geometry_sphere_positions --> n_runtime_reset_all_state
    n_geometry_sphere_positions --> n_state_load_positions
    n_models_card_position --> n_geometry_sphere_positions
    n_models_flashcard --> n_runtime_visible_cards
    n_parser_load_decks --> n_decks_add_enabled_deck
    n_parser_load_decks --> n_decks_remove_enabled_deck
    n_runtime_available_decks --> n_decks_add_enabled_deck
    n_runtime_available_decks --> n_panels_deck_control
    n_runtime_refresh_deck_state --> n_decks_add_enabled_deck
    n_runtime_refresh_deck_state --> n_decks_remove_enabled_deck
    n_runtime_visible_cards --> n_callbacks_update_card
    n_parser_load_decks -.-> n_runtime_visible_cards
    n_runtime_available_decks -.-> n_callbacks_update_card
    n_runtime_available_decks -.-> n_cards_pick_random
    n_runtime_available_decks -.-> n_cards_toggle_reveal
    n_runtime_available_decks -.-> n_colors_group_color
    n_runtime_available_decks -.-> n_colors_progress_color
    n_runtime_available_decks -.-> n_connections_create_link
    n_runtime_available_decks -.-> n_connections_disconnect_link
    n_runtime_available_decks -.-> n_decks_deck_filter_options
    n_runtime_available_decks -.-> n_decks_remove_enabled_deck
    n_runtime_available_decks -.-> n_groups_add_to_group
    n_runtime_available_decks -.-> n_groups_create_group
    n_runtime_available_decks -.-> n_groups_delete_group
    n_runtime_available_decks -.-> n_groups_remove_from_group
    n_runtime_available_decks -.-> n_map_make_figure
    n_runtime_available_decks -.-> n_panels_connection_control
    n_runtime_available_decks -.-> n_panels_difficulty_control
    n_runtime_available_decks -.-> n_panels_group_control
    n_runtime_available_decks -.-> n_panels_position_control
    n_runtime_available_decks -.-> n_parser_load_decks
    n_runtime_available_decks -.-> n_positions_set_position
    n_runtime_available_decks -.-> n_progress_set_difficulty
    n_runtime_available_decks -.-> n_runtime_refresh_deck_state
    n_runtime_available_decks -.-> n_runtime_reset_all_state
    n_runtime_available_decks -.-> n_runtime_visible_cards
    n_runtime_available_decks -.-> n_server_main
    n_runtime_available_decks -.-> n_state_load_enabled_decks
    n_runtime_available_decks -.-> n_state_load_groups
    n_runtime_available_decks -.-> n_state_load_links
    n_runtime_available_decks -.-> n_state_load_positions
    n_runtime_available_decks -.-> n_state_load_progress
    n_state_load_enabled_decks -.-> n_decks_add_enabled_deck
    n_state_load_enabled_decks -.-> n_decks_remove_enabled_deck
    n_state_load_enabled_decks -.-> n_runtime_visible_cards
    n_state_load_groups -.-> n_runtime_visible_cards
    classDef ext stroke:#3b82f6,stroke-dasharray: 4 3
    linkStyle default stroke: #3b82f6, color: #3b82f6
    classDef default fill:inherit, stroke: #3b82f6, color:inherit;
```
<!-- diagram:end -->

These components select information that is computed based on the current state, such as sphere positions, decks, cards.


<Details markdown="1">
<Summary><sd

#### [Sphere positions](./flashcards_app/geometry.py#L7-33 "geometry:sphere_positions")

</Summary>
Generate reproducible random points inside sphere. Creates uniform random distribution within unit sphere.

**Algorithm**:

1. Initialize Random with seed
2. For each card_id: generate random x,y,z in [-1,1]
3. Reject if distance_squared > 1 or == 0
4. Scale by radius and create CardPosition

```yaml
tags: [geometry, 3d, random]
```

</Details>


<Details markdown="1">
<Summary><sd

#### [Available decks](./flashcards_app/runtime.py#L20-26 "runtime:available_decks")

</Summary>
The `available_decks()` function retrieves the list of decks that are currently available in the application.

**Algorithm**:

1. Access the application's deck repository
2. Return the list of available decks

```yaml
tags: []
```

</Details>


<Details markdown="1">
<Summary><sd

#### [Visible cards](./flashcards_app/runtime.py#L66-73 "runtime:visible_cards")

</Summary>
The `visible_cards()` function retrieves the list of cards that are currently visible to the user.

**Algorithm**:

1. Access the application's card repository
2. Filter the cards based on their visibility status
3. Return the list of visible cards

```yaml
tags: []
```

</Details>


<Details markdown="1">
<Summary><sd

#### [Add enabled deck](./flashcards_app/services/decks.py#L12-18 "decks:add_enabled_deck")

</Summary>
The `add_enabled_deck()` function adds a deck to the list of enabled decks.

**Algorithm**:

1. Load the current list of enabled decks
2. Add the specified deck to the list
3. Refresh the deck state to reflect the changes

```yaml
tags: []
```

</Details>


<Details markdown="1">
<Summary><sd

#### [Remove enabled deck](./flashcards_app/services/decks.py#L20-27 "decks:remove_enabled_deck")

</Summary>
The `remove_enabled_deck()` function removes a deck from the list of enabled decks.

**Algorithm**:

1. Load the current list of enabled decks
2. Remove the specified deck from the list
3. Refresh the deck state to reflect the changes

```yaml
tags: []
```

</Details>

<font color="#3b82f6">********************************************************</font>


### User interface (control panels)

<!-- diagram:start (generated by update_index.py - do not edit) -->
```mermaid
graph LR
    %% arrow A --> B: B uses A; dashed = component of another section
    %% dashed arrow A -.-> B: transitive relation (data flow through module-level variables)
    n_decks_deck_filter_options["decks:deck_filter_options"]
    n_panels_deck_control["panels:deck_control"]
    n_panels_card_panel["panels:card_panel"]
    n_panels_difficulty_control["panels:difficulty_control"]
    n_panels_position_control["panels:position_control"]
    n_panels_group_control["panels:group_control"]
    n_panels_connection_control["panels:connection_control"]
    n_callbacks_update_card["callbacks:update_card"]:::ext
    n_models_flashcard["models:flashcard"]:::ext
    n_parser_load_decks["parser:load_decks"]:::ext
    n_runtime_available_decks["runtime:available_decks"]:::ext
    n_state_load_enabled_decks["state:load_enabled_decks"]:::ext
    n_state_load_groups["state:load_groups"]:::ext
    n_state_load_positions["state:load_positions"]:::ext
    n_state_load_progress["state:load_progress"]:::ext
    n_decks_deck_filter_options --> n_callbacks_update_card
    n_decks_deck_filter_options --> n_panels_deck_control
    n_models_flashcard --> n_panels_card_panel
    n_models_flashcard --> n_panels_connection_control
    n_models_flashcard --> n_panels_difficulty_control
    n_models_flashcard --> n_panels_group_control
    n_models_flashcard --> n_panels_position_control
    n_panels_card_panel --> n_callbacks_update_card
    n_panels_connection_control --> n_callbacks_update_card
    n_panels_deck_control --> n_callbacks_update_card
    n_panels_difficulty_control --> n_callbacks_update_card
    n_panels_group_control --> n_callbacks_update_card
    n_panels_position_control --> n_callbacks_update_card
    n_runtime_available_decks --> n_panels_deck_control
    n_parser_load_decks -.-> n_panels_connection_control
    n_parser_load_decks -.-> n_panels_difficulty_control
    n_parser_load_decks -.-> n_panels_group_control
    n_parser_load_decks -.-> n_panels_position_control
    n_runtime_available_decks -.-> n_decks_deck_filter_options
    n_runtime_available_decks -.-> n_panels_connection_control
    n_runtime_available_decks -.-> n_panels_difficulty_control
    n_runtime_available_decks -.-> n_panels_group_control
    n_runtime_available_decks -.-> n_panels_position_control
    n_state_load_enabled_decks -.-> n_decks_deck_filter_options
    n_state_load_enabled_decks -.-> n_panels_connection_control
    n_state_load_enabled_decks -.-> n_panels_deck_control
    n_state_load_enabled_decks -.-> n_panels_difficulty_control
    n_state_load_enabled_decks -.-> n_panels_group_control
    n_state_load_enabled_decks -.-> n_panels_position_control
    n_state_load_groups -.-> n_panels_connection_control
    n_state_load_groups -.-> n_panels_group_control
    n_state_load_positions -.-> n_panels_position_control
    n_state_load_progress -.-> n_panels_difficulty_control
    classDef ext stroke:#3b82f6,stroke-dasharray: 4 3
    linkStyle default stroke: #3b82f6, color: #3b82f6
    classDef default fill:inherit, stroke: #3b82f6, color:inherit;
```
<!-- diagram:end -->

There are various control elements located within panels. Each panel corresponds to a specific user interface component that allows interaction with flashcards.


<Details markdown="1">
<Summary><sd

#### [Deck filter options](./flashcards_app/services/decks.py#L5-10 "decks:deck_filter_options")

</Summary>
The `deck_filter_options()` function retrieves the available filter options for decks.

**Algorithm**:

1. Retrieve the list of available filter options for decks
2. Return the list of available filter options

```yaml
tags: []
```

</Details>

<Details markdown="1">
<Summary><sd

#### [Deck control](./flashcards_app/visualization/panels.py#L156-209 "panels:deck_control")

</Summary>
Generates user interface control for selecting decks of flashcards.

**Algorithm**:

1. Retrieve the current deck
2. Create control layout
3. Handle user interactions to update the deck
4. Return the constructed control

```yaml
tags: []
```

</Details>


<Details markdown="1">
<Summary><sd

#### [Card panel](./flashcards_app/visualization/panels.py#L9-27 "panels:card_panel")

</Summary>
The `card_panel()` function generates the user interface panel for displaying and interacting with a flashcard.

**Algorithm**:

1. Retrieve the flashcard data
2. Create the panel layout with the flashcard content
3. Include controls for interacting with the flashcard (e.g., reveal answer, navigate)
4. Return the constructed panel

```yaml
tags: []
```

</Details>


<Details markdown="1">
<Summary><sd

#### [Difficulty control](./flashcards_app/visualization/panels.py#L29-56 "panels:difficulty_control")

</Summary>
The `difficulty_control()` function generates the user interface control for selecting the difficulty level of a flashcard.

**Algorithm**:

1. Retrieve the current difficulty level of the flashcard
2. Create the control layout with options for different difficulty levels
3. Handle user interactions to update the difficulty level
4. Return the constructed control

```yaml
tags: []
```

</Details>


<Details markdown="1">
<Summary><sd

#### [Position control](./flashcards_app/visualization/panels.py#L58-89 "panels:position_control")

</Summary>
The `position_control()` function generates the user interface control for selecting the position of a flashcard.

**Algorithm**:

1. Retrieve the current position of the flashcard
2. Create the control layout with options for different positions
3. Handle user interactions to update the position
4. Return the constructed control

```yaml
tags: []
```

</Details>


<Details markdown="1">
<Summary><sd

#### [Group control](./flashcards_app/visualization/panels.py#L91-154 "panels:group_control")

</Summary>
The `group_control()` function generates the user interface control for selecting the group of a flashcard.

**Algorithm**:

1. Retrieve the current group of the flashcard
2. Create the control layout with options for different groups
3. Handle user interactions to update the group
4. Return the constructed control

```yaml
tags: []
```

</Details>


<Details markdown="1">
<Summary><sd

#### [Connection control](./flashcards_app/visualization/panels.py#L211-248 "panels:connection_control")

</Summary>
The `connection_control()` function generates the user interface control for selecting the connection of a flashcard.

**Algorithm**:

1. Retrieve the current connection of the flashcard
2. Create the control layout with options for different connections
3. Handle user interactions to update the connection
4. Return the constructed control

```yaml
tags: []
```

</Details>

<font color="#3b82f6">********************************************************</font>


### Rendering visual mapping

<!-- diagram:start (generated by update_index.py - do not edit) -->
```mermaid
graph LR
    %% arrow A --> B: B uses A; dashed = component of another section
    %% dashed arrow A -.-> B: transitive relation (data flow through module-level variables)
    n_map_make_figure["map:make_figure"]
    n_colors_hex_to_rgb["colors:hex_to_rgb"]
    n_colors_rgb_to_hex["colors:rgb_to_hex"]
    n_colors_interpolate_color["colors:interpolate_color"]
    n_colors_progress_color["colors:progress_color"]
    n_colors_group_color["colors:group_color"]
    n_callbacks_update_card["callbacks:update_card"]:::ext
    n_models_flashcard["models:flashcard"]:::ext
    n_parser_load_decks["parser:load_decks"]:::ext
    n_runtime_available_decks["runtime:available_decks"]:::ext
    n_state_load_enabled_decks["state:load_enabled_decks"]:::ext
    n_state_load_groups["state:load_groups"]:::ext
    n_state_load_links["state:load_links"]:::ext
    n_state_load_positions["state:load_positions"]:::ext
    n_state_load_progress["state:load_progress"]:::ext
    n_colors_group_color --> n_map_make_figure
    n_colors_hex_to_rgb --> n_colors_interpolate_color
    n_colors_interpolate_color --> n_colors_progress_color
    n_colors_progress_color --> n_map_make_figure
    n_colors_rgb_to_hex --> n_colors_interpolate_color
    n_map_make_figure --> n_callbacks_update_card
    n_models_flashcard --> n_map_make_figure
    n_parser_load_decks -.-> n_colors_group_color
    n_parser_load_decks -.-> n_colors_progress_color
    n_parser_load_decks -.-> n_map_make_figure
    n_runtime_available_decks -.-> n_colors_group_color
    n_runtime_available_decks -.-> n_colors_progress_color
    n_runtime_available_decks -.-> n_map_make_figure
    n_state_load_enabled_decks -.-> n_colors_group_color
    n_state_load_enabled_decks -.-> n_colors_progress_color
    n_state_load_enabled_decks -.-> n_map_make_figure
    n_state_load_groups -.-> n_colors_group_color
    n_state_load_groups -.-> n_map_make_figure
    n_state_load_links -.-> n_map_make_figure
    n_state_load_positions -.-> n_map_make_figure
    n_state_load_progress -.-> n_colors_progress_color
    classDef ext stroke:#3b82f6,stroke-dasharray: 4 3
    linkStyle default stroke: #3b82f6, color: #3b82f6
    classDef default fill:inherit, stroke: #3b82f6, color:inherit;
```
<!-- diagram:end -->

The visualization on a 3D sphere provides an intuitive way to explore the spatial relationships within the deck.

Used framework: Dash (Plotly) with Flask for boot-id endpoint Visualization: Plotly 3D Scatter plots showing cards on a sphere.

<Details markdown="1">
<Summary><sd

#### [Make figure](./flashcards_app/visualization/map.py#L9-138 "map:make_figure")

</Summary>
The `make_figure()` function generates a visual representation of the flashcards on a map, using colors to indicate progress and group membership.

**Algorithm**:

1. Initialize figure and axes
2. For each flashcard: determine color based on progress and group
3. Plot flashcard on map
4. Return the generated figure

```yaml
tags: []
```

</Details>


<Details markdown="1">
<Summary><sd

#### [Hex to rgb](./flashcards_app/visualization/colors.py#L4-7 "colors:hex_to_rgb")

</Summary>
The `hex_to_rgb()` function converts a hexadecimal color string to an RGB tuple.

**Algorithm**:

1. Remove the leading '#' from the hex string if present
2. Convert the hex string to an integer
3. Extract the red, green, and blue components
4. Return the RGB tuple

```yaml
tags: []
```

</Details>


<Details markdown="1">
<Summary><sd

#### [Rgb to hex](./flashcards_app/visualization/colors.py#L9-11 "colors:rgb_to_hex")

</Summary>
The `rgb_to_hex()` function converts an RGB tuple to a hexadecimal color string.

**Algorithm**:

1. Extract the red, green, and blue components from the RGB tuple
2. Convert each component to a two-digit hexadecimal string
3. Concatenate the hexadecimal strings with a leading '#'
4. Return the hexadecimal color string

```yaml
tags: []
```

</Details>


<Details markdown="1">
<Summary><sd

#### [Interpolate color](./flashcards_app/visualization/colors.py#L13-22 "colors:interpolate_color")

</Summary>
The `interpolate_color()` function calculates an intermediate color between two given colors based on a specified ratio.

**Algorithm**:

1. Convert the start and end colors from hex to RGB
2. Interpolate each RGB component based on the ratio
3. Convert the interpolated RGB color back to hex
4. Return the resulting color

```yaml
tags: []
```

</Details>


<Details markdown="1">
<Summary><sd

#### [Progress color](./flashcards_app/visualization/colors.py#L24-38 "colors:progress_color")

</Summary>
The `progress_color()` function determines the color representing the progress based on a given ratio.

**Algorithm**:

1. Define the start and end colors for the progress
2. Use the `interpolate_color()` function to calculate the intermediate color based on the ratio
3. Return the resulting color

```yaml
tags: []
```

</Details>


<Details markdown="1">
<Summary><sd

#### [Group color](./flashcards_app/visualization/colors.py#L40-45 "colors:group_color")

</Summary>
The `group_color()` function determines the color associated with a specific group.

**Algorithm**:

1. Define a mapping of groups to colors
2. Look up the color for the given group
3. Return the corresponding color

```yaml
tags: []
```

</Details>

<font color="#3b82f6">********************************************************</font>


### Selection logic

<!-- diagram:start (generated by update_index.py - do not edit) -->
```mermaid
graph LR
    %% arrow A --> B: B uses A; dashed = component of another section
    %% dashed arrow A -.-> B: transitive relation (data flow through module-level variables)
    n_cards_choose_random_card["cards:choose_random_card"]
    n_cards_pick_random["cards:pick_random"]
    n_cards_adjacent_card["cards:adjacent_card"]
    n_cards_pick_adjacent["cards:pick_adjacent"]
    n_cards_select_from_click["cards:select_from_click"]
    n_cards_toggle_reveal["cards:toggle_reveal"]
    n_callbacks_update_card["callbacks:update_card"]:::ext
    n_models_card_progress["models:card_progress"]:::ext
    n_models_flashcard["models:flashcard"]:::ext
    n_parser_load_decks["parser:load_decks"]:::ext
    n_runtime_available_decks["runtime:available_decks"]:::ext
    n_state_load_enabled_decks["state:load_enabled_decks"]:::ext
    n_state_load_progress["state:load_progress"]:::ext
    n_cards_adjacent_card --> n_cards_pick_adjacent
    n_cards_choose_random_card --> n_cards_pick_random
    n_cards_pick_adjacent --> n_callbacks_update_card
    n_cards_pick_random --> n_callbacks_update_card
    n_cards_select_from_click --> n_callbacks_update_card
    n_cards_toggle_reveal --> n_callbacks_update_card
    n_models_card_progress --> n_cards_choose_random_card
    n_models_flashcard --> n_cards_adjacent_card
    n_models_flashcard --> n_cards_choose_random_card
    n_models_flashcard --> n_cards_pick_adjacent
    n_models_flashcard --> n_cards_pick_random
    n_parser_load_decks -.-> n_cards_pick_random
    n_parser_load_decks -.-> n_cards_toggle_reveal
    n_runtime_available_decks -.-> n_cards_pick_random
    n_runtime_available_decks -.-> n_cards_toggle_reveal
    n_state_load_enabled_decks -.-> n_cards_pick_random
    n_state_load_enabled_decks -.-> n_cards_toggle_reveal
    n_state_load_progress -.-> n_cards_pick_random
    n_state_load_progress -.-> n_cards_toggle_reveal
    classDef ext stroke:#3b82f6,stroke-dasharray: 4 3
    linkStyle default stroke: #3b82f6, color: #3b82f6
    classDef default fill:inherit, stroke: #3b82f6, color:inherit;
```
<!-- diagram:end -->

<Details markdown="1">
<Summary><sd

#### [Choose random card](./flashcards_app/services/cards.py#L5-13 "cards:choose_random_card")

</Summary>
The `choose_random_card()` function selects a random card from the available flashcards.

**Algorithm**:

1. Retrieve the list of all flashcards
2. Randomly select one card from the list
3. Return the selected card

```yaml
tags: []
```

</Details>


<Details markdown="1">
<Summary><sd

#### [Pick random](./flashcards_app/services/cards.py#L37-40 "cards:pick_random")

</Summary>
The `pick_random()` function selects a random flashcard using the `choose_random_card()` function and returns it.

**Algorithm**:

1. Call the `choose_random_card()` function to select a random card
2. Return the selected card

```yaml
tags: []
```

</Details>


<Details markdown="1">
<Summary><sd

#### [Adjacent card](./flashcards_app/services/cards.py#L15-22 "cards:adjacent_card")

</Summary>
The `adjacent_card()` function retrieves the card adjacent to the currently selected card, either the previous or next one based on the specified direction.

**Algorithm**:

1. Determine the current card's position in the list of flashcards
2. Calculate the position of the adjacent card based on the direction
3. Return the adjacent card

```yaml
tags: []
```

</Details>


<Details markdown="1">
<Summary><sd

#### [Pick adjacent](./flashcards_app/services/cards.py#L42-45 "cards:pick_adjacent")

</Summary>
The `pick_adjacent()` function retrieves the flashcard adjacent to the currently selected one using the `adjacent_card()` function and returns it.

**Algorithm**:

1. Call the `adjacent_card()` function to get the adjacent card
2. Return the adjacent card

```yaml
tags: []
```

</Details>


<Details markdown="1">
<Summary><sd

#### [Select from click](./flashcards_app/services/cards.py#L24-28 "cards:select_from_click")

</Summary>
The `select_from_click()` function selects a flashcard based on a user's click input and returns it.

**Algorithm**:

1. Determine which card was clicked based on the input
2. Return the selected card

```yaml
tags: []
```

</Details>


<Details markdown="1">
<Summary><sd

#### [Toggle reveal](./flashcards_app/services/cards.py#L30-35 "cards:toggle_reveal")

</Summary>
The `toggle_reveal()` function toggles the reveal state of the currently selected flashcard.

**Algorithm**:

1. Check the current reveal state of the flashcard
2. Toggle the reveal state

```yaml
tags: []
```

</Details>

<font color="#3b82f6">********************************************************</font>


### Orchestration

<!-- diagram:start (generated by update_index.py - do not edit) -->
```mermaid
graph LR
    %% arrow A --> B: B uses A; dashed = component of another section
    %% dashed arrow A -.-> B: transitive relation (data flow through module-level variables)
    n_server_boot_id["server:boot_id"]
    n_server_main["server:main"]
    n_parser_load_decks["parser:load_decks"]:::ext
    n_runtime_available_decks["runtime:available_decks"]:::ext
    n_state_load_enabled_decks["state:load_enabled_decks"]:::ext
    n_state_load_groups["state:load_groups"]:::ext
    n_state_load_links["state:load_links"]:::ext
    n_state_load_positions["state:load_positions"]:::ext
    n_state_load_progress["state:load_progress"]:::ext
    n_state_save_state["state:save_state"]:::ext
    n_state_save_state --> n_server_main
    n_parser_load_decks -.-> n_server_main
    n_runtime_available_decks -.-> n_server_main
    n_state_load_enabled_decks -.-> n_server_main
    n_state_load_groups -.-> n_server_main
    n_state_load_links -.-> n_server_main
    n_state_load_positions -.-> n_server_main
    n_state_load_progress -.-> n_server_main
    classDef ext stroke:#3b82f6,stroke-dasharray: 4 3
    linkStyle default stroke: #3b82f6, color: #3b82f6
    classDef default fill:inherit, stroke: #3b82f6, color:inherit;
```
<!-- diagram:end -->

These background functionalities manage the overall state and visibility of decks and cards within the application. Functions are moved to this section if they primarily deal with maintaining or updating the application's state rather than direct user interactions.



<Details markdown="1">
<Summary><sd

#### [Boot id](./flashcards_app/server.py#L20-23 "server:boot_id")

</Summary>
The `boot_id()` function retrieves the unique boot identifier for the application instance.

**Algorithm**:

1. Access the system or application configuration for the boot ID
2. Return the boot ID to the caller

```yaml
tags: []
```

</Details>


<Details markdown="1">
<Summary><sd

#### [Main](./flashcards_app/server.py#L96-99 "server:main")

</Summary>
The `main()` function serves as the entry point for the application, initializing necessary components and starting the application's main loop.

**Algorithm**:

1. Initialize application components and configurations
2. Start the main application loop
3. Handle any startup errors or exceptions
4. Ensure proper shutdown and cleanup of resources

```yaml
tags: []
```

</Details>

<font color="#3b82f6">********************************************************</font>


## Unindexed Components

<font color="green">If you see any components below, note that the keys are proposals. Copy the components manually into the appropriate section above and complete the metadata.

Once you placed the new components into the appropriate sections above, run the `update_index.py` script again to regenerate the index. The section below is regenerated on each run, from its title line to the end of the file. Don't add your own text or tags below it. They would be overwritten. </font>

**End of file**
