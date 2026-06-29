from importer.normalize import (
    auto_detect_mapping,
    country_to_continent,
    detect_swapped_name,
    normalize_country,
    normalize_email,
    normalize_orcid,
    normalize_whitespace,
    split_full_name,
)


class TestNormalizeOrcid:
    def test_url_prefix_stripped(self):
        assert normalize_orcid("https://orcid.org/0000-0001-2345-6789") == "0000-0001-2345-6789"

    def test_already_formatted(self):
        assert normalize_orcid("0000-0001-2345-6789") == "0000-0001-2345-6789"

    def test_no_dashes(self):
        assert normalize_orcid("0000000123456789") == "0000-0001-2345-6789"

    def test_check_digit_x(self):
        assert normalize_orcid("0000-0002-1694-233X") == "0000-0002-1694-233X"

    def test_invalid_check_digit_returns_none(self):
        assert normalize_orcid("0000-0002-1825-009X") is None

    def test_invalid_too_short(self):
        assert normalize_orcid("0000-0001") is None

    def test_invalid_non_numeric(self):
        assert normalize_orcid("XXXX-0001-2345-6789") is None

    def test_empty_string(self):
        assert normalize_orcid("") is None

    def test_whitespace_stripped(self):
        assert normalize_orcid("  0000-0001-2345-6789  ") == "0000-0001-2345-6789"


class TestNormalizeEmail:
    def test_lowercases_domain(self):
        assert normalize_email("Test@EXAMPLE.COM") == "Test@example.com"

    def test_preserves_local_part_case(self):
        result = normalize_email("MyUser@Example.com")
        assert result == "MyUser@example.com"

    def test_empty_string(self):
        assert normalize_email("") == ""

    def test_strips_whitespace(self):
        assert normalize_email("  user@example.com  ") == "user@example.com"

    def test_no_at_sign(self):
        assert normalize_email("notanemail") == "notanemail"


class TestNormalizeWhitespace:
    def test_collapses_internal_spaces(self):
        assert normalize_whitespace("Ada   Lovelace") == "Ada Lovelace"

    def test_strips_edges(self):
        assert normalize_whitespace("  Ada Lovelace  ") == "Ada Lovelace"

    def test_tabs_collapsed(self):
        assert normalize_whitespace("Ada\tLovelace") == "Ada Lovelace"

    def test_empty_string(self):
        assert normalize_whitespace("") == ""


class TestDetectSwappedName:
    def test_detects_comma_in_given(self):
        assert detect_swapped_name("Lovelace, Ada", "Ada") is True

    def test_normal_order_is_false(self):
        assert detect_swapped_name("Ada", "Lovelace") is False

    def test_empty_names(self):
        assert detect_swapped_name("", "") is False


class TestAutoDetectMapping:
    def test_first_maps_to_given_name(self):
        assert auto_detect_mapping("first") == "given_name"

    def test_last_maps_to_family_name(self):
        assert auto_detect_mapping("last") == "family_name"

    def test_email_maps_to_email(self):
        assert auto_detect_mapping("email") == "email"

    def test_orcid_maps_to_orcid(self):
        assert auto_detect_mapping("orcid") == "orcid"

    def test_institution_maps_to_organization(self):
        assert auto_detect_mapping("institution") == "organization"

    def test_affiliation_maps_to_organization(self):
        assert auto_detect_mapping("affiliation") == "organization"

    def test_unknown_returns_empty(self):
        assert auto_detect_mapping("telephone") == ""

    def test_case_insensitive(self):
        assert auto_detect_mapping("Email") == "email"

    def test_spaces_normalized(self):
        assert auto_detect_mapping("given name") == "given_name"


class TestSplitFullName:
    def test_given_family_order(self):
        assert split_full_name("Ada Lovelace") == ("Ada", "Lovelace")

    def test_middle_name_stays_in_family(self):
        assert split_full_name("Grace Murray Hopper") == ("Grace", "Murray Hopper")

    def test_comma_format_family_given(self):
        assert split_full_name("Lovelace, Ada") == ("Ada", "Lovelace")

    def test_comma_format_given_with_middle(self):
        assert split_full_name("Hopper, Grace Murray") == ("Grace Murray", "Hopper")

    def test_single_name(self):
        assert split_full_name("Cher") == ("Cher", "")

    def test_empty_string(self):
        assert split_full_name("") == ("", "")

    def test_extra_whitespace_collapsed(self):
        assert split_full_name("  Ada   Lovelace  ") == ("Ada", "Lovelace")

    def test_auto_detect_name_column(self):
        from importer.normalize import auto_detect_mapping

        assert auto_detect_mapping("name") == "full_name"
        assert auto_detect_mapping("full_name") == "full_name"
        assert auto_detect_mapping("participant") == "full_name"


class TestNormalizeCountry:
    def test_alpha2_passthrough(self):
        assert normalize_country("CA") == "CA"

    def test_alpha2_lowercase_normalized(self):
        assert normalize_country("ca") == "CA"

    def test_full_name_canada(self):
        assert normalize_country("Canada") == "CA"

    def test_full_name_united_states(self):
        assert normalize_country("United States") == "US"

    def test_full_name_usa(self):
        assert normalize_country("USA") == "US"

    def test_full_name_uk(self):
        assert normalize_country("United Kingdom") == "GB"

    def test_full_name_uk_alias(self):
        assert normalize_country("uk") == "GB"

    def test_full_name_australia(self):
        assert normalize_country("Australia") == "AU"

    def test_unrecognized_returns_empty(self):
        assert normalize_country("Narnia") == ""

    def test_empty_string_returns_empty(self):
        assert normalize_country("") == ""

    def test_strips_whitespace(self):
        assert normalize_country("  Canada  ") == "CA"


class TestCountryToContinent:
    def test_canada(self):
        assert country_to_continent("CA") == "North America"

    def test_uk(self):
        assert country_to_continent("GB") == "Europe"

    def test_australia(self):
        assert country_to_continent("AU") == "Oceania"

    def test_unknown_code(self):
        assert country_to_continent("ZZ") == ""

    def test_case_insensitive(self):
        assert country_to_continent("ca") == "North America"
