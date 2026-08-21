## ADDED Requirements

### Requirement: Nine Terms Of Indigenous Legislative Elections Are Covered
The dataset SHALL cover the mountain-indigenous and plain-indigenous legislative elections of 1995, 1998, 2001, 2004, 2008, 2012, 2016, 2020, and 2024, for both categories in every term. A term that is present in the source archive and absent from the output SHALL abort the build rather than produce a partial dataset.

#### Scenario: Counting seats per term
- **WHEN** a consumer counts elected candidates per term and category
- **THEN** the counts SHALL be 3 for each category in 1995, 4 for each category in 1998, 2001 and 2004, and 3 for each category in 2008, 2012, 2016, 2020 and 2024

#### Scenario: A source term fails to parse
- **WHEN** any one of the eighteen source files cannot be parsed
- **THEN** the build SHALL abort naming the term and category, and SHALL NOT write any output file

### Requirement: Legislative Data Is Published Separately From Local Office Data
The indigenous legislative elections SHALL be published as their own long tables, distinct from the local-office long tables. Adding legislative coverage SHALL NOT change the columns, row count, or bytes of the local-office long tables.

#### Scenario: A consumer of the local-office tables rebuilds after this change
- **WHEN** the local-office long tables are rebuilt with legislative coverage present in the project
- **THEN** their content SHALL be byte-identical to the content produced before legislative coverage existed

#### Scenario: Distinguishing the two datasets by election type code
- **WHEN** a consumer reads the election type code in the legislative tables
- **THEN** plain-indigenous legislators SHALL be coded `L2` and mountain-indigenous legislators `L3`, and the documentation SHALL state that these are project-assigned codes rather than codes taken from the source

### Requirement: The Nationwide Constituency Is Stated, Not Implied
Indigenous legislators are elected from a single nationwide constituency per category. The district column carries no constituency meaning in these files, and its raw value differs across terms. The dataset SHALL preserve the raw value and SHALL publish, alongside it, an explicit statement of whether the column carries constituency meaning in that term.

#### Scenario: A consumer groups by district column
- **WHEN** a consumer groups the legislative tables by the district column expecting separate constituencies
- **THEN** the accompanying meaning column SHALL tell them the column carries no constituency meaning, so that the grouping is recognised as meaningless rather than silently producing plausible subtotals

#### Scenario: The district column takes an undeclared value
- **WHEN** the district column in a term contains a value outside the set declared for that term and category
- **THEN** the build SHALL abort naming the term, category, file, the declared set, and the value found

### Requirement: A Term's Breakdown Never Silently Coarsens
The finest administrative level present differs by term: the 1995 through 2004 elections are broken down to township level, and the 2008 through 2024 elections to polling-station level. A term SHALL NOT be published at a coarser breakdown than the one it has historically carried.

#### Scenario: Fine-grained rows disappear from a source term
- **WHEN** a term that has historically reached polling-station level yields only township-level rows
- **THEN** the build SHALL abort, because the totals would otherwise remain correct while the breakdown silently coarsened, and nothing in the output would say so

#### Scenario: A consumer checks what breakdown a term supports
- **WHEN** a consumer needs to know whether a term can be analysed at polling-station level
- **THEN** the documentation SHALL state the finest level per term, so that an empty result is distinguishable from an unsupported query

### Requirement: Elected Status Follows The Project's Established Column Convention
The legislative tables SHALL carry elected status under the same convention as the local-office tables: the plainest-named elected column holds the cross-file determined value, the source's own mark and its decoding remain available unchanged, and the basis of the determination is published alongside. This convention SHALL hold even in terms where the source's mark and the official summary agree.

#### Scenario: Counting seats without reading documentation
- **WHEN** a consumer counts elected candidates from the plainest-named elected column
- **THEN** the count SHALL equal the seat total stated by the official summary file for that term and category

#### Scenario: The source mark disagrees with the official summary in a future term
- **WHEN** a term is added or re-issued in which the source mark and the official summary disagree
- **THEN** the build SHALL abort rather than publish either figure silently, because the compensating check exists for the source going wrong later, not only for defects already known

### Requirement: Geographic Keys Are Not Published As Falsely Joinable
County and township codes in these files are re-issued across terms: the same township carries different codes in different terms, and counties change both their code and their identity as they are upgraded to municipalities. The dataset SHALL NOT publish raw geographic codes as though they were stable keys. Either a normalised key that is comparable across terms SHALL be published alongside the raw value, or the field SHALL be left explicitly empty to mark it as not normalised.

#### Scenario: A consumer joins two terms on township code
- **WHEN** a consumer joins rows from two terms using the published normalised township key
- **THEN** rows SHALL only match when they refer to the same township, and SHALL NOT match a different township that happens to reuse the code

#### Scenario: A term whose codes cannot be normalised
- **WHEN** a term's geographic codes cannot be mapped to a stable identity
- **THEN** the normalised field SHALL be empty rather than carrying the raw code, because a raw code in a field named as normalised would join successfully against the wrong unit and report no error

#### Scenario: A county that was upgraded to a municipality
- **WHEN** a consumer follows one area across a term in which it was upgraded
- **THEN** the normalised key SHALL identify it as the same area on both sides of the upgrade, or the documentation SHALL state that this particular area is not traceable across that boundary

### Requirement: Personal Data Fields Are Never Published
The source candidate files contain date of birth, place of birth, and education. These SHALL NOT appear in any published output of this capability, in any form, including derived fields from which they could be reconstructed.

#### Scenario: A consumer looks for date of birth
- **WHEN** a consumer inspects every column of the published legislative tables
- **THEN** date of birth, place of birth, and education SHALL be absent, while age SHALL be present as a value that does not identify a birth date
