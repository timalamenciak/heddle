"""Tests for graph/exporters/kgx.py and graph/slices.py."""

import csv
import datetime
import io

import pytest

from core.models import Affiliation, Authorship, Collaboration, Organization, Person, Publication
from events.models import Event, Participation
from graph.exporters.kgx import (
    ALLOWED_CATEGORIES,
    EDGE_FIELDNAMES,
    NODE_FIELDNAMES,
    build_kgx_export,
    node_id_event,
    node_id_org,
    node_id_person,
    node_id_pub,
)
from graph.slices import (
    event_kgx_export,
    full_kgx_export,
    person_neighbourhood_kgx_export,
)

# ── Helpers ─────────────────────────────────────────────────────────────────


def _parse_tsv(text: str) -> tuple[list[str], list[dict]]:
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    headers = list(reader.fieldnames or [])
    rows = list(reader)
    return headers, rows


def _person(**kw) -> Person:
    defaults = {"given_name": "Ada", "family_name": "Lovelace"}
    defaults.update(kw)
    return Person.objects.create(**defaults)


def _org(**kw) -> Organization:
    defaults = {"name": "Test Org"}
    defaults.update(kw)
    return Organization.objects.create(**defaults)


def _pub(**kw) -> Publication:
    defaults = {"title": "Test Paper"}
    defaults.update(kw)
    return Publication.objects.create(**defaults)


def _event(**kw) -> Event:
    defaults = {"name": "Test Event", "start_date": datetime.date(2024, 1, 15)}
    defaults.update(kw)
    return Event.objects.create(**defaults)


# ── Node-ID helpers ──────────────────────────────────────────────────────────


class TestNodeIdPerson:
    def test_with_orcid(self):
        p = Person(orcid="0000-0001-2345-6789")
        assert node_id_person(p) == "ORCID:0000-0001-2345-6789"

    def test_without_orcid(self):
        p = Person(orcid=None)
        p.pk = "aaaa-1111"
        assert node_id_person(p) == "heddle:person/aaaa-1111"

    def test_anon_index(self):
        p = Person(orcid="0000-0001-2345-6789")
        assert node_id_person(p, anon_idx=3) == "heddle:anon/3"


class TestNodeIdOrg:
    def test_bare_ror(self):
        org = Organization(ror_id="0abcde123")
        assert node_id_org(org) == "ROR:0abcde123"

    def test_full_ror_url_stripped(self):
        org = Organization(ror_id="https://ror.org/0abcde123")
        assert node_id_org(org) == "ROR:0abcde123"

    def test_without_ror(self):
        org = Organization(ror_id="")
        org.pk = "bbbb-2222"
        assert node_id_org(org) == "heddle:org/bbbb-2222"


class TestNodeIdPub:
    def test_with_doi_normalized(self):
        pub = Publication(doi_normalized="10.1234/test")
        assert node_id_pub(pub) == "doi:10.1234/test"

    def test_without_doi(self):
        pub = Publication(doi_normalized="")
        pub.pk = "cccc-3333"
        assert node_id_pub(pub) == "heddle:pub/cccc-3333"


class TestNodeIdEvent:
    def test_event_id(self):
        event = Event()
        event.pk = "dddd-4444"
        assert node_id_event(event) == "heddle:event/dddd-4444"


