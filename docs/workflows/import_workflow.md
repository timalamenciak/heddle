# Import workflow

Brings external contact lists (conference rosters, partner CSVs, manual spreadsheets) into
heddle with normalization, deduplication, and a dry-run preview before any write touches
the database.

## Steps

### 1. Upload a CSV

Navigate to **Import** in the top nav. Upload any UTF-8 or UTF-16 CSV file. Supported
column names are detected automatically; unrecognised columns are ignored.

Accepted column names include (case-insensitive):

| Column header variant | Maps to |
|---|---|
| `given_name`, `first_name`, `firstname` | Given name |
| `family_name`, `last_name`, `surname` | Family name |
| `full_name`, `name`, `participant` | Split into given + family |
| `email` | Email |
| `orcid`, `orcid_id` | ORCID iD |
| `country`, `country_code` | ISO alpha-2 country code |
| `organization`, `institution`, `affiliation` | Primary organization name |

### 2. Map columns

On the next screen, confirm or correct the column mapping. Each CSV column is paired with a
heddle field. Columns mapped to `(ignore)` are skipped.

### 3. Preview (dry-run)

The preview screen shows every row categorised as:

- **Create** — no existing person matched; a new record will be created.
- **Update** — matched an existing person (by ORCID → email → normalised name + org);
  at least one field differs.
- **Unchanged** — matched and no fields differ; no write needed.
- **Error** — missing both given name and family name; row will be skipped.

Warnings appear inline (e.g. unrecognised country name, invalid ORCID format). No database
writes happen during preview.

### 4. Apply

Click **Apply import** to execute the changes shown in the preview. Counts of created,
updated, and unchanged records are shown on the confirmation page.
Application is transaction-locked and idempotent: a session cannot be applied twice.
After success, Heddle erases the raw uploaded CSV and retains its SHA-256 fingerprint,
source label, actor, filename, row count, timestamp, and aggregate result counts.

Uploads default to a 5 MB, 10,000-row, 100-column limit. Operators can lower these
limits through the documented environment settings.

## Normalization rules

Applied automatically during preview and apply:

| Field | Rule |
|---|---|
| `full_name` | Split on last whitespace token → given + family |
| `orcid` | Strips URL prefix; validates check-digit; normalised to `0000-0000-0000-000X` |
| `email` | Lowercased; whitespace stripped |
| `country` | Full name → ISO alpha-2 (e.g. "Canada" → "CA"); unknown values left blank with warning |
| `continent` | Auto-derived from country when blank |
| `given_name`, `family_name`, `organization`, `notes` | Whitespace collapsed |

## Deduplication

Rows are matched to existing people in priority order:

1. **ORCID** — exact match on normalised ORCID iD.
2. **Email** — case-insensitive match on a single record (skipped if ambiguous).
3. **Name + org** — normalised `given family` against `name_normalized`; narrowed by
   organisation when more than one match exists.

If a match is found, only differing fields are updated. Human-entered data is never silently
overwritten by import — derived or imported values go through MetadataSuggestions first
(ORCID sync) or are shown in the preview diff (CSV import).

## Formula injection safety

Every exported cell that starts with `= + - @ \t` is prefixed with `'` before writing to
CSV so spreadsheet applications cannot execute them as formulas. This rule applies to all
heddle CSV exports, not just the import preview.
