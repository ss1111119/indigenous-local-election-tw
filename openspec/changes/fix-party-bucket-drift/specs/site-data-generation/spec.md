## ADDED Requirements

### Requirement: Party Buckets Are Keyed By Source Identity
The generator SHALL assign each candidate to a chart bucket using a named lookup table keyed by the
pair `(政黨代號, 政黨名稱)` taken from the source row, not by party name alone and not by party code
alone. Identities absent from the table SHALL fall into the residual bucket.

Both single-field keys are known to be wrong for this dataset: the same party appears under two codes
across eras (民主進步黨 is `2` before 2009 and `16` from 2009), and the same concept appears under two
names across eras (independents are `99`/「無」 before 2009 and `999`/「無黨籍及未經政黨推薦」 from 2009).

#### Scenario: The same concept under two source encodings
- **WHEN** the generator buckets a 1998 candidate whose source row carries code `99` and name 「無」
- **THEN** that candidate SHALL be counted in the same bucket as a 2018 candidate carrying code `999`
  and name 「無黨籍及未經政黨推薦」

#### Scenario: The same party under two source codes
- **WHEN** the generator buckets a 2002 candidate carrying code `2` and name 「民主進步黨」
- **THEN** that candidate SHALL be counted in the same bucket as a 2018 candidate carrying code `16`
  and the same name

#### Scenario: One code reused for two names
- **WHEN** two source rows share a party code but carry different party names, and neither pair is
  listed in the lookup table
- **THEN** the generator SHALL NOT merge them on the strength of the shared code, and both SHALL fall
  into the residual bucket, so that a recycled code cannot silently misattribute one party's results
  to another

### Requirement: The Independent Bucket Is Non-Empty In Every Term
The test suite SHALL assert that the independent bucket has a non-zero candidate count in every term
the dataset covers. This is a named domain claim about this dataset, not a general rule that every
bucket is non-empty in every term.

No statistical threshold is used for this, because measurement showed the obvious candidates do not
work: a "largest residual member must stay under 5% of the term's candidates" rule still fails after
the defect is fixed (2002 residual is led by 親民黨 at 28 of 164, 17.1%), and a "residual members must
be smaller than named buckets" rule misfires because 民主進步黨 fielded only 3 to 7 candidates per term
before 2009.

#### Scenario: A bucket silently emptied by encoding drift
- **WHEN** the lookup table loses the entry that maps a term's encoding of independents
- **THEN** the assertion SHALL fail for that term, naming the term and the bucket

### Requirement: Bucket Membership Has A Single Source
Every page that colours or groups candidates by bucket SHALL derive that grouping from the same
lookup table, emitted by the generator into the page. No page SHALL carry a hand-maintained copy of
the bucket membership.

#### Scenario: The roster page groups by bucket
- **WHEN** the roster page assigns a colour slot to a candidate's party badge
- **THEN** it SHALL use a mapping emitted by the generator, so that a change to the lookup table
  reaches every page without a second hand edit

### Requirement: Colour Is Not The Only Encoding
Charts and badges SHALL convey bucket identity through at least one non-colour channel in addition to
colour, and SHALL NOT assign a colour that is conventionally identified with a specific political
party to a bucket that is not that party.

The verification of colour accessibility SHALL be recorded with the tool used, the colour-vision
deficiency types simulated, and the contrast threshold applied. A bare claim that a palette was
"checked" is not a record.

#### Scenario: Reading the chart without colour
- **WHEN** a reader cannot distinguish the bucket colours
- **THEN** the bucket SHALL still be identifiable from the value labels, badge text, or legend text
  present on the page
