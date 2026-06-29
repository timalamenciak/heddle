"""CSV normalization utilities for the importer pipeline."""

from core.identifiers import normalize_orcid as normalize_orcid

_COUNTRY_CONTINENT: dict[str, str] = {
    # Africa
    "DZ": "Africa",
    "AO": "Africa",
    "BJ": "Africa",
    "BW": "Africa",
    "BF": "Africa",
    "BI": "Africa",
    "CM": "Africa",
    "CV": "Africa",
    "CF": "Africa",
    "TD": "Africa",
    "KM": "Africa",
    "CG": "Africa",
    "CD": "Africa",
    "CI": "Africa",
    "DJ": "Africa",
    "EG": "Africa",
    "GQ": "Africa",
    "ER": "Africa",
    "ET": "Africa",
    "GA": "Africa",
    "GM": "Africa",
    "GH": "Africa",
    "GN": "Africa",
    "GW": "Africa",
    "KE": "Africa",
    "LS": "Africa",
    "LR": "Africa",
    "LY": "Africa",
    "MG": "Africa",
    "MW": "Africa",
    "ML": "Africa",
    "MR": "Africa",
    "MU": "Africa",
    "MA": "Africa",
    "MZ": "Africa",
    "NA": "Africa",
    "NE": "Africa",
    "NG": "Africa",
    "RW": "Africa",
    "ST": "Africa",
    "SN": "Africa",
    "SL": "Africa",
    "SO": "Africa",
    "ZA": "Africa",
    "SS": "Africa",
    "SD": "Africa",
    "SZ": "Africa",
    "TZ": "Africa",
    "TG": "Africa",
    "TN": "Africa",
    "UG": "Africa",
    "ZM": "Africa",
    "ZW": "Africa",
    # Antarctica
    "AQ": "Antarctica",
    # Asia
    "AF": "Asia",
    "AM": "Asia",
    "AZ": "Asia",
    "BH": "Asia",
    "BD": "Asia",
    "BT": "Asia",
    "BN": "Asia",
    "KH": "Asia",
    "CN": "Asia",
    "CY": "Asia",
    "GE": "Asia",
    "IN": "Asia",
    "ID": "Asia",
    "IR": "Asia",
    "IQ": "Asia",
    "IL": "Asia",
    "JP": "Asia",
    "JO": "Asia",
    "KZ": "Asia",
    "KW": "Asia",
    "KG": "Asia",
    "LA": "Asia",
    "LB": "Asia",
    "MY": "Asia",
    "MV": "Asia",
    "MN": "Asia",
    "MM": "Asia",
    "NP": "Asia",
    "KP": "Asia",
    "OM": "Asia",
    "PK": "Asia",
    "PS": "Asia",
    "PH": "Asia",
    "QA": "Asia",
    "SA": "Asia",
    "SG": "Asia",
    "KR": "Asia",
    "LK": "Asia",
    "SY": "Asia",
    "TW": "Asia",
    "TJ": "Asia",
    "TH": "Asia",
    "TL": "Asia",
    "TR": "Asia",
    "TM": "Asia",
    "AE": "Asia",
    "UZ": "Asia",
    "VN": "Asia",
    "YE": "Asia",
    # Europe
    "AL": "Europe",
    "AD": "Europe",
    "AT": "Europe",
    "BY": "Europe",
    "BE": "Europe",
    "BA": "Europe",
    "BG": "Europe",
    "HR": "Europe",
    "CZ": "Europe",
    "DK": "Europe",
    "EE": "Europe",
    "FI": "Europe",
    "FR": "Europe",
    "DE": "Europe",
    "GR": "Europe",
    "HU": "Europe",
    "IS": "Europe",
    "IE": "Europe",
    "IT": "Europe",
    "XK": "Europe",
    "LV": "Europe",
    "LI": "Europe",
    "LT": "Europe",
    "LU": "Europe",
    "MK": "Europe",
    "MT": "Europe",
    "MD": "Europe",
    "MC": "Europe",
    "ME": "Europe",
    "NL": "Europe",
    "NO": "Europe",
    "PL": "Europe",
    "PT": "Europe",
    "RO": "Europe",
    "RU": "Europe",
    "SM": "Europe",
    "RS": "Europe",
    "SK": "Europe",
    "SI": "Europe",
    "ES": "Europe",
    "SE": "Europe",
    "CH": "Europe",
    "UA": "Europe",
    "GB": "Europe",
    "VA": "Europe",
    # North America
    "AG": "North America",
    "BS": "North America",
    "BB": "North America",
    "BZ": "North America",
    "CA": "North America",
    "CR": "North America",
    "CU": "North America",
    "DM": "North America",
    "DO": "North America",
    "SV": "North America",
    "GD": "North America",
    "GT": "North America",
    "HT": "North America",
    "HN": "North America",
    "JM": "North America",
    "MX": "North America",
    "NI": "North America",
    "PA": "North America",
    "KN": "North America",
    "LC": "North America",
    "VC": "North America",
    "TT": "North America",
    "US": "North America",
    # Oceania
    "AU": "Oceania",
    "FJ": "Oceania",
    "KI": "Oceania",
    "MH": "Oceania",
    "FM": "Oceania",
    "NR": "Oceania",
    "NZ": "Oceania",
    "PW": "Oceania",
    "PG": "Oceania",
    "WS": "Oceania",
    "SB": "Oceania",
    "TO": "Oceania",
    "TV": "Oceania",
    "VU": "Oceania",
    # South America
    "AR": "South America",
    "BO": "South America",
    "BR": "South America",
    "CL": "South America",
    "CO": "South America",
    "EC": "South America",
    "GY": "South America",
    "PY": "South America",
    "PE": "South America",
    "SR": "South America",
    "UY": "South America",
    "VE": "South America",
}

