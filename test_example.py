import re
from playwright.sync_api import Page, expect


def test_example(page: Page) -> None:
    page.goto("https://playwright.dev/")
    expect(page.get_by_role("heading", name="Playwright MCP")).to_be_visible()
    page.get_by_role("link", name="Get started").click()
    page.get_by_role("link", name="Playwright logo Playwright").click()
    with page.expect_popup() as page1_info:
        page.get_by_role("link", name="Star microsoft/playwright on").click()
    page1 = page1_info.value
    expect(page1.get_by_role("button", name="Code", exact=True)).to_be_visible()
    expect(page1.locator("[id=\"_R_3idahlik5_\"]")).to_contain_text("Code")
    page1.get_by_role("button", name="Code", exact=True).click()