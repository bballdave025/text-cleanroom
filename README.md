# Text Cleanroom

A lightweight, deterministic toolkit for analyzing and fixing problematic filenames and text artifacts in real-world datasets.

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
- text files coming from a variety of sources and having a variety of (sometimes mixed) encodings, including with messily-encoded websites, notably those with text pasted from Microsoft Office products and elsewhere

- 

## Features

- Detection of:
  - literal spaces
  - percent-encoded spaces (`%20`)
  - mixed or inconsistent encoding patterns
- Highlighting of problematic spans (CLI-friendly and editor-friendly modes)
- CSV output for downstream analysis
- Foundation for comm-style comparison reports
- Designed to support later normalization and fixing passes
- Fixing passes
  - Fixing filenames
  - Fixing files with otherwise unusable encodings
- Denormalization passes
  - mostly used for transcript normalization before scoring
  - modularized for use as part of a transcript-preparation pipeline as well as for usage of any step, independently
    - `.tolower` and `casefold` style processing
    - remove punctuation
    - ASCII-ise everything, including a (non-one-to-one) process to go from multilingual to ASCII
    - numbers
    - time of day
    - many more text processing use cases, including handling of hyphenated words for comparability
    - many more-involved NLP use cases for correctness and comparability, including handling of
      - units of measure
      - alternate accepted spellings&mdash; intranationally and internationally
      - acronyms/initialisms/hybrids
      - URL and email addresses
      - proper name homonyms
      - postal addresses handling

## Philosophy

This toolkit is built around a few guiding principles:

- **Determinism over heuristics**
- **Observability before correction**
- **Reproducibility and auditability**
- **Separation of concerns** (reporting vs fixing vs normalization)
- **Robustness to messy, real-world data**

## Project Scope

This repository includes pieces of a broad personal toolkit for:

- text normalization
- encoding/decoding workflows
- filename analysis and correction

See:

- `PROVENANCE.md`

for details on provenance and scope.

## Installation (local development)

```bash
pip install -e .
```

or

```Windows PowerShell
pip install -e .
```

# Original `text-cleanroom` description

Text encoding, decoding, normalization, etc. I like keeping things ASCII with no spaces nor special characters, so you'll see that as an option most places. For filenames and text file contents.
