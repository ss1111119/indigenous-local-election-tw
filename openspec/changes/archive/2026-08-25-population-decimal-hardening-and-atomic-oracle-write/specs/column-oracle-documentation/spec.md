## ADDED Requirements

### Requirement: Population column validation rejects non-finite and non-string values
The shared population-column check SHALL reject values that are not finite decimal numbers (including `Infinity`, `-Infinity`, and `NaN`) and values that are not strings, raising the project's unified validation exception in both cases, distinguishable from the "not a decimal number" and "negative value" failure messages.

#### Scenario: Infinity is rejected
- **WHEN** a row's population column value is `"Infinity"` or `"-Infinity"`
- **THEN** the build aborts with the project's unified validation exception, with a message distinguishable from the "not a decimal number" and "negative value" messages

#### Scenario: NaN is rejected without an unhandled exception
- **WHEN** a row's population column value is `"NaN"`
- **THEN** the build aborts with the project's unified validation exception, and no unrelated exception type (such as `decimal.InvalidOperation` propagating uncaught from a subsequent comparison) is raised instead

#### Scenario: A non-string input is rejected with the unified exception type
- **WHEN** a row's population column value is not a string (for example `None`)
- **THEN** the build aborts with the project's unified validation exception rather than an unwrapped `TypeError`

#### Scenario: Valid finite non-negative values still pass
- **WHEN** a row's population column value is a finite non-negative decimal string (including `"0"` and strings with a fractional component)
- **THEN** the check does not raise any exception

### Requirement: The shared oracle document is written atomically
Writing `docs/schema/oracles.md` SHALL be atomic: the file SHALL always contain either its complete previous content or its complete new content, never a partial or interleaved write, regardless of which build script performs the write or whether the write is interrupted.

#### Scenario: A completed write replaces the file wholesale
- **WHEN** a build script finishes generating the oracle document content
- **THEN** the file on disk is replaced via an atomic filesystem operation rather than being overwritten in place, and its content after the write exactly matches the freshly generated content

#### Scenario: Both build scripts share one write path
- **WHEN** either `scripts/build_local_election.py` or `scripts/build_legislative_election.py` writes the oracle document
- **THEN** both invoke the same shared write function rather than each independently constructing the target path and performing its own file write
