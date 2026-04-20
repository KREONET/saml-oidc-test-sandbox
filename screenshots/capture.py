"""Sandbox screenshot automation.

Drives the four working sandbox SPs through an alice login and dumps PNGs
under /out (mounted to docs/screenshots/ by the compose profile). Run
with `docker compose --profile screenshots run --rm screenshots`.
"""
import os
import sys
import time
from pathlib import Path

from playwright.sync_api import Page, TimeoutError, sync_playwright

OUT = Path(os.environ.get("OUT_DIR", "/out"))
OUT.mkdir(parents=True, exist_ok=True)

ALICE = {"username": "alice", "password": "Sandbox!Alice"}
VIEWPORT = {"width": 1280, "height": 820}


def kc_login(page: Page, user: dict[str, str]) -> None:
    """Fill + submit the Keycloak login form wherever it appears."""
    page.wait_for_selector('input[name="username"]', timeout=15_000)
    page.fill('input[name="username"]', user["username"])
    page.fill('input[name="password"]', user["password"])
    page.locator('input[type="submit"], button[type="submit"]').first.click()


def shot(page: Page, name: str) -> None:
    path = OUT / name
    page.screenshot(path=str(path), full_page=True)
    print(f"wrote {path}")


def otest_flow(page: Page) -> None:
    print("== otest-app (OIDC Claim Inspector) ==")
    page.goto("http://otest.sandbox.ac.kr/", wait_until="networkidle")
    shot(page, "01-otest-oidc-main.png")
    page.get_by_text("OIDC 로그인 시작").click()
    page.wait_for_url("**/realms/sandbox/protocol/openid-connect/auth**")
    page.wait_for_selector('input[name="username"]')
    shot(page, "02-keycloak-login.png")
    kc_login(page, ALICE)
    page.wait_for_url("**/me", timeout=15_000)
    page.wait_for_load_state("networkidle")
    shot(page, "03-otest-oidc-claim-inspector.png")


def owiki_flow(page: Page) -> None:
    print("== owiki-app (Outline OIDC, logged-in view) ==")
    page.goto("http://owiki.sandbox.ac.kr/", wait_until="networkidle")
    # Outline renders a "Continue with Sandbox SSO" button (Korean locale
    # may show "Sandbox SSO 사용하여 계속하기"). Click whichever is visible.
    for selector in [
        "button:has-text('Sandbox SSO')",
        "a:has-text('Sandbox SSO')",
        "button:has-text('Continue')",
        "a:has-text('Continue')",
    ]:
        el = page.locator(selector).first
        if el.count() > 0:
            try:
                el.click(timeout=3_000)
                break
            except TimeoutError:
                continue
    # We should now be at Keycloak; sign in as alice.
    try:
        page.wait_for_url("**/realms/sandbox/**", timeout=15_000)
        kc_login(page, ALICE)
    except TimeoutError:
        pass
    # Wait to land back on owiki after the OIDC roundtrip.
    try:
        page.wait_for_url("http://owiki.sandbox.ac.kr/**", timeout=30_000)
    except TimeoutError:
        pass
    page.wait_for_load_state("networkidle")
    # Outline may drop the user on / (home) or a welcome flow — give the
    # SPA a moment to settle on its logged-in dashboard before the shot.
    time.sleep(3)
    shot(page, "04-owiki-logged-in.png")


def stest_flow(page: Page) -> None:
    print("== stest-app (SAML Assertion Inspector) ==")
    page.goto("http://stest.sandbox.ac.kr/", wait_until="networkidle")
    shot(page, "05-stest-saml-main.png")
    page.get_by_text("SAML SSO 로그인 시작").click()
    page.wait_for_url("**/realms/sandbox/protocol/saml**", timeout=15_000)
    page.wait_for_selector('input[name="username"]')
    kc_login(page, ALICE)
    page.wait_for_url("**/me", timeout=15_000)
    page.wait_for_load_state("networkidle")
    shot(page, "06-stest-saml-assertion.png")


def swiki_flow(page: Page) -> None:
    print("== swiki-app (MediaWiki + Shibboleth SP, logged-in view) ==")
    # Visiting Special:UserLogin triggers mod_shib → Keycloak → ACS →
    # MediaWiki session. After that, Main_Page shows the logged-in view.
    page.goto("http://swiki.sandbox.ac.kr/wiki/Special:UserLogin",
              wait_until="networkidle", timeout=20_000)
    page.wait_for_selector('input[name="username"]', timeout=15_000)
    kc_login(page, ALICE)
    # Wait for the SAML roundtrip to settle back on swiki. Keycloak's
    # auto-submit form POSTs the SAMLResponse → Shibboleth sets the
    # session cookie and redirects; the target URL may be a 404 but the
    # cookie sticks.
    try:
        page.wait_for_url("http://swiki.sandbox.ac.kr/**", timeout=20_000)
    except TimeoutError:
        pass
    page.wait_for_load_state("networkidle")
    # Now load Main_Page fresh so Auth_remoteuser promotes the Shib
    # session (REMOTE_USER header) into a MediaWiki session.
    page.goto("http://swiki.sandbox.ac.kr/wiki/Main_Page",
              wait_until="networkidle", timeout=15_000)
    shot(page, "07-swiki-logged-in.png")


FLOWS = [
    ("otest", otest_flow),
    ("owiki", owiki_flow),
    ("stest", stest_flow),
    ("swiki", swiki_flow),
]


def main() -> int:
    errors: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--disable-dev-shm-usage"])
        for name, flow in FLOWS:
            context = browser.new_context(viewport=VIEWPORT, locale="ko-KR")
            page = context.new_page()
            try:
                flow(page)
            except Exception as e:
                msg = f"{name}: {type(e).__name__}: {e}"
                print(f"!! {msg}", file=sys.stderr)
                errors.append(msg)
                try:
                    shot(page, f"ERROR-{name}.png")
                except Exception:
                    pass
            finally:
                context.close()
        browser.close()
    if errors:
        print("\n--- some flows failed ---")
        for e in errors:
            print(f"  - {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
