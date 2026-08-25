# site-offline-resource-policy Specification

## Purpose

The site is a set of static GitHub Pages, and its design has long assumed
that pages can be opened offline, shared as single files, and opened
directly via `file://` without hitting CORS restrictions — `fetch()` calls
were explicitly avoided for this reason. That assumption was never checked
against the actual published pages: they linked to Google Fonts, silently
breaking the offline promise until a design review caught it by hand.

This capability governs the site's commitment to loading no external
network resources, and the automated check that turns that commitment into
something the build enforces rather than something documented and hoped
for. It covers what counts as an external resource (any `http(s)://`
reference other than the fixed, non-fetching SVG namespace URI) and the
requirement that typography fall back to generic or system font families
instead of naming a typeface that depends on an external font service.

## Requirements

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


<!-- @trace
source: remove-external-font-dependency
updated: 2026-08-25
code:
  - docs/index.html
  - docs/roster.html
  - docs/en/index.html
  - docs/legislative.html
  - docs/en/legislative.html
  - scripts/build_site_data.py
  - README.md
tests:
  - scripts/test_build_site_data.py
-->

---
### Requirement: Typography falls back to generic or system font keywords, never a named external typeface
Every `font-family` declaration across the published pages (in `<style>` blocks and in inline JS that sets SVG text styling) SHALL resolve using only generic CSS font families (`serif`, `sans-serif`, `monospace`) or system font keywords (such as `ui-monospace`), never a named typeface that depends on an external font service.

#### Scenario: A CSS font-family stack no longer names an external typeface
- **WHEN** a `<style>` block's `font-family` declaration is inspected on any of the five published pages
- **THEN** it does not contain the strings `"IBM Plex Mono"`, `"Noto Sans TC"`, or `"Noto Serif TC"`, and still names at least one generic or system font family

#### Scenario: An inline SVG font-family attribute no longer names an external typeface
- **WHEN** the JS code that sets `"font-family"` on SVG elements is inspected on `docs/index.html`, `docs/legislative.html`, `docs/en/index.html`, and `docs/en/legislative.html`
- **THEN** the attribute value does not contain the string `"IBM Plex Mono"`, and still names a generic font family such as `"monospace"`

<!-- @trace
source: remove-external-font-dependency
updated: 2026-08-25
code:
  - docs/index.html
  - docs/roster.html
  - docs/en/index.html
  - docs/legislative.html
  - docs/en/legislative.html
  - scripts/build_site_data.py
  - README.md
tests:
  - scripts/test_build_site_data.py
-->