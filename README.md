# Text Cleanroom

A lightweight, deterministic toolkit for analyzing and fixing problematic text artifacts in filenames and text files drawn from real-world datasets.

## Overview

This project provides tools for:

- detecting filename inconsistencies
- identifying encoding issues (e.g., `%20` vs literal space)
- reporting problematic patterns in a structured, reproducible way
- preparing data for normalization and correction pipelines
- implementing those normalization and correction pipelines

It is designed for messy, human-generated inputs such as:

- exported spreadsheets
- copy/pasted filename lists
- mixed encoding environments
- partially structured HTML/text artifacts
- text originating from heterogeneous sources, including Office exports and poorly encoded web content

---

## Design Intent

Many real-world datasets fail—not because of model limitations—but because of inconsistencies in text representation.

This toolkit focuses on making those inconsistencies visible, measurable, and correctable before downstream processing.

---

## Features

### Detection and Reporting

- Detection of:
  - literal spaces
  - percent-encoded spaces (`%20`)
  - mixed or inconsistent encoding patterns
- Highlighting of problematic spans (CLI-friendly and editor-friendly modes)
- CSV output for downstream analysis
- Foundation for comm-style comparison reports

### Correction (Fixing Passes)

- Filename normalization and repair
- Repair of text files with inconsistent or unusable encodings

### Normalization / Denormalization Pipelines

Primarily designed for transcript preparation and comparability tasks, but modular enough for independent use.

Includes:

- Case normalization (`.lower`, `casefold`)
- Punctuation removal
- ASCII normalization (including lossy multilingual → ASCII transforms where appropriate)
- Handling of:
  - numbers
  - time expressions
  - hyphenated words (for comparability)
  - units of measure
  - alternate spellings (intranational and international)
  - acronyms and initialisms
  - URLs and email addresses
  - proper-name homonyms
  - postal addresses

---

## Philosophy

This toolkit is built around a few guiding principles:

- **Determinism over heuristics**
- **Observability before correction**
- **Reproducibility and auditability**
- **Separation of concerns** (reporting vs fixing vs normalization)
- **Robustness to messy, real-world data**

---

## Project Scope

This repository includes components of a broader personal toolkit for:

- text normalization
- encoding and decoding workflows
- filename analysis and correction

The goal is to make these tools usable both independently and as part of larger pipelines.

See:

- `PROVENANCE.md`

for details on provenance, scope, and usage boundaries.

---

## Installation (local development)

```bash
pip install -e .
```

## Usage (example)
```Bash
text-cleanroom --input file1.txt file2.txt
```

## Status

Still collecting many tools and writing them so they're in one place, coding more cleanly, etc., so it's progressing quickly while actively evolving.

The current focus is on:

- reliable detection from different inputs
- structured reporting

## License

This project is licensed under the MIT License.

See LICENSE for details.


## Notes

This project reflects a preference for:

- ASCII-safe representations where appropriate
- reproducible transformations
- explicit handling of edge cases over silent assumptions

It is intended for use across professional, personal, and research contexts involving real-world, imperfect text data.

