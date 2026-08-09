import time
import logging
from datetime import datetime, timezone
from packages.common.database import SessionLocal, check_db_connection
from packages.common.models import NewsArticle
from packages.news_engine.news import NewsIntelligenceEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("axonforge.worker.news")

def run_news_worker():
    logger.info("News Worker başlatılıyor...")
    
    try:
        check_db_connection()
    except Exception:
        logger.error("Veritabanı bağlantısı yok. Worker durduruluyor.")
        return

    db = SessionLocal()
    nlp = NewsIntelligenceEngine()

    # Örnek Türkçe Finans Haber Akışı (Simüle Haber Kaynakları)
    mock_feed = [
        {
            "title": "Türk Hava Yolları rekor kâr açıkladı!",
            "body": "Türk Hava Yolları (THY), yılın ikinci çeyreğinde beklentilerin üzerinde net kâr elde ettiğini duyurdu. Büyüme rakamları analistleri şaşırttı.",
            "source": "KapHaber"
        },
        {
            "title": "Tüpraş temettü dağıtacağını bildirdi",
            "body": "Tüpraş yönetim kurulu, pay sahiplerine hisse başına brüt 12.50 TL nakit temettü ödenmesini genel kurula teklif etme kararı aldı.",
            "source": "FinansHaber"
        },
        {
            "title": "Piyasalarda faiz artışı baskısı sürüyor",
            "body": "Merkez Bankası'nın (TCMB) enflasyon ile mücadele kapsamında faiz oranlarında artışa gidebileceği yönündeki beklentiler borsada baskı yaratıyor.",
            "source": "MerkezFinans"
        },
        {
            "title": "Teknoloji hisselerinde gerileme",
            "body": "Küresel yarı iletken krizinin etkisiyle Nvidia ve Apple gibi devlerin hisselerinde kısa vadeli değer kayıpları ve kâr satışları yaşanıyor.",
            "source": "GlobalFinance"
        }
    ]

    try:
        for item in mock_feed:
            # Aynı haberin tekrarlanmasını önlemek için başlığa göre kontrol et
            existing = db.query(NewsArticle).filter(NewsArticle.title == item["title"]).first()
            if existing:
                continue
                
            # NLP İşlemleri (Dil tespiti, olay tipi, duygu skoru)
            article_data = nlp.process_article(item["title"], item["body"], item["source"])
            
            db_news = NewsArticle(
                source=article_data["source"],
                published_at=article_data["published_at"],
                title=article_data["title"],
                body=article_data["body"],
                language=article_data["language"],
                entities=article_data["entities"],
                event_type=article_data["event_type"],
                sentiment=article_data["sentiment"],
                impact=article_data["impact"],
                data_quality_score=article_data["data_quality_score"]
            )
            
            db.add(db_news)
            logger.info(f"Yeni haber kaydedildi: {item['title']} - Sinyal Grubu: {article_data['event_type']} ({article_data['sentiment']})")
            
        db.commit()
        logger.info("Haber akış taraması tamamlandı.")
        
    except Exception as e:
        logger.error(f"News Worker çalışırken hata: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    run_news_worker()
