import time
from playwright.sync_api import sync_playwright
from collectors.facebook_ads_library import build_search_url, parse_ad_card

url = build_search_url("cirurgiao plastico")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        locale="pt-BR",
        viewport={"width": 1440, "height": 1600},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    page = context.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=120000)
    page.wait_for_timeout(10000)
    
    buttons = page.get_by_text("Ver detalhes do anúncio")
    count = buttons.count()
    print("Buttons found:", count)
    
    if count > 0:
        first_btn = buttons.nth(0)
        card = first_btn.locator("xpath=ancestor::*[6]")
        print("Card count:", card.count())
        
        raw_text = card.inner_text()
        print("\n--- Raw Text of Card ---\n", repr(raw_text))
        
        # Test parse_ad_card
        ad = parse_ad_card(card, "cirurgiao plastico", url)
        print("\n--- Parsed Ad Card Details ---")
        print("Page Name:", repr(ad.page_name))
        print("Ad Text:", repr(ad.ad_text))
        print("Library ID:", repr(ad.ad_library_id))
        print("Start Date:", repr(ad.start_date))
        print("Ad Status:", repr(ad.ad_status))
        print("CTA Text:", repr(ad.cta_text))
        print("Destination URL:", repr(ad.destination_url))
        print("Destination Domain:", repr(ad.destination_domain))
        
    browser.close()
