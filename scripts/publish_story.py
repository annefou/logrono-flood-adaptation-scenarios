"""Sign (and optionally publish) the Science Live story nanopub of the synthesis.

The platform's story page (/np/story?uri=…) renders a dedicated story nanopub: a
schema:Article about the chain apex, with a headline, a hero image, one figure per
finding (schema:associatedMedia, each about its Outcome) and the plain-language
summaries (schema:hasPart). Same shape as the stories already on the network, made
from the story template. Figures are pinned to each repository's release tag.

    python scripts/publish_story.py --profile ../ai-profile/profile.yml            # dry run
    python scripts/publish_story.py --profile ../ai-profile/profile.yml --publish  # publish

Needs the `nanopub` package (not a project dependency; run it from a separate env).
"""

import argparse
import re
import sys
import urllib.request
from pathlib import Path

import yaml
from nanopub import Nanopub, NanopubConf, load_profile
from nanopub.definitions import DUMMY_NAMESPACE
from rdflib import RDF, Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, PROV

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_chain_draft import parse_published  # noqa: E402

TEMPLATE = "https://w3id.org/np/RAfjXiLtYji0w1Y3AtKmtL_S21esoh5jprGWAPpRQ1zUk"
TAG = "v0.1.0"
FIGURE = "figures/main_result.png"
SCHEMA = Namespace("https://schema.org/")
NT = Namespace("https://w3id.org/np/o/ntemplate/")
NPX = Namespace("http://purl.org/nanopub/x/")


def raw(slug: str, ref: str, path: str) -> str:
    return f"https://raw.githubusercontent.com/{slug}/{ref}/{path}"


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "logrono-story/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode()


def version_doi(slug: str) -> str:
    cff = yaml.safe_load(fetch(raw(slug, "main", "CITATION.cff")))
    for i in cff.get("identifiers", []):
        if "version" in (i.get("description") or "").lower():
            return f"https://doi.org/{i['value']}"
    raise SystemExit(f"{slug}: no version DOI in CITATION.cff")


def outcome_label(slug: str) -> str:
    draft = fetch(raw(slug, "main", "nanopubs/drafts/05_outcome.md"))
    m = re.search(r"<!-- field: label -->.*?```\n(.+?)\n```", draft, re.S)
    return m.group(1).strip()


def limbs(published_md: str) -> list[dict]:
    """(repository, Outcome URI) per row of the sources table, in the ledger's order."""
    rows = re.findall(r"\[[^\]]+\]\(https://github\.com/([\w.-]+/[\w.-]+)\)\s*\|\s*<([^>]+)>", published_md)
    return [{"slug": s, "outcome": o} for s, o in rows]


def story_nanopub(root: Path, conf: NanopubConf, author: str) -> Nanopub:
    md = (root / "nanopubs" / "PUBLISHED.md").read_text()
    published = parse_published(md)
    apex = published["08"]
    headline = yaml.safe_load((root / "CITATION.cff").read_text())["title"]
    summaries = re.findall(r"<(https://w3id\.org/np/RA[\w-]+)>", md.split("## AI plain-language summaries", 1)[1].split("\n## ", 1)[0])
    a = Graph()
    story = URIRef(f"{apex}/story")
    a.add((story, RDF.type, SCHEMA.Article))
    a.add((story, SCHEMA.about, URIRef(apex)))
    a.add((story, SCHEMA.headline, Literal(headline)))
    hero = URIRef(raw("annefou/logrono-flood-adaptation-scenarios", TAG, FIGURE))
    a.add((story, SCHEMA.image, hero))
    a.add((hero, RDF.type, SCHEMA.ImageObject))
    a.add((hero, SCHEMA.caption, Literal("Overview — the shared analysis behind the three findings")))
    for pos, limb in enumerate(limbs(md), start=1):
        fig = URIRef(raw(limb["slug"], TAG, FIGURE))
        a.add((story, SCHEMA.associatedMedia, fig))
        a.add((fig, RDF.type, SCHEMA.ImageObject))
        a.add((fig, SCHEMA.about, URIRef(limb["outcome"])))
        a.add((fig, SCHEMA.caption, Literal(f"{FIGURE} — {outcome_label(limb['slug'])}")))
        a.add((fig, SCHEMA.isBasedOn, URIRef(version_doi(limb["slug"]))))
        a.add((fig, SCHEMA.position, Literal(str(pos))))
    for pos, uri in enumerate(summaries, start=1):
        a.add((story, SCHEMA.hasPart, URIRef(uri)))
        a.add((URIRef(uri), SCHEMA.position, Literal(str(pos))))
    prov = Graph()
    prov.add((DUMMY_NAMESPACE["assertion"], PROV.wasAttributedTo, URIRef(author)))
    prov.add((DUMMY_NAMESPACE["assertion"], NT.wasCreatedFromTemplate, URIRef(TEMPLATE)))
    pub = Graph()
    pub.add((DUMMY_NAMESPACE[""], DCTERMS.creator, URIRef(author)))
    pub.add((DUMMY_NAMESPACE[""], DCTERMS.license, URIRef("https://creativecommons.org/licenses/by/4.0/")))
    pub.add((DUMMY_NAMESPACE[""], DCTERMS.title, Literal(f"Story: {headline}")))
    pub.add((DUMMY_NAMESPACE[""], NPX.hasNanopubType, SCHEMA.Article))
    return Nanopub(assertion=a, provenance=prov, pubinfo=pub, conf=conf)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--profile", required=True, help="nanopub profile of the signing identity")
    ap.add_argument("--publish", action="store_true", help="publish (default: sign and print only)")
    args = ap.parse_args()
    root = Path(__file__).resolve().parent.parent
    author = yaml.safe_load((root / "CITATION.cff").read_text())["authors"][0]["orcid"]
    conf = NanopubConf(profile=load_profile(args.profile), add_pubinfo_generated_time=True)
    np_ = story_nanopub(root, conf, author)
    if args.publish:
        np_.publish()
        print(f"published {np_.source_uri}")
        print(f"story page: https://platform.sciencelive4all.org/np/story?uri={np_.source_uri}")
    else:
        np_.sign()
        print(f"signed, not published: {np_.source_uri}")
        print(np_.rdf.serialize(format="trig"))


if __name__ == "__main__":
    main()
