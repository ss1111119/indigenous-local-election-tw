## ADDED Requirements

### Requirement: Cross-Term Party Encoding Drift Is Named, Not Inferred
Where the source encodes the same party or party status under different codes or different names in
different terms, the project SHALL record the correspondence as an explicit named entry rather than
inferring it from string similarity, substring matching, or a shared code.

The measured drift in this dataset is: independents are code `99` name 「無」 in 1994 through 2006 and
code `999` name 「無黨籍及未經政黨推薦」 from 2009 onward; 民主進步黨 is code `2` before 2009 and code
`16` from 2009 while keeping one name; 新黨, 親民黨, 台灣團結聯盟, 無黨團結聯盟 and 勞動黨 each carry two
codes across eras; and codes `166`, `199`, `254`, `290` and `303` each carry two different names.

#### Scenario: Correspondence asserted without an explicit entry
- **WHEN** a rule would merge two source party identities on the basis of similar names or a shared
  code, without a named entry recording that they are the same entity
- **THEN** the project SHALL NOT merge them

#### Scenario: Substring matching on the independent category
- **WHEN** a rule matches independents by testing whether the party name contains 「無」 or starts with
  「無黨」
- **THEN** that rule is incorrect, because 無黨團結聯盟 is a distinct registered party that such a rule
  would absorb

### Requirement: A Silently Zeroed Series Is Treated As A Defect
Where a category is present in the source for a term but reaches the published output with a count of
zero, that SHALL be treated as a defect in the classification, not as a fact about the term.

#### Scenario: Independents present in source but absent from output
- **WHEN** the source for a term contains rows whose party identity denotes independents, and the
  published output reports zero independents for that term
- **THEN** this SHALL be recorded as a classification defect and corrected, rather than published as
  a finding that no independents contested that term
