import os
from pathlib import Path

from playwright.sync_api import sync_playwright

url = os.environ["BASE_URL"].rstrip("/")
output = Path("artifacts")
output.mkdir(exist_ok=True)
with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    response = page.goto(url, wait_until="networkidle", timeout=30000)
    assert response is not None and response.status == 200
    assert page.locator("#service-address").inner_text() == url
    expected = os.environ.get("EXPECTED_VERSION")
    if expected:
        assert page.locator("dd code").inner_text() == expected
    page.screenshot(path=str(output / "azure-public.png"), full_page=True)
    (output / "deployment.txt").write_text(
        f"URL vérifiée : {url}\nHTTP : {response.status}\nVersion : {expected or 'non imposée'}\n",
        encoding="utf-8",
    )
    browser.close()
