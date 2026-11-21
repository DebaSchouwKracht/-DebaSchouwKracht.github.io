"""Bouw een statische GitHub Pages-site in een nieuwe uitvoermap."""

import argparse
from difflib import SequenceMatcher
from html import escape
import json
from pathlib import Path
import re
from shutil import copy2, copytree
from string import Template
import tempfile
from urllib.parse import quote
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://debaschouwkracht.nl"
SERVICE = "schoorsteenvegen.html"
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
FIELDS = {"plaats", "slug", "beschrijving", "intro", "kop", "lokaal", "vraag", "antwoord"}
LOCAL_FIELDS = ("intro", "lokaal", "vraag", "antwoord")


def normalized(text, place, slug):
    for name in {place.casefold(), slug.replace("-", " ")}:
        text = re.sub(r"\b" + re.escape(name) + r"(?:se|s)?\b", " ", text.casefold())
    return " ".join(re.findall(r"[^\W_]+", text.casefold()))


def similar(first, second):
    a, b = first.split(), second.split()
    a_pairs, b_pairs = set(zip(a, a[1:])), set(zip(b, b[1:]))
    overlap = len(a_pairs & b_pairs) / max(1, min(len(a_pairs), len(b_pairs)))
    return overlap >= .8 or SequenceMatcher(None, a, b, autojunk=False).ratio() >= .8


def load_regions(path):
    entries = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(entries, list):
        raise ValueError("plaatsen.json moet een lijst zijn.")

    seen_slugs, seen_places, seen_descriptions = set(), set(), set()
    previous = []
    for index, entry in enumerate(entries, 1):
        if not isinstance(entry, dict) or entry.keys() != FIELDS:
            raise ValueError(f"Regel {index}: gebruik dezelfde velden als in het Helmond-voorbeeld.")
        if any(not isinstance(value, str) or not value.strip() for value in entry.values()):
            raise ValueError(f"Regel {index}: elk veld moet tekst bevatten.")
        entry = {key: value.strip() for key, value in entry.items()}
        place, slug = entry["plaats"], entry["slug"]
        place_key = "".join(re.findall(r"[^\W_]+", place.casefold()))
        if not place_key or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
            raise ValueError(f"{place}: ongeldige plaatsnaam of slug.")
        if slug in seen_slugs or place_key in seen_places:
            raise ValueError(f"{place}: plaats of slug komt meerdere keren voor.")
        description = entry["beschrijving"].casefold()
        if not 60 <= len(description) <= 165 or place.casefold() not in description:
            raise ValueError(f"{place}: schrijf een metabeschrijving van 60–165 tekens met de plaatsnaam.")
        if description in seen_descriptions:
            raise ValueError(f"{place}: dubbele metabeschrijving.")
        sections = {field: normalized(entry[field], place, slug) for field in LOCAL_FIELDS}
        combined = " ".join(sections.values())
        if len(combined.split()) < 90 or min(len(sections[field].split()) for field in LOCAL_FIELDS) < 8:
            raise ValueError(f"{place}: schrijf ten minste 90 woorden lokale inhoud en vul alle tekstvelden in.")
        for other, other_sections, other_combined in previous:
            if similar(combined, other_combined) or similar(sections["lokaal"], other_sections["lokaal"]):
                raise ValueError(f"{place}: lokale inhoud lijkt te veel op {other}.")
        seen_slugs.add(slug)
        seen_places.add(place_key)
        seen_descriptions.add(description)
        previous.append((place, sections, combined))
        entries[index - 1] = entry

    return sorted(entries, key=lambda entry: entry["plaats"].casefold())


