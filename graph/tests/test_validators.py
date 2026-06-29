"""Tests for graph/validators.py."""

import pytest

from graph.exporters.kgx import build_kgx_export
from graph.validators import (
    ALLOWED_CATEGORIES,
    ALLOWED_PREDICATES,
    validate_kgx_export,
)

# ── Minimal valid TSV builders ───────────────────────────────────────────────


def _nodes_tsv(*rows: dict) -> str:
    header = "id\tcategory\tname\torcid\tcountry\tyear\tknowledge_source\n"
    lines = [header]
    for r in rows:
        lines.append(
            "\t".join(
                [
                    r.get("id", ""),
                    r.get("category", "biolink:Person"),
                    r.get("name", "Test"),
                    r.get("orcid", ""),
                    r.get("country", ""),
                    r.get("year", ""),
                    r.get("knowledge_source", "heddle"),
                ]
            )
            + "\n"
        )
    return "".join(lines)


def _edges_tsv(*rows: dict) -> str:
    header = "id\tsubject\tpredicate\tobject\tknowledge_source\n"
    lines = [header]
    for r in rows:
        lines.append(
            "\t".join(
                [
                    r.get("id", "heddle:edge/1"),
                    r.get("subject", ""),
                    r.get("predicate", "biolink:affiliated_with"),
                    r.get("object", ""),
                    r.get("knowledge_source", "heddle"),
                ]
            )
            + "\n"
        )
    return "".join(lines)


# ── Valid export ─────────────────────────────────────────────────────────────


class TestValidKGXExport:
    def test_empty_export_is_valid(self):
        nodes = _nodes_tsv()
        edges = _edges_tsv()
        result = validate_kgx_export(nodes, edges)
        assert result.valid is True
        assert result.errors == []
        assert result.node_count == 0
        assert result.edge_count == 0

    def test_single_node_is_valid(self):
        nodes = _nodes_tsv({"id": "heddle:person/1", "category": "biolink:Person", "name": "Ada"})
        edges = _edges_tsv()
        result = validate_kgx_export(nodes, edges)
        assert result.valid is True
        assert result.node_count == 1

    def test_valid_edge_is_valid(self):
        nodes = _nodes_tsv(
            {"id": "heddle:person/1", "category": "biolink:Person"},
            {"id": "heddle:org/1", "category": "biolink:Organization"},
        )
        edges = _edges_tsv(
            {
                "id": "heddle:edge/1",
                "subject": "heddle:person/1",
                "predicate": "biolink:affiliated_with",
                "object": "heddle:org/1",
            }
        )
        result = validate_kgx_export(nodes, edges)
        assert result.valid is True
        assert result.node_count == 2
        assert result.edge_count == 1

    def test_all_allowed_categories_pass(self):
        rows = [
            {"id": f"node/{i}", "category": cat} for i, cat in enumerate(sorted(ALLOWED_CATEGORIES))
        ]
        nodes = _nodes_tsv(*rows)
        result = validate_kgx_export(nodes, _edges_tsv())
        assert result.valid is True

    def test_all_allowed_predicates_pass(self):
        # Need two nodes first
        nodes = _nodes_tsv(
            {"id": "heddle:person/1", "category": "biolink:Person"},
            {"id": "heddle:pub/1", "category": "biolink:Publication"},
        )
        edges = (
            "\n".join(
                [
                    "id\tsubject\tpredicate\tobject\tknowledge_source",
                ]
                + [
                    f"heddle:edge/{i}\theddle:person/1\t{pred}\theddle:pub/1\theddle"
                    for i, pred in enumerate(sorted(ALLOWED_PREDICATES))
                ]
            )
            + "\n"
        )
        result = validate_kgx_export(nodes, edges)
        assert result.valid is True


# ── Errors ───────────────────────────────────────────────────────────────────


