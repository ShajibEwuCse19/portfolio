from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[2]


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


html_paths = sorted(ROOT.glob("*.html"))
parsers: dict[Path, SiteParser] = {}
for html_path in html_paths:
    parser = SiteParser()
    parser.feed(html_path.read_text(encoding="utf-8"))
    parsers[html_path.resolve()] = parser

errors: list[str] = []
local_references: set[str] = set()
total_details = 0
total_ids = 0

for html_path, parser in parsers.items():
    duplicate_ids = sorted({value for value in parser.ids if parser.ids.count(value) > 1})
    if duplicate_ids:
        errors.append(f"{html_path.name}: duplicate IDs {duplicate_ids}")
    if parser.details_count != parser.summary_count:
        errors.append(
            f"{html_path.name}: {parser.details_count} details and "
            f"{parser.summary_count} summaries"
        )

    total_details += parser.details_count
    total_ids += len(parser.ids)

    for _, reference in parser.references:
        parsed = urlparse(reference)
        if parsed.scheme or reference.startswith("//"):
            continue

        local_path = parsed.path or html_path.name
        local_references.add(local_path)
        target_path = (ROOT / local_path).resolve()
        if not target_path.exists():
            errors.append(f"{html_path.name}: missing local file {local_path}")
            continue

        if parsed.fragment and target_path.suffix.lower() == ".html":
            target_parser = parsers.get(target_path)
            if target_parser and parsed.fragment not in target_parser.ids:
                errors.append(
                    f"{html_path.name}: missing target "
                    f"{local_path}#{parsed.fragment}"
                )

if errors:
    raise SystemExit("\n".join(errors))

print(f"Validated {len(html_paths)} HTML pages")
print(f"Validated {total_ids} IDs")
print(f"Validated {total_details} expandable detail sections")
print(f"Validated {len(local_references)} unique local references")
