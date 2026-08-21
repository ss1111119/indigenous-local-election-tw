## MODIFIED Requirements

### Requirement: Authoritative Elected Status Derivation
Where the source's own elected mark is known to be corrupt, the project SHALL derive elected status by
cross-file reconciliation and SHALL publish that derived status under the plainest column name, so
that a consumer who aggregates seats without reading any documentation gets the correct count.

The source's own claim SHALL remain available: the raw mark and its decoding stay in the long table
unchanged. The project SHALL NOT publish a second column holding the same derived status under a
longer name, because two columns carrying one fact will drift.

The basis of the derivation — which level of the votes file it was taken from — SHALL be published
alongside, because the levels differ in strength.

#### Scenario: Counting seats without reading documentation
- **WHEN** a consumer counts elected candidates from the plainest-named elected column
- **THEN** the count SHALL be the cross-file derived one, not the source's corrupt claim

#### Scenario: Recovering what the source claimed
- **WHEN** a consumer needs the source's own claim
- **THEN** the raw mark and its decoded meaning SHALL still be present, unchanged, one row for one row

### Requirement: Elected Status Compensating Checks
The compensating check that bounds the named mark anomalies SHALL compare the value derived from the
source mark against the cross-file derived value. It SHALL NOT compare the published elected column
against the cross-file value once those two hold the same thing.

A check whose two sides are the same value passes for every row and raises nothing. The named anomaly
list it guards then becomes a list nothing tests, and the corruption it was written to catch would
reappear unnoticed.

#### Scenario: The two sides of the check become the same value
- **WHEN** the published elected column is changed to hold the cross-file derived value
- **THEN** the check SHALL be re-pointed at the value derived from the source mark, and a mutation
  restoring the same-value comparison SHALL be detected by the test suite

#### Scenario: A mark anomaly outside the named list
- **WHEN** a candidate's source-derived status disagrees with the cross-file derived status and that
  candidate is not on the named list
- **THEN** the build SHALL abort, naming the term, election type, candidate and mark
