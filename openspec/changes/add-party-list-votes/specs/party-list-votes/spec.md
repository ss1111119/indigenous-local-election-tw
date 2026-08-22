## ADDED Requirements

### Requirement: Party-List Votes Are Built From The Same Archive As Every Other Dataset
The party-list (at-large) legislative votes for 2008, 2012, 2016, 2020, and 2024 SHALL be built from the same source archive the project already uses, at polling-station level, and SHALL be published as their own long tables. They SHALL NOT be merged into the local-office or indigenous-legislator tables, because they measure a different ballot cast by a different electorate.

Two source file types appear here that no other dataset uses: the at-large party representative file and the at-large party vote file. Their semantics SHALL be taken from the official format document inside the archive, not inferred from column position.

#### Scenario: Column counts follow the official format document
- **WHEN** any of the seven source files is read
- **THEN** its column count SHALL be checked per row against the official document, and a row with any other count SHALL abort the build

#### Scenario: The quoting convention varies within a term
- **WHEN** reading the 2008 files
- **THEN** the quoting flag SHALL be determined per file rather than per term, because in that term three files are unquoted and four are quoted

#### Scenario: One file in a term carries no filename suffix
- **WHEN** reading the 2016 files, whose names carry a category suffix
- **THEN** the party registry file SHALL be read without that suffix, as the project's existing declaration of suffix-free files already records

#### Scenario: Party votes reconcile to the station's valid votes
- **WHEN** the per-party votes at a polling station are summed
- **THEN** the sum SHALL equal that station's valid-vote count, and any discrepancy SHALL abort the build

### Requirement: The District Column Is Declared Per File And Ignored When Joining
The district column is used inconsistently across the four keyed files and differs between 2008 and later terms. Each file's permitted values SHALL be declared, a value outside its declaration SHALL abort the build, and keys used to join files SHALL ignore that column.

Ignoring a column is not the same as not validating it: the declaration is what makes ignoring it safe.

#### Scenario: Joining without ignoring the district column
- **WHEN** the vote file is joined to the profile file for 2008 using the district column as part of the key
- **THEN** almost every unit fails to match, so the key SHALL exclude that column

#### Scenario: An undeclared district value appears
- **WHEN** a source file's district column contains a value outside its declared set
- **THEN** the build SHALL abort naming the file and the actual values found

### Requirement: Party Identity Is Keyed On Code And Name Together
Party codes are not stable across terms: several codes name a different party in different terms. Any grouping, bucketing, or cross-term comparison of parties SHALL key on the pair (party code, party name).

That the two largest parties keep the same code in every term SHALL NOT be treated as evidence that codes are stable.

#### Scenario: A code names two different parties in two terms
- **WHEN** a party code is compared across terms
- **THEN** records SHALL be grouped by code and name together, so a code whose name changed does not silently merge two distinct parties

#### Scenario: A code names two different parties within one term
- **WHEN** one term's party registry maps a single code to two different names
- **THEN** the build SHALL abort, because the pairing key would no longer identify a party

### Requirement: Seat Allocation Figures Are Preserved, Not Recomputed
The at-large party vote file carries two vote-share figures per party: one over all valid party votes, and one recomputed over only the parties that cleared the threshold. The second is the basis for seat allocation. Both SHALL be preserved as they came, and neither SHALL be recomputed or overwritten.

#### Scenario: Seat totals hold across terms
- **WHEN** the seats won by all parties in a term are summed
- **THEN** the total SHALL equal the at-large seat count fixed by law for that term, and any other total SHALL abort the build

#### Scenario: Vote shares sum to one hundred percent
- **WHEN** either vote-share column is summed across all parties in a term
- **THEN** the total SHALL be 100.00%, and any other total SHALL abort the build

#### Scenario: The candidate-count column is not read as a seat count
- **WHEN** the fourth column of the at-large party vote file is used
- **THEN** it SHALL be treated as the length of that party's list, not as seats to be allocated

### Requirement: Personal Data In The Party Representative File Is Never Output
The at-large party representative file carries date of birth, place of birth, and education for every person on every party list, in every term. Those SHALL NOT appear in any published output, matching the treatment the project already applies to the candidate file.

#### Scenario: Output columns are checked against the exclusion
- **WHEN** any output table is written
- **THEN** it SHALL contain no column derived from date of birth, place of birth, or education, and a build that would write one SHALL abort
