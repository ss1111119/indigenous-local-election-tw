# historical-terms-1994-2006 Specification

## Purpose

The dataset reaches back past 2009 to 1994, but the earlier terms are not simply
more of the same series. Three things change: some categories are different
institutions that happen to share a name, the administrative code scheme is
renumbered between terms, and one term's files cover a category that no longer
exists. This capability governs which historical records join the comparable
series and which are carried but held apart.

The distinction is by institution, not by date. The 1998, 2002, and 2005 mountain
and plain indigenous county councilors are the same office as the later terms and
belong to the main sequence. The 1994 provincial councilors and the combined
indigenous city councilor category are not, and they carry custom election type
codes so no query can reach them by asking for T2 or T3.

Whether a record is comparable is therefore a property of the record, declared in
the output as `is_main_sequence` and `admin_code_system`, rather than something a
reader is expected to infer from the year. A reader who sums a column without
filtering gets a wrong answer either way; the flags make the wrong answer
detectable instead of invisible.

## Requirements

### Requirement: T2 and T3 Main Sequence Inclusion
The system SHALL include the 1998, 2002, and 2005 mountain indigenous (T3) and plain indigenous (T2) county councilors in the dataset and flag them as part of the main sequence.

#### Scenario: Processing 1998-2005 T2-T3 files
- **WHEN** processing 1998, 2002, and 2005 county councilor files
- **THEN** the output records SHALL have the `is_main_sequence` flag set to true


<!-- @trace
source: include-1994-2006-terms
updated: 2026-08-20
code:
  - CLAUDE.md
  - data/processed/cec-local-election-votes-long.csv.gz
  - AGENTS.md
  - docs/schema/oracles.md
  - .spectra.yaml
  - docs/schema/cec-local-election.md
  - data/processed/cec-local-election-candidates-long.csv
  - data/processed/cec-local-election-summary-long.csv.gz
  - GEMINI.md
  - scripts/build_local_election.py
  - HANDOFF.md
  - data/sources.json
  - scripts/oracles.py
  - README.md
  - data/processed/validation-report.json
  - data/reference/cec-county-code-crosswalk-1998-2002.csv
tests:
  - scripts/test_build_local_election.py
-->

---
### Requirement: Custom Election Type Codes
The system SHALL assign custom, project-specific election type codes for 1994 Taiwan Provincial Councilors and the "combo" indigenous city councilor category (which exists across multiple early terms).

#### Scenario: Assigning codes to 1994 provincial councilors
- **WHEN** processing 1994 provincial councilor files
- **THEN** the system SHALL assign a new custom code distinct from T2 and T3

#### Scenario: Assigning codes to combo indigenous city councilors
- **WHEN** processing combo indigenous city councilors
- **THEN** the system SHALL assign a custom combo code distinct from T2 and T3


<!-- @trace
source: include-1994-2006-terms
updated: 2026-08-20
code:
  - CLAUDE.md
  - data/processed/cec-local-election-votes-long.csv.gz
  - AGENTS.md
  - docs/schema/oracles.md
  - .spectra.yaml
  - docs/schema/cec-local-election.md
  - data/processed/cec-local-election-candidates-long.csv
  - data/processed/cec-local-election-summary-long.csv.gz
  - GEMINI.md
  - scripts/build_local_election.py
  - HANDOFF.md
  - data/sources.json
  - scripts/oracles.py
  - README.md
  - data/processed/validation-report.json
  - data/reference/cec-county-code-crosswalk-1998-2002.csv
tests:
  - scripts/test_build_local_election.py
-->

---
### Requirement: Comparability Flags
The output long datasets SHALL include new flag columns: `is_main_sequence` (boolean) and `admin_code_system` (string) to indicate the schema year of the administrative codes.

#### Scenario: Flagging non-main sequence records
- **WHEN** the record is a 1994 provincial councilor or a combo indigenous city councilor
- **THEN** the `is_main_sequence` flag SHALL be set to false

#### Scenario: Setting admin code system version
- **WHEN** processing files from a specific election year
- **THEN** the `admin_code_system` SHALL reflect the corresponding system version

<!-- @trace
source: include-1994-2006-terms
updated: 2026-08-20
code:
  - CLAUDE.md
  - data/processed/cec-local-election-votes-long.csv.gz
  - AGENTS.md
  - docs/schema/oracles.md
  - .spectra.yaml
  - docs/schema/cec-local-election.md
  - data/processed/cec-local-election-candidates-long.csv
  - data/processed/cec-local-election-summary-long.csv.gz
  - GEMINI.md
  - scripts/build_local_election.py
  - HANDOFF.md
  - data/sources.json
  - scripts/oracles.py
  - README.md
  - data/processed/validation-report.json
  - data/reference/cec-county-code-crosswalk-1998-2002.csv
tests:
  - scripts/test_build_local_election.py
-->

---
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

<!-- @trace
source: normalise-town-codes-1998-2005
updated: 2026-08-22
code:
  - README.md
  - data/reference/cec-town-code-crosswalk-1998-2005.csv
  - docs/index.html
  - GEMINI.md
  - .spectra.yaml
  - docs/三屆概況.md
  - scripts/build_local_election.py
  - docs/schema/cec-local-election.md
  - AGENTS.md
  - data/processed/cec-local-election-votes-long.csv.gz
  - data/processed/validation-report.json
  - data/processed/cec-local-election-candidates-long.csv
  - scripts/build_town_crosswalk.py
  - CLAUDE.md
  - scripts/mutate_build_local_election.py
  - data/processed/cec-local-election-summary-long.csv.gz
  - HANDOFF.md
tests:
  - scripts/test_build_local_election.py
-->