#!/usr/bin/env python3
#  This next one isn't needed, but I like the clarity and spitefulness, 
#+ to the point that I'm putting it in completely wrong.
''' -*- coding: utf-8 -*- '''

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import argparse
import csv
import io
import re
import traceback
from typing import Iterable


@dataclass
class IssueRecord:
    source_file: str
    line_number: int
    category: str
    match_text: str
    line_text: str
    highlighted_line_text: str
    note: str = ""


class FilenameReporter:
    """
    Lean prototype for scanning text files that contain either:
      - plain filename-like lines
      - anchor-tag / encoded filename lines

    Output is a list of IssueRecord objects.
    """

    NON_ASCII_RE = re.compile(r"[^\x00-\x7F]")
    ASCII_CONTROL_RE = re.compile(r"[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]")
    LEADING_TRAILING_WS_RE = re.compile(r"^\s+|\s+$")
    ANCHOR_CONTAM_RE = re.compile(r"&lt;a\b|&lt;/a&gt;|href=")

    # All percent-escaped bytes
    PERCENT_BYTE_RE = re.compile(r"%[0-9A-Fa-f]{2}")

    # Consecutive percent-escaped bytes: likely multibyte / grouped encoding
    PERCENT_MULTI_RE = re.compile(r"(?:%[0-9A-Fa-f]{2}){2,}")

    # Literal space/tab characters in the decoded text
    HEX_SPACE_TAB_HEX_RE = re.compile(r"[\x09\x20]")

    # Percent-escaped space/tab bytes in the encoded text
    PERCENT_SPACE_TAB_RE = re.compile(r"%(?:09|20)")

    VALID_HIGHLIGHT_STYLES = {"marker", "box"}

    def __init__(
        self,
        paths: Iterable[str | Path],
        highlight_style: str = "marker",
    ) -> None:
        self.paths = [Path(p) for p in paths]
        if highlight_style not in self.VALID_HIGHLIGHT_STYLES:
            raise ValueError(
                f"Invalid highlight_style={highlight_style!r}. "
                f"Expected one of {sorted(self.VALID_HIGHLIGHT_STYLES)}."
            )
        self.highlight_style = highlight_style

    def read_lines(self) -> list[tuple[Path, int, str]]:
        rows: list[tuple[Path, int, str]] = []
        for path in self.paths:
            with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
                for i, line in enumerate(f, start=1):
                    rows.append((path, i, line.rstrip("\r\n")))
        return rows

    def find_issues(self) -> list[IssueRecord]:
        issues: list[IssueRecord] = []

        for path, line_number, line in self.read_lines():
            issues.extend(self._detect_non_ascii(path, line_number, line))
            issues.extend(self._detect_ascii_control(path, line_number, line))
            issues.extend(self._detect_whitespace_boundary(path, line_number, line))
            issues.extend(self._detect_anchor_contamination(path, line_number, line))
            issues.extend(self._detect_percent_escapes(path, line_number, line))
            issues.extend(self._detect_hex_space_tab(path, line_number, line))
            issues.extend(self._detect_percent_space_tab(path, line_number, line))

        return issues

    def summarize_counts(self, issues: Iterable[IssueRecord]) -> list[dict]:
        counts: dict[str, int] = {}
        for issue in issues:
            counts[issue.category] = counts.get(issue.category, 0) + 1

        return [
            {"category": category, "count": count}
            for category, count in sorted(counts.items())
        ]

    def write_csv(self, issues: Iterable[IssueRecord], output_path: str | Path) -> None:
        output_path = Path(output_path)
        rows = [asdict(issue) for issue in issues]
        if not rows:
            rows = [{
                "source_file": "",
                "line_number": "",
                "category": "",
                "match_text": "",
                "line_text": "",
                "highlighted_line_text": "",
                "note": "",
            }]

        with output_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    def _is_ascii_control(self, ch: str) -> bool:
        cp = ord(ch)
        return (
            0x00 <= cp <= 0x08
            or 0x0B <= cp <= 0x0C
            or 0x0E <= cp <= 0x1F
            or cp == 0x7F
        )

    def _render_visible_for_general_audience(self, ch: str) -> str:
        """
        Render a single character in a way that is readable in hostile environments
        such as PowerShell stdout.
        """
        if ch == "\t":
            return r"\t"
        if ch == "\n":
            return r"\n"
        if ch == "\r":
            return r"\r"
        if self._is_ascii_control(ch):
            return f"\\x{ord(ch):02X}"
        return ch

    def _render_boxed_char(self, ch: str) -> str:
        """
        Render a single highlighted character using U+20DE.
        For ASCII control characters, render a visible escape plus the box.
        """
        if ch == "\t":
            return r"\t" + "\u20DE"
        if ch == "\n":
            return r"\n" + "\u20DE"
        if ch == "\r":
            return r"\r" + "\u20DE"
        if self._is_ascii_control(ch):
            return f"\\x{ord(ch):02X}\u20DE"
        return ch + "\u20DE"

    def _highlight_span_in_line_box(self, line: str, start: int, end: int) -> str:
        out: list[str] = []
        for i, ch in enumerate(line):
            if start <= i < end:
                out.append(self._render_boxed_char(ch))
            else:
                out.append(ch)
        return "".join(out)

    def _highlight_span_in_line_marker(self, line: str, start: int, end: int) -> str:
        prefix = line[:start]
        matched = line[start:end]
        suffix = line[end:]

        visible_matched = "".join(
            self._render_visible_for_general_audience(ch) for ch in matched
        )
        return f"{prefix}>>{visible_matched}<<{suffix}"

    def _highlight_span_in_line(self, line: str, start: int, end: int) -> str:
        if self.highlight_style == "box":
            return self._highlight_span_in_line_box(line, start, end)
        return self._highlight_span_in_line_marker(line, start, end)

    def _make_issue(
        self,
        *,
        path: Path,
        line_number: int,
        category: str,
        match_text: str,
        line: str,
        start: int,
        end: int,
        note: str = "",
    ) -> IssueRecord:
        return IssueRecord(
            source_file=str(path),
            line_number=line_number,
            category=category,
            match_text=match_text,
            line_text=line,
            highlighted_line_text=self._highlight_span_in_line(line, start, end),
            note=note,
        )

    def _detect_non_ascii(self, path: Path, line_number: int, line: str) -> list[IssueRecord]:
        seen = set()
        out = []
        for m in self.NON_ASCII_RE.finditer(line):
            value = m.group(0)
            if value not in seen:
                seen.add(value)
                start, end = m.span()
                out.append(self._make_issue(
                    path=path,
                    line_number=line_number,
                    category="NonASCII",
                    match_text=value,
                    line=line,
                    start=start,
                    end=end,
                    note=f"U+{ord(value):04X}",
                ))
        return out

    def _detect_ascii_control(self, path: Path, line_number: int, line: str) -> list[IssueRecord]:
        seen = set()
        out = []
        for m in self.ASCII_CONTROL_RE.finditer(line):
            value = m.group(0)
            if value not in seen:
                seen.add(value)
                start, end = m.span()
                out.append(self._make_issue(
                    path=path,
                    line_number=line_number,
                    category="ASCIIControl",
                    match_text=value,
                    line=line,
                    start=start,
                    end=end,
                    note=f"U+{ord(value):04X}",
                ))
        return out

    def _detect_whitespace_boundary(self, path: Path, line_number: int, line: str) -> list[IssueRecord]:
        out = []
        for m in self.LEADING_TRAILING_WS_RE.finditer(line):
            start, end = m.span()
            out.append(self._make_issue(
                path=path,
                line_number=line_number,
                category="WhitespaceBoundary",
                match_text=m.group(0),
                line=line,
                start=start,
                end=end,
                note=f"length={len(m.group(0))}",
            ))
        return out

    def _detect_anchor_contamination(self, path: Path, line_number: int, line: str) -> list[IssueRecord]:
        seen = set()
        out = []
        for m in self.ANCHOR_CONTAM_RE.finditer(line):
            value = m.group(0)
            if value not in seen:
                seen.add(value)
                start, end = m.span()
                out.append(self._make_issue(
                    path=path,
                    line_number=line_number,
                    category="AnchorTagContamination",
                    match_text=value,
                    line=line,
                    start=start,
                    end=end,
                    note="",
                ))
        return out

    def _detect_percent_escapes(self, path: Path, line_number: int, line: str) -> list[IssueRecord]:
        out: list[IssueRecord] = []

        multi_spans: list[tuple[int, int]] = []
        for m in self.PERCENT_MULTI_RE.finditer(line):
            start, end = m.span()
            multi_spans.append((start, end))
            out.append(self._make_issue(
                path=path,
                line_number=line_number,
                category="PercentEscapedMultiByte",
                match_text=m.group(0),
                line=line,
                start=start,
                end=end,
                note="",
            ))

        for m in self.PERCENT_BYTE_RE.finditer(line):
            start, end = m.span()
            in_multi = any(ms <= start and end <= me for ms, me in multi_spans)
            if in_multi:
                continue

            token = m.group(0)
            hex_part = token[1:].upper()
            value = int(hex_part, 16)

            if value in {0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x20}:
                category = "PercentEscapedSpaceLike"
            elif (
                0x00 <= value <= 0x08
                or 0x0B <= value <= 0x0C
                or 0x0E <= value <= 0x1F
                or value == 0x7F
            ):
                category = "PercentEscapedASCIIControl"
            else:
                category = "PercentEscapedSingleByteOther"

            out.append(self._make_issue(
                path=path,
                line_number=line_number,
                category=category,
                match_text=token,
                line=line,
                start=start,
                end=end,
                note=f"hex={hex_part}",
            ))

        return out

    def _detect_hex_space_tab(self, path: Path, line_number: int, line: str) -> list[IssueRecord]:
        out = []
        for m in self.HEX_SPACE_TAB_HEX_RE.finditer(line):
            start, end = m.span()

            # Do not report leading/trailing space/tab here.
            # Those belong to WhitespaceBoundary.
            if start == 0 or end == len(line):
                continue

            out.append(self._make_issue(
                path=path,
                line_number=line_number,
                category="HexSpaceOrTab",
                match_text=m.group(0),
                line=line,
                start=start,
                end=end,
                note=f"length={len(m.group(0))}",
            ))
        return out

    def _detect_percent_space_tab(self, path: Path, line_number: int, line: str) -> list[IssueRecord]:
        out = []
        for m in self.PERCENT_SPACE_TAB_RE.finditer(line):
            start, end = m.span()
            out.append(self._make_issue(
                path=path,
                line_number=line_number,
                category="PercentEscapedSpaceOrTab",
                match_text=m.group(0),
                line=line,
                start=start,
                end=end,
                note=f"length={len(m.group(0))}",
            ))
        return out


