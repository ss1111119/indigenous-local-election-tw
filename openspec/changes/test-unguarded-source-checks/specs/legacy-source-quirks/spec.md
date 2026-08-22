## ADDED Requirements

### Requirement: A Compensating Check Is Not Considered Tested Until An Input Exists That Trips It
This capability's standing response to a source defect is a named exception plus a compensating check. A compensating check whose condition never becomes true on the available data is indistinguishable from one that has been deleted: the build passes, the output is byte-identical, and no test turns red. Every such check SHALL therefore have an input that makes its condition true and its abort observable. A check without one SHALL NOT be described as tested, in documentation or in commit messages.

#### Scenario: A guard is disabled and nothing turns red
- **WHEN** a compensating check is changed so that its condition can never be true
- **THEN** at least one test SHALL fail, and the failure SHALL be attributable to that specific check rather than to a general build failure

#### Scenario: A guard has never fired on the available data
- **WHEN** a check's condition has not become true on any source file the project has processed
- **THEN** this SHALL NOT be taken as evidence that the condition is impossible, and the check SHALL NOT be removed as dead code on that basis alone

#### Scenario: Distinguishing "not yet triggered" from "cannot trigger"
- **WHEN** deciding whether a check is redundant
- **THEN** the decision SHALL rest on measurement of whether the branch is reached, not on reading the surrounding code, because a branch that executes but whose condition is false is reachable by definition

#### Scenario: Another check intercepts the input first
- **WHEN** an input intended to trip one check is caught by a different check earlier in the pipeline
- **THEN** the test SHALL be treated as not yet covering its target, because an abort from elsewhere proves nothing about the check under test

#### Scenario: A check is made vacuous rather than removed
- **WHEN** a change makes a check's assertion always hold instead of removing the check
- **THEN** the test SHALL assert on a value that the change alters, not on whether the build aborted, because a vacuous assertion aborts on nothing
