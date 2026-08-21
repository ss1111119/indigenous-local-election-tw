## ADDED Requirements

### Requirement: A Change In Key Formatting Aborts Rather Than Silently Failing To Match
Some source files carry a leading apostrophe on their key columns, an artefact of spreadsheet export. Keys that differ only by such an artefact SHALL NOT be treated as different units, and a file whose key formatting differs from the formatting it has previously carried SHALL abort the build.

#### Scenario: A file that previously carried the artefact stops carrying it
- **WHEN** a file whose keys have carried leading apostrophes is re-issued without them
- **THEN** the build SHALL abort, so that the change is seen rather than absorbed

#### Scenario: A file that never carried the artefact starts carrying it
- **WHEN** a file whose keys have not carried leading apostrophes is re-issued with them
- **THEN** the build SHALL abort naming the term, election type and file, rather than cross-file joins silently matching nothing and yielding zero rows

#### Scenario: Only the affected file is altered
- **WHEN** the artefact is removed from the file that carries it
- **THEN** the key values of every other file SHALL be byte-identical to what the source contained, because a blanket cleanup would also alter keys that were never affected

### Requirement: Superseded Duplicate Source Directories Are Excluded By Name
The source archive contains a superseded copy of at least one term alongside the current one, distinguished only by a path segment. The two copies agree on national totals but differ in their breakdown row counts, and the cause of the difference is not established. The project SHALL take the current copy, SHALL exclude the superseded copy by name, and SHALL abort if a superseded copy reaches the parser.

#### Scenario: A superseded copy is resolved as a source path
- **WHEN** the set of resolved source paths contains a superseded copy
- **THEN** the build SHALL abort naming that path, rather than choosing between the copies by row count or by whichever was found first

#### Scenario: A consumer asks which copy the figures came from
- **WHEN** a consumer needs to know which of two disagreeing copies a published figure was taken from
- **THEN** the named-defect record SHALL state which copy was used, how the copies differ, and that the cause of the difference is not established

### Requirement: A Term's Seat Total Is Fixed By History, Not By Whatever The Source Currently Says
The number of seats contested is not constant across terms of the same office. Each term's seat total is a historical fact that SHALL NOT change because a source file was re-issued. A published seat total that differs from the historical one SHALL abort the build instead of being adopted.

#### Scenario: A term's seat total changes in the source
- **WHEN** the seat total parsed for a term differs from that term's historical total
- **THEN** the build SHALL abort naming the term, election type, both figures, rather than accepting the new figure as the current truth

#### Scenario: A reader assumes a constant seat total across terms
- **WHEN** a consumer reads the documentation for this office
- **THEN** it SHALL state the seat total per term rather than a single figure, so that the change across terms is visible without inspecting the data