def parse_input_as_string(input_as_string: str) -> list[str]:
    """
    Parse a comma-separated string of file paths using CSV parsing rules,
    so quoted commas are handled correctly.
    """
    reader = csv.reader(io.StringIO(input_as_string), skipinitialspace=True)
    rows = list(reader)
    if not rows:
        return []
    return [item for item in rows[0] if item]


def filter_issues_by_category(issues: list[IssueRecord], category: str | None) -> list[IssueRecord]:
    if category is None:
        return issues

    if category == "space":
        allowed = {"HexSpaceOrTab", "PercentEscapedSpaceOrTab"}
        return [issue for issue in issues if issue.category in allowed]

    raise ValueError(f"Unsupported category filter: {category!r}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scan filename-list text files for problematic content."
    )

    parser.add_argument(
        "--input",
        nargs="+",
        help="Space-separated list of input files. Consumes values until the next flag.",
    )
    parser.add_argument(
        "--input-as-string",
        help=(
            "Comma-separated input file list, parsed with CSV rules so quoted commas "
            "are handled correctly."
        ),
    )
    parser.add_argument(
        "--output-csv",
        default="toy_issue_report.csv",
        help="Path to the output CSV file. Default: toy_issue_report.csv",
    )
    parser.add_argument(
        "--highlight-style",
        choices=["marker", "box"],
        default="marker",
        help="Highlight style for highlighted_line_text. Default: marker",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress stdout output, but still allow stderr.",
    )
    parser.add_argument(
        "--category",
        choices=["space"],
        help="Optional category filter. Currently implemented: space",
    )

    return parser


def resolve_input_paths(args: argparse.Namespace) -> list[str]:
    paths: list[str] = []

    if args.input:
        paths.extend(args.input)

    if args.input_as_string:
        paths.extend(parse_input_as_string(args.input_as_string))

    if not paths:
        paths = [
            "fir_tree_driv_filename.txt",
            "fir_tree_driv_file.txt",
        ]

    return paths


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    input_paths = resolve_input_paths(args)

    reporter = TableFnameReportCreator(
        input_paths,
        highlight_style=args.highlight_style,
    )

    issues = reporter.find_issues()
    issues = filter_issues_by_category(issues, args.category)

    if not args.quiet:
        for issue in issues:
            print(issue)

        print("\nSummary:")
        for row in reporter.summarize_counts(issues):
            print(row)

    try:
        reporter.write_csv(issues, args.output_csv)
    except Exception:
        traceback.print_exc()
        print("Check if the file is open in Microsoft Excel.")

    return 0
