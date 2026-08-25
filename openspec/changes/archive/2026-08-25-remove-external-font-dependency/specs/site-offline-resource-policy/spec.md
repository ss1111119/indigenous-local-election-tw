## ADDED Requirements

### Requirement: Published pages load no external network resources
Every `.html` file under `docs/` SHALL contain no reference to an external network resource (an `http://` or `https://` URL pointing outside the document itself), with the sole exception of the fixed SVG namespace URI `http://www.w3.org/2000/svg`, which does not trigger a network request and is not an external resource in this sense.

#### Scenario: A page referencing Google Fonts fails the check
- **WHEN** a `.html` file under `docs/` contains a `<link>` or `<script>` tag pointing to `fonts.googleapis.com`, `fonts.gstatic.com`, or any other external host
- **THEN** the build aborts with an error naming the file and the external reference found

#### Scenario: The SVG namespace URI does not trigger a false positive
- **WHEN** a `.html` file contains the literal string `http://www.w3.org/2000/svg` (used by `document.createElementNS`) and no other `http://` or `https://` reference
- **THEN** the check does not raise an error

#### Scenario: The five published pages pass the check
- **WHEN** `scripts/build_site_data.py` is run with `--check` or `--write` against the current `docs/index.html`, `docs/roster.html`, `docs/legislative.html`, `docs/en/index.html`, and `docs/en/legislative.html`
- **THEN** the check passes for all five files

### Requirement: Typography falls back to generic or system font keywords, never a named external typeface
Every `font-family` declaration across the published pages (in `<style>` blocks and in inline JS that sets SVG text styling) SHALL resolve using only generic CSS font families (`serif`, `sans-serif`, `monospace`) or system font keywords (such as `ui-monospace`), never a named typeface that depends on an external font service.

#### Scenario: A CSS font-family stack no longer names an external typeface
- **WHEN** a `<style>` block's `font-family` declaration is inspected on any of the five published pages
- **THEN** it does not contain the strings `"IBM Plex Mono"`, `"Noto Sans TC"`, or `"Noto Serif TC"`, and still names at least one generic or system font family

#### Scenario: An inline SVG font-family attribute no longer names an external typeface
- **WHEN** the JS code that sets `"font-family"` on SVG elements is inspected on `docs/index.html`, `docs/legislative.html`, `docs/en/index.html`, and `docs/en/legislative.html`
- **THEN** the attribute value does not contain the string `"IBM Plex Mono"`, and still names a generic font family such as `"monospace"`