_COUNTRY_NAMES: dict[str, str] = {
    # Africa
    "algeria": "DZ",
    "angola": "AO",
    "egypt": "EG",
    "ethiopia": "ET",
    "ghana": "GH",
    "kenya": "KE",
    "morocco": "MA",
    "mozambique": "MZ",
    "nigeria": "NG",
    "south africa": "ZA",
    "tanzania": "TZ",
    "uganda": "UG",
    "zimbabwe": "ZW",
    # Asia
    "afghanistan": "AF",
    "bangladesh": "BD",
    "china": "CN",
    "people's republic of china": "CN",
    "india": "IN",
    "indonesia": "ID",
    "iran": "IR",
    "iraq": "IQ",
    "israel": "IL",
    "japan": "JP",
    "jordan": "JO",
    "kazakhstan": "KZ",
    "malaysia": "MY",
    "mongolia": "MN",
    "myanmar": "MM",
    "burma": "MM",
    "nepal": "NP",
    "north korea": "KP",
    "pakistan": "PK",
    "philippines": "PH",
    "saudi arabia": "SA",
    "singapore": "SG",
    "south korea": "KR",
    "korea": "KR",
    "sri lanka": "LK",
    "taiwan": "TW",
    "thailand": "TH",
    "turkey": "TR",
    "turkiye": "TR",
    "united arab emirates": "AE",
    "uae": "AE",
    "uzbekistan": "UZ",
    "vietnam": "VN",
    "viet nam": "VN",
    "yemen": "YE",
    # Europe
    "albania": "AL",
    "austria": "AT",
    "belarus": "BY",
    "belgium": "BE",
    "bosnia": "BA",
    "bosnia and herzegovina": "BA",
    "bulgaria": "BG",
    "croatia": "HR",
    "czech republic": "CZ",
    "czechia": "CZ",
    "denmark": "DK",
    "estonia": "EE",
    "finland": "FI",
    "france": "FR",
    "germany": "DE",
    "greece": "GR",
    "hungary": "HU",
    "iceland": "IS",
    "ireland": "IE",
    "italy": "IT",
    "latvia": "LV",
    "lithuania": "LT",
    "luxembourg": "LU",
    "netherlands": "NL",
    "holland": "NL",
    "norway": "NO",
    "poland": "PL",
    "portugal": "PT",
    "romania": "RO",
    "russia": "RU",
    "russian federation": "RU",
    "serbia": "RS",
    "slovakia": "SK",
    "slovenia": "SI",
    "spain": "ES",
    "sweden": "SE",
    "switzerland": "CH",
    "ukraine": "UA",
    "united kingdom": "GB",
    "uk": "GB",
    "great britain": "GB",
    "england": "GB",
    "scotland": "GB",
    "wales": "GB",
    # North America
    "canada": "CA",
    "costa rica": "CR",
    "cuba": "CU",
    "guatemala": "GT",
    "haiti": "HT",
    "honduras": "HN",
    "jamaica": "JM",
    "mexico": "MX",
    "nicaragua": "NI",
    "panama": "PA",
    "trinidad and tobago": "TT",
    "united states": "US",
    "usa": "US",
    "united states of america": "US",
    "u.s.a.": "US",
    "u.s.": "US",
    # Oceania
    "australia": "AU",
    "fiji": "FJ",
    "new zealand": "NZ",
    "papua new guinea": "PG",
    # South America
    "argentina": "AR",
    "bolivia": "BO",
    "brazil": "BR",
    "brasil": "BR",
    "chile": "CL",
    "colombia": "CO",
    "ecuador": "EC",
    "peru": "PE",
    "uruguay": "UY",
    "venezuela": "VE",
}

