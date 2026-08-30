## MODIFIED Requirements

### Requirement: The census does not decide inclusion and produces no derived figures
The census establishes what the source data looks like. Deciding whether the office joins the published datasets is a separate judgement, and the census SHALL NOT make it.

The census SHALL NOT modify the published long tables, SHALL NOT add an election type code, SHALL NOT alter any published page, and SHALL NOT compute any ratio, share, or other figure derived by dividing across populations.

#### Scenario: The census finds the data is clean and matchable
- **WHEN** the census concludes that a term's data can be matched to the list without defects
- **THEN** it SHALL record that finding and stop, without adding the records to any published dataset

#### Scenario: A summary figure would be convenient
- **WHEN** stating how many mountain indigenous township chief seats exist would make the report easier to read
- **THEN** a raw count of units or records is permitted, but any figure formed by dividing one population by another SHALL NOT be produced

#### Scenario: Clean census results are read as authorising inclusion
- **WHEN** the census reports that a term's data is complete and defect-free
- **THEN** that finding alone SHALL NOT be treated as a decision to publish the office, because the inclusion judgement is made separately and rests on constraints the census does not evaluate