# ── build_kgx_export ────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestBuildKGXExport:
    def test_empty_export_has_headers(self):
        export = build_kgx_export(people=[])
        node_hdrs, node_rows = _parse_tsv(export.nodes_tsv)
        edge_hdrs, edge_rows = _parse_tsv(export.edges_tsv)
        assert set(NODE_FIELDNAMES) == set(node_hdrs)
        assert set(EDGE_FIELDNAMES) == set(edge_hdrs)
        assert node_rows == []
        assert edge_rows == []

    def test_person_with_orcid_gets_orcid_id(self):
        p = _person(orcid="0000-0001-2345-6789", consent_public_profile=True)
        export = build_kgx_export(people=[p])
        _, rows = _parse_tsv(export.nodes_tsv)
        assert rows[0]["id"] == "ORCID:0000-0001-2345-6789"
        assert rows[0]["category"] == "biolink:Person"
        assert rows[0]["orcid"] == "0000-0001-2345-6789"

    def test_person_without_orcid_gets_heddle_id(self):
        p = _person(consent_public_profile=True)
        export = build_kgx_export(people=[p])
        _, rows = _parse_tsv(export.nodes_tsv)
        assert rows[0]["id"] == f"heddle:person/{p.pk}"

    def test_non_consenting_person_is_anonymised(self):
        p = _person(orcid="0000-0001-2345-6789", consent_public_profile=False)
        export = build_kgx_export(people=[p], anonymize_non_consenting=True)
        _, rows = _parse_tsv(export.nodes_tsv)
        node = rows[0]
        assert node["id"].startswith("heddle:anon/")
        assert node["name"] == "Anonymous"
        assert node["orcid"] == ""
        assert node["country"] == ""

    def test_non_consenting_not_anonymised_when_disabled(self):
        p = _person(orcid="0000-0001-2345-6789", consent_public_profile=False)
        export = build_kgx_export(people=[p], anonymize_non_consenting=False)
        _, rows = _parse_tsv(export.nodes_tsv)
        assert rows[0]["id"] == "ORCID:0000-0001-2345-6789"
        assert rows[0]["name"] != "Anonymous"

    def test_org_node_with_ror(self):
        org = _org(ror_id="https://ror.org/01abc123")
        export = build_kgx_export(people=[], organizations=[org])
        _, rows = _parse_tsv(export.nodes_tsv)
        assert rows[0]["id"] == "ROR:01abc123"
        assert rows[0]["category"] == "biolink:Organization"

    def test_pub_node_with_doi(self):
        pub = _pub(doi="10.1234/test", year=2021)
        export = build_kgx_export(people=[], publications=[pub])
        _, rows = _parse_tsv(export.nodes_tsv)
        assert rows[0]["id"] == "doi:10.1234/test"
        assert rows[0]["category"] == "biolink:Publication"
        assert rows[0]["year"] == "2021"

    def test_event_node(self):
        event = _event(name="EcoTransform 2024", country="CA")
        export = build_kgx_export(people=[], events=[event])
        _, rows = _parse_tsv(export.nodes_tsv)
        assert rows[0]["id"] == f"heddle:event/{event.pk}"
        assert rows[0]["category"] == "biolink:Event"
        assert rows[0]["country"] == "CA"
        assert rows[0]["year"] == "2024"

    def test_affiliation_edge(self):
        p = _person(consent_public_profile=True)
        org = _org()
        aff = Affiliation.objects.create(person=p, organization=org)
        export = build_kgx_export(
            people=[p],
            organizations=[org],
            affiliations=[aff],
        )
        _, edge_rows = _parse_tsv(export.edges_tsv)
        assert len(edge_rows) == 1
        assert edge_rows[0]["predicate"] == "biolink:affiliated_with"
        assert edge_rows[0]["subject"] == f"heddle:person/{p.pk}"
        assert edge_rows[0]["object"] == f"heddle:org/{org.pk}"

    def test_authorship_edge(self):
        p = _person(consent_public_profile=True)
        pub = _pub(doi="10.1/t")
        Authorship.objects.create(publication=pub, person=p)
        auth = Authorship.objects.select_related("person", "publication").get(person=p)
        export = build_kgx_export(
            people=[p],
            publications=[pub],
            authorships=[auth],
        )
        _, edge_rows = _parse_tsv(export.edges_tsv)
        assert len(edge_rows) == 1
        assert edge_rows[0]["predicate"] == "biolink:contributes_to"

    def test_collaboration_edge(self):
        p_a = _person(given_name="Ada", consent_public_profile=True)
        p_b = _person(given_name="Grace", family_name="Hopper", consent_public_profile=True)
        a_id, b_id = sorted([str(p_a.pk), str(p_b.pk)])
        collab = Collaboration.objects.create(
            person_a_id=a_id, person_b_id=b_id, publication_count=1
        )
        collab_obj = Collaboration.objects.select_related("person_a", "person_b").get(pk=collab.pk)
        export = build_kgx_export(
            people=[p_a, p_b],
            collaborations=[collab_obj],
        )
        _, edge_rows = _parse_tsv(export.edges_tsv)
        assert len(edge_rows) == 1
        assert edge_rows[0]["predicate"] == "biolink:related_to"

    def test_participation_edge(self):
        p = _person(consent_public_profile=True)
        event = _event()
        part = Participation.objects.create(person=p, event=event)
        part_obj = Participation.objects.select_related("person", "event").get(pk=part.pk)
        export = build_kgx_export(
            people=[p],
            events=[event],
            participations=[part_obj],
        )
        _, edge_rows = _parse_tsv(export.edges_tsv)
        assert len(edge_rows) == 1
        assert edge_rows[0]["predicate"] == "biolink:participates_in"

    def test_dangling_edge_excluded(self):
        """Edge is dropped when target node is not in the export."""
        p = _person(consent_public_profile=True)
        org = _org()
        aff = Affiliation.objects.create(person=p, organization=org)
        # Pass affiliation but NOT the org in organizations=
        aff_obj = Affiliation.objects.select_related("person", "organization").get(pk=aff.pk)
        export = build_kgx_export(
            people=[p],
            organizations=[],
            affiliations=[aff_obj],
        )
        _, edge_rows = _parse_tsv(export.edges_tsv)
        assert edge_rows == []

    def test_formula_injection_escaped(self):
        p = _person(given_name="=DANGER", family_name="Person", consent_public_profile=True)
        export = build_kgx_export(people=[p])
        _, rows = _parse_tsv(export.nodes_tsv)
        assert rows[0]["name"].startswith("'")

    def test_manifest_fields(self):
        p = _person(consent_public_profile=True)
        q = _person(given_name="Anon", consent_public_profile=False)
        export = build_kgx_export(people=[p, q], slice_name="test", generated_by="tester")
        m = export.manifest
        assert m["slice"] == "test"
        assert m["generated_by"] == "tester"
        assert m["node_count"] == 2
        assert m["anonymized_people"] == 1
        assert "generated_at" in m
        assert "schema" in m

    def test_all_node_categories_are_biolink(self):
        p = _person(consent_public_profile=True)
        org = _org()
        pub = _pub()
        event = _event()
        export = build_kgx_export(
            people=[p], organizations=[org], publications=[pub], events=[event]
        )
        _, rows = _parse_tsv(export.nodes_tsv)
        for row in rows:
            assert row["category"] in ALLOWED_CATEGORIES

    def test_email_never_in_nodes_tsv(self):
        p = _person(email="secret@example.com", consent_public_profile=True)
        export = build_kgx_export(people=[p])
        assert "secret@example.com" not in export.nodes_tsv


