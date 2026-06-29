"""KGX (Knowledge Graph eXchange) export — Biolink-aligned nodes + edges TSV.

Node-ID conventions
-------------------
Person with ORCID  → ORCID:<orcid>
Person without     → heddle:person/<uuid>
Anonymised person  → heddle:anon/<n>   (n = opaque sequential index per export)
Organisation, ROR  → ROR:<bare-ror-id>
Organisation, none → heddle:org/<uuid>
Publication, DOI   → doi:<normalised-doi>
Publication, none  → heddle:pub/<uuid>
Event              → heddle:event/<uuid>
"""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

from config.version import __version__
from core.models import Affiliation, Authorship, Collaboration, Organization, Person, Publication
from events.models import Event, Participation

SCHEMA_VERSION = "v1.0"
_SOURCE = "heddle"

ALLOWED_CATEGORIES: frozenset[str] = frozenset(
    {
        "biolink:Person",
        "biolink:Organization",
        "biolink:Publication",
        "biolink:Event",
    }
)

ALLOWED_PREDICATES: frozenset[str] = frozenset(
    {
        "biolink:affiliated_with",
        "biolink:contributes_to",
        "biolink:related_to",
        "biolink:participates_in",
    }
)

NODE_FIELDNAMES = ["id", "category", "name", "orcid", "country", "year", "knowledge_source"]
EDGE_FIELDNAMES = ["id", "subject", "predicate", "object", "knowledge_source"]

_FORMULA_PREFIXES = frozenset({"=", "+", "-", "@", "\t"})


def _esc(val: object) -> str:
    s = str(val) if val is not None else ""
    if s and s[0] in _FORMULA_PREFIXES:
        return f"'{s}"
    return s


def node_id_person(person: Person, anon_idx: int | None = None) -> str:
    if anon_idx is not None:
        return f"heddle:anon/{anon_idx}"
    if person.orcid:
        return f"ORCID:{person.orcid}"
    return f"heddle:person/{person.pk}"


def node_id_org(org: Organization) -> str:
    ror = (org.ror_id or "").strip()
    if ror:
        for pfx in ("https://ror.org/", "http://ror.org/"):
            if ror.startswith(pfx):
                ror = ror[len(pfx) :]
        return f"ROR:{ror}"
    return f"heddle:org/{org.pk}"


def node_id_pub(pub: Publication) -> str:
    if pub.doi_normalized:
        return f"doi:{pub.doi_normalized}"
    return f"heddle:pub/{pub.pk}"


def node_id_event(event: Event) -> str:
    return f"heddle:event/{event.pk}"


def _tsv(rows: list[dict], fieldnames: list[str]) -> str:
    out = io.StringIO()
    writer = csv.DictWriter(
        out,
        fieldnames=fieldnames,
        delimiter="\t",
        extrasaction="ignore",
        lineterminator="\n",
    )
    writer.writeheader()
    for row in rows:
        writer.writerow({k: _esc(row.get(k, "")) for k in fieldnames})
    return out.getvalue()


@dataclass
class KGXExport:
    nodes_tsv: str
    edges_tsv: str
    manifest: dict


def build_kgx_export(
    *,
    people: Iterable[Person],
    organizations: Iterable[Organization] = (),
    publications: Iterable[Publication] = (),
    events: Iterable[Event] = (),
    affiliations: Iterable[Affiliation] = (),
    authorships: Iterable[Authorship] = (),
    collaborations: Iterable[Collaboration] = (),
    participations: Iterable[Participation] = (),
    anonymize_non_consenting: bool = True,
    slice_name: str = "full",
    generated_by: str = "system",
) -> KGXExport:
    """
    Build a KGXExport from pre-fetched iterables.

    People without consent_public_profile are anonymised (opaque ID, name="Anonymous",
    no ORCID/country) when anonymize_non_consenting=True.
    Email is never included.
    """
    people_list = list(people)

    # Anonymisation map: person.pk → sequential anon index
    anon_map: dict = {}
    if anonymize_non_consenting:
        idx = 0
        for p in people_list:
            if not p.consent_public_profile:
                anon_map[p.pk] = idx
                idx += 1

    def _pid(p: Person) -> str:
        return node_id_person(p, anon_map.get(p.pk))

    # ── Nodes ──────────────────────────────────────────────────────────────
    nodes: list[dict] = []

    for p in people_list:
        is_anon = p.pk in anon_map
        nodes.append(
            {
                "id": _pid(p),
                "category": "biolink:Person",
                "name": "Anonymous" if is_anon else p.full_name,
                "orcid": "" if is_anon else (p.orcid or ""),
                "country": "" if is_anon else (p.country or ""),
                "year": "",
                "knowledge_source": _SOURCE,
            }
        )

    for org in organizations:
        nodes.append(
            {
                "id": node_id_org(org),
                "category": "biolink:Organization",
                "name": org.name,
                "orcid": "",
                "country": org.country or "",
                "year": "",
                "knowledge_source": _SOURCE,
            }
        )

    for pub in publications:
        nodes.append(
            {
                "id": node_id_pub(pub),
                "category": "biolink:Publication",
                "name": pub.title,
                "orcid": "",
                "country": "",
                "year": str(pub.year) if pub.year else "",
                "knowledge_source": _SOURCE,
            }
        )

    for event in events:
        nodes.append(
            {
                "id": node_id_event(event),
                "category": "biolink:Event",
                "name": event.name,
                "orcid": "",
                "country": event.country or "",
                "year": str(event.start_date.year) if event.start_date else "",
                "knowledge_source": _SOURCE,
            }
        )

    known_ids: set[str] = {n["id"] for n in nodes}

    # ── Edges ──────────────────────────────────────────────────────────────
    edges: list[dict] = []
    _edge_n = 0

    def _next_eid() -> str:
        nonlocal _edge_n
        _edge_n += 1
        return f"heddle:edge/{_edge_n}"

    def _maybe_edge(subj: str, pred: str, obj: str) -> None:
        if subj in known_ids and obj in known_ids:
            edges.append(
                {
                    "id": _next_eid(),
                    "subject": subj,
                    "predicate": pred,
                    "object": obj,
                    "knowledge_source": _SOURCE,
                }
            )

    for aff in affiliations:
        if aff.person_id and aff.organization_id:
            _maybe_edge(_pid(aff.person), "biolink:affiliated_with", node_id_org(aff.organization))

    for auth in authorships:
        person = auth.person
        if person is not None and auth.publication_id:
            _maybe_edge(_pid(person), "biolink:contributes_to", node_id_pub(auth.publication))

    for collab in collaborations:
        if collab.person_a_id and collab.person_b_id:
            _maybe_edge(_pid(collab.person_a), "biolink:related_to", _pid(collab.person_b))

    for part in participations:
        if part.person_id and part.event_id:
            _maybe_edge(_pid(part.person), "biolink:participates_in", node_id_event(part.event))

    manifest = {
        "heddle_version": __version__,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "generated_by": generated_by,
        "slice": slice_name,
        "schema": f"heddle_kgx {SCHEMA_VERSION}",
        "node_count": len(nodes),
        "edge_count": len(edges),
        "anonymized_people": len(anon_map),
    }

    return KGXExport(
        nodes_tsv=_tsv(nodes, NODE_FIELDNAMES),
        edges_tsv=_tsv(edges, EDGE_FIELDNAMES),
        manifest=manifest,
    )