_FIELD_HINTS: dict[str, str] = {
    "name": "full_name",
    "full_name": "full_name",
    "fullname": "full_name",
    "display_name": "full_name",
    "participant": "full_name",
    "given": "given_name",
    "first": "given_name",
    "given_name": "given_name",
    "firstname": "given_name",
    "first_name": "given_name",
    "family": "family_name",
    "last": "family_name",
    "surname": "family_name",
    "family_name": "family_name",
    "lastname": "family_name",
    "last_name": "family_name",
    "email": "email",
    "e-mail": "email",
    "e_mail": "email",
    "mail": "email",
    "orcid": "orcid",
    "orcid_id": "orcid",
    "org": "organization",
    "organization": "organization",
    "organisation": "organization",
    "institution": "organization",
    "affiliation": "organization",
    "role": "organization_role",
    "org_role": "organization_role",
    "position": "organization_role",
    "title": "organization_role",
    "country": "country",
    "country_code": "country",
    "continent": "continent",
    "website": "website",
    "url": "website",
    "web": "website",
    "homepage": "website",
    "notes": "notes",
    "note": "notes",
    "comment": "notes",
    "comments": "notes",
    "consent": "consent_contact",
    "consent_contact": "consent_contact",
}


def normalize_email(raw: str) -> str:
    """Lowercase domain part only (RFC 5321 preserves local-part case)."""
    stripped = raw.strip()
    if not stripped or "@" not in stripped:
        return stripped.lower()
    local, domain = stripped.rsplit("@", 1)
    return f"{local}@{domain.lower()}"


def normalize_whitespace(raw: str) -> str:
    """Collapse internal whitespace and strip edges."""
    return " ".join(raw.split())


def detect_swapped_name(given_name: str, family_name: str) -> bool:
    """Return True if given_name looks like it actually contains 'Family, Given'."""
    return "," in given_name


def auto_detect_mapping(column_header: str) -> str:
    """Guess field name for a CSV column header. Returns '' if no match."""
    key = column_header.strip().lower().replace(" ", "_").replace("-", "_")
    return _FIELD_HINTS.get(key, "")


def country_to_continent(country_code: str) -> str:
    """Map ISO alpha-2 country code to continent name. Returns '' if unknown."""
    return _COUNTRY_CONTINENT.get(country_code.upper().strip(), "")


def normalize_country(raw: str) -> str:
    """Normalize a country string to ISO alpha-2.

    Accepts an existing alpha-2 code or a common English country name.
    Returns '' for unrecognized values so callers never see a value > 2 chars.
    """
    v = raw.strip()
    if not v:
        return ""
    upper = v.upper()
    if len(upper) == 2 and upper in _COUNTRY_CONTINENT:
        return upper
    code = _COUNTRY_NAMES.get(v.lower(), "")
    return code


def split_full_name(full_name: str) -> tuple[str, str]:
    """Split a full name string into (given_name, family_name).

    Handles two formats:
    - "Given [Middle] Family"  →  given="Given", family="Middle Family"
    - "Family, Given [Middle]" →  given="Given Middle", family="Family"

    Returns ("", "") for blank input.
    """
    name = normalize_whitespace(full_name)
    if not name:
        return "", ""
    if "," in name:
        # "Family, Given" format
        family_part, _, given_part = name.partition(",")
        return given_part.strip(), family_part.strip()
    parts = name.split()
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])
