"""Structural validator for KGX exports.

Checks required fields, allowed categories, and allowed predicates.
The allowed sets mirror the definitions in graph/schema/heddle_kgx.yaml.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field

from .exporters.kgx import ALLOWED_CATEGORIES, ALLOWED_PREDICATES

REQUIRED_NODE_FIELDS: frozenset[str] = frozenset({"id", "category", "name"})
REQUIRED_EDGE_FIELDS: frozenset[str] = frozenset({"id", "subject", "predicate", "object"})


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    node_count: int = 0
    edge_count: int = 0


def _parse_tsv(text: str) -> tuple[list[str], list[dict]]:
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    headers = list(reader.fieldnames or [])
    rows = list(reader)
    return headers, rows


def validate_kgx_export(nodes_tsv: str, edges_tsv: str) -> ValidationResult:
    """Validate nodes.tsv and edges.tsv strings against the heddle_kgx schema."""
    errors: list[str] = []
    warnings: list[str] = []

    # ── Nodes ──────────────────────────────────────────────────────────────
    node_headers, node_rows = _parse_tsv(nodes_tsv)
    node_ids: set[str] = set()

    missing_node_fields = REQUIRED_NODE_FIELDS - set(node_headers)
    if missing_node_fields:
        errors.append(f"nodes.tsv missing required columns: {sorted(missing_node_fields)}")

    for i, row in enumerate(node_rows, start=2):
        nid = row.get("id", "").strip()
        cat = row.get("category", "").strip()
        name = row.get("name", "").strip()

        if not nid:
            errors.append(f"nodes.tsv row {i}: empty 'id'")
        else:
            if nid in node_ids:
                errors.append(f"nodes.tsv row {i}: duplicate node id {nid!r}")
            node_ids.add(nid)

        if cat not in ALLOWED_CATEGORIES:
            errors.append(
                f"nodes.tsv row {i}: unknown category {cat!r}. "
                f"Allowed: {sorted(ALLOWED_CATEGORIES)}"
            )

        if not name:
            warnings.append(f"nodes.tsv row {i}: node {nid!r} has empty 'name'")

    # ── Edges ──────────────────────────────────────────────────────────────
    edge_headers, edge_rows = _parse_tsv(edges_tsv)
    edge_ids: set[str] = set()

    missing_edge_fields = REQUIRED_EDGE_FIELDS - set(edge_headers)
    if missing_edge_fields:
        errors.append(f"edges.tsv missing required columns: {sorted(missing_edge_fields)}")

    for i, row in enumerate(edge_rows, start=2):
        eid = row.get("id", "").strip()
        subj = row.get("subject", "").strip()
        pred = row.get("predicate", "").strip()
        obj = row.get("object", "").strip()

        if not eid:
            errors.append(f"edges.tsv row {i}: empty 'id'")
        else:
            if eid in edge_ids:
                errors.append(f"edges.tsv row {i}: duplicate edge id {eid!r}")
            edge_ids.add(eid)

        if pred not in ALLOWED_PREDICATES:
            errors.append(
                f"edges.tsv row {i}: unknown predicate {pred!r}. "
                f"Allowed: {sorted(ALLOWED_PREDICATES)}"
            )

        if subj and subj not in node_ids:
            warnings.append(f"edges.tsv row {i}: subject {subj!r} not in nodes.tsv")

        if obj and obj not in node_ids:
            warnings.append(f"edges.tsv row {i}: object {obj!r} not in nodes.tsv")

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        node_count=len(node_rows),
        edge_count=len(edge_rows),
    )
