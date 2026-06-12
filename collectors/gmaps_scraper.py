from __future__ import annotations

import re
import time
from urllib.parse import quote_plus
from typing import Any, Dict, List

from playwright.sync_api import sync_playwright

def scrape_maps(query: str, max_results: int = 20) -> List[Dict[str, Any]]:
    """
    Native Google Maps scraper using Playwright.
    Returns a list of dicts with keys matching what the downstream pipeline expects:
    - nome
    - telefone
    - endereco
    - site
    - categoria
    - avaliacoes
    - nota
    """
    
    encoded_query = quote_plus(query)
    url = f"https://www.google.com/maps/search/{encoded_query}?hl=pt-BR"
    
    results: List[Dict[str, Any]] = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            page.wait_for_selector('div[role="feed"]', timeout=15000)
            
            # Scroll to load more results
            feed_handle = page.query_selector('div[role="feed"]')
            if feed_handle:
                items_count = 0
                retries = 0
                while items_count < max_results and retries < 10:
                    page.evaluate('(element) => element.scrollTo(0, element.scrollHeight)', feed_handle)
                    page.wait_for_timeout(1000)
                    
                    # Count items currently loaded
                    elements = page.query_selector_all('div[role="feed"] > div > div > a')
                    new_count = len(elements)
                    
                    if new_count == items_count:
                        retries += 1
                    else:
                        items_count = new_count
                        retries = 0
                        
            # Now extract the data
            articles = page.query_selector_all('div[role="feed"] > div > div > a')
            for index, a_tag in enumerate(articles):
                if len(results) >= max_results:
                    break
                    
                # We can't click all of them easily without losing context, 
                # but we can get basic info from the card itself aria-label
                label = a_tag.get_attribute('aria-label')
                href = a_tag.get_attribute('href')
                if not label:
                    continue
                    
                parent = a_tag.evaluate_handle('el => el.parentElement.parentElement')
                text_content = parent.inner_text() or ""
                
                # Parsing text content (which usually has: Name, Rating, Reviews, Category, Address, Status...)
                lines = [line.strip() for line in text_content.split('\n') if line.strip()]
                
                nome = label
                nota = 0.0
                avaliacoes = 0
                categoria = ""
                endereco = ""
                telefone = ""
                site = ""
                
                if len(lines) > 0:
                    # Look for rating and reviews: e.g. "4.5 (120)"
                    for line in lines:
                        rating_match = re.search(r'([\d,.]+)\s*\(([\d,.]+)\)', line)
                        if rating_match:
                            try:
                                nota_str = rating_match.group(1).replace(',', '.')
                                nota = float(nota_str)
                                av_str = rating_match.group(2).replace('.', '').replace(',', '')
                                avaliacoes = int(av_str)
                            except ValueError:
                                pass
                                
                        # Extract phone if present
                        phone_match = re.search(r'\(?\d{2}\)?\s*\d{4,5}[-\s]\d{4}', line)
                        if phone_match and not telefone:
                            telefone = phone_match.group(0)
                
                # Check if it has website button
                buttons = parent.query_selector_all('button, a')
                for btn in buttons:
                    btn_text = btn.inner_text()
                    if btn_text and "website" in btn_text.lower() or "site" in btn_text.lower():
                        href_attr = btn.get_attribute('href')
                        if href_attr and href_attr.startswith('http'):
                            site = href_attr
                            
                results.append({
                    "nome": nome,
                    "telefone": telefone,
                    "endereco": endereco, # Hard to parse cleanly from list view without clicking
                    "site": site,
                    "categoria": categoria,
                    "avaliacoes": avaliacoes,
                    "nota": nota
                })
                
        except Exception as e:
            print(f"Error scraping maps for query {query}: {e}")
        finally:
            browser.close()
            
    return results
