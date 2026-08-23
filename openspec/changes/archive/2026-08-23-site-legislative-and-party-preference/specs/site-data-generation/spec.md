## MODIFIED Requirements

### Requirement: Site Data Is Generated From The Long Tables
The site data constants embedded in the site's HTML pages SHALL be produced by a script that reads `data/processed/`, and SHALL NOT be maintained by hand. The script SHALL replace only the data constant line in each HTML file, leaving every other byte unchanged.

The script SHALL read every dataset the site presents, not only the first one it was written for. Where a page presents a dataset, that page's constants SHALL be generated from that dataset's long tables by the same mechanism, with its own marker line.

#### Scenario: Regenerating after a dataset change
- **WHEN** the long tables are rebuilt and the site generator is run
- **THEN** every HTML page SHALL carry data covering every term present in the long tables it presents

#### Scenario: Marker line missing
- **WHEN** an HTML file does not contain the marker line that delimits one of its data constants
- **THEN** the generator SHALL abort rather than fall back to a fuzzy match

#### Scenario: Required column missing
- **WHEN** a long table lacks a column the generator depends on, such as the authoritative elected field
- **THEN** the generator SHALL abort and SHALL NOT write a partial result

#### Scenario: A new dataset is added to the site
- **WHEN** a page is added that presents a dataset the generator did not previously read
- **THEN** the generator SHALL be extended to read that dataset's long tables, and the page's constants SHALL NOT be written by hand even once
