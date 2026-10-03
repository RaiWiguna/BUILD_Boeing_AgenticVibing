import sys
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    html = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/Proposal/ATC_FlowLens_PitchDeck_Detailed.html").resolve()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(html.as_uri(), wait_until="load")
        issues = []
        for i in range(page.locator(".slide").count()):
            slide = page.locator(".slide").nth(i)
            sb = slide.bounding_box()
            loc = slide.locator("*")
            for j in range(loc.count()):
                el = loc.nth(j)
                bb = el.bounding_box()
                if not bb:
                    continue
                outside = (
                    bb["x"] < sb["x"] - 1
                    or bb["y"] < sb["y"] - 1
                    or bb["x"] + bb["width"] > sb["x"] + sb["width"] + 1
                    or bb["y"] + bb["height"] > sb["y"] + sb["height"] + 1
                )
                if outside:
                    tag = el.evaluate(
                        "e => e.tagName + '.' + (typeof e.className === 'string' ? e.className : '')"
                    )
                    text = el.inner_text(timeout=500)[:100].replace("\n", " ")
                    issues.append((i + 1, tag, text))
                    break
        print("slides", page.locator(".slide").count())
        print("issues", len(issues))
        for issue in issues:
            print(issue)
        browser.close()


if __name__ == "__main__":
    main()
