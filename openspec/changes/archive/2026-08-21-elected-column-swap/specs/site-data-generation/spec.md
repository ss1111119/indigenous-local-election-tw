## MODIFIED Requirements

### Requirement: Seats Come From The Authoritative Elected Field
Every seat count, elected marker, and statistic derived from winners SHALL be computed from the `當選` field, which holds the cross-file authoritative determination. They SHALL NOT be recomputed from `當選註記`, which preserves the source's own marking and carries its known corruption.

#### Scenario: Displaying 2005 county councilor seats
- **WHEN** the site shows seats for the 2005 mountain-indigenous or plain-indigenous county councilors
- **THEN** it SHALL show 30 and 27 respectively, not the 18 and 20 that `當選註記` yields

#### Scenario: Marking winners in the roster
- **WHEN** the roster marks a candidate as elected
- **THEN** the marking SHALL follow `當選`, while the women's-quota (`!`) and displaced (`-`) distinctions SHALL still come from `當選註記`

#### Scenario: A consumer reads the most plainly named elected field
- **WHEN** a reader takes the field named `當選` without consulting documentation first
- **THEN** the value they receive SHALL be the authoritative one, so that being uninformed yields correct seat counts rather than silently wrong ones

### Requirement: Site Data Is Generated From The Long Tables
The site data constants embedded in `docs/index.html` and `docs/roster.html` SHALL be produced by a script that reads `data/processed/`, and SHALL NOT be maintained by hand. The script SHALL replace only the data constant line in each HTML file, leaving every other byte unchanged.

#### Scenario: Regenerating after a dataset change
- **WHEN** the long tables are rebuilt and the site generator is run
- **THEN** both HTML files SHALL carry data covering every term present in the long tables

#### Scenario: Marker line missing
- **WHEN** the HTML file does not contain the marker line that delimits the data constant
- **THEN** the generator SHALL abort rather than fall back to a fuzzy match

#### Scenario: Required column missing
- **WHEN** a long table lacks a column the generator depends on, such as `當選`
- **THEN** the generator SHALL abort and SHALL NOT write a partial result
