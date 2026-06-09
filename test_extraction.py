import unittest
from collectors.analyzers.funnel_analyzer import (
    extract_emails_from_text,
    extract_phones_from_text,
)

class TestExtraction(unittest.TestCase):
    def test_email_extraction(self):
        text = "Entre em contato por email: teste@exemplo.com ou contato@empresa.com.br."
        emails = extract_emails_from_text(text)
        self.assertEqual(emails, ["teste@exemplo.com", "contato@empresa.com.br"])

    def test_phone_extraction_wa_links(self):
        text = "Fale conosco no wa.me/5511999998888 ou api.whatsapp.com/send?phone=5511777776666."
        phones = extract_phones_from_text(text)
        self.assertEqual(phones, ["5511999998888", "5511777776666"])

    def test_phone_extraction_brazilian_numbers(self):
        text = "Nosso telefone e (11) 98765-4321 ou +55 21 91234 5678. Landline: (11) 3222-1111."
        phones = extract_phones_from_text(text)
        # Mobile pattern matches first
        self.assertIn("5511987654321", phones)
        self.assertIn("5521912345678", phones)
        self.assertIn("551132221111", phones)

if __name__ == "__main__":
    unittest.main()
