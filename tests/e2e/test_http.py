import json
import os
from html.parser import HTMLParser
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

import pytest


@pytest.fixture(scope="module")
def base_url():
    url = os.environ.get("BASE_URL")
    if not url:
        pytest.fail("BASE_URL absent : lancer bash scripts/test-e2e.sh")
    return url.rstrip("/")


def get(url, method="GET"):
    opener = build_opener(ProxyHandler({}))
    try:
        response = opener.open(Request(url, method=method), timeout=10)
    except HTTPError as error:
        response = error
    with response:
        return response.status, response.headers, response.read().decode("utf-8")


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.hrefs.append(dict(attrs).get("href"))


def test_application_is_available(base_url):
    status, headers, body = get(base_url + "/health")
    assert status == 200
    assert headers.get_content_type() == "application/json"
    assert json.loads(body) == {"status": "ok"}


def test_user_opens_home_then_follows_identity_link(base_url):
    status, _, page = get(base_url + "/")
    assert status == 200
    links = Links()
    links.feed(page)
    assert "/who" in links.hrefs
    status, headers, body = get(base_url + "/who")
    assert status == 200
    assert headers.get_content_type() == "text/plain"
    assert body == "Thomas Soubirou-Pouey"


def test_running_version_matches_expected_release(base_url):
    status, _, body = get(base_url + "/version")
    assert status == 200
    version = json.loads(body)["version"]
    assert isinstance(version, str) and version
    if expected := os.environ.get("EXPECTED_VERSION"):
        assert version == expected


def test_unknown_page_returns_404(base_url):
    assert get(base_url + "/inconnue")[0] == 404


def test_identity_cannot_be_modified_by_post(base_url):
    assert get(base_url + "/who", method="POST")[0] == 405
