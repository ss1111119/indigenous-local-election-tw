## MODIFIED Requirements

### Requirement: Sentinel Values Are Not Presented As Measurements
Where a source column carries a fixed value that stands for "not recorded" rather than a measurement,
the published output SHALL NOT present that value as if it were the measurement.

The substitution SHALL happen in the long table, at the point where the cleaned column is produced,
and the source's own value SHALL be preserved under an explicitly-marked name. It SHALL NOT be
deferred to the presentation layer alone: a consumer reading the long table directly never reaches
that layer, and gets the sentinel counted as a measurement with no error raised.

The measured instance is the candidate age column: it holds `99` for every one of the 483 candidates
in the 1994, 1998, 2002, 2005 and 2006 terms, and never holds `99` in the 2009-2010, 2014, 2018 or
2022 terms, whose ages range from 23 to 89.

#### Scenario: A term whose age column is uniformly the sentinel
- **WHEN** any consumer reads the cleaned column for a term in which every source value is the
  sentinel
- **THEN** the field SHALL be empty rather than carrying the sentinel, so that no claim is made about
  that person's age

#### Scenario: A term that records real ages
- **WHEN** a consumer reads the cleaned column for a term whose source values are real ages
- **THEN** the value SHALL be the source's value unchanged

#### Scenario: A consumer who needs the sentinel itself
- **WHEN** a consumer reads the explicitly-marked source column
- **THEN** the sentinel SHALL still be there, because preserving what the source wrote is what that
  column is for

## ADDED Requirements

### Requirement: The Plainest Column Name Holds The Safest Data
Where a source column mixes a "not recorded" sentinel with real measurements, the plainest column
name SHALL hold the cleaned values — the value where one was recorded, empty where none was — and
the source's own value SHALL be preserved under an explicitly-marked name.

Adding a separate clean column beside the raw one is not sufficient. It opens a safe route without
closing the trap: the plainest name carries the strongest default pull, so a consumer who has not
read the documentation aggregates it and gets a wrong answer with no error. For the candidate age
column the nine-term mean moves from 50.80 over 7,335 recorded ages to 53.78 over 7,818 rows once
the 483 sentinels are counted as ages.

#### Scenario: A consumer who has not read the documentation
- **WHEN** a consumer aggregates the plainest-named column without consulting any documentation
- **THEN** the answer SHALL be correct, because rows with no recorded value are empty rather than
  carrying a stand-in number

#### Scenario: A consumer who needs exactly what the source wrote
- **WHEN** a consumer reads the explicitly-marked source column
- **THEN** it SHALL contain exactly what the source recorded, sentinel included, one row for one row

#### Scenario: Renaming changes what a published column means
- **WHEN** this exchange is made to a column that has already been published
- **THEN** the project SHALL record that the same column name now means something different from
  earlier revisions, because no error will be raised for a consumer who re-reads it

### Requirement: A Cleaned Column Holds Values, Not A Validity Flag
A column that exists to make sentinel-bearing data safe SHALL carry the usable value itself, not a
boolean saying whether the source value is usable.

A boolean requires the consumer to know the flag exists before it protects them, which leaves the
original failure mode intact for anyone who does not. A column that holds the value is self-directing:
its name tells the consumer which column to use.

#### Scenario: A consumer unaware of the derived column's existence
- **WHEN** a consumer aggregates the original column without knowing about the derived one
- **THEN** the project SHALL NOT treat that as protected, because no flag was consulted

### Requirement: One Implementation Of A Sentinel Rule
Where a sentinel rule decides what is presented, it SHALL be implemented once, at the point where the
cleaned column is produced. Consumers of the long tables — including this project's own site
generator — SHALL read the cleaned column rather than re-deriving the rule from the source column.

The checks that guard the rule's premises move with the rule; they are not dropped when the
re-derivation is removed.

#### Scenario: A second implementation of the same rule
- **WHEN** a consumer re-implements the sentinel rule instead of reading the derived column
- **THEN** that is a defect, because the two implementations will diverge and only one of them will
  be exercised by any given test
