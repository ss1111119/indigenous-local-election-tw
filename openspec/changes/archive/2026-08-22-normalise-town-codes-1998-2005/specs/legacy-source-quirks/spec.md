## ADDED Requirements

### Requirement: Town Codes Re-Numbered Per File Are Resolved Through The Same-Term Regional File
The 1998, 2002, and 2005 plain-indigenous (T2) and mountain-indigenous (T3) county councilor files number their town codes internally, so the same township carries a different code than it does in the same-term regional file. The system SHALL resolve every town in those six files to the same-term regional file's town code and record it in the normalized town column. Resolution SHALL key on the pair (county name, town name), because the county codes in those terms are themselves re-numbered per file and cannot serve as a join key.

The regional file is the canonical target for the term. Agreement between the two files establishes that they can be reconciled; it does not establish that the regional file's codes are externally correct, and documentation SHALL NOT claim the stronger property.

#### Scenario: A town resolves to a different code than it carries locally
- **WHEN** a town in one of the six files matches exactly one town of the same name in the same county of the same-term regional file
- **THEN** the normalized town column SHALL hold the regional file's town code, and the source town column SHALL retain the file's own code unchanged

##### Example: the four resolution outcomes

| Case | Term / type | County | Source name | Source code | Resolved code |
| --- | --- | --- | --- | --- | --- |
| Exact, code differs | 2002 T3 | 屏東縣 | 霧臺鄉 | `033` | `027` |
| Exact, code already agrees | 2005 T2 | 花蓮縣 | 吉安鄉 | `004` | `004` |
| Named alias | 2002 T3 | 嘉義縣 | 里山鄉 | file-local | code of 阿里山鄉 |
| Unknown name | any | any | 火星鄉 | any | **abort** |

Across the six files 1,290 towns resolve, of which 829 receive a code that
differs from the one they carry locally and 4 resolve through a named alias.

#### Scenario: No matching town in the target
- **WHEN** a town name in one of the six files has no same-named town in that county of the regional file, and no named alias covers it
- **THEN** the build SHALL abort naming the term, election type, county, and town name

#### Scenario: More than one matching town in the target
- **WHEN** a town name matches more than one town in that county of the regional file
- **THEN** the build SHALL abort, because a single match reached by chance is not a resolution

#### Scenario: Target-side names are not assumed unique
- **WHEN** the regional file contains two towns with the same name in the same county
- **THEN** the build SHALL abort, and this SHALL be checked at build time rather than relied upon from a one-time census

#### Scenario: Two source towns resolve to one target
- **WHEN** two towns in the same source file resolve to the same (province, county, town) triple in the regional file
- **THEN** the build SHALL abort, because merging two townships keeps every total balanced and leaves no other trace

### Requirement: Truncated Town Names Are Named, Never Pattern-Matched
Four town names in these files are missing their leading character: 里山鄉, 地門鄉, and 麻里鄉 in the 2002 mountain-indigenous file, and 麻里鄉 in the 2005 mountain-indigenous file. The system SHALL resolve these through an explicit alias list keyed on (term, election type, county name, source name) and SHALL NOT use any string rule such as dropping a leading character, matching on a suffix, or edit distance.

The causes are not uniform: in the 2002 mountain-indigenous file no town name exceeds three characters and all three four-character names are truncated, while the 2005 mountain-indigenous file preserves 三地門鄉 and 阿里山鄉 and truncates only 太麻里鄉. A length rule therefore fails on 2005, and a leading-character rule produces false positives against the legitimate two-character district names present in the plain-indigenous files.

#### Scenario: A truncated name resolves through its alias
- **WHEN** a source town name matches an alias entry for that term, election type, and county
- **THEN** the town SHALL resolve to the target named by that alias entry

#### Scenario: An alias entry is never used
- **WHEN** the build completes and an alias entry was not applied
- **THEN** the build SHALL abort, because a stale alias list is itself a defect

#### Scenario: An alias is applied a different number of times than declared
- **WHEN** an alias entry's application count differs from its declared expected count
- **THEN** the build SHALL abort, because "used at least once" does not establish that it was used where intended

#### Scenario: An alias points at a target that does not agree
- **WHEN** an alias entry names a target town code whose name in the regional file differs from the alias's target name
- **THEN** the build SHALL abort

#### Scenario: A new truncation appears in a future source revision
- **WHEN** a source file is revised and introduces a truncated name not covered by the alias list
- **THEN** the build SHALL abort rather than resolve it by inference

### Requirement: An Unresolved Town Is An Abort, Not An Empty Cell
An empty normalized town column previously meant one thing only: that the project performed no town-level normalization for that file. Once resolution is attempted, an empty cell would acquire a second meaning — that a particular row could not be resolved — and the two are indistinguishable downstream. They SHALL NOT share a representation. The system SHALL either write a resolved code or abort the build; it SHALL NOT write an empty value to represent a failed lookup.

#### Scenario: Resolution fails partway through a file
- **WHEN** any town in a covered file cannot be resolved
- **THEN** the build SHALL abort and SHALL NOT write an empty normalized value for that row, because a downstream reader cannot distinguish a deliberate blank from a failed lookup

## RENAMED Requirements

- FROM: `### Requirement: Normalization Depth Is Limited To County Level`
- TO: `### Requirement: Normalization Depth Reaches Township, Not Below`

## MODIFIED Requirements

### Requirement: Normalization Depth Reaches Township, Not Below
The system SHALL output the source administrative codes unchanged and SHALL add separate
normalized columns. The county normalized column SHALL carry the same-term regional code.
The town normalized column SHALL also carry the same-term regional code, resolved through
the town crosswalk for files whose town codes are renumbered file-locally. Normalization
now reaches township level; it SHALL NOT reach village or polling-station level, because
the files that renumber their town codes contain no rows below township.

The town normalized column SHALL NOT be empty for any file. Leaving it empty would make
one representation carry two meanings — "this file needs no normalization" and "this row
could not be resolved" — and a downstream reader cannot tell those apart.

#### Scenario: Town codes are renumbered file-locally
- **WHEN** processing the 1998, 2002, or 2005 mountain- or plain-indigenous county councilor
  files, whose town codes are renumbered from `001` within each file
- **THEN** the town normalized column SHALL carry the same-term regional file's town code,
  and the source town column SHALL retain the file's own code unchanged

#### Scenario: County codes became term-global before town codes did
- **WHEN** processing 2005 files
- **THEN** the county code SHALL need no crosswalk conversion, but the town code SHALL still
  require it — "term-global from 2005" holds at county level only

#### Scenario: Combined indigenous city councilor files
- **WHEN** processing the 1994, 1998, 2002, or 2006 combined indigenous city councilor files,
  whose county and town codes match the same-term city regional file exactly
- **THEN** both normalized columns SHALL carry the source codes

#### Scenario: Rows above township level
- **WHEN** a row aggregates above township level, so its source town code is all zeros
- **THEN** the town normalized column SHALL carry that same all-zero code, matching what
  every other file emits for such rows, rather than being left empty

#### Scenario: Normalization is not extended below township
- **WHEN** considering village or polling-station level normalization for these files
- **THEN** it SHALL NOT be added, because those files contain no rows at those levels and a
  normalization declared for a level with no data is a rule that can never be exercised
