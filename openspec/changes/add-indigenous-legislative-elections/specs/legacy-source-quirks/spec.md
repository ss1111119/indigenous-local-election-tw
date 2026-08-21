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
The source archive contains a superseded copy of at least one term alongside the current one, distinguished only by a path segment. The two copies are the same election published under different administrative code systems; they agree on national totals but differ in their breakdown row counts, and one may be more internally consistent than the other. The project SHALL take exactly one copy by name, SHALL exclude the other by name, and SHALL abort if the excluded copy reaches the parser. The choice SHALL NOT be made by row count, by internal consistency alone, or by whichever path was found first.

#### Scenario: A superseded copy is resolved as a source path
- **WHEN** the set of resolved source paths contains the excluded copy
- **THEN** the build SHALL abort naming that path, rather than silently choosing between the copies

#### Scenario: The excluded copy is the internally consistent one
- **WHEN** the copy that is excluded is more internally consistent than the copy that is used
- **THEN** the choice SHALL still be recorded with its reasoning, and the consequences for the copy that is used SHALL be handled explicitly rather than inherited silently

#### Scenario: A consumer asks which copy the figures came from
- **WHEN** a consumer needs to know which of two disagreeing copies a published figure was taken from
- **THEN** the named-defect record SHALL state which copy was used, how the copies differ, and why that copy was chosen

### Requirement: Aggregate Rows That Disagree With Their Own Detail Are Named, And The Detail Wins
A source file may carry an aggregate row whose figures disagree with the sum of the finer-level rows beneath it. Where this occurs, the finer levels SHALL be treated as authoritative and the aggregate row SHALL be recorded as the defect. The set of disagreeing units SHALL be named exactly; a disagreement outside the named set, or a named unit that stops disagreeing, SHALL abort the build.

#### Scenario: An aggregate row omits one unit's votes
- **WHEN** a county-level row's total is short by exactly one township's votes, and that township's own rows are present and correct
- **THEN** the township rows SHALL be published unchanged and the county row SHALL be recorded as the defect, naming the township and the amount

#### Scenario: The check is pointed the wrong way
- **WHEN** the comparison is written so that the aggregate row is treated as authoritative
- **THEN** the correct finer-level rows would be reported as anomalous — the opposite of what happened — so the direction of the comparison SHALL be stated where the check is defined

#### Scenario: A published rate contradicts its own numerator and denominator
- **WHEN** a rate column states zero while the counts it derives from are non-zero
- **THEN** the source value SHALL be preserved in its own column, the recomputed value SHALL be published alongside, and the affected rows SHALL be named exactly

#### Scenario: A named aggregate defect stops appearing
- **WHEN** a re-issued source no longer contains one of the named disagreements
- **THEN** the build SHALL abort, because the record has become stale and would otherwise keep asserting a defect that no longer exists

### Requirement: A Term's Seat Total Is Fixed By History, Not By Whatever The Source Currently Says
The number of seats contested is not constant across terms of the same office. Each term's seat total is a historical fact that SHALL NOT change because a source file was re-issued. A published seat total that differs from the historical one SHALL abort the build instead of being adopted.

#### Scenario: A term's seat total changes in the source
- **WHEN** the seat total parsed for a term differs from that term's historical total
- **THEN** the build SHALL abort naming the term, election type, both figures, rather than accepting the new figure as the current truth

#### Scenario: A reader assumes a constant seat total across terms
- **WHEN** a consumer reads the documentation for this office
- **THEN** it SHALL state the seat total per term rather than a single figure, so that the change across terms is visible without inspecting the data
