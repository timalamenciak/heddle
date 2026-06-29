import pytest

from enrichment.adapters.http import _validate_url


@pytest.mark.parametrize(
    "url",
    [
        "http://api.openalex.org/works",
        "https://127.0.0.1/internal",
        "https://api.openalex.org.evil.example/works",
        "file:///etc/passwd",
        "https://user:pass@api.openalex.org/works",
    ],
)
def test_outbound_url_allowlist_rejects_unsafe_urls(url):
    with pytest.raises(ValueError):
        _validate_url(url)


def test_outbound_url_allowlist_accepts_known_https_api():
    _validate_url("https://api.openalex.org/works?filter=doi:10.1/x")
