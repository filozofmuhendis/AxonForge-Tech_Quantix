import logging
import requests
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from packages.common.config import settings
from packages.ai_agent.tools import (
    get_asset_info,
    get_historical_prices,
    calculate_technical_indicators,
    get_current_market_regime,
    get_portfolio_status,
    run_stress_test_scenario,
    generate_asset_trade_proposal
)
from sqlalchemy.orm import Session

logger = logging.getLogger("axonforge.ai_agent.agent")

class AIAgentUnavailableException(Exception):
    """LLM sunucusuna (Ollama, OpenAI vb.) bağlanılamadığında fırlatılan özel hata."""
    def __init__(self, message: str = "AI_AGENT_UNAVAILABLE: Yapay Zeka Ajanı (LLM) servislerine erişilemiyor."):
        self.message = message
        super().__init__(self.message)

class FinancialAIAgent:
    """Doğal dil komutlarını anlayan ve finansal araçları koordine eden yapay zeka ajanı."""
    
    def __init__(self):
        self.provider = settings.LLM_PROVIDER.lower()
        self.model = settings.LLM_MODEL
        self.ollama_host = settings.OLLAMA_HOST

    def check_llm_health(self) -> bool:
        """LLM sağlayıcısının aktif olup olmadığını kontrol eder. Başarısız ise AIAgentUnavailableException fırlatır."""
        if self.provider == "ollama":
            try:
                # Ollama health check
                response = requests.get(f"{self.ollama_host}/api/tags", timeout=3.0)
                if response.status_code == 200:
                    return True
                raise AIAgentUnavailableException()
            except Exception:
                raise AIAgentUnavailableException()
        elif self.provider in ["openai", "anthropic"]:
            # API key kontrolü
            key = settings.OPENAI_API_KEY if self.provider == "openai" else settings.ANTHROPIC_API_KEY
            if not key or len(key.strip()) == 0:
                logger.error(f"{self.provider.upper()} API anahtarı bulunamadı.")
                raise AIAgentUnavailableException(f"AI_AGENT_UNAVAILABLE: {self.provider.upper()} API anahtarı tanımlanmamış.")
            return True
        else:
            raise AIAgentUnavailableException("AI_AGENT_UNAVAILABLE: Bilinmeyen LLM Sağlayıcısı.")

    def run_query(self, db: Session, user_query: str, session_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Kullanıcı sorgusunu alır, ilgili aracı tetikler ve yapılandırılmış
        Türkçe yanıt şablonunu oluşturur.
        """
        # İlk olarak LLM sağlığını kontrol et
        self.check_llm_health()
        
        query_lower = user_query.lower()
        
        # Basit kural tabanlı araç yönlendirme (Niyet Analizi - Intent Routing)
        # LLM kapalı olsa bile bu hata fırlatılır, ancak LLM açıksa sorgu işlenir
        try:
            # 1. Sembol tespiti (Örn: "THYAO", "AAPL", "NVDA", "TUPRS")
            target_symbol = None
            for key in ["thyao", "tuprs", "eregl", "garan", "asels", "aapl", "msft", "tsla", "nvda"]:
                if key in query_lower:
                    if key == "thyao": target_symbol = "THYAO.IS"
                    elif key == "tuprs": target_symbol = "TUPRS.IS"
                    elif key == "eregl": target_symbol = "EREGL.IS"
                    elif key == "garan": target_symbol = "GARAN.IS"
                    elif key == "asels": target_symbol = "ASELS.IS"
                    else: target_symbol = key.upper()
                    break

            # 2. Araç Koordine Etme (Tool Orchestration)
            tool_data = {}
            response_content = ""
            
            if "portföy" in query_lower or "portfoy" in query_lower:
                port_status = get_portfolio_status(db)
                tool_data = {"portfolio": port_status}
                
                # Türkçe yanıt şablonunu oluştur
                response_content = self._format_portfolio_response(port_status)
                
            elif "stres" in query_lower or "şok" in query_lower:
                # BIST -15% ve USDTRY +10% şok testi yap
                shocks = {"BIST": -0.15, "USDTRY": 0.10}
                stress_res = run_stress_test_scenario(db, shocks)
                tool_data = {"stress_test": stress_res}
                response_content = self._format_stress_response(stress_res)
                
            elif target_symbol and ("işlem" in query_lower or "sinyal" in query_lower or "öneri" in query_lower or "oneri" in query_lower):
                proposal_res = generate_asset_trade_proposal(db, target_symbol)
                tool_data = {"trade_proposal": proposal_res}
                response_content = self._format_proposal_response(proposal_res)
                
            elif target_symbol:
                # Genel teknik ve piyasa analizi
                tech = calculate_technical_indicators(db, target_symbol)
                regime = get_current_market_regime(db, target_symbol)
                tool_data = {"technical": tech, "regime": regime}
                response_content = self._format_analysis_response(target_symbol, tech, regime)
                
            else:
                # Genel sohbet / fallback
                response_content = (
                    "**ÖZET**\nAxonForge Terminal Yapay Zeka Ajanına hoş geldiniz.\n\n"
                    "**ANALİZ**\nSize şu konularda yardımcı olabilirim:\n"
                    "- Varlık analizi yapabilirim (Örn: '*THYAO analizi yap*')\n"
                    "- İşlem ve sinyal önerileri sunabilirim (Örn: '*THYAO için işlem teklifi oluştur*')\n"
                    "- Portföy değerinizi ve riskinizi inceleyebilirim (Örn: '*Portföyümü değerlendir*')\n"
                    "- Portföyünüze makro stres testleri uygulayabilirim (Örn: '*Stres testi yap*')\n"
                )
                
            return {
                "yanit": response_content,
                "data": tool_data,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Ajan sorgu yürütme hatası: {str(e)}")
            raise AIAgentUnavailableException(f"AI_AGENT_UNAVAILABLE: Ajan çalışırken hata oluştu: {str(e)}")

    # Türkçe Rapor Şablon Biçimlendiricileri
    def _format_portfolio_response(self, port: Dict[str, Any]) -> str:
        pos_lines = []
        for pos in port["positions"]:
            pos_lines.append(f"- **{pos['symbol']}**: Miktar: {pos['quantity']}, Maliyet: {pos['cost_basis']} {pos['currency']}, Kar/Zarar: %{pos['unrealized_pnl_pct']}")
            
        return (
            f"**ÖZET**\nPortföy Değerleme Raporu.\n\n"
            f"**VERİ**\n"
            f"- Portföy Toplam Değeri: **{port['portfoy_toplam_deger']:.2f} TRY**\n"
            f"- Nakit Bakiye: **{port['nakit']:.2f} TRY**\n"
            f"- Yatırımdaki Tutar: **{port['total_value']:.2f} TRY**\n"
            f"- Toplam Kâr/Zarar: **{port['total_pnl']:.2f} TRY** (%{port['total_pnl_pct']})\n\n"
            f"**ANALİZ**\n"
            f"Açık Pozisyonlar:\n" + "\n".join(pos_lines) + "\n\n"
            f"**RİSKLER**\n"
            f"- Sektörel Dağılım: {port['exposures']['sector']}\n"
            f"- Döviz Dağılımı: {port['exposures']['currency']}\n"
        )

    def _format_stress_response(self, stress: Dict[str, Any]) -> str:
        pos_lines = []
        for pos in stress["pozisyon_etkileri"]:
            pos_lines.append(f"- **{pos['symbol']}**: Başlangıç Değeri: {pos['initial_value']} TRY, Beklenen P&L: {pos['expected_pnl']} TRY (%{pos['pnl_pct']})")
            
        return (
            f"**ÖZET**\nMakro Stres Testi Simülasyon Raporu.\n\n"
            f"**PİYASA BAĞLAMI**\n"
            f"Uygulanan Şok Senaryosu: {stress['senaryo_soklari']}\n\n"
            f"**ANALİZ**\n"
            f"Portföy Etkisi: **{stress['portfoy_beklenen_pnl']:.2f} TRY** (Beklenen Değişim: **%{stress['portfoy_beklenen_pnl_yuzde']}**)\n"
            f"Pozisyon Etki Detayları:\n" + "\n".join(pos_lines) + "\n\n"
            f"**RİSKLER**\n"
            f"Sektörel Kayıp Dağılımları: {stress['kırilimlar']['sektor']}\n"
        )

    def _format_proposal_response(self, prop: Dict[str, Any]) -> str:
        if prop.get("islem_onerisi") == "YOK":
            return f"**ÖZET**\nİşlem Önerisi Raporu ({prop['symbol']}).\n\n**SİNYALLER**\n{prop['gerekce']}"
            
        teklif = prop["teklif"]
        g_ayrisim = prop["guven_ayrisimi"]
        
        return (
            f"**ÖZET**\n{prop['symbol']} için Alış Sinyali ve İşlem Teklifi Üretilmiştir.\n\n"
            f"**SİNYALLER**\n"
            f"- Sinyal Gücü: **{prop['skor']}/100** ({prop['sinyal']})\n"
            f"- Tetikleyici Gerekçe: {teklif['reason']}\n\n"
            f"**İŞLEM ÖNERİSİ**\n"
            f"- Yön: **{teklif['direction']}**\n"
            f"- Giriş Aralığı: **{teklif['entry_zone']['min']} - {teklif['entry_zone']['max']}**\n"
            f"- Stop Loss: **{teklif['stop_loss']}** (ATR Tabanlı)\n"
            f"- Kâr Hedefi: **{teklif['target_price']}**\n"
            f"- Risk/Ödül Oranı: **{teklif['risk_reward_ratio']}**\n"
            f"- Önerilen Pozisyon Büyüklüğü: **{teklif['position_size']} Adet**\n"
            f"- Toplam Yatırım Tutarı: **{teklif['total_investment']} TRY**\n\n"
            f"**GÜVEN DEĞERİ (CONFIDENCE BREAKDOWN)**\n"
            f"- Sinyal Güveni: %{g_ayrisim['signal_confidence']*100:.1f}\n"
            f"- Model Kalibrasyon Kalitesi: %{g_ayrisim['model_calibration']*100:.1f}\n"
            f"- Veri Kalite Skoru: %{g_ayrisim['data_quality']*100:.1f}\n"
            f"- Tarihsel Analog Eşleşme Gücü: %{g_ayrisim['historical_analog_strength']*100:.1f}\n"
            f"- Piyasa Rejimi Kararlılığı: %{g_ayrisim['market_regime_stability']*100:.1f}\n"
            f"- Risk Sınırı Payı Güveni: %{g_ayrisim['risk_confidence']*100:.1f}\n\n"
            f"**VARSAYIMLAR**\n"
            f"- {teklif['invalidation_conditions']}\n"
        )

    def _format_analysis_response(self, symbol: str, tech: Dict[str, Any], regime: Dict[str, Any]) -> str:
        return (
            f"**ÖZET**\n{symbol} Piyasa ve Teknik Analiz Raporu.\n\n"
            f"**PİYASA BAĞLAMI**\n"
            f"- Geçerli Piyasa Rejimi: **{regime['regime']}**\n"
            f"- Rejim Kararlılık Skoru: **{regime['stability_score']:.2f}**\n"
            f"- Tarihsel Volatilite Yüzdeliği: **%{regime['volatility_percentile']*100:.1f}**\n\n"
            f"**VERİ**\n"
            f"- Son Kapanış Fiyatı: **{tech['close']:.2f}**\n"
            f"- 20 Günlük SMA: **{tech['sma_20']:.2f}**\n"
            f"- 50 Günlük SMA: **{tech['sma_50']:.2f}**\n"
            f"- 200 Günlük SMA: **{tech['sma_200']:.2f}**\n\n"
            f"**ANALİZ**\n"
            f"- Göreceli Güç Endeksi (RSI): **{tech['rsi']:.2f}**\n"
            f"- Destek Seviyesi: **{tech['support']:.2f}**\n"
            f"- Direnç Seviyesi: **{tech['resistance']:.2f}**\n"
            f"- Ortalama Gerçek Aralık (ATR): **{tech['atr']:.2f}**\n"
        )
