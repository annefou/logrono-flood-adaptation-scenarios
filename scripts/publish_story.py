"""Sign (and optionally publish) the Science Live story nanopub from nanopubs/story-draft.json.

The story draft is the file the platform's story wizard pre-fills from
(/np/create/story?draft=<url>), built by scripts/build_story_draft.py; this script
publishes exactly that content with the story template's shape (v4): a schema:Article
<apex>/story about the apex, headline, framing (schema:abstract), hero image, one
figure per finding (schema:associatedMedia, each about its Outcome, credited to a
version DOI) and the pinned plain-language summaries (schema:hasPart). The human
author is the creator and the assertion is attributed to them; the signing profile
decides who can later supersede the story (--supersedes, same key only).

    python scripts/publish_story.py --profile ../ai-profile/profile.yml            # dry run
    python scripts/publish_story.py --profile ../ai-profile/profile.yml --publish  # publish

Needs the `nanopub` package (not a project dependency; run it from a separate env).
"""

import argparse
import json
from pathlib import Path

import yaml
from nanopub import Nanopub, NanopubConf, load_profile
from nanopub.definitions import DUMMY_NAMESPACE
from rdflib import RDF, Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, PROV

TEMPLATE = "https://w3id.org/np/RAfjXiLtYji0w1Y3AtKmtL_S21esoh5jprGWAPpRQ1zUk"  # story template v4
SCHEMA = Namespace("https://schema.org/")
NT = Namespace("https://w3id.org/np/o/ntemplate/")
NPX = Namespace("http://purl.org/nanopub/x/")


def image(a: Graph, url: str, caption: str, doi: str | None) -> URIRef:
    img = URIRef(url)
    a.add((img, RDF.type, SCHEMA.ImageObject))
    a.add((img, SCHEMA.caption, Literal(caption)))
    if doi:
        a.add((img, SCHEMA.isBasedOn, URIRef(doi)))
    return img


def story_nanopub(draft: dict, author: str, conf: NanopubConf, supersedes: str | None) -> Nanopub:
    apex = draft["apex"]
    a = Graph()
    story = URIRef(f"{apex}/story")
    a.add((story, RDF.type, SCHEMA.Article))
    a.add((story, SCHEMA.about, URIRef(apex)))
    a.add((story, SCHEMA.headline, Literal(draft["headline"])))
    if draft.get("framing"):
        a.add((story, SCHEMA.abstract, Literal(draft["framing"])))
    if draft.get("hero"):
        h = draft["hero"]
        a.add((story, SCHEMA.image, image(a, h["contentUrl"], h["caption"], h.get("doi"))))
    for f in draft.get("figures", []):
        fig = image(a, f["contentUrl"], f["caption"], f.get("doi"))
        a.add((story, SCHEMA.associatedMedia, fig))
        if f.get("about"):
            a.add((fig, SCHEMA.about, URIRef(f["about"])))
        a.add((fig, SCHEMA.position, Literal(str(f["position"]))))
    for s in draft.get("summaries", []):
        a.add((story, SCHEMA.hasPart, URIRef(s["uri"])))
        a.add((URIRef(s["uri"]), SCHEMA.position, Literal(str(s["position"]))))
    prov = Graph()
    prov.add((DUMMY_NAMESPACE["assertion"], PROV.wasAttributedTo, URIRef(author)))
    prov.add((DUMMY_NAMESPACE["assertion"], NT.wasCreatedFromTemplate, URIRef(TEMPLATE)))
    pub = Graph()
    pub.add((DUMMY_NAMESPACE[""], DCTERMS.creator, URIRef(author)))
    pub.add((DUMMY_NAMESPACE[""], DCTERMS.license, URIRef("https://creativecommons.org/licenses/by/4.0/")))
    pub.add((DUMMY_NAMESPACE[""], DCTERMS.title, Literal(f"Story: {draft['headline']}")))
    pub.add((DUMMY_NAMESPACE[""], NPX.hasNanopubType, SCHEMA.Article))
    if supersedes:
        pub.add((DUMMY_NAMESPACE[""], NPX.supersedes, URIRef(supersedes)))
    return Nanopub(assertion=a, provenance=prov, pubinfo=pub, conf=conf)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--profile", required=True, help="nanopub profile of the signing identity")
    ap.add_argument("--draft", default=None, help="story draft (default: nanopubs/story-draft.json)")
    ap.add_argument("--supersedes", default=None, help="URI of an earlier story signed with the same key")
    ap.add_argument("--publish", action="store_true", help="publish (default: sign and print only)")
    args = ap.parse_args()
    root = Path(__file__).resolve().parent.parent
    draft = json.loads(Path(args.draft or root / "nanopubs" / "story-draft.json").read_text())
    author = yaml.safe_load((root / "CITATION.cff").read_text())["authors"][0]["orcid"]
    conf = NanopubConf(profile=load_profile(args.profile), add_pubinfo_generated_time=True)
    np_ = story_nanopub(draft, author, conf, args.supersedes)
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
