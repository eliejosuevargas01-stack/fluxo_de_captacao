from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import requests

from meta_ads_pipeline import load_cards, enrich_card
from models import build_webhook_payload

app = FastAPI(title="Lead Extraction API")

class ScrapeRequest(BaseModel):
    queries: List[str]
    max_results: int = 10
    webhook_url: Optional[str] = None

def process_meta_ads(request: ScrapeRequest):
    try:
        cards = load_cards(request.queries, request.max_results)
        unique_cards = {}
        for card in cards:
            key = card.ad_library_id or card.raw_hash
            unique_cards[key] = card

        for card in unique_cards.values():
            enriched = enrich_card(card)
            payload = build_webhook_payload(enriched)

            if request.webhook_url:
                try:
                    requests.post(request.webhook_url, json=payload, timeout=10)
                except Exception as e:
                    print(f"Error sending to webhook: {e}")
            else:
                print(f"Scraped Payload: {payload}")
    except Exception as e:
        print(f"Error processing meta ads: {e}")

@app.post("/scrape/meta_ads")
async def scrape_meta_ads(request: ScrapeRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(process_meta_ads, request)
    return {"status": "accepted", "message": "Scraping meta ads in background"}

@app.post("/scrape/google_maps")
async def scrape_google_maps(request: ScrapeRequest):
    # Placeholder as collectors/google_maps.py is empty
    return {"status": "not_implemented", "message": "Google Maps collector is not yet implemented"}
