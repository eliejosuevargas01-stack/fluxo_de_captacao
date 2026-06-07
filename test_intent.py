from models import build_webhook_payload

card1 = {"cta_text": "Enviar mensagem", "destination_type": "website"}
card2 = {"cta_text": "Saiba mais", "destination_type": "whatsapp"}
card3 = {"cta_text": "Saiba mais", "destination_type": "website"}

print("Card 1 (Intent Message):", build_webhook_payload(card1, None)["funil_whatsapp_direct"]["tipo_redirecionamento_anuncio"])
print("Card 2 (Dest WhatsApp):", build_webhook_payload(card2, None)["funil_whatsapp_direct"]["tipo_redirecionamento_anuncio"])
print("Card 3 (Website/No msg):", build_webhook_payload(card3, None)["funil_whatsapp_direct"]["tipo_redirecionamento_anuncio"])
