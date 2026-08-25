## ADDED Requirements

### Requirement: Semantic word-break points for static Chinese headings
The generator SHALL insert `<wbr>` elements at BudouX-computed semantic segment boundaries inside the plain-text content of every `<h1>` and `<h2>` element in `docs/index.html` and `docs/legislative.html`, and SHALL NOT alter the visible text of those headings.

#### Scenario: Heading with multiple semantic segments
- **WHEN** the generator processes an `<h1>` or `<h2>` whose text BudouX segments into two or more chunks
- **THEN** the rewritten element contains a `<wbr>` between each pair of adjacent chunks, and the text with all `<wbr>` and `<br>` tags stripped is byte-identical to the original text

#### Scenario: Heading with a single semantic segment
- **WHEN** the generator processes an `<h1>` or `<h2>` whose text BudouX segments into exactly one chunk (for example a two-character label such as "性別")
- **THEN** the rewritten element contains zero `<wbr>` tags, and this is not a failure condition

#### Scenario: Existing manual line break is replaced
- **WHEN** the generator processes `docs/index.html`'s `<h1>`, which currently contains a hand-written `<br>`
- **THEN** the rewritten `<h1>` contains no hand-written `<br>`, and any line breaks present are `<wbr>` tags produced by the BudouX segmentation of the element's text

#### Scenario: Unsupported heading markup aborts the build
- **WHEN** an `<h1>` or `<h2>` in `docs/index.html` or `docs/legislative.html` contains child markup other than plain text or a `<br>` tag
- **THEN** the generator raises an error naming the file and the offending heading, and does not write any output file

### Requirement: Idempotent heading rewrite
Re-running the generator against its own previous output SHALL produce zero changes to the heading markup.

#### Scenario: Second consecutive run is a no-op
- **WHEN** the generator is run twice in succession against the same source heading text, with no other content changes between runs
- **THEN** the second run's output HTML for every `<h1>` and `<h2>` is byte-identical to the first run's output

### Requirement: CSS enforces the semantic break points at all widths
`docs/index.html` and `docs/legislative.html` SHALL each declare `word-break: keep-all` and `overflow-wrap: anywhere` on their `h1` and `h2` CSS rules, so that `<wbr>`-marked segment boundaries take precedence over the browser's default per-character line-breaking for CJK text at any viewport width.

#### Scenario: Narrow viewport does not split a semantic chunk
- **WHEN** a heading containing a `<wbr>`-marked BudouX chunk (for example "投票率") is rendered at a viewport narrow enough that the heading wraps
- **THEN** the line break falls only at a `<wbr>` boundary, never inside a chunk that BudouX identified as a single semantic unit

### Requirement: Scope limited to static Chinese page headings
The generator SHALL apply heading segmentation only to `<h1>` and `<h2>` elements in `docs/index.html` and `docs/legislative.html`, and SHALL NOT modify heading text in `docs/en/index.html`, `docs/en/legislative.html`, or the JS-generated county headings in `docs/roster.html`.

#### Scenario: English pages are untouched
- **WHEN** the generator runs
- **THEN** `docs/en/index.html` and `docs/en/legislative.html` are not modified by the heading segmentation step

#### Scenario: Roster's runtime-generated headings are untouched
- **WHEN** the generator runs
- **THEN** the JS template literal in `docs/roster.html` that produces `<h2>${county}</h2>` at runtime is not modified by the heading segmentation step
