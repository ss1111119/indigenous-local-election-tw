## ADDED Requirements

### Requirement: T2 and T3 Main Sequence Inclusion
The system SHALL include the 1998, 2002, and 2005 mountain indigenous (T3) and plain indigenous (T2) county councilors in the dataset and flag them as part of the main sequence.

#### Scenario: Processing 1998-2005 T2-T3 files
- **WHEN** processing 1998, 2002, and 2005 county councilor files
- **THEN** the output records SHALL have the `is_main_sequence` flag set to true

### Requirement: Custom Election Type Codes
The system SHALL assign custom, project-specific election type codes for 1994 Taiwan Provincial Councilors and the "combo" indigenous city councilor category (which exists across multiple early terms).

#### Scenario: Assigning codes to 1994 provincial councilors
- **WHEN** processing 1994 provincial councilor files
- **THEN** the system SHALL assign a new custom code distinct from T2 and T3

#### Scenario: Assigning codes to combo indigenous city councilors
- **WHEN** processing combo indigenous city councilors
- **THEN** the system SHALL assign a custom combo code distinct from T2 and T3

### Requirement: Comparability Flags
The output long datasets SHALL include new flag columns: `is_main_sequence` (boolean) and `admin_code_system` (string) to indicate the schema year of the administrative codes.

#### Scenario: Flagging non-main sequence records
- **WHEN** the record is a 1994 provincial councilor or a combo indigenous city councilor
- **THEN** the `is_main_sequence` flag SHALL be set to false

#### Scenario: Setting admin code system version
- **WHEN** processing files from a specific election year
- **THEN** the `admin_code_system` SHALL reflect the corresponding system version
