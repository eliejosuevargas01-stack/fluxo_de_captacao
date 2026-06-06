from models import build_webhook_payload

dummy_card = {
    "ad_library_id": "12345",
    "raw_hash": "hash123",
    "gap": "Missing CTA",
    "contact_has_form": "nao",
    "contact_has_whatsapp": "sim",
    "destination_type": "website",
    "destination_clean_url": "https://example.com",
    "score": 150,
    "offer": "Bot WhatsApp",
    "niche": "veterinaria",
    "page_name": "Vet Clinic",
    "page_url": "https://facebook.com/vet",
    "search_url": "https://search.com",
    "start_date": "2023-01-01",
    "platforms": "instagram, facebook",
    "destination_url": "https://example.com/click"
}

payload = build_webhook_payload(dummy_card)
import json
print(json.dumps(payload, indent=2))
