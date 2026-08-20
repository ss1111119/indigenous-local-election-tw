## ADDED Requirements

### Requirement: Sentinel-Bearing Columns Carry A Usable Derived Column
Where a published column holds a sentinel that stands for "not recorded", the long table SHALL also
carry a derived column that is safe to aggregate: it holds the value where one was recorded and is
empty where none was. The original column SHALL be left exactly as the source wrote it.

Documentation alone is not sufficient protection. A consumer who aggregates the raw column gets a
wrong answer with no error: for the candidate age column, the nine-term mean moves from 50.80 over
7,335 recorded ages to 53.78 over 7,818 rows once the 483 sentinels are counted as ages.

#### Scenario: Aggregating the derived column
- **WHEN** a consumer aggregates the derived column
- **THEN** rows whose value was not recorded SHALL be absent from the aggregate, because the field is
  empty rather than carrying a stand-in number

#### Scenario: Reading the original column
- **WHEN** a consumer reads the original column
- **THEN** it SHALL contain exactly what the source recorded, sentinel included

### Requirement: A Derived Column Holds Values, Not A Validity Flag
A derived column that exists to make a sentinel-bearing column safe SHALL carry the usable value
itself, not a boolean saying whether the original is usable.

A boolean requires the consumer to know the flag exists before it protects them, which leaves the
original failure mode intact for anyone who does not. A column that holds the value is self-directing:
its name tells the consumer which column to use.

#### Scenario: A consumer unaware of the derived column's existence
- **WHEN** a consumer aggregates the original column without knowing about the derived one
- **THEN** the project SHALL NOT treat that as protected, because no flag was consulted

### Requirement: One Implementation Of A Sentinel Rule
Where a sentinel rule decides what is presented, it SHALL be implemented once, at the point where the
derived column is produced. Consumers of the long tables — including this project's own site
generator — SHALL read the derived column rather than re-deriving the rule.

The checks that guard the rule's premises move with the rule; they are not dropped when the
re-derivation is removed.

#### Scenario: A second implementation of the same rule
- **WHEN** a consumer re-implements the sentinel rule instead of reading the derived column
- **THEN** that is a defect, because the two implementations will diverge and only one of them will
  be exercised by any given test
