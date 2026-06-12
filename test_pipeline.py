from collectors.analyzers.funnel_analyzer import build_offer, FunnelSignals

signals = FunnelSignals(
    destination_type="whatsapp",
    clean_url="https://wa.me/5511999999999",
    domain="wa.me",
    has_whatsapp=True,
    has_form=False,
    has_booking=False,
    has_instagram=False,
    has_phone=False,
    has_email=False,
    title="",
    error=""
)

proposal1 = build_offer("veterinaria", signals, "active")
print("=== Dummy Lead 1: WhatsApp without form (Veterinaria) ===")
print("Gap:", proposal1.gap)
print("Offer:", proposal1.offer)
print("Score:", proposal1.score)
print("Confidence:", proposal1.confidence)
print("Evidence:", proposal1.evidence)
print()

signals2 = FunnelSignals(
    destination_type="instagram_profile",
    clean_url="https://instagram.com/clinicaxyz",
    domain="instagram.com",
    has_whatsapp=False,
    has_form=False,
    has_booking=False,
    has_instagram=True,
    has_phone=False,
    has_email=False,
    title="",
    error=""
)

proposal2 = build_offer("odontologia", signals2, "active")
print("=== Dummy Lead 2: Instagram profile (Odontologia) ===")
print("Gap:", proposal2.gap)
print("Offer:", proposal2.offer)
print("Score:", proposal2.score)
print("Confidence:", proposal2.confidence)
print("Evidence:", proposal2.evidence)
print()

signals3 = FunnelSignals(
    destination_type="website",
    clean_url="https://imobiliaria-ruim.com",
    domain="imobiliaria-ruim.com",
    has_whatsapp=False,
    has_form=False,
    has_booking=False,
    has_instagram=False,
    has_phone=False,
    has_email=False,
    title="",
    error=""
)

proposal3 = build_offer("imobiliaria", signals3, "active")
print("=== Dummy Lead 3: Website without form (Imobiliaria) ===")
print("Gap:", proposal3.gap)
print("Offer:", proposal3.offer)
print("Score:", proposal3.score)
print("Confidence:", proposal3.confidence)
print("Evidence:", proposal3.evidence)
