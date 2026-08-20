## ADDED Requirements

### Requirement: Site Data Is Generated From The Long Tables
The site data constants embedded in `docs/index.html` and `docs/roster.html` SHALL be produced by a script that reads `data/processed/`, and SHALL NOT be maintained by hand. The script SHALL replace only the data constant line in each HTML file, leaving every other byte unchanged.

#### Scenario: Regenerating after a dataset change
- **WHEN** the long tables are rebuilt and the site generator is run
- **THEN** both HTML files SHALL carry data covering every term present in the long tables

#### Scenario: Marker line missing
- **WHEN** the HTML file does not contain the marker line that delimits the data constant
- **THEN** the generator SHALL abort rather than fall back to a fuzzy match

#### Scenario: Required column missing
- **WHEN** a long table lacks a column the generator depends on, such as `elected_authoritative`
- **THEN** the generator SHALL abort and SHALL NOT write a partial result

### Requirement: Existing Terms Must Be Reproduced Before Extending
The generator SHALL provide a mode that emits only the terms already present in the site, so its output can be compared key by key against the current hand-maintained constants. Any difference SHALL be named and explained before the site is extended to further terms.

#### Scenario: Reproduction differs from the current site
- **WHEN** the reproduction mode produces a value that differs from the current site constant
- **THEN** the build SHALL abort unless that difference is recorded in a named list stating whether the site's old value or the generator is wrong

#### Scenario: Reproduction matches
- **WHEN** every key matches
- **THEN** the generator SHALL emit every term present in the long tables

### Requirement: Seats Come From The Authoritative Elected Field
Every seat count, elected marker, and statistic derived from winners SHALL be computed from `elected_authoritative`, not from the `當選` field, because `當選` reflects known source corruption.

#### Scenario: Displaying 2005 county councilor seats
- **WHEN** the site shows seats for the 2005 mountain-indigenous or plain-indigenous county councilors
- **THEN** it SHALL show 30 and 27 respectively, not the 18 and 20 that `當選` yields

#### Scenario: Marking winners in the roster
- **WHEN** the roster marks a candidate as elected
- **THEN** the marking SHALL follow `elected_authoritative`, while the women's-quota (`!`) and displaced (`-`) distinctions SHALL still come from `當選註記`

### Requirement: Cross-Term Lines Are Restricted To The Main Sequence
Any chart that connects values across terms SHALL include only rows whose `is_main_sequence` is `true`. The project-defined election type codes SHALL be presented in a separate block that states why they cannot be added to the main sequence.

#### Scenario: Plotting a cross-term line
- **WHEN** the site draws a line across terms
- **THEN** rows for `T-PRV2`, `T-PRV3`, and `T-COMBO` SHALL be excluded

#### Scenario: Presenting the excluded types
- **WHEN** the site presents the 1994 provincial councilors or the combined indigenous city councilors
- **THEN** it SHALL do so outside the cross-term lines and SHALL state that the provincial assembly was abolished in 1998, and that the combined category is not split into plain and mountain indigenous

### Requirement: Absent Election Types Are Marked Rather Than Zero-Filled
Where an election type did not exist in a term, the site SHALL mark it as absent and SHALL NOT display a zero.

#### Scenario: A type absent from a term
- **WHEN** the site renders indigenous district chief (D2) figures for 1998, a term in which that election did not exist
- **THEN** it SHALL show the absent marker, so that "did not exist" is distinguishable from "zero seats"
