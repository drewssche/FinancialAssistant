"""Build the ordered browser scripts into one cacheable file for the app image."""

import gzip
import hashlib
import re
from pathlib import Path


def build(static: Path) -> Path:
    scripts = static / "js"
    manifest = (scripts / "app-manifest.js").read_text()
    sources = re.findall(r'^\s*"(/static/js/[^"]+\.js)",?\s*$', manifest, re.MULTILINE)
    if not sources or sources[-1] != "/static/js/app-init.js" or len(sources) != len(set(sources)):
        raise ValueError("Invalid frontend manifest")
    content = b"\n;\n".join((static / src.removeprefix("/static/")).read_bytes() for src in sources)
    digest = hashlib.sha256(content).hexdigest()[:20]
    bundle = scripts / f"app-runtime-{digest}.js"
    bundle.write_bytes(content)
    bundle.with_suffix(".js.gz").write_bytes(gzip.compress(content, mtime=0))

    index = static / "index.html"
    html, count = re.subn(
        r'<script src="/static/js/app-manifest\.js\?[^"]+"></script>\s*<script src="/static/js/app-bootstrap\.js',
        f'<script data-bundle="/static/js/{bundle.name}" src="/static/js/app-bootstrap.js',
        index.read_text(),
    )
    if count != 1:
        raise ValueError("Frontend entry scripts missing")
    index.write_text(html)
    return bundle


if __name__ == "__main__":
    build(Path(__file__).resolve().parents[1] / "static")
