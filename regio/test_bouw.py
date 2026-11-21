import json
from html.parser import HTMLParser
from pathlib import Path
import re
import tempfile
import unittest
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

from bouw import ORIGIN, ROOT, SERVICE, SITEMAP_NS, build, load_regions


class Html(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.tags = []
        self.feed(path.read_text(encoding="utf-8"))

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def matching(self, tag, **attrs):
        return [
            values for name, values in self.tags
            if name == tag and all(values.get(key) == value for key, value in attrs.items())
        ]


class BuildTest(unittest.TestCase):
    def test_site_contains_existing_pages_and_valid_region_links(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "site"
            build(ROOT, output)
            for name in ("index.html", "style.css", "script.js", "CNAME", ".nojekyll"):
                self.assertEqual((ROOT / name).read_bytes(), (output / name).read_bytes(), name)
            for path in (ROOT / "assets").rglob("*"):
                if path.is_file():
                    self.assertEqual(path.read_bytes(), (output / path.relative_to(ROOT)).read_bytes())

            original = (ROOT / SERVICE).read_bytes()
            built = (output / SERVICE).read_bytes()
            self.assertEqual(re.sub(rb'<section class="section area" aria-labelledby="regios">.*?</section>\n', b"", built, flags=re.S), original)

            expected = [f"{ORIGIN}/", f"{ORIGIN}/{SERVICE}"]
            for entry in load_regions(ROOT / "regio/plaatsen.json"):
                name = f"schoorsteenveger-{entry['slug']}.html"
                canonical = f"{ORIGIN}/{name}"
                expected.append(canonical)
                page = Html(output / name)
                self.assertEqual(page.matching("link", rel="canonical"), [{"rel": "canonical", "href": canonical}])
                self.assertEqual(page.matching("meta", property="og:url")[0]["content"], canonical)
                self.assertTrue(page.matching("meta", name="viewport"))
                schema = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', (output / name).read_text())[1])
                self.assertEqual(schema["offers"]["price"], "74.50")
                self.assertEqual(schema["areaServed"]["name"], entry["plaats"])
                self.assertTrue(Html(output / SERVICE).matching("a", href=name))
                self.assertTrue(page.matching("a", href=SERVICE))
                whatsapps = [attrs["href"] for attrs in page.matching("a") if attrs.get("href", "").startswith("https://wa.me/")]
                self.assertTrue(whatsapps)
                for url in whatsapps:
                    message = unquote(urlsplit(url).query)
                    for text in (entry["plaats"], "Postcode en huisnummer:", "Type kachel of haard:", "Laatste veegbeurt (als bekend):"):
                        self.assertIn(text, message)
                    self.assertEqual(urlsplit(url).path, "/31659012504")

            sitemap = ET.parse(output / "sitemap.xml")
            self.assertEqual([e.text for e in sitemap.findall(".//s:loc", {"s": SITEMAP_NS})], expected)
            self.check_links(output)

    def check_links(self, output):
        pages = {path.name: Html(path) for path in output.glob("*.html")}
        for name, page in pages.items():
            for tag, attrs in page.tags:
                if tag == "link" and attrs.get("rel") == "canonical":
                    continue
                url = attrs.get("href") or attrs.get("src")
                if not url:
                    continue
                parsed = urlsplit(url)
                if parsed.scheme or parsed.netloc:
                    continue
                path = (parsed.path.lstrip("/") or "index.html") if parsed.path else name
                path = "index.html" if path == "./" else path
                self.assertTrue((output / path).is_file(), f"{name}: {url}")
                if parsed.fragment and path in pages:
                    self.assertTrue(any(attrs.get("id") == parsed.fragment for _, attrs in pages[path].tags), f"{name}: {url}")

    def test_rejects_duplicate_slug_and_place_only_rewrite(self):
        # Use a self-contained record so the checks also run with an empty place list.
        entry = {
            "plaats": "Teststad", "slug": "teststad",
            "beschrijving": "Vraag in Teststad een afspraak aan en vermeld informatie over de bereikbaarheid.",
            "kop": "Een afspraak maken",
        }
        for field in ("intro", "lokaal", "vraag", "antwoord"):
            entry[field] = "Geef in Teststad de postcode, het type toestel en de bereikbaarheid van het rookkanaal door. Vermeld ook hoelang de kachel buiten gebruik was en wanneer het onderhoud is uitgevoerd."
        duplicate = {key: value.replace("Teststad", "Andere stad") for key, value in entry.items()}
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "plaatsen.json"
            path.write_text(json.dumps([entry, duplicate]))
            with self.assertRaisesRegex(ValueError, "plaats of slug"):
                load_regions(path)
            duplicate["slug"] = "andere-stad"
            path.write_text(json.dumps([entry, duplicate]))
            with self.assertRaisesRegex(ValueError, "lijkt te veel"):
                load_regions(path)


if __name__ == "__main__":
    unittest.main()
