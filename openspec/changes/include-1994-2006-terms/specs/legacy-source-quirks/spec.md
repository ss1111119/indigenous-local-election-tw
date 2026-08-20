## ADDED Requirements

### Requirement: Relational Key Field Trailing Whitespace Normalization
The system SHALL strip surrounding whitespace from **relational key fields** — the
administrative code columns, the candidate number (`號次`) column, and the party code
columns — across all legacy and current files when reading CSVs. The key fields SHALL be
declared per source file kind as an explicit whitelist.

The system SHALL NOT normalize non-key fields. Values the project preserves verbatim
(`得票率`, `人口數`, `投票率`) and the officially defined four-value elected mark domain
(where a single space `" "` means "not elected") SHALL be read exactly as the source
provides them.

#### Scenario: Parsing unquoted codes with trailing spaces
- **WHEN** the administrative code in the raw CSV is "0 "
- **THEN** the system SHALL parse and store it as "0"

#### Scenario: Joining candidate numbers across files with inconsistent padding
- **WHEN** the 2005 `elctks` candidate number is "1 " and the same candidate's `elcand`
  candidate number is "1"
- **THEN** the system SHALL normalize both to "1" so the cross-file reference resolves

#### Scenario: Preserving whitespace in non-key fields
- **WHEN** a vote-share field is "1.58 " or an elected mark field is " "
- **THEN** the reader SHALL leave the value unchanged, because those columns are either
  preserved verbatim by project discipline or carry meaning in the official value domain

### Requirement: County Code Crosswalk
The system SHALL map the internally re-numbered county codes in the 1998 and 2002 T2 and T3 files to the authoritative regional codes for that term using a version-controlled crosswalk CSV.

#### Scenario: Resolving 1998 and 2002 county codes
- **WHEN** processing 1998 or 2002 T2 or T3 files
- **THEN** the system SHALL look up the internal county code in the crosswalk table and use the corresponding regional code

#### Scenario: Mismatched county names
- **WHEN** a county name does not match the crosswalk table
- **THEN** the system SHALL abort the build

##### Example: the three-step resolution

| Case | `local_code` | In crosswalk? | Same-term regional file | Result |
| --- | --- | --- | --- | --- |
| Mapped | `01005` (嘉義縣) | yes → `01010` | `01010` is 嘉義縣 | `010` |
| Identity | `01001` (臺北縣) | no | `01001` is 臺北縣 | `001` |
| Unknown code | `01999` (火星縣) | no | absent | **abort** |
| Name mismatch | `01001` (桃園縣) | no | `01001` is 臺北縣 | **abort** |
| Three-way name mismatch | `01005` (嘉義市) | yes → `01010` | `01010` is 嘉義縣 | **abort** |

#### Scenario: Crosswalk row never used
- **WHEN** the crosswalk contains a row for a term and election type that was processed, but
  no source record resolved through it
- **THEN** the build SHALL abort. Usage SHALL be judged including `elbase`, because the 1998
  plain-indigenous 嘉義縣 code appears only in `elbase` and would otherwise be misjudged as
  a stale row

### Requirement: Normalization Depth Is Limited To County Level
The system SHALL output the source administrative codes unchanged and SHALL add separate
normalized columns. The county normalized column SHALL carry the same-term regional code.
The town normalized column SHALL be empty for files whose town codes are renumbered
file-locally, rather than carrying the un-normalized source code.

#### Scenario: Town codes are renumbered file-locally
- **WHEN** processing the 1998, 2002, or 2005 mountain- or plain-indigenous county councilor
  files, whose town codes are renumbered from `001` within each file
- **THEN** the town normalized column SHALL be empty, so that a downstream join on the
  normalized columns fails to match rather than matching the wrong district

#### Scenario: County codes became term-global before town codes did
- **WHEN** processing 2005 files
- **THEN** the county code SHALL need no crosswalk conversion, but the town normalized column
  SHALL still be empty — "term-global from 2005" holds at county level only

#### Scenario: Combined indigenous city councilor files
- **WHEN** processing the 1994, 1998, 2002, or 2006 combined indigenous city councilor files,
  whose county and town codes match the same-term city regional file exactly
- **THEN** both normalized columns SHALL carry the source codes

### Requirement: Population String Preservation and Level Restriction
The system SHALL preserve the population field as a string exactly as provided (including decimal points) and SHALL restrict its valid applicability to county-level and above.

#### Scenario: Processing population values with decimals
- **WHEN** the population field contains "206740.12"
- **THEN** the system SHALL output "206740.12" without casting it to an integer

#### Scenario: Processing invalid population values at town level
- **WHEN** a population value exists for a town-level or village-level record
- **THEN** the system SHALL flag the population value with an applicability level indicator

