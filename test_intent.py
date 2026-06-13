from models import build_webhook_payload

card1 = {"cta_text": "Enviar mensagem", "destination_type": "website"}
card2 = {"cta_text": "Saiba mais", "destination_type": "whatsapp", "destination_url": "https://wa.me/551199999"}
card3 = {"cta_text": "Saiba mais", "destination_type": "website"}

payload1 = build_webhook_payload(card1, None)
payload2 = build_webhook_payload(card2, None)
payload3 = build_webhook_payload(card3, None)

print("Card 1 - Tem Site Proprio:", payload1.get("tem_site_proprio"))
print("Card 2 - Link WhatsApp:", payload2.get("link_whatsapp"))
print("Card 3 - Tem CTA:", payload3.get("tem cta?"))