def render_region(template, entry, url):
    place = entry["plaats"]
    title = f"Schoorsteenveger in {place} | Deba Schouwkracht"
    message = quote(
        f"Goedendag, ik wil een schoorsteenveegbeurt aanvragen in {place}.\n\n"
        "Postcode en huisnummer: \n"
        "Type kachel of haard: \n"
        "Laatste veegbeurt (als bekend): "
    )
    schema = {
        "@context": "https://schema.org",
        "@type": "Service",
        "name": f"Schoorsteenvegen in {place}",
        "serviceType": "Schoorsteenvegen",
        "url": url,
        "provider": {
            "@type": "HomeAndConstructionBusiness",
            "@id": f"{ORIGIN}/#bedrijf",
            "name": "Deba Schouwkracht",
            "url": f"{ORIGIN}/",
            "telephone": "+31659012504",
        },
        "areaServed": {"@type": "City", "name": place},
        "offers": {
            "@type": "Offer", "price": "74.50", "priceCurrency": "EUR", "url": url,
            "description": "Inclusief btw, veegbewijs en standaard voorrijkosten.",
        },
    }
    return template.substitute(
        {key: escape(value) for key, value in entry.items()},
        titel=escape(title), origin=ORIGIN, canonical=url,
        whatsapp=f"https://wa.me/31659012504?text={message}",
        schema=json.dumps(schema, ensure_ascii=False).replace("<", "\\u003c"),
    )


def write_sitemap(output, urls):
    ET.register_namespace("", SITEMAP_NS)
    root = ET.Element(f"{{{SITEMAP_NS}}}urlset")
    for url in urls:
        node = ET.SubElement(root, f"{{{SITEMAP_NS}}}url")
        ET.SubElement(node, f"{{{SITEMAP_NS}}}loc").text = url
    ET.indent(root, space="  ")
    ET.ElementTree(root).write(output / "sitemap.xml", encoding="utf-8", xml_declaration=True)


def build(root, output):
    if output.exists() or output.is_symlink():
        raise ValueError(f"Uitvoermap bestaat al: {output}")
    if output.resolve().is_relative_to((root / "assets").resolve()):
        raise ValueError("Kies een uitvoermap buiten assets.")
    source = root / "regio"
    regions = load_regions(source / "plaatsen.json")
    template = Template((source / "pagina.html").read_text(encoding="utf-8"))
    pages = {}
    for entry in regions:
        name = f"schoorsteenveger-{entry['slug']}.html"
        if (root / name).exists():
            raise ValueError(f"Regiopagina overschrijft een bestaand bestand: {name}")
        pages[name] = render_region(template, entry, f"{ORIGIN}/{name}")

    service = (root / SERVICE).read_bytes()
    if regions:
        links = "\n".join(
            f'    <li><a href="{name}">Schoorsteenveger in {escape(entry["plaats"])}</a></li>'
            for name, entry in zip(pages, regions)
        )
        section = (
            '<section class="section area" aria-labelledby="regios"><div class="container">\n'
            '  <h2 id="regios">Schoorsteenvegen per plaats</h2>\n  <ul>\n'
            f'{links}\n  </ul>\n</div></section>\n'
        )
        if service.count(b"</main>") != 1:
            raise ValueError(f"{SERVICE} moet precies één afsluitende main-tag bevatten.")
        service = service.replace(b"</main>", section.encode("utf-8") + b"</main>")

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as temporary:
        site = Path(temporary) / "site"
        site.mkdir()
        for pattern in ("*.html", "*.css", "*.js", "*.txt", "CNAME", ".nojekyll"):
            for path in root.glob(pattern):
                if path.is_file() and path.name != "README.txt":
                    copy2(path, site / path.name)
        copytree(root / "assets", site / "assets")
        copy2(source / "regio.css", site / "regio.css")
        (site / SERVICE).write_bytes(service)
        for name, html in pages.items():
            (site / name).write_text(html, encoding="utf-8")
        write_sitemap(site, [f"{ORIGIN}/", f"{ORIGIN}/{SERVICE}", *(f"{ORIGIN}/{name}" for name in pages)])
        site.rename(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("uitvoermap", type=Path)
    args = parser.parse_args()
    try:
        build(ROOT, args.uitvoermap.absolute())
    except ValueError as error:
        parser.exit(1, f"{error}\n")
