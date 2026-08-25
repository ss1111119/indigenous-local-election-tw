## ADDED Requirements

### Requirement: Every declared column manifest is rendered into the shared oracle document
`docs/schema/oracles.md` SHALL contain a section for every column manifest declared in `scripts/oracles.py` that a build script actively uses for column-consistency checking, and each section SHALL list every column that manifest declares.

#### Scenario: The legislative manifest gains a rendered section
- **WHEN** `scripts/build_legislative_election.py` completes a run
- **THEN** `docs/schema/oracles.md` contains sections covering all columns declared in `LEGISLATIVE_MANIFEST`'s `legislative_summary`, `legislative_candidates`, and `legislative_votes` entries

#### Scenario: The local-election sections are unaffected
- **WHEN** `scripts/build_local_election.py` completes a run after this change
- **THEN** the local-election sections of `docs/schema/oracles.md` are byte-identical to what they were before this change, for the same input data

#### Scenario: A manifest gains a new column
- **WHEN** a column is added to `LEGISLATIVE_MANIFEST`
- **THEN** the next run of `scripts/build_legislative_election.py` produces a `docs/schema/oracles.md` whose legislative section includes the new column, without requiring any manual edit to the document

### Requirement: Population column has parity in self-verification across datasets
Where two datasets share the same raw-value handling convention for a column (the value is preserved as a string, not converted, per the source format), the generator for each dataset SHALL perform equivalent parseability and validity checks on that column, not just the dataset whose check was implemented first.

#### Scenario: Legislative population values are checked for parseability
- **WHEN** `scripts/build_legislative_election.py` processes a row whose `人口數` value is not parseable as a decimal number
- **THEN** the build aborts with an error naming the offending row's administrative-area identifier and the invalid value

#### Scenario: Legislative population values are checked for non-negativity
- **WHEN** `scripts/build_legislative_election.py` processes a row whose `人口數` value parses as a negative decimal number
- **THEN** the build aborts with an error naming the offending row's administrative-area identifier and the value

#### Scenario: Valid population values pass through unaffected
- **WHEN** every row's `人口數` value is a non-negative decimal string (including `"0"` and values with a fractional component)
- **THEN** the build completes without raising an error from this check
