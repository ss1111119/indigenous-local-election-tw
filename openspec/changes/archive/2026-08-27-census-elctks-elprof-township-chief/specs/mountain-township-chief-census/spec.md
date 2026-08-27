## ADDED Requirements

### Requirement: A census covers the files the figures come from before it is relied upon for inclusion
Establishing that units and candidates can be matched is not the same as establishing that the figures are sound. The files that identify administrative units and candidates are not the files that carry seat counts, electorate sizes, and vote totals.

A census SHALL NOT be relied upon as the basis for including a term's figures unless it has examined the files those figures are read from. Where a census has examined only the identifying files, it SHALL record that limitation explicitly, and the limitation SHALL be stated as unchecked rather than as absence of defect.

#### Scenario: A census examined only the identifying files
- **WHEN** a census has opened the files that name units and candidates but not the files that carry vote and profile figures
- **THEN** it SHALL NOT be cited as establishing that those figures can be included, and the unexamined files SHALL appear as unchecked

#### Scenario: Inclusion is proposed on the strength of a partial census
- **WHEN** inclusion of a term's figures is proposed and the census for that term has not covered the files those figures are read from
- **THEN** the census SHALL be completed for those files first, and the expected counts used by the inclusion work SHALL be taken from the completed census

#### Scenario: A term proves unsuitable for inclusion
- **WHEN** the census of a term's figure-bearing files finds a defect that prevents the figures being read reliably
- **THEN** the term SHALL be recorded as not includable with the defect named, rather than the verification standard being lowered to admit it

### Requirement: Per-term includability is recorded as a conclusion separate from the inclusion decision
A census that ends without saying which terms its findings support leaves the next worker to infer it, and inference is where an unchecked term becomes an assumed-clean term.

The census SHALL record, per term, whether the data structure supports inclusion and why. That technical conclusion SHALL remain distinct from the decision about whether the office belongs in the project's published datasets, which this capability continues to place outside the census.

#### Scenario: A term's files are censused and found sound
- **WHEN** a term's figure-bearing files are censused with no defect that prevents reliable reading
- **THEN** the census SHALL record that term as structurally includable, and SHALL NOT thereby record that it should be included

#### Scenario: The technical conclusion is read as the inclusion decision
- **WHEN** a term is recorded as structurally includable
- **THEN** that record SHALL NOT be treated as deciding publication, because the publication decision is governed elsewhere
