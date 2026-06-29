# Metadata quality workflow

heddle treats data quality as a first-class workflow, not an afterthought.
Every record can answer: where did this data come from, when was it last verified,
who verified it, and what still needs fixing.

## Quality score

Each person, organisation, and publication has a **score from 0 to 100**.

The score is computed from open metadata issues: each issue deducts `weight` points.
Weights are stored in the database so they can be tuned without a code change.
The score is always shown with a **why-this-score breakdown** — never an opaque number.

A record with no open issues scores **100**.

## Issue severities

| Severity | Meaning | Excluded from invite lists? |
|---|---|---|
| **Critical** | Data is likely wrong or dangerous to use | Yes (by default) |
| **Warning** | Data is incomplete or suspicious | No |
| **Info** | Informational; low priority | No |

## Built-in checks

### Person checks

| Code | Severity | Fires when |
|---|---|---|
| `missing_orcid` | warning | No ORCID iD on record |
| `invalid_orcid` | critical | ORCID fails check-digit validation |
| `unverified_orcid` | warning | ORCID present but never synced |
| `stale_orcid_sync` | warning | Last ORCID sync > 365 days ago |
| `missing_country` | warning | No country on record |
| `missing_continent` | info | No continent derived from country |
| `missing_affiliation` | info | No organisation linked |
| `missing_consent` | warning | Neither consent flag is set |
| `dup_orcid` | critical | Another person has the same ORCID |
| `dup_email` | critical | Another person has the same email |
| `dup_name` | warning | Another person has the same normalised name |
| `no_expertise` | info | No expertise terms linked |
| `profile_not_updated` | info | Record not updated in > 365 days |

### Publication checks

| Code | Severity | Fires when |
|---|---|---|
| `pub_missing_doi` | warning | No DOI on publication |
| `pub_invalid_doi` | warning | DOI does not match `10.\d{4,}/\S+` |
| `pub_duplicate_doi` | critical | Another publication has the same DOI |
| `pub_unlinked_authors` | info | Authorship records with no linked Person |
| `pub_unreviewed_import` | info | ORCID-imported publication > 365 days old and not reviewed |

## Workflow

### 1. Run checks

From the **Quality** dashboard, click **Run checks now** to run all checks over all
people, organisations, and publications. This is also available as a management command
for nightly automation:

```bash
python manage.py run_metadata_checks
```

### 2. Review issues

The dashboard shows a table of open issues grouped by severity. Click **View** on any
row to go directly to the affected record.

On a person detail page, the **Metadata quality** panel on the right lists all open issues
with:
- Severity badge
- Check name and detail
- Points deducted
- Suggested fix (where available)
- **Resolve** / **Ignore** buttons

### 3. Resolve or ignore

- **Resolve** — marks the issue closed. If the underlying data was fixed, it will not
  reopen. If the data reverts, the next check run will reopen it.
- **Ignore** — suppresses the issue permanently (visible in the collapsed "ignored" list
  on the record). Use for known acceptable gaps.

### 4. Verify a record

After resolving all issues on a person, an Admin+ can change `metadata_status` to
`verified`. The quality dashboard tracks verified vs. unreviewed vs. stale counts.

## ORCID suggestions

When an ORCID sync (`Sync ORCID` button) fetches new data, **nothing is overwritten
automatically**. Instead, each differing field becomes a **MetadataSuggestion** with
`status=open`. An organiser reviews suggestions on the Suggestions page and accepts or
rejects each one. Acceptance writes the new value and records a `MetadataVerification`.

This ensures derived data never silently overwrites human-entered data.

## Invite list exclusions

When building an invite list (segment or event export), records with open **critical**
issues are excluded by default. The export manifest notes how many records were excluded
and why, so the omissions are auditable.
