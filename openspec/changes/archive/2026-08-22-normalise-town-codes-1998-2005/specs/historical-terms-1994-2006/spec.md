## ADDED Requirements

### Requirement: Town-Level Comparability Is Declared Per File, Not Assumed From The Term
Whether a record can be joined to other files at township level is a property of the file, not of the year. The 1998, 2002, and 2005 indigenous county councilor files re-number their town codes per file and SHALL carry a resolved code in the normalized town column. The combined indigenous city councilor files and the 1994 provincial councilor files do not re-number theirs and SHALL carry their own code unchanged, because it is already the term's code.

Once this capability applies, the normalized town column SHALL hold a value for every row of every file; no row SHALL carry an empty normalized town code. A reader SHALL be able to join on that column without first consulting a table of which files were fixed when.

#### Scenario: Reading town-level comparability
- **WHEN** a consumer needs to join a record to another file at township level
- **THEN** the normalized town column SHALL be comparable across files of the same term regardless of which file the record came from, and SHALL NOT require the consumer to know whether that file re-numbered its codes

#### Scenario: Six files gain town-level joinability
- **WHEN** the 1998, 2002, and 2005 plain- and mountain-indigenous county councilor files are processed
- **THEN** all of their township-level units SHALL carry a resolved normalized town code, and none SHALL be left empty

#### Scenario: These files carry no sub-township rows
- **WHEN** township-level normalization is applied to these six files
- **THEN** it SHALL NOT be extended to village or polling-station codes, because those files contain no rows below township level and a normalization declared for a level with no data would be a check that can never fail
