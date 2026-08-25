## MODIFIED Requirements

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

#### Scenario: The party-list manifest gains a rendered section
- **WHEN** `scripts/build_party_list_election.py` completes a run
- **THEN** `docs/schema/oracles.md` contains sections covering all columns declared in `PARTY_LIST_MANIFEST`'s `party_list_summary`, `party_list_votes`, and `party_list_seats` entries

#### Scenario: The legislative and local-election sections stay unaffected by the party-list addition
- **WHEN** `scripts/build_party_list_election.py` completes a run after this change
- **THEN** the local-election and legislative sections of `docs/schema/oracles.md` are byte-identical to what they were before this change, for the same input data
