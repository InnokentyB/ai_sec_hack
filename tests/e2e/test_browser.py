"""Real browser acceptance over loopback HTTP with durable SQLite and receiver."""

import socket
import threading
import time
from pathlib import Path

import pytest
import uvicorn
from playwright.sync_api import sync_playwright, expect

from app.main import create_app


@pytest.fixture()
def live(tmp_path: Path):
    """Serve a disposable HTTP application; no test clock/fault API is exposed."""
    application = create_app(data_dir=tmp_path, testing=True)
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    application.state.origin = origin
    server = uvicorn.Server(uvicorn.Config(application, log_level="warning"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    assert server.started
    try:
        yield application, origin
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()


def test_s01_s02_s05_s06_s10_s14_s23_s31_browser(live, tmp_path: Path) -> None:
    """Owner UI grants, blocks attacks, delivers, enforces replay and exports."""
    app, origin = live
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True, chromium_sandbox=True, args=["--disable-dev-shm-usage"]
        )
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        try:
            page.goto(origin + "/login")
            page.get_by_label("Owner access key").fill(app.state.runtime.credentials["owner"])
            page.get_by_role("button", name="Open ledger").click()
            expect(page.get_by_text("No authorizations yet.", exact=False)).to_be_visible()
            expect(page.get_by_role("heading", name="Harbor Robotics → Northstar Logistics")).to_be_visible()
            page.get_by_role("button", name="Approve authorization").click()
            expect(page.get_by_role("heading", name="Maya → Atlas")).to_be_visible()
            page.get_by_text("Test a blocked action", exact=True).click()
            page.get_by_role("button", name="Atlas: change recipient to Mallory").click()
            expect(page.get_by_role("status")).to_contain_text("SCOPE_ESCALATION")
            page.get_by_role("button", name="Atlas: delegate to Courier", exact=True).click()
            expect(page.get_by_role("heading", name="Atlas → Courier · Delivery agent")).to_be_visible()
            page.get_by_role("button", name="Test unapproved report v2").click()
            expect(page.get_by_role("status")).to_contain_text("DOCUMENT_CHANGED")
            page.get_by_role("button", name="Courier · Delivery agent: deliver report", exact=True).click()
            expect(page.get_by_role("heading", name="Delivery confirmed")).to_be_visible()
            expect(page.get_by_role("heading", name="Document received", exact=True)).to_be_visible()
            page.get_by_role("button", name="Courier · Delivery agent: deliver report", exact=True).click()
            expect(page.get_by_role("status")).to_contain_text("LIMIT_RESERVED_OR_USED")
            with page.expect_download() as download:
                page.get_by_role("link", name="Download evidence.zip").click()
            assert download.value.suggested_filename == "evidence.zip"
            for width, name in [(1280, "desktop"), (768, "tablet"), (390, "mobile")]:
                page.set_viewport_size({"width": width, "height": 800})
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                page.screenshot(path=str(tmp_path / f"ledger-{name}.png"), full_page=True)
            page.keyboard.press("Tab")
            assert page.evaluate("document.activeElement.tagName") in {
                "BUTTON",
                "A",
                "SUMMARY",
                "INPUT",
                "SELECT",
            }
        finally:
            browser.close()


def test_s12_s17_s18_s32_browser(live) -> None:
    """Browser renders uncertain delivery and resolves it through read-only reconciliation."""
    app, origin = live
    app.state.runtime.receiver.lose_response = True
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, chromium_sandbox=True)
        page = browser.new_page()
        try:
            page.goto(origin + "/login")
            page.get_by_label("Owner access key").fill(app.state.runtime.credentials["owner"])
            page.get_by_role("button", name="Open ledger").click()
            page.get_by_role("button", name="Approve authorization").click()
            page.get_by_role("button", name="Atlas: delegate to Courier", exact=True).click()
            page.get_by_role("button", name="Courier · Delivery agent: deliver report", exact=True).click()
            expect(page.get_by_role("heading", name="Delivery status unknown")).to_be_visible()
            page.reload()
            expect(page.get_by_role("heading", name="Delivery status unknown")).to_be_visible()
            page.get_by_role("button", name="Reconcile receipt").click()
            expect(page.get_by_role("heading", name="Delivery confirmed")).to_be_visible()
            page.get_by_role("button", name="Revoke", exact=True).click()
            expect(
                page.get_by_text("Revocation does not guarantee cancellation of a dispatch already started.")
            ).to_be_visible()
        finally:
            browser.close()
