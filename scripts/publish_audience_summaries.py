"""Sign (and optionally publish) the AI plain-language summary nanopubs.

One nanopub per audience in nanopubs/audience.json, about the chain apex, following the
AI plain-language summary template and the summaries already on the network: the
human author is dcterms:creator, the AI agent identity is attributed and signs.

    python scripts/publish_audience_summaries.py --profile ../ai-profile/profile.yml \
        --subject "the Logroño flood-adaptation synthesis" [--supersedes citizens=URI schools=URI]  # dry run
    ... --publish  # publish

Needs the `nanopub` package (not a project dependency; run it from a separate env).
"""

import argparse
import json
import sys
from pathlib import Path

import yaml
from nanopub import Nanopub, NanopubConf, load_profile
from nanopub.definitions import DUMMY_NAMESPACE
from rdflib import RDF, RDFS, Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audience_summaries import AUDIENCE, MAX_CHARS, TEMPLATE, flatten  # noqa: E402
from build_chain_draft import parse_published  # noqa: E402

SCHEMA = Namespace("https://schema.org/")
NT = Namespace("https://w3id.org/np/o/ntemplate/")
NPX = Namespace("http://purl.org/nanopub/x/")


def summary_nanopub(aud: dict, apex: str, label: str, author: str, conf: NanopubConf,
                    supersedes: str | None = None) -> Nanopub:
    text = flatten(aud)
    if len(text) > MAX_CHARS:
        raise SystemExit(f"{aud['id']}: {len(text)} characters, the template allows {MAX_CHARS}.")
    s = DUMMY_NAMESPACE[aud["id"]]
    a = Graph()
    a.add((s, RDF.type, SCHEMA.CreativeWork))
    a.add((s, DCTERMS.creator, URIRef(author)))
    a.add((s, RDFS.comment, Literal(text)))
    a.add((s, SCHEMA.about, URIRef(apex)))
    a.add((s, SCHEMA.audience, URIRef(AUDIENCE[aud["id"]])))
    p = Graph()
    p.add((DUMMY_NAMESPACE[""], NT.wasCreatedFromTemplate, URIRef(TEMPLATE)))
    # The template's pattern, "Plain-language summary of ${subject} for ${audience}",
    # with a readable name for the subject: filled literally it embeds the apex URI.
    p.add((DUMMY_NAMESPACE[""], RDFS.label, Literal(label)))
    if supersedes:  # only valid when signed with the key that signed the old summary
        p.add((DUMMY_NAMESPACE[""], NPX.supersedes, URIRef(supersedes)))
    return Nanopub(assertion=a, pubinfo=p, conf=conf)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--profile", required=True, help="nanopub profile of the AI agent identity")
    ap.add_argument("--publish", action="store_true", help="publish (default: sign and print only)")
    ap.add_argument("--subject", required=True,
                    help="readable name of the apex for the label, e.g. 'the Logroño flood-adaptation synthesis'")
    ap.add_argument("--supersedes", nargs="*", default=[], metavar="AUDIENCE=URI",
                    help="earlier summary each new one replaces, e.g. citizens=https://w3id.org/np/RA...")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    published = parse_published((root / "nanopubs" / "PUBLISHED.md").read_text())
    apex = published.get("08") or published.get("05")
    author = yaml.safe_load((root / "CITATION.cff").read_text())["authors"][0]["orcid"]
    conf = NanopubConf(profile=load_profile(args.profile), add_prov_generated_time=True,
                       attribute_assertion_to_profile=True, attribute_publication_to_profile=True)
    replaces = dict(s.split("=", 1) for s in args.supersedes)
    for aud in json.loads((root / "nanopubs" / "audience.json").read_text())["audiences"]:
        label = f"Plain-language summary of {args.subject} for {aud['id']}"
        np_ = summary_nanopub(aud, apex, label, author, conf, replaces.get(aud["id"]))
        if args.publish:
            np_.publish()
            print(f"{aud['id']}: published {np_.source_uri}")
        else:
            np_.sign()
            print(f"--- {aud['id']} (signed, not published): {np_.source_uri}")
            print(np_.rdf.serialize(format="trig"))


if __name__ == "__main__":
    main()
