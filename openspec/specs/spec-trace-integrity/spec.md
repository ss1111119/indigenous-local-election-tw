# spec-trace-integrity Specification

## Purpose

Each requirement carries trace metadata naming the files it relates to, injected
when a change is archived from whatever the working tree happened to contain at
the time. That origin makes the metadata prone to two kinds of rot: paths that
resolve only on the author's machine, and paths that resolved once and no longer
do because a file moved.

This capability governs the part of that rot which can be settled objectively —
whether a path points at something a reader who obtains the project can actually
open. It deliberately does not govern whether the association itself is correct,
because that question has no test: deciding which file implements a given
requirement is a judgement, and a judgement written into metadata reads exactly
like a verified fact.

The check that enforces this is required to fail rather than degrade, because
the two ways it can be hollowed out — an environment without version control,
and an empty input set — both produce a clean result for the wrong reason. And
what the check does not establish is required to be written down, because
metadata whose paths all resolve invites more trust than metadata that is
visibly broken.

## Requirements

### Requirement: A trace entry points to something a reader can actually obtain
Trace metadata exists so that someone who did not write the change can find what a requirement relates to. A path that resolves only on the author's machine does not serve that purpose, and a path that resolves nowhere serves it less.

Every path recorded in a requirement's trace SHALL be a file under version control. Presence on disk SHALL NOT be accepted as sufficient, because directories excluded from version control exist for the author and for no one else.

#### Scenario: A trace path is present locally but excluded from version control
- **WHEN** a trace entry names a file that exists on the author's machine but is not tracked
- **THEN** it SHALL be treated as a broken entry, because a reader who obtains the project cannot follow it

#### Scenario: A trace path names a file that has been moved
- **WHEN** the file a trace entry names has moved to another directory and remains under version control
- **THEN** the entry SHALL be corrected to the current path rather than deleted, because the association it records is still true and only its location is stale

#### Scenario: The moved file cannot be identified with confidence
- **WHEN** a broken entry cannot be matched to a current file with confidence
- **THEN** it SHALL be removed rather than repointed at a guess

---
### Requirement: The integrity check fails rather than degrades when it cannot do its job
A check that quietly weakens when its inputs are unavailable reports success for the wrong reason. Two ways this check can be hollowed out are an environment where version control is unavailable, and an input set that is empty.

The check SHALL abort and name the reason when it cannot determine which files are tracked, and SHALL NOT fall back to testing whether files exist. It SHALL also abort when it finds no specifications or no trace blocks to examine, because a clean result drawn from nothing is indistinguishable from a clean result drawn from everything.

#### Scenario: Version control information is unavailable
- **WHEN** the check cannot obtain the list of tracked files
- **THEN** it SHALL abort naming that reason, because falling back to a presence test would pass exactly the entries it exists to catch

#### Scenario: No specifications are found
- **WHEN** the check finds no specification files, or finds specifications but no trace blocks
- **THEN** it SHALL abort, because reporting no violations from no input reads as a passing check

#### Scenario: A broken entry is found
- **WHEN** any trace entry fails the check
- **THEN** the failure SHALL name the capability, the requirement, and the path, because a count alone does not tell anyone where to look

---
### Requirement: The check has an execution point, and what it does not verify is written down
A rule that nothing runs is not a rule. This project has already published a wrong figure because a check that would have caught it existed but was never invoked.

The integrity check SHALL be reachable from the project's existing verification entry point rather than existing only as a standalone script.

Passing this check SHALL NOT be presented as evidence that the trace metadata is correct. It establishes only that the paths resolve. Where trace entries are known to carry paths unrelated to the requirement they sit under, and where requirements are known to carry no trace at all, both SHALL be recorded in the project's handover notes rather than left for a reader to discover.

#### Scenario: The check exists but nothing invokes it
- **WHEN** the check is added as a standalone script with no caller
- **THEN** that SHALL be treated as incomplete, because an uninvoked check is indistinguishable from an absent one

#### Scenario: The cleanup makes the metadata look more reliable than it is
- **WHEN** broken entries are removed and every remaining path resolves
- **THEN** the remaining unreliability SHALL be recorded, because paths that all resolve invite the reader to trust associations that were never verified

#### Scenario: A requirement carries no trace at all
- **WHEN** a requirement has no trace block
- **THEN** that absence SHALL be left as it is and recorded, rather than filled in with an inferred association
