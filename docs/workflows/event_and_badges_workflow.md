# Events, invites, and badge exports

## Events

An **Event** represents a workshop, hackathon, conference, or webinar. Create one from
**Events → Create event**.

Fields:
- Name, type (workshop / hackathon / conference / webinar / other)
- Start date, end date (optional), location, country
- Website, is_public flag

### Roster

The event detail page shows the full participant roster with role, status, and metadata
quality score. Statuses follow the invite lifecycle:

`invited → confirmed → attended / no-show / cancelled`

Bulk status updates are available from the roster: select participants and choose a new
status.

### Adding participants

Click **Add participant** on the event detail page. You can add a single person or import
a list from a saved segment.

## Segments

A **Saved Segment** is a named, reusable filter set for people. Build one from
**Segments → Create segment**.

Supported filter criteria:
- Country, continent
- Metadata status (`verified`, `needs_review`, etc.)
- (Additional criteria can be added; see `events/services.py`)

The segment preview page shows every matched person with a "why matched" explanation
drawn from the active filters. Segments are the main tool for building defensible invite
lists.

### Invite list CSV

From the segment preview page, export an **Invite list CSV**. This export:
- Excludes people with open **critical** metadata issues (by default).
- Excludes people without `consent_contact=True` when the `consent` filter is active.
- Records exclusion counts in the export manifest.

## Badge CSV export

The badge CSV is input for a downstream badge/DXF generator tool. heddle does not
generate badges itself.

Export path: **Graph → badge exports → By event**.

Each row contains:

| Column | Notes |
|---|---|
| `person_id` | ORCID: or heddle:person/ CURIE — stable across exports |
| `display_name` | Full name |
| `public_label` | Reserved for credential / title (blank in v1) |
| `orcid` | Bare ORCID iD |
| `organization` | Primary organisation name |
| `country` | ISO alpha-2 |
| `event_code` | First 8 chars of event UUID |
| `event_name` | Full event name |
| `participation_role` | attendee / speaker / organizer / etc. |
| `participation_status` | confirmed / attended / etc. |
| `consent_public_profile` | Always `true` (non-consenting rows excluded) |
| `qr_target_url` | Blank — to be filled by badge tool |
| `metadata_quality_score` | 0–100 score at time of export |
| `metadata_status` | Current metadata status |

**Privacy guarantee:** only participants with `consent_public_profile = True` appear in the
badge CSV. The manifest records how many were excluded and why.
Email is never included.

### Manifest

Every export (badge CSV, KGX) ships with a `manifest.json`:

```json
{
  "generated_at": "2024-06-15T10:30:00+00:00",
  "generated_by": "user@example.com",
  "event_id": "...",
  "event_name": "EcoTransform 2024",
  "tool": "heddle-badge-export v1.0",
  "included": 47,
  "excluded_no_consent": 3,
  "excluded_no_person_record": 0,
  "note": "Only participants with consent_public_profile=True are included..."
}
```

## KGX graph export

KGX (Knowledge Graph eXchange) exports feed directly into the EcoWeaver pipeline via
rosettaR. See `docs/workflows/kgx_export.md` for details.

**Export slices available:**
- **Full** — all people, organisations, publications, events, and edges
- **By event** — participants and their data for one event
- **By segment** — people matching a saved segment filter
- **Person neighbourhood** — a person plus their coauthorship collaborators (1–3 hops)

All KGX exports validate against `graph/schema/heddle_kgx.yaml` before download.
Non-consenting people are anonymised (`heddle:anon/N`, name `"Anonymous"`, no ORCID).
