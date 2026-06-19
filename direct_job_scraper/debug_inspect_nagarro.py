"""Inspect Nagarro careers job search page - deeper."""
from playwright.sync_api import sync_playwright

URL = "https://www.nagarro.com/en/careers/job-search?country=india"

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False,
        args=["--disable-blink-features=AutomationControlled"],
    )
    context = browser.new_context(
        viewport={"width": 1440, "height": 900},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        locale="en-IN",
    )
    context.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
    )
    page = context.new_page()

    api_urls: list[str] = []

    def on_response(response):
        url = response.url
        if any(k in url.lower() for k in ("job", "career", "search", "vacanc", "position")):
            api_urls.append(f"{response.status} {url[:160]}")

    page.on("response", on_response)
    page.goto(URL, wait_until="domcontentloaded", timeout=90000)

    for sel in ["button:has-text('Accept All')", "#onetrust-accept-btn-handler", "button:has-text('Accept')"]:
        loc = page.locator(sel).first
        try:
            if loc.count() and loc.is_visible():
                loc.click(timeout=3000)
                break
        except Exception:
            pass

    for wait in [5000, 10000, 15000]:
        page.wait_for_timeout(5000)
        counts = {
            "job-card": page.locator("[class*='job-card']").count(),
            "jobCard": page.locator("[class*='JobCard']").count(),
            "job_list": page.locator("[class*='job-list']").count(),
            "job-item": page.locator("[class*='job-item']").count(),
            "opening": page.locator("[class*='opening']").count(),
            "position": page.locator("[class*='position']").count(),
            "a[href*='job-detail']": page.locator("a[href*='job-detail']").count(),
            "a[href*='jobs/']": page.locator("a[href*='jobs/']").count(),
            "a[href*='job-search']": page.locator("a[href*='job-search']").count(),
        }
        print(f"\n=== After {wait}ms ===")
        for k, v in counts.items():
            if v:
                print(f"  {k}: {v}")

    print("\n=== API responses ===")
    for u in api_urls[:30]:
        print(u)

    # sample elements with job in class
    print("\n=== Sample [class*=job] outerHTML ===")
    loc = page.locator("[class*='job']")
    for i in range(min(5, loc.count())):
        el = loc.nth(i)
        cls = el.get_attribute("class") or ""
        tag = el.evaluate("el => el.tagName")
        text = el.inner_text().strip().replace("\n", " ")[:120]
        print(f"{i}: <{tag} class='{cls[:80]}'> {text}")

    # try clicking India if not selected
    print("\n=== Job detail links ===")
    for sel in [
        "a[href*='job-detail']",
        "a[href*='/careers/job']",
        "a[href*='jobId']",
        "[class*='job-card'] a",
        "[class*='JobCard'] a",
        "[class*='job-list'] a",
    ]:
        links = page.locator(sel)
        c = links.count()
        if c:
            print(f"\n{sel} ({c}):")
            for i in range(min(5, c)):
                a = links.nth(i)
                print(" ", a.get_attribute("href"), "|", a.inner_text().strip()[:80].replace("\n", " "))

    print("\n=== job-rows-wrapper sample ===")
    wrapper = page.locator(".job-rows-wrapper").first
    if wrapper.count():
        outer = wrapper.evaluate("el => el.innerHTML")
        print(outer[:2500])

    print("\n=== All smartrecruiters links count ===")
    sr = page.locator("a[href*='smartrecruiters.com']")
    print(sr.count())
    for i in range(min(3, sr.count())):
        a = sr.nth(i)
        print(a.get_attribute("href"))
        print(a.evaluate("el => el.outerHTML")[:500])
