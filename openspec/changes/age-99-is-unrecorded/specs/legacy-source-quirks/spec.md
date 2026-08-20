## ADDED Requirements

### Requirement: Sentinel Values Are Not Presented As Measurements
Where a source column carries a fixed value that stands for "not recorded" rather than a measurement,
the published output SHALL NOT present that value as if it were the measurement. The value SHALL be
preserved unchanged in the long tables; the substitution happens only where the figure is presented.

The measured instance is the candidate age column: it holds `99` for every one of the 483 candidates
in the 1994, 1998, 2002, 2005 and 2006 terms, and never holds `99` in the 2009-2010, 2014, 2018 or
2022 terms, whose ages range from 23 to 89.

#### Scenario: A term whose age column is uniformly the sentinel
- **WHEN** the site presents a candidate from a term in which every age is the sentinel value
- **THEN** it SHALL omit the age rather than state it, so that no claim is made about that person's age

#### Scenario: A term that records real ages
- **WHEN** the site presents a candidate from a term whose age column carries real values
- **THEN** the age SHALL be presented unchanged

### Requirement: Sentinel Recognition Is Named Per Term, Not Global
The set of terms in which a value is treated as a sentinel SHALL be an explicit named list. A value
SHALL NOT be treated as a sentinel merely because it once served that purpose, because the same
number can be a genuine measurement in another term.

Two checks SHALL bound the list, and both SHALL abort the build rather than adjust behaviour silently:
the listed terms SHALL contain no value other than the sentinel, and the unlisted terms SHALL contain
no occurrence of the sentinel.

#### Scenario: A listed term turns out to hold a real value
- **WHEN** a term on the list carries any age other than the sentinel
- **THEN** the build SHALL abort naming that term and the value, because the premise for listing it
  no longer holds and a real age would otherwise be discarded

#### Scenario: An unlisted term starts carrying the sentinel
- **WHEN** a term not on the list carries the sentinel value
- **THEN** the build SHALL abort naming that term, because either the sentinel convention has spread
  to a new term or a genuine value coincides with it, and the two cannot be told apart automatically

### Requirement: Column Semantics Are Taken From The Source Format Document First
The authority for what a source column means is the format document shipped inside the source
archive. Before describing a column's semantics — and before claiming that no such description
exists — that document SHALL be consulted.

Where the format document does define the value, the project's documentation SHALL cite it. Only
where the document has been consulted and found silent may the meaning be described as inferred from
the data, and the documentation SHALL then say which measurement supports the inference.

For the age column the document is explicit: `年齡 Num(3) (部分選舉未必有資料，可能 0 或 99)`.

#### Scenario: A column whose meaning the format document defines
- **WHEN** the project documents what a value in that column means
- **THEN** it SHALL cite the format document, and SHALL NOT describe the meaning as inferred from
  the data distribution

#### Scenario: Two documented no-data values with different ambiguity
- **WHEN** the format document lists more than one no-data value for a column
- **THEN** each SHALL be handled according to whether it could also be a genuine measurement: a
  value outside the plausible range needs no per-term naming, while a value inside it does, because
  only the latter risks discarding a real measurement
