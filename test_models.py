from models import build_webhook_payload
dummy_card = {
    "ad_library_id": "123",
    "destination_type": "website",
    "status_code": 404
}
payload = build_webhook_payload(dummy_card, None)
print("Tem site proprio:", payload.get("tem_site_proprio"))
print("Erros:", payload.get("erros_identificados_site"))

dummy_card_ok = {
    "ad_library_id": "123",
    "destination_type": "website",
    "status_code": 200
}
payload_ok = build_webhook_payload(dummy_card_ok, None)
print("Tem site proprio OK:", payload_ok.get("tem_site_proprio"))
print("Erros OK:", payload_ok.get("erros_identificados_site"))
