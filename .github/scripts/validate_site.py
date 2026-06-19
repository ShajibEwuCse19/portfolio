from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[2]
HTML_PATH = ROOT / "index.html"


class SiteParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.references: list[tuple[str, str]] = []
        self.details_count = 0
        self.summary_count = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if attributes.get("id"):
            self.ids.append(attributes["id"])
        for attribute in ("href", "src"):
            if attributes.get(attribute):
                self.references.append((tag, attributes[attribute]))
        if tag == "details":
            self.details_count += 1
        elif tag == "summary":
            self.summary_count += 1


parser = SiteParser()
parser.feed(HTML_PATH.read_text(encoding="utf-8"))

duplicate_ids = sorted({value for value in parser.ids if parser.ids.count(value) > 1})
local_references: set[str] = set()
fragment_references: set[str] = set()

for _, reference in parser.references:
    if reference.startswith("#"):
        fragment_references.add(reference[1:])
    elif not urlparse(reference).scheme and not reference.startswith("//"):
        local_references.add(reference.split("#", 1)[0].split("?", 1)[0])

missing_local_files = sorted(
    reference
    for reference in local_references
    if reference and not (ROOT / reference).exists()
)
missing_fragment_targets = sorted(
    fragment
    for fragment in fragment_references
    if fragment and fragment not in parser.ids
)

errors = []
if duplicate_ids:
    errors.append(f"Duplicate IDs: {duplicate_ids}")
if parser.details_count != parser.summary_count:
    errors.append(
        f"Toggle mismatch: {parser.details_count} details and "
        f"{parser.summary_count} summaries"
    )
if missing_local_files:
    errors.append(f"Missing local files: {missing_local_files}")
if missing_fragment_targets:
    errors.append(f"Missing fragment targets: {missing_fragment_targets}")

if errors:
    raise SystemExit("\n".join(errors))

print(f"Validated {len(parser.ids)} IDs")
print(f"Validated {parser.details_count} expandable detail sections")
print(f"Validated {len(local_references)} unique local references")