##### Example: applicability by administrative level

| Administrative level | `人口數適用層級` |
| --- | --- |
| 檔別合計 | 縣市以上 |
| 直轄市縣市 | 縣市以上 |
| 選舉區 | 低於縣市_不適用 |
| 鄉鎮市區 | 低於縣市_不適用 |
| 村里 | 低於縣市_不適用 |
| 投開票所 | 低於縣市_不適用 |

#### Scenario: Electoral-district level is below county level
- **WHEN** the record is at the 選舉區 (electoral district) level
- **THEN** the system SHALL flag it as not applicable, because the requirement restricts
  applicability to county level and above and no oracle establishes validity below it

#### Scenario: Applicability does not assert value validity
- **WHEN** a record at county level or above is flagged `縣市以上`
- **THEN** the flag SHALL be read as "the column is applicable at this level" and NOT as
  "this value has been verified" — county-level values include non-integer figures
  (e.g. "206740.121634792") that cannot be a headcount, and the column has no arithmetic
  oracle and no verified upstream source

### Requirement: Authoritative Elected Status Derivation
The system SHALL preserve the `elcand` elected status column and the `當選` field derived
from it exactly as the source provides them, including where the source is known to be
corrupt (the 2005 county councilor files), and SHALL derive a separate
`elected_authoritative` field from the `elctks` vote breakdown, together with an
`elected_authoritative_basis` field recording which administrative level the value came
from.

Matching a candidate to `elctks` rows SHALL constrain only those administrative code
columns that are non-blank on the candidate record, and SHALL take the marks from the
highest administrative level among the matching rows. The elected marks are `*` and `!`
(both appear in `elctks`).

The system SHALL abort rather than guess when a candidate has no matching `elctks` row,
or when the marks at the chosen level disagree.

#### Scenario: Deriving elected status from vote breakdown
- **WHEN** the candidate's mark at the highest matching `elctks` level is `*` or `!`
- **THEN** `elected_authoritative` SHALL be true

#### Scenario: Candidate record is less specific than the vote breakdown
- **WHEN** the candidate's town column is blank (`000`) and the only `elctks` rows for that
  candidate are at town level — as for the 2005 mountain-indigenous Pingtung 16th district,
  which has no district-level aggregate row
- **THEN** the blank column SHALL NOT constrain the match, the value SHALL be derived from
  the town-level rows, and `elected_authoritative_basis` SHALL record `elctks_鄉鎮市區`

#### Scenario: Candidate record is less specific but the town column distinguishes candidates
- **WHEN** the candidate's electoral-district column is blank (`00`), as for indigenous
  district chief (D2) and district representative (R3) elections whose real unit is the town
- **THEN** the town column SHALL still constrain the match, so that candidates sharing a
  number in different towns are not merged

#### Scenario: Lower levels carry no mark information
- **WHEN** a candidate has rows at both district and town level, and the town-level marks
  are blank as in the 2002 plain-indigenous file
- **THEN** the district-level mark SHALL be used, because it is the highest matching level

#### Scenario: No elctks row for a candidate
- **WHEN** a candidate has no matching `elctks` row at any level
- **THEN** the build SHALL abort. The system SHALL NOT fall back to inferring election from
  `elprof` candidate/elected counts: no candidate in any covered file lacks an `elctks` row,
  and such a fallback would silently mark a whole district elected if `elctks` rows were
  lost, while still satisfying the per-district compensating check

#### Scenario: Conflicting marks at the chosen level
- **WHEN** the marks at the highest matching level disagree
- **THEN** the build SHALL abort rather than take a majority or treat any asterisk as elected

### Requirement: Elected Status Compensating Checks
The system SHALL validate `elected_authoritative` independently of the existing `elcand`
checks, so that adding the derived field does not remove the ability to detect `elcand`
corruption.

#### Scenario: Existing elcand checks stay unchanged
- **WHEN** the build validates `elprof` elected counts against `elcand`
- **THEN** that check SHALL continue to use the `elcand`-derived `當選` field

#### Scenario: Authoritative totals must reconcile
- **WHEN** the build validates `elected_authoritative`
- **THEN** the count SHALL equal the `elprof` elected count for the file, and for every
  electoral district present at district level in `elprof`

#### Scenario: Disagreement with elcand must be named per candidate
- **WHEN** `elected_authoritative` disagrees with the `elcand`-derived `當選`
- **THEN** the build SHALL abort unless that candidate is listed individually in the known
  anomaly set, and SHALL also abort if the set of disagreeing candidates is not exactly the
  listed set — naming a whole file SHALL NOT be accepted