# ── Slices ───────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestFullKGXSlice:
    def test_full_export_includes_all_people(self):
        _person(given_name="Alice", consent_public_profile=True)
        _person(given_name="Bob", family_name="Smith", consent_public_profile=True)
        export = full_kgx_export(generated_by="test")
        _, rows = _parse_tsv(export.nodes_tsv)
        person_rows = [r for r in rows if r["category"] == "biolink:Person"]
        assert len(person_rows) == 2

    def test_full_export_manifest_slice_name(self):
        export = full_kgx_export()
        assert export.manifest["slice"] == "full"


@pytest.mark.django_db
class TestEventKGXSlice:
    def test_event_slice_includes_only_event_participants(self):
        p1 = _person(given_name="Participant", consent_public_profile=True)
        _person(given_name="Other", family_name="Person", consent_public_profile=True)
        event = _event()
        Participation.objects.create(person=p1, event=event)

        export = event_kgx_export(event.pk, generated_by="test")
        _, rows = _parse_tsv(export.nodes_tsv)
        person_rows = [r for r in rows if r["category"] == "biolink:Person"]
        # Only p1 participated
        assert len(person_rows) == 1
        assert rows[0]["id"] == f"heddle:person/{p1.pk}"

    def test_event_slice_includes_event_node(self):
        event = _event()
        export = event_kgx_export(event.pk, generated_by="test")
        _, rows = _parse_tsv(export.nodes_tsv)
        event_rows = [r for r in rows if r["category"] == "biolink:Event"]
        assert len(event_rows) == 1

    def test_event_slice_manifest_names_event(self):
        event = _event()
        export = event_kgx_export(event.pk)
        assert f"event:{event.pk}" in export.manifest["slice"]


@pytest.mark.django_db
class TestPersonNeighbourhoodSlice:
    def test_1hop_includes_direct_collaborator(self):
        p1 = _person(given_name="P1", consent_public_profile=True)
        p2 = _person(given_name="P2", family_name="Smith", consent_public_profile=True)
        p3 = _person(given_name="P3", family_name="Jones", consent_public_profile=True)
        a, b = sorted([str(p1.pk), str(p2.pk)])
        Collaboration.objects.create(person_a_id=a, person_b_id=b, publication_count=1)

        export = person_neighbourhood_kgx_export(p1.pk, hops=1, generated_by="test")
        _, rows = _parse_tsv(export.nodes_tsv)
        person_ids = {r["id"] for r in rows if r["category"] == "biolink:Person"}
        assert f"heddle:person/{p1.pk}" in person_ids
        assert f"heddle:person/{p2.pk}" in person_ids
        # p3 is not a collaborator of p1
        assert f"heddle:person/{p3.pk}" not in person_ids

    def test_hops_capped_at_3(self):
        p = _person(consent_public_profile=True)
        # hops=99 should be silently capped to 3
        export = person_neighbourhood_kgx_export(p.pk, hops=99)
        assert export.manifest["slice"].endswith(":3")

    def test_isolated_person_export(self):
        p = _person(consent_public_profile=True)
        export = person_neighbourhood_kgx_export(p.pk, hops=1)
        _, rows = _parse_tsv(export.nodes_tsv)
        assert len([r for r in rows if r["category"] == "biolink:Person"]) == 1