class TestValidationErrors:
    def test_unknown_category_is_error(self):
        nodes = _nodes_tsv({"id": "x:1", "category": "schema:Thing"})
        result = validate_kgx_export(nodes, _edges_tsv())
        assert result.valid is False
        assert any("unknown category" in e for e in result.errors)

    def test_unknown_predicate_is_error(self):
        nodes = _nodes_tsv(
            {"id": "heddle:person/1", "category": "biolink:Person"},
            {"id": "heddle:org/1", "category": "biolink:Organization"},
        )
        edges = _edges_tsv(
            {
                "id": "heddle:edge/1",
                "subject": "heddle:person/1",
                "predicate": "biolink:caused_by",
                "object": "heddle:org/1",
            }
        )
        result = validate_kgx_export(nodes, edges)
        assert result.valid is False
        assert any("unknown predicate" in e for e in result.errors)

    def test_duplicate_node_id_is_error(self):
        nodes = _nodes_tsv(
            {"id": "heddle:person/1", "category": "biolink:Person"},
            {"id": "heddle:person/1", "category": "biolink:Person"},
        )
        result = validate_kgx_export(nodes, _edges_tsv())
        assert result.valid is False
        assert any("duplicate node id" in e for e in result.errors)

    def test_duplicate_edge_id_is_error(self):
        nodes = _nodes_tsv(
            {"id": "heddle:person/1", "category": "biolink:Person"},
            {"id": "heddle:org/1", "category": "biolink:Organization"},
        )
        edges = _edges_tsv(
            {
                "id": "heddle:edge/1",
                "subject": "heddle:person/1",
                "predicate": "biolink:affiliated_with",
                "object": "heddle:org/1",
            },
            {
                "id": "heddle:edge/1",
                "subject": "heddle:person/1",
                "predicate": "biolink:affiliated_with",
                "object": "heddle:org/1",
            },
        )
        result = validate_kgx_export(nodes, edges)
        assert result.valid is False
        assert any("duplicate edge id" in e for e in result.errors)

    def test_missing_required_node_column_is_error(self):
        # Only provide id column, missing category and name
        nodes = "id\n heddle:person/1\n"
        result = validate_kgx_export(nodes, _edges_tsv())
        assert result.valid is False
        assert any("missing required columns" in e for e in result.errors)

    def test_missing_required_edge_column_is_error(self):
        nodes = _nodes_tsv({"id": "heddle:person/1", "category": "biolink:Person"})
        # Only id column
        edges = "id\nheddle:edge/1\n"
        result = validate_kgx_export(nodes, edges)
        assert result.valid is False
        assert any("missing required columns" in e for e in result.errors)


# ── Warnings ─────────────────────────────────────────────────────────────────


class TestValidationWarnings:
    def test_empty_name_is_warning_not_error(self):
        nodes = _nodes_tsv({"id": "heddle:person/1", "category": "biolink:Person", "name": ""})
        result = validate_kgx_export(nodes, _edges_tsv())
        assert result.valid is True
        assert any("empty 'name'" in w for w in result.warnings)

    def test_dangling_subject_is_warning_not_error(self):
        nodes = _nodes_tsv({"id": "heddle:org/1", "category": "biolink:Organization"})
        edges = _edges_tsv(
            {
                "id": "heddle:edge/1",
                "subject": "heddle:person/MISSING",
                "predicate": "biolink:affiliated_with",
                "object": "heddle:org/1",
            }
        )
        result = validate_kgx_export(nodes, edges)
        assert result.valid is True
        assert any("not in nodes.tsv" in w for w in result.warnings)

    def test_dangling_object_is_warning_not_error(self):
        nodes = _nodes_tsv({"id": "heddle:person/1", "category": "biolink:Person"})
        edges = _edges_tsv(
            {
                "id": "heddle:edge/1",
                "subject": "heddle:person/1",
                "predicate": "biolink:affiliated_with",
                "object": "heddle:org/MISSING",
            }
        )
        result = validate_kgx_export(nodes, edges)
        assert result.valid is True
        assert any("not in nodes.tsv" in w for w in result.warnings)


# ── Round-trip with build_kgx_export ─────────────────────────────────────────


@pytest.mark.django_db
class TestRoundTripValidation:
    def test_built_export_always_validates(self):
        import datetime

        from core.models import Affiliation, Organization, Person
        from events.models import Event, Participation

        p = Person.objects.create(
            given_name="Ada", family_name="Lovelace", consent_public_profile=True
        )
        org = Organization.objects.create(name="Test Org")
        aff = Affiliation.objects.create(person=p, organization=org)
        event = Event.objects.create(name="Test Event", start_date=datetime.date(2024, 1, 1))
        part = Participation.objects.create(person=p, event=event)

        aff_obj = Affiliation.objects.select_related("person", "organization").get(pk=aff.pk)
        part_obj = Participation.objects.select_related("person", "event").get(pk=part.pk)

        export = build_kgx_export(
            people=[p],
            organizations=[org],
            events=[event],
            affiliations=[aff_obj],
            participations=[part_obj],
        )
        result = validate_kgx_export(export.nodes_tsv, export.edges_tsv)
        assert result.valid is True
        assert result.node_count == 3  # 1 person + 1 org + 1 event
        assert result.edge_count == 2  # affiliated_with + participates_in
