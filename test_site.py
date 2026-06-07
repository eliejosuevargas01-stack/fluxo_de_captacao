from collectors.analyzers.funnel_analyzer import inspect_destination

urls = [
    "https://wa.me/5511999999999",
    "https://instagram.com/blabla",
    "https://facebook.com/blabla",
    "https://www.meusiteexterno.com.br",
]

for url in urls:
    signals = inspect_destination(url)
    print(f"{url} -> {signals.destination_type}")
