import os
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    def __init__(self):
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
        self.OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
        self.ALLOWED_DOMAINS = os.getenv("ALLOWED_DOMAINS", "reuters.com,coindesk.com,theblock.co")
        self.QUERY_PACK = os.getenv("QUERY_PACK", "BTC ETH driver;exchange hack exploit")
        self.DEFAULT_WINDOW = os.getenv("DEFAULT_WINDOW", "2h")
        
        # CryptoPanic settings
        self.CRYPTOPANIC_TOKEN = os.getenv("CRYPTOPANIC_TOKEN", "")
        self.CRYPTOPANIC_WINDOW_MIN = int(os.getenv("CRYPTOPANIC_WINDOW_MIN", "120"))
        self.CRYPTOPANIC_FILTER = os.getenv("CRYPTOPANIC_FILTER", "hot")
        self.CRYPTOPANIC_KIND = os.getenv("CRYPTOPANIC_KIND", "news")
        self.CRYPTOPANIC_PUBLIC = os.getenv("CRYPTOPANIC_PUBLIC", "true").lower() == "true"

    @property
    def domains(self) -> List[str]:
        return [d.strip() for d in self.ALLOWED_DOMAINS.split(",") if d.strip()]

    @property
    def queries(self) -> List[str]:
        return [q.strip() for q in self.QUERY_PACK.split(";") if q.strip()]

settings = Settings()  # reads from env
