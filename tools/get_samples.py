"""Download real-world sample documents (public repos and Wikimedia) for integration tests."""

import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "tests" / "resources" / "real"

RAW = "https://raw.githubusercontent.com"

SAMPLES: dict[str, str] = {
    "real_paragraphs.docx": f"{RAW}/python-openxml/python-docx/master/features/steps/test_files/par-known-paragraphs.docx",
    "real_comments.docx": f"{RAW}/python-openxml/python-docx/master/features/steps/test_files/comments-rich-para.docx",
    "real_deck.pptx": f"{RAW}/scanny/python-pptx/master/features/steps/test_files/test-image-jpg-mime.pptx",
    "real_book.xlsx": f"{RAW}/dilshod/xlsx2csv/master/test/xlsx2csv-test-file.xlsx",
    "real_chapter.epub": "https://github.com/IDPF/epub-revision/raw/main/archive/epub32/samples/epub-32-new-features.epub",
    "real_dummy.pdf": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
    "real_photo.png": "https://commons.wikimedia.org/wiki/Special:FilePath/Example.png",
    "real_logo.svg": "https://commons.wikimedia.org/wiki/Special:FilePath/Wiki.svg",
    "real_anim.gif": "https://commons.wikimedia.org/wiki/Special:FilePath/Loading.gif",
    "real_site.html": "https://example.com/",
}


def main() -> int:
    ROOT.mkdir(parents=True, exist_ok=True)
    failures = 0
    for name, url in SAMPLES.items():
        target = ROOT / name
        if target.exists():
            sys.stdout.write(f"cached  {name}\n")
            continue
        request = urllib.request.Request(url, headers={"User-Agent": "anytomd-tests/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = response.read()
        except Exception as error:  # noqa: BLE001
            failures += 1
            sys.stdout.write(f"FAILED  {name}: {error}\n")
            continue
        target.write_bytes(payload)
        sys.stdout.write(f"fetched {name} ({len(payload)} bytes)\n")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
