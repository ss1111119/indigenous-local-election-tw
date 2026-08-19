## ADDED Requirements

### Requirement: Administrative Code Trailing Whitespace Normalization
The system SHALL strip trailing whitespaces from administrative code fields across all legacy and current files when reading CSVs.

#### Scenario: Parsing unquoted codes with trailing spaces
- **WHEN** the administrative code in the raw CSV is "0 "
- **THEN** the system SHALL parse and store it as "0"

### Requirement: County Code Crosswalk
The system SHALL map the internally re-numbered county codes in the 1998 and 2002 T2 and T3 files to the authoritative regional codes for that term using a version-controlled crosswalk CSV.

#### Scenario: Resolving 1998 and 2002 county codes
- **WHEN** processing 1998 or 2002 T2 or T3 files
- **THEN** the system SHALL look up the internal county code in the crosswalk table and use the corresponding regional code

#### Scenario: Mismatched county names
- **WHEN** a county name does not match the crosswalk table
- **THEN** the system SHALL abort the build

### Requirement: Population String Preservation and Level Restriction
The system SHALL preserve the population field as a string exactly as provided (including decimal points) and SHALL restrict its valid applicability to county-level and above.

#### Scenario: Processing population values with decimals
- **WHEN** the population field contains "206740.12"
- **THEN** the system SHALL output "206740.12" without casting it to an integer

#### Scenario: Processing invalid population values at town level
- **WHEN** a population value exists for a town-level or village-level record
- **THEN** the system SHALL flag the population value with an applicability level indicator

### Requirement: Authoritative Elected Status Derivation for 2005
The system SHALL preserve the corrupted elcand elected status column for 2005 files but SHALL derive a new `elected_authoritative` boolean field by checking the candidate asterisk in the elctks vote breakdown file, falling back to elprof summary elected counts if the elctks record is missing.

#### Scenario: Deriving elected status from vote breakdown
- **WHEN** the candidate has an asterisk in the elctks file for 2005
- **THEN** the `elected_authoritative` flag SHALL be set to true

#### Scenario: Deriving elected status for uncontested elections
- **WHEN** the elctks record is missing but the elprof file indicates seats were won
- **THEN** the system SHALL infer the `elected_authoritative` status based on the candidate count matching the elected count in elprof
