import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

# Türkçe finansal duygu analiz sözlüğü (Lexicon)
TURKISH_FINANCIAL_LEXICON = {
    # Olumlu Kelimeler
    "kâr": 0.8, "artış": 0.6, "büyüme": 0.7, "yükseliş": 0.6, "rekor": 0.9, 
    "temettü": 0.5, "kazanç": 0.7, "başarı": 0.6, "pozitif": 0.5, "güçlü": 0.6,
    "beklenti üstü": 0.8, "satın alma": 0.4, "ortaklık": 0.5, "teşvik": 0.6,
    "onay": 0.4, "anlaşma": 0.5, "verimli": 0.6, "ihracat": 0.5,
    # Olumsuz Kelimeler
    "zarar": -0.8, "düşüş": -0.6, "kayıp": -0.7, "dava": -0.4, "ceza": -0.7,
    "negatif": -0.5, "zayıf": -0.6, "beklenti altı": -0.8, "iptal": -0.5,
    "gerileme": -0.6, "kriz": -0.9, "risk": -0.4, "tehlike": -0.5, "iflas": -1.0,
    "faiz artışı": -0.3, "enflasyon": -0.4, "borç": -0.3, "daralma": -0.5
}

# Şirket ve Sembol Eşleştirme Sözlüğü
ENTITY_MAP = {
    "türk hava yolları": "THYAO.IS", "thy": "THYAO.IS", "thyao": "THYAO.IS",
    "tüpraş": "TUPRS.IS", "tuprs": "TUPRS.IS",
    "ereğli": "EREGL.IS", "eregl": "EREGL.IS",
    "garanti": "GARAN.IS", "garan": "GARAN.IS",
    "aselsan": "ASELS.IS", "asels": "ASELS.IS",
    "apple": "AAPL", "aapl": "AAPL",
    "microsoft": "MSFT", "msft": "MSFT",
    "tesla": "TSLA", "tsla": "TSLA",
    "nvidia": "NVDA", "nvda": "NVDA"
}

class NewsIntelligenceEngine:
    """Haber duygu analizi, olay sınıflandırması ve varlık eşleme motoru."""

    def detect_language(self, text: str) -> str:
        """Metnin dilini basit kurallarla tespit eder."""
        turkish_chars = re.compile(r'[ğüşöçİıĞÜŞÖÇ]')
        if turkish_chars.search(text):
            return "tr"
        return "en"

    def extract_entities(self, text: str) -> List[str]:
        """Metindeki şirket isimlerini ve borsa sembollerini eşleştirir."""
        text_lower = text.lower()
        found_symbols = set()
        
        for name, symbol in ENTITY_MAP.items():
            if name in text_lower:
                found_symbols.add(symbol)
                
        return list(found_symbols)

    def classify_event(self, title: str, body: str) -> str:
        """Haber başlığı ve içeriğine göre olay tipini sınıflandırır."""
        combined = f"{title} {body}".lower()
        
        if "temettü" in combined or "dividend" in combined:
            return "DIVIDEND"
        elif "bilanço" in combined or "kâr" in combined or "earnings" in combined or "net gelir" in combined:
            return "EARNINGS"
        elif "satın alma" in combined or "ortaklık" in combined or "m&a" in combined or "birleşme" in combined:
            return "M&A"
        elif "faiz" in combined or "interest rate" in combined or "politika faizi" in combined:
            return "INTEREST_RATE"
        elif "jeopolitik" in combined or "geopolitical" in combined or "savaş" in combined or "gerginlik" in combined:
            return "GEOPOLITICAL"
        elif "derecelendirme" in combined or "rating" in combined or "fitch" in combined or "moody" in combined or "not artışı" in combined:
            return "RATING"
        elif "beklenti" in combined or "öngörü" in combined or "guidance" in combined:
            return "GUIDANCE"
        elif "tcmb" in combined or "fed" in combined or "merkez bankası" in combined or "central bank" in combined:
            return "CENTRAL_BANK"
        elif "enflasyon" in combined or "tüfe" in combined or "cpi" in combined or "gdp" in combined:
            return "MACRO"
        elif "yönetim" in combined or "ceo" in combined or "atama" in combined:
            return "MANAGEMENT"
        elif "dava" in combined or "legal" in combined or "mahkeme" in combined or "ceza" in combined:
            return "LEGAL"
        elif "düzenleme" in combined or "spk" in combined or "sec" in combined or "regülasyon" in combined:
            return "REGULATION"
        elif "hisse geri alım" in combined or "buyback" in combined:
            return "BUYBACK"
        else:
            return "PRODUCT"  # Varsayılan genel olay tipi


    def calculate_sentiment(self, text: str) -> float:
        """Metindeki kelimelerin finansal sözlükteki ağırlıklarına göre sentiment hesaplar."""
        text_clean = re.sub(r'[^\w\s]', '', text.lower())
        words = text_clean.split()
        
        sentiment_score = 0.0
        match_count = 0
        
        for word in words:
            if word in TURKISH_FINANCIAL_LEXICON:
                sentiment_score += TURKISH_FINANCIAL_LEXICON[word]
                match_count += 1
                
        if match_count > 0:
            # -1 ile +1 aralığına normalize et
            return max(-1.0, min(1.0, sentiment_score / match_count))
        return 0.0  # Nötr

    def estimate_impact(self, title: str, sentiment: float, event_type: str) -> str:
        """Habere ait piyasa etki derecesini hesaplar."""
        sentiment_abs = abs(sentiment)
        
        # Kritik olay tipleri ve yüksek duygu oranları yüksek etki yaratır
        if event_type in ["EARNINGS", "CENTRAL_BANK", "CRISIS", "M&A"] and sentiment_abs > 0.5:
            return "HIGH"
        elif sentiment_abs > 0.3:
            return "MEDIUM"
        else:
            return "LOW"

    def process_article(self, title: str, body: str, source: str) -> Dict[str, Any]:
        """Ham haberi işler ve veritabanı şemasına uygun duygu analiz çıktısı üretir."""
        lang = self.detect_language(title + " " + body)
        entities = self.extract_entities(title + " " + body)
        event_type = self.classify_event(title, body)
        sentiment = self.calculate_sentiment(title + " " + body)
        impact = self.estimate_impact(title, sentiment, event_type)
        
        return {
            "source": source,
            "published_at": datetime.now(timezone.utc),
            "title": title,
            "body": body,
            "language": lang,
            "entities": entities,
            "event_type": event_type,
            "sentiment": round(sentiment, 2),
            "impact": impact,
            "data_quality_score": 100.0  # Başarılı NLP işlemi sonrası tam kalite skoru
        }
