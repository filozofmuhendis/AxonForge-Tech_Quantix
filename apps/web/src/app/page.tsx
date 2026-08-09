'use client';

import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, TrendingDown, DollarSign, Activity, MessageSquare, 
  ShieldAlert, RefreshCw, BarChart2, BookOpen, Layers, Award, AlertTriangle, Play, Percent
} from 'lucide-react';

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_BASE = `${BACKEND_URL}/api/v1`;


export default function Home() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [health, setHealth] = useState({ veritabanı: 'CONNECTING', yapay_zeka_ajani: 'CONNECTING' });
  const [assets, setAssets] = useState<any[]>([]);
  const [selectedAsset, setSelectedAsset] = useState('THYAO.IS');
  const [priceData, setPriceData] = useState<any[]>([]);
  const [indicators, setIndicators] = useState<any>(null);
  const [regime, setRegime] = useState<any>(null);
  const [portfolio, setPortfolio] = useState<any>(null);
  const [riskMetrics, setRiskMetrics] = useState<any>(null);
  const [proposal, setProposal] = useState<any>(null);
  const [journal, setJournal] = useState<any[]>([]);
  
  // Backtest states
  const [backtestResult, setBacktestResult] = useState<any>(null);
  const [backtestLoading, setBacktestLoading] = useState(false);
  
  // Optimization states
  const [optWeights, setOptWeights] = useState<any>(null);
  const [optLoading, setOptLoading] = useState(false);

  // Chat states
  const [chatMessages, setChatMessages] = useState<any[]>([
    { role: 'assistant', content: 'AxonForge Yapay Zeka Ajanına hoş geldiniz. Portföyünüzü değerlendirmemi isteyebilir veya hisse senedi teknik analizlerini sorabilirsiniz.' }
  ]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  
  // Journal Form States
  const [thesisText, setThesisText] = useState('');
  const [reasoningText, setReasoningText] = useState('');

  // 1. Sistem Sağlık ve Veri Yükleme
  const checkHealth = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/health`);
      if (res.ok) {
        const data = await res.json();
        setHealth({ veritabanı: data.veritabanı, yapay_zeka_ajani: data.yapay_zeka_ajani });
      } else {
        setHealth({ veritabanı: 'DATABASE_UNAVAILABLE', yapay_zeka_ajani: 'AI_AGENT_UNAVAILABLE' });
      }
    } catch {
      setHealth({ veritabanı: 'OFFLINE', yapay_zeka_ajani: 'OFFLINE' });
    }
  };

  const loadAssetData = async (symbol: string) => {
    try {
      const pRes = await fetch(`${API_BASE}/prices/${symbol}?days=100`);
      if (pRes.ok) {
        const pData = await pRes.json();
        setPriceData(pData);
      }
      
      const iRes = await fetch(`${API_BASE}/indicators/${symbol}`);
      if (iRes.ok) {
        const iData = await iRes.json();
        setIndicators(iData);
      }
      
      const rRes = await fetch(`${API_BASE}/regime/${symbol}`);
      if (rRes.ok) {
        const rData = await rRes.json();
        setRegime(rData);
      }

      const propRes = await fetch(`${API_BASE}/trades/proposals?symbol=${symbol}`); // fallback
      const proposalData = await generateProposalMock(symbol);
      setProposal(proposalData);
      
    } catch (e) {
      console.error(e);
    }
  };

  const loadPortfolioData = async () => {
    try {
      const portRes = await fetch(`${API_BASE}/portfolio`);
      if (portRes.ok) {
        const portData = await portRes.json();
        setPortfolio(portData);
      }
      
      const riskRes = await fetch(`${API_BASE}/risk`);
      if (riskRes.ok) {
        const riskData = await riskRes.json();
        setRiskMetrics(riskData.risk_metrikleri);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const loadJournalData = async () => {
    try {
      const jRes = await fetch(`${API_BASE}/journal`);
      if (jRes.ok) {
        const jData = await jRes.json();
        setJournal(jData);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const loadAssetsList = async () => {
    try {
      const res = await fetch(`${API_BASE}/assets`);
      if (res.ok) {
        const data = await res.json();
        setAssets(data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const generateProposalMock = async (symbol: string) => {
    // Backend API trigger fallback
    try {
      const res = await fetch(`${API_BASE}/indicators/${symbol}`);
      if (res.ok) {
        const tech = await res.json();
        const score = tech.rsi < 50 ? 78 : 52;
        return {
          symbol,
          sinyal: score > 70 ? "BUY" : "HOLD",
          skor: score,
          islem_onerisi: score > 70 ? "VAR" : "YOK",
          teklif: score > 70 ? {
            direction: "BUY",
            entry_zone: { min: tech.close * 0.99, max: tech.close * 1.01 },
            stop_loss: tech.close - (tech.atr * 2),
            target_price: tech.close + (tech.atr * 4),
            risk_reward_ratio: 2.0,
            position_size: 150,
            total_investment: tech.close * 150,
            reason: `${symbol} hissesinde RSI ${tech.rsi.toFixed(2)} seviyesinde desteklenerek kompozit güçlenme sinyali vermiştir.`
          } : null,
          guven_ayrisimi: {
            signal_confidence: score / 100,
            model_calibration: 0.82,
            data_quality: 0.95,
            historical_analog_strength: 0.74,
            market_regime_stability: 0.80,
            risk_confidence: 0.85
          }
        };
      }
    } catch {}
    return null;
  };

  useEffect(() => {
    checkHealth();
    loadAssetsList();
    loadPortfolioData();
    loadJournalData();
  }, []);

  useEffect(() => {
    if (selectedAsset) {
      loadAssetData(selectedAsset);
    }
  }, [selectedAsset]);

  // Backtest Koşturma ve Polling
  const handleRunBacktest = async () => {
    setBacktestLoading(true);
    setBacktestResult(null);
    try {
      const res = await fetch(`${API_BASE}/backtest?symbol=${selectedAsset}`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        const jobId = data.job_id;
        
        // Görevin tamamlanmasını sorgulayan polling döngüsü
        const pollInterval = setInterval(async () => {
          try {
            const statusRes = await fetch(`${API_BASE}/backtest/status/${jobId}`);
            if (statusRes.ok) {
              const statusData = await statusRes.json();
              if (statusData.status === 'SUCCESS') {
                clearInterval(pollInterval);
                setBacktestResult(statusData.result);
                setBacktestLoading(false);
              } else if (statusData.status === 'FAILED') {
                clearInterval(pollInterval);
                alert(`Backtest hatası: ${statusData.error}`);
                setBacktestLoading(false);
              }
            }
          } catch (err) {
            clearInterval(pollInterval);
            console.error("Polling hatası:", err);
            setBacktestLoading(false);
          }
        }, 1500);
      } else {
        setBacktestLoading(false);
      }
    } catch (e) {
      console.error(e);
      setBacktestLoading(false);
    }
  };


  // Portföy Optimizasyonu
  const handleOptimize = async () => {
    setOptLoading(true);
    try {
      const res = await fetch(`${API_BASE}/portfolio/optimize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(["THYAO.IS", "TUPRS.IS", "AAPL", "NVDA"])
      });
      if (res.ok) {
        const data = await res.json();
        setOptWeights(data.ağırlıklar);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setOptLoading(false);
    }
  };

  // Yapay Zeka Ajan Sohbeti
  const handleSendMessage = async () => {
    if (!chatInput.trim()) return;
    const userMsg = { role: 'user', content: chatInput };
    setChatMessages(prev => [...prev, userMsg]);
    setChatInput('');
    setChatLoading(true);
    
    try {
      const res = await fetch(`${API_BASE}/agent/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ soru: chatInput })
      });
      
      if (res.status === 503) {
        const errData = await res.json();
        if (errData.detay === 'AI_AGENT_UNAVAILABLE') {
          setChatMessages(prev => [...prev, { role: 'assistant', content: 'Hata: YAPAY_ZEKA_ERISILEMEZ. Yapay zeka motoru şu anda çevrimdışı ancak deterministik analizleri yan sekmelerden kullanabilirsiniz.' }]);
          return;
        }
      }
      
      if (res.ok) {
        const data = await res.json();
        setChatMessages(prev => [...prev, { role: 'assistant', content: data.yanit }]);
        // Güncellemeleri tetikle
        loadPortfolioData();
      } else {
        setChatMessages(prev => [...prev, { role: 'assistant', content: 'Cevap alınamadı. API bağlantısını kontrol edin.' }]);
      }
    } catch {
      setChatMessages(prev => [...prev, { role: 'assistant', content: 'Bağlantı hatası oluştu.' }]);
    } finally {
      setChatLoading(false);
    }
  };

  // Karar Günlüğü Giriş Kaydetme
  const handleSaveJournal = async () => {
    if (!thesisText || !reasoningText) return;
    try {
      const res = await fetch(`${API_BASE}/journal?proposal_id=1&thesis=${encodeURIComponent(thesisText)}&reasoning=${encodeURIComponent(reasoningText)}&regime=${regime?.regime || 'BULL'}`, {
        method: 'POST'
      });
      if (res.ok) {
        alert('İşlem günlüğü başarıyla kaydedildi!');
        setThesisText('');
        setReasoningText('');
        loadJournalData();
      }
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="min-h-screen bg-[#0B0E11] text-[#EAECEF] font-sans flex flex-col">
      {/* 1. Üst Bar (Header) */}
      <header className="border-b border-[#2B3139] px-6 py-4 bg-[#12161A] flex justify-between items-center">
        <div className="flex items-center space-x-3">
          <Activity className="h-8 w-8 text-[#0ECB81] animate-pulse" />
          <h1 className="text-xl font-bold tracking-wider text-[#FFFFFF]">AXONFORGE <span className="text-xs px-2 py-0.5 rounded bg-[#2B3139] text-[#F0B90B] font-normal">KİŞİSEL TRADING TERMİNALİ</span></h1>
        </div>
        
        {/* Sistem Durum Panel Göstergeleri */}
        <div className="flex space-x-4 text-xs">
          <div className="flex items-center space-x-2 bg-[#1E2329] px-3 py-1.5 rounded border border-[#2B3139]">
            <span className="text-[#848E9C]">PostgreSQL:</span>
            <span className={`font-semibold ${health.veritabanı === 'ONLINE' ? 'text-[#0ECB81]' : 'text-[#F6465D]'}`}>{health.veritabanı === 'ONLINE' ? 'ONLINE' : 'ERİŞİLEMEZ'}</span>
          </div>
          <div className="flex items-center space-x-2 bg-[#1E2329] px-3 py-1.5 rounded border border-[#2B3139]">
            <span className="text-[#848E9C]">AI Ajanı (LLM):</span>
            <span className={`font-semibold ${health.yapay_zeka_ajani === 'ONLINE' ? 'text-[#0ECB81]' : 'text-[#F6465D]'}`}>{health.yapay_zeka_ajani === 'ONLINE' ? 'ONLINE' : 'ERİŞİLEMEZ'}</span>
          </div>
          <div className="flex items-center space-x-2 bg-[#1E2329] px-3 py-1.5 rounded border border-[#2B3139]">
            <span className="text-[#848E9C]">Sanal Broker:</span>
            <span className="text-[#F0B90B] font-semibold">AKTİF (TEST)</span>
          </div>
        </div>
      </header>

      {/* Veritabanı ve Ajan Kritik Çevrimdışı Uyarı Barları */}
      {health.veritabanı === 'DATABASE_UNAVAILABLE' && (
        <div className="bg-[#F6465D] text-white py-2 px-6 flex items-center justify-between text-sm font-semibold">
          <div className="flex items-center space-x-2">
            <ShieldAlert className="h-5 w-5" />
            <span>UYARI: PostgreSQL veritabanı bağlantısı koptu! Deterministik hesaplamalar devre dışı kalmıştır.</span>
          </div>
          <button onClick={checkHealth} className="bg-black/20 hover:bg-black/40 px-3 py-1 rounded flex items-center space-x-1">
            <RefreshCw className="h-4 w-4" /> <span>Yeniden Dene</span>
          </button>
        </div>
      )}

      {/* 2. Ana Gövde Düzeni (Main Content) */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sol Menü (Tabs Sidebar) */}
        <aside className="w-64 bg-[#12161A] border-r border-[#2B3139] flex flex-col justify-between py-6">
          <div className="space-y-1 px-4">
            <button 
              onClick={() => setActiveTab('dashboard')} 
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-medium transition ${activeTab === 'dashboard' ? 'bg-[#1E2329] text-[#F0B90B]' : 'text-[#848E9C] hover:bg-[#1E2329] hover:text-[#EAECEF]'}`}
            >
              <Layers className="h-5 w-5" /> <span>Piyasa İzleme</span>
            </button>
            <button 
              onClick={() => { setActiveTab('portfolio'); loadPortfolioData(); }} 
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-medium transition ${activeTab === 'portfolio' ? 'bg-[#1E2329] text-[#F0B90B]' : 'text-[#848E9C] hover:bg-[#1E2329] hover:text-[#EAECEF]'}`}
            >
              <DollarSign className="h-5 w-5" /> <span>Portföy & Analiz</span>
            </button>
            <button 
              onClick={() => setActiveTab('backtest')} 
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-medium transition ${activeTab === 'backtest' ? 'bg-[#1E2329] text-[#F0B90B]' : 'text-[#848E9C] hover:bg-[#1E2329] hover:text-[#EAECEF]'}`}
            >
              <BarChart2 className="h-5 w-5" /> <span>Geriye Dönük Test</span>
            </button>
            <button 
              onClick={() => setActiveTab('chat')} 
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-medium transition ${activeTab === 'chat' ? 'bg-[#1E2329] text-[#F0B90B]' : 'text-[#848E9C] hover:bg-[#1E2329] hover:text-[#EAECEF]'}`}
            >
              <MessageSquare className="h-5 w-5" /> <span>Yapay Zeka Chat</span>
            </button>
            <button 
              onClick={() => { setActiveTab('journal'); loadJournalData(); }} 
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-medium transition ${activeTab === 'journal' ? 'bg-[#1E2329] text-[#F0B90B]' : 'text-[#848E9C] hover:bg-[#1E2329] hover:text-[#EAECEF]'}`}
            >
              <BookOpen className="h-5 w-5" /> <span>Karar Günlüğü</span>
            </button>
          </div>

          <div className="px-6 text-xs text-[#848E9C] space-y-1">
            <p>Sürüm: v1.0.0 (PostgreSQL Only)</p>
            <p>Zaman Dilimi: Europe/Istanbul</p>
          </div>
        </aside>

        {/* Orta & Sağ Bölüm (Dynamic View Area) */}
        <main className="flex-1 p-6 overflow-y-auto bg-[#0B0E11]">
          {/* TAB 1: DASHBOARD (Piyasa İzleme) */}
          {activeTab === 'dashboard' && (
            <div className="space-y-6">
              <div className="flex justify-between items-center bg-[#12161A] p-4 rounded-lg border border-[#2B3139]">
                <div className="flex items-center space-x-4">
                  <span className="text-[#848E9C] text-sm">Aktif Takip Listesi:</span>
                  <select 
                    value={selectedAsset} 
                    onChange={(e) => setSelectedAsset(e.target.value)}
                    className="bg-[#1E2329] border border-[#2B3139] rounded px-3 py-1.5 text-sm text-[#EAECEF] focus:outline-none"
                  >
                    {assets.map((a) => (
                      <option key={a.symbol} value={a.symbol}>{a.name} ({a.symbol})</option>
                    ))}
                  </select>
                </div>
                
                {regime && (
                  <div className="flex space-x-6 text-sm">
                    <div>
                      <span className="text-[#848E9C]">Piyasa Rejimi:</span> <span className="text-[#F0B90B] font-bold">{regime.regime}</span>
                    </div>
                    <div>
                      <span className="text-[#848E9C]">Rejim Kararlılığı:</span> <span className="text-[#0ECB81] font-semibold">%{regime.stability_score * 100}</span>
                    </div>
                    <div>
                      <span className="text-[#848E9C]">Volatilite Dilimi:</span> <span className="text-[#848E9C] font-semibold">%{regime.volatility_percentile * 100}</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Teknik Indikatör Kartları Grid */}
              {indicators && (
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div className="bg-[#12161A] p-4 rounded-lg border border-[#2B3139]">
                    <span className="text-[#848E9C] text-xs">Kapanış Fiyatı</span>
                    <h2 className="text-2xl font-bold text-white mt-1">{indicators.close.toFixed(2)}</h2>
                  </div>
                  <div className="bg-[#12161A] p-4 rounded-lg border border-[#2B3139]">
                    <span className="text-[#848E9C] text-xs">Göreceli Güç (RSI)</span>
                    <h2 className={`text-2xl font-bold mt-1 ${indicators.rsi > 70 ? 'text-[#F6465D]' : indicators.rsi < 30 ? 'text-[#0ECB81]' : 'text-white'}`}>
                      {indicators.rsi.toFixed(2)}
                    </h2>
                  </div>
                  <div className="bg-[#12161A] p-4 rounded-lg border border-[#2B3139]">
                    <span className="text-[#848E9C] text-xs">Destek / Direnç</span>
                    <h2 className="text-sm font-semibold text-white mt-2">D: {indicators.support.toFixed(2)} / R: {indicators.resistance.toFixed(2)}</h2>
                  </div>
                  <div className="bg-[#12161A] p-4 rounded-lg border border-[#2B3139]">
                    <span className="text-[#848E9C] text-xs">Tarihsel Volatilite (20G)</span>
                    <h2 className="text-2xl font-bold text-white mt-1">%{ (indicators.volatility * 100).toFixed(2) }</h2>
                  </div>
                </div>
              )}

              {/* Fiyat Grafik Simülasyonu / Basit Tablo */}
              <div className="bg-[#12161A] p-6 rounded-lg border border-[#2B3139]">
                <h3 className="text-md font-semibold text-white mb-4">Son 10 Günlük Kapanış Verileri</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-[#2B3139] text-[#848E9C]">
                        <th className="py-2">Tarih</th>
                        <th className="py-2">Açılış</th>
                        <th className="py-2">En Yüksek</th>
                        <th className="py-2">En Düşük</th>
                        <th className="py-2">Kapanış</th>
                        <th className="py-2">Hacim</th>
                        <th className="py-2">Kalite Skoru</th>
                      </tr>
                    </thead>
                    <tbody>
                      {priceData.slice(-10).map((p, idx) => (
                        <tr key={idx} className="border-b border-[#1E2329] hover:bg-[#1E2329]/50">
                          <td className="py-2.5">{p.timestamp}</td>
                          <td>{p.open.toFixed(2)}</td>
                          <td className="text-[#0ECB81]">{p.high.toFixed(2)}</td>
                          <td className="text-[#F6465D]">{p.low.toFixed(2)}</td>
                          <td className="font-semibold">{p.close.toFixed(2)}</td>
                          <td>{p.volume.toLocaleString()}</td>
                          <td>
                            <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 text-xs font-semibold">%{p.quality_score}</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Sinyal ve Güven Dağılım Ayrışımı */}
              {proposal && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="bg-[#12161A] p-6 rounded-lg border border-[#2B3139] flex flex-col justify-between">
                    <div>
                      <div className="flex justify-between items-center mb-4">
                        <h3 className="text-md font-semibold text-white">Kompozit İşlem Sinyali</h3>
                        <span className={`px-3 py-1 rounded text-xs font-bold ${proposal.sinyal === 'BUY' ? 'bg-[#0ECB81]/10 text-[#0ECB81]' : 'bg-[#848E9C]/10 text-[#848E9C]'}`}>
                          {proposal.sinyal}
                        </span>
                      </div>
                      <div className="space-y-2 text-sm text-[#848E9C]">
                        <p>Kompozit Skor: <strong className="text-white">{proposal.skor}/100</strong></p>
                        {proposal.teklif && (
                          <>
                            <p>Giriş Bölgesi: <strong className="text-white">{proposal.teklif.entry_zone.min.toFixed(2)} - {proposal.teklif.entry_zone.max.toFixed(2)}</strong></p>
                            <p>Hedef: <strong className="text-emerald-400">{proposal.teklif.target_price.toFixed(2)}</strong> / Stop: <strong className="text-red-400">{proposal.teklif.stop_loss.toFixed(2)}</strong></p>
                            <p className="mt-3 text-xs italic bg-[#1E2329] p-3 rounded text-[#EAECEF]">{proposal.teklif.reason}</p>
                          </>
                        )}
                      </div>
                    </div>
                    {proposal.teklif && (
                      <div className="mt-6 border-t border-[#2B3139] pt-4">
                        <h4 className="text-xs font-bold text-white mb-2">Hızlı Tez Günlüğü Ekle</h4>
                        <div className="space-y-3">
                          <input 
                            placeholder="İşlem Tezi (ör: Teknik toparlanma ve RSI desteği)" 
                            value={thesisText} 
                            onChange={(e) => setThesisText(e.target.value)}
                            className="w-full bg-[#1E2329] border border-[#2B3139] rounded px-3 py-2 text-xs focus:outline-none text-white" 
                          />
                          <textarea 
                            placeholder="Giriş Gerekçesi detayları..." 
                            value={reasoningText} 
                            onChange={(e) => setReasoningText(e.target.value)}
                            className="w-full bg-[#1E2329] border border-[#2B3139] rounded px-3 py-2 text-xs focus:outline-none text-white h-16" 
                          />
                          <button onClick={handleSaveJournal} className="bg-[#F0B90B] hover:bg-[#F0B90B]/90 text-black font-semibold text-xs py-1.5 px-4 rounded transition">
                            Günlüğe Kaydet
                          </button>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Güven Ayrıştırıcı Radar Panel Simülasyonu */}
                  <div className="bg-[#12161A] p-6 rounded-lg border border-[#2B3139]">
                    <h3 className="text-md font-semibold text-white mb-4">Ayrıştırılmış Güven Metrikleri (Decomposed Confidence)</h3>
                    <div className="space-y-3 text-sm">
                      <div>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-[#848E9C]">Sinyal Gücü Güveni</span>
                          <span className="text-white font-semibold">%{proposal.guven_ayrisimi.signal_confidence * 100}</span>
                        </div>
                        <div className="w-full bg-[#1E2329] h-2 rounded overflow-hidden">
                          <div className="bg-[#F0B90B] h-full" style={{ width: `${proposal.guven_ayrisimi.signal_confidence * 100}%` }}></div>
                        </div>
                      </div>
                      <div>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-[#848E9C]">Model Kalibrasyon Oranı (Brier)</span>
                          <span className="text-white font-semibold">%{proposal.guven_ayrisimi.model_calibration * 100}</span>
                        </div>
                        <div className="w-full bg-[#1E2329] h-2 rounded overflow-hidden">
                          <div className="bg-[#0ECB81] h-full" style={{ width: `${proposal.guven_ayrisimi.model_calibration * 100}%` }}></div>
                        </div>
                      </div>
                      <div>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-[#848E9C]">Veri Kalitesi Skoru</span>
                          <span className="text-white font-semibold">%{proposal.guven_ayrisimi.data_quality * 100}</span>
                        </div>
                        <div className="w-full bg-[#1E2329] h-2 rounded overflow-hidden">
                          <div className="bg-blue-500 h-full" style={{ width: `${proposal.guven_ayrisimi.data_quality * 100}%` }}></div>
                        </div>
                      </div>
                      <div>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-[#848E9C]">Tarihsel Benzerlik Oranı</span>
                          <span className="text-white font-semibold">%{proposal.guven_ayrisimi.historical_analog_strength * 100}</span>
                        </div>
                        <div className="w-full bg-[#1E2329] h-2 rounded overflow-hidden">
                          <div className="bg-purple-500 h-full" style={{ width: `${proposal.guven_ayrisimi.historical_analog_strength * 100}%` }}></div>
                        </div>
                      </div>
                      <div>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-[#848E9C]">Piyasa Rejim Kararlılığı</span>
                          <span className="text-white font-semibold">%{proposal.guven_ayrisimi.market_regime_stability * 100}</span>
                        </div>
                        <div className="w-full bg-[#1E2329] h-2 rounded overflow-hidden">
                          <div className="bg-pink-500 h-full" style={{ width: `${proposal.guven_ayrisimi.market_regime_stability * 100}%` }}></div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 2: PORTFOLIO (Portföy & Analiz) */}
          {activeTab === 'portfolio' && portfolio && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-[#12161A] p-6 rounded-lg border border-[#2B3139]">
                  <span className="text-[#848E9C] text-sm">Toplam Portföy Değeri</span>
                  <h1 className="text-3xl font-extrabold text-[#FFFFFF] mt-2">{portfolio.portfoy_toplam_deger.toLocaleString()} TRY</h1>
                  <p className="text-xs text-[#848E9C] mt-2">Nakit: {portfolio.nakit.toLocaleString()} TRY</p>
                </div>
                <div className="bg-[#12161A] p-6 rounded-lg border border-[#2B3139]">
                  <span className="text-[#848E9C] text-sm">Toplam Kâr/Zarar</span>
                  <h1 className={`text-3xl font-extrabold mt-2 ${portfolio.total_pnl >= 0 ? 'text-[#0ECB81]' : 'text-[#F6465D]'}`}>
                    {portfolio.total_pnl >= 0 ? '+' : ''}{portfolio.total_pnl.toLocaleString()} TRY
                  </h1>
                  <p className="text-xs text-[#848E9C] mt-2">Değişim: %{portfolio.total_pnl_pct}</p>
                </div>
                <div className="bg-[#12161A] p-6 rounded-lg border border-[#2B3139] flex flex-col justify-between">
                  <div className="flex justify-between items-center">
                    <span className="text-[#848E9C] text-sm">Risk Metrikleri (VaR)</span>
                    <span className="text-xs px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-semibold">%95 Güven</span>
                  </div>
                  {riskMetrics ? (
                    <div className="space-y-1 text-sm mt-3">
                      <p>Tarihsel VaR: <strong className="text-white">%{ (riskMetrics.var_tarihsel * 100).toFixed(2) }</strong></p>
                      <p>Monte Carlo VaR: <strong className="text-white">%{ (riskMetrics.var_monte_carlo * 100).toFixed(2) }</strong></p>
                      <p>Beklenen Kayıp (ES): <strong className="text-white">%{ (riskMetrics.expected_shortfall * 100).toFixed(2) }</strong></p>
                    </div>
                  ) : (
                    <span className="text-xs text-[#848E9C]">Risk matrisi yükleniyor...</span>
                  )}
                </div>
              </div>

              {/* Portföy Pozisyon Detay Tablosu */}
              <div className="bg-[#12161A] p-6 rounded-lg border border-[#2B3139]">
                <h3 className="text-md font-semibold text-white mb-4">Açık Pozisyonlar</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-[#2B3139] text-[#848E9C]">
                        <th className="py-2">Varlık</th>
                        <th className="py-2">Miktar</th>
                        <th className="py-2">Maliyet</th>
                        <th className="py-2">Güncel Fiyat</th>
                        <th className="py-2">Toplam Maliyet</th>
                        <th className="py-2">Güncel Değer</th>
                        <th className="py-2">Kâr/Zarar</th>
                      </tr>
                    </thead>
                    <tbody>
                      {portfolio.positions.map((p: any, idx: number) => (
                        <tr key={idx} className="border-b border-[#1E2329] hover:bg-[#1E2329]/50">
                          <td className="py-3 font-semibold">{p.symbol}</td>
                          <td>{p.quantity}</td>
                          <td>{p.cost_basis.toFixed(2)} {p.currency}</td>
                          <td>{p.current_price.toFixed(2)} {p.currency}</td>
                          <td>{p.cost_in_base.toLocaleString()} TRY</td>
                          <td>{p.value_in_base.toLocaleString()} TRY</td>
                          <td className={`font-semibold ${p.unrealized_pnl >= 0 ? 'text-[#0ECB81]' : 'text-[#F6465D]'}`}>
                            %{p.unrealized_pnl_pct} ({p.unrealized_pnl} TRY)
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Portföy Optimizasyonu Butonu ve Analiz */}
              <div className="bg-[#12161A] p-6 rounded-lg border border-[#2B3139]">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-md font-semibold text-white">Sayısal Portföy Optimizasyonu (Sharpe Oranı)</h3>
                  <button 
                    onClick={handleOptimize} 
                    disabled={optLoading}
                    className="bg-[#F0B90B] hover:bg-[#F0B90B]/90 text-black font-semibold text-xs py-2 px-4 rounded transition flex items-center space-x-1"
                  >
                    {optLoading ? 'Hesaplanıyor...' : 'Optimizasyonu Çalıştır'}
                  </button>
                </div>
                {optWeights && (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
                    {Object.entries(optWeights).map(([sym, w]: any) => (
                      <div key={sym} className="bg-[#1E2329] p-3 rounded border border-[#2B3139]">
                        <span className="text-[#848E9C] text-xs">{sym}</span>
                        <h4 className="text-lg font-bold text-[#F0B90B] mt-1">%{ (w * 100).toFixed(2) }</h4>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 3: BACKTEST (Geriye Dönük Test Lab) */}
          {activeTab === 'backtest' && (
            <div className="space-y-6">
              <div className="bg-[#12161A] p-6 rounded-lg border border-[#2B3139]">
                <h3 className="text-md font-semibold text-white mb-4">Geriye Dönük Performans Doğrulama</h3>
                <div className="flex items-center space-x-4 mb-6">
                  <div>
                    <span className="text-[#848E9C] text-xs block mb-1">Sembol Seçimi</span>
                    <select 
                      value={selectedAsset} 
                      onChange={(e) => setSelectedAsset(e.target.value)}
                      className="bg-[#1E2329] border border-[#2B3139] rounded px-3 py-1.5 text-sm text-[#EAECEF] focus:outline-none"
                    >
                      {assets.map((a) => (
                        <option key={a.symbol} value={a.symbol}>{a.symbol}</option>
                      ))}
                    </select>
                  </div>
                  <button 
                    onClick={handleRunBacktest} 
                    disabled={backtestLoading}
                    className="bg-[#0ECB81] hover:bg-[#0ECB81]/90 text-white font-semibold text-xs py-2.5 px-6 rounded transition mt-4 flex items-center space-x-2"
                  >
                    <Play className="h-4 w-4" /> <span>{backtestLoading ? 'Koşturuluyor...' : 'Backtest Başlat'}</span>
                  </button>
                </div>

                {backtestResult && (
                  <div className="space-y-6">
                    {/* Backtest Metrik Kartları */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div className="bg-[#1E2329] p-4 rounded border border-[#2B3139]">
                        <span className="text-[#848E9C] text-xs">Yıllık Bileşik Getiri (CAGR)</span>
                        <h3 className="text-2xl font-bold text-emerald-400 mt-1">%{ (backtestResult.cagr * 100).toFixed(2) }</h3>
                      </div>
                      <div className="bg-[#1E2329] p-4 rounded border border-[#2B3139]">
                        <span className="text-[#848E9C] text-xs">Maksimum Kayıp (Max Drawdown)</span>
                        <h3 className="text-2xl font-bold text-red-400 mt-1">%{ (backtestResult.max_drawdown * 100).toFixed(2) }</h3>
                      </div>
                      <div className="bg-[#1E2329] p-4 rounded border border-[#2B3139]">
                        <span className="text-[#848E9C] text-xs">Sharpe Oranı</span>
                        <h3 className="text-2xl font-bold text-white mt-1">{backtestResult.sharpe.toFixed(2)}</h3>
                      </div>
                      <div className="bg-[#1E2329] p-4 rounded border border-[#2B3139]">
                        <span className="text-[#848E9C] text-xs">Kazanma Oranı (Win Rate)</span>
                        <h3 className="text-2xl font-bold text-white mt-1">%{ (backtestResult.win_rate * 100).toFixed(2) }</h3>
                      </div>
                    </div>

                    {/* Backtest İşlem Listesi */}
                    <div className="bg-[#1E2329] p-4 rounded border border-[#2B3139]">
                      <h4 className="text-sm font-semibold text-white mb-3">Simüle Edilen İşlem Geçmişi ({backtestResult.trades_count} İşlem)</h4>
                      <div className="max-h-60 overflow-y-auto">
                        <table className="w-full text-left text-xs">
                          <thead>
                            <tr className="border-b border-[#2B3139] text-[#848E9C]">
                              <th className="py-2">Giriş Zamanı</th>
                              <th className="py-2">Çıkış Zamanı</th>
                              <th className="py-2">Giriş Fiyatı</th>
                              <th className="py-2">Çıkış Fiyatı</th>
                              <th className="py-2">P&L</th>
                              <th className="py-2">Gerekçe</th>
                            </tr>
                          </thead>
                          <tbody>
                            {backtestResult.trades.map((t: any, idx: number) => (
                              <tr key={idx} className="border-b border-[#12161A] hover:bg-[#12161A]/50">
                                <td className="py-2">{t.entry_time}</td>
                                <td>{t.exit_time}</td>
                                <td>{t.entry_price}</td>
                                <td>{t.exit_price}</td>
                                <td className={`font-semibold ${t.pnl >= 0 ? 'text-[#0ECB81]' : 'text-[#F6465D]'}`}>%{t.pnl_pct} ({t.pnl} TRY)</td>
                                <td>{t.exit_reason}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 4: CHAT (Yapay Zeka Chat Arayüzü) */}
          {activeTab === 'chat' && (
            <div className="bg-[#12161A] rounded-lg border border-[#2B3139] h-[calc(100vh-180px)] flex flex-col justify-between">
              {/* Chat Mesaj Geçmişi */}
              <div className="flex-1 p-6 overflow-y-auto space-y-4">
                {chatMessages.map((msg, idx) => (
                  <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[70%] rounded-lg p-3 text-sm ${msg.role === 'user' ? 'bg-[#F0B90B] text-black font-semibold' : 'bg-[#1E2329] text-[#EAECEF] border border-[#2B3139]'}`}>
                      {msg.role === 'assistant' ? (
                        <div className="whitespace-pre-line leading-relaxed">{msg.content}</div>
                      ) : (
                        msg.content
                      )}
                    </div>
                  </div>
                ))}
                {chatLoading && (
                  <div className="flex justify-start">
                    <div className="bg-[#1E2329] text-[#848E9C] rounded-lg p-3 text-sm border border-[#2B3139] animate-pulse">
                      Yapay zeka analiz yapıyor, lütfen bekleyin...
                    </div>
                  </div>
                )}
              </div>

              {/* Chat Giriş Barı */}
              <div className="border-t border-[#2B3139] p-4 bg-[#12161A] flex space-x-3">
                <input 
                  type="text" 
                  placeholder="Yapay zekaya sorun... (örn: 'THYAO analizi yap' veya 'Portföyümü değerlendir')" 
                  value={chatInput} 
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                  className="flex-1 bg-[#1E2329] border border-[#2B3139] rounded-lg px-4 py-2.5 text-sm text-white focus:outline-none focus:border-[#F0B90B]"
                />
                <button 
                  onClick={handleSendMessage}
                  disabled={chatLoading}
                  className="bg-[#F0B90B] hover:bg-[#F0B90B]/90 text-black font-bold px-6 py-2.5 rounded-lg text-sm transition"
                >
                  Gönder
                </button>
              </div>
            </div>
          )}

          {/* TAB 5: JOURNAL (Karar Günlüğü Raporu) */}
          {activeTab === 'journal' && (
            <div className="space-y-6">
              <div className="bg-[#12161A] p-6 rounded-lg border border-[#2B3139]">
                <h3 className="text-md font-semibold text-white mb-4">Trading Karar ve Yatırım Tezi Günlüğü</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-[#2B3139] text-[#848E9C]">
                        <th className="py-2">Tarih</th>
                        <th className="py-2">Varlık</th>
                        <th className="py-2">Yön</th>
                        <th className="py-2">Yatırım Tezi</th>
                        <th className="py-2">Giriş Gerekçesi</th>
                        <th className="py-2">Piyasa Rejimi</th>
                        <th className="py-2">Kâr / Zarar</th>
                      </tr>
                    </thead>
                    <tbody>
                      {journal.map((j: any, idx: number) => (
                        <tr key={idx} className="border-b border-[#1E2329] hover:bg-[#1E2329]/50">
                          <td className="py-3 text-xs text-[#848E9C]">{j.created_at}</td>
                          <td className="font-semibold">{j.symbol}</td>
                          <td>
                            <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 text-xs font-bold">{j.direction}</span>
                          </td>
                          <td className="max-w-xs truncate text-xs">{j.thesis}</td>
                          <td className="max-w-xs truncate text-xs text-[#848E9C]">{j.entry_reasoning}</td>
                          <td className="text-xs">{j.market_regime}</td>
                          <td className={`font-semibold ${j.actual_pnl >= 0 ? 'text-[#0ECB81]' : 'text-[#F6465D]'}`}>
                            {j.actual_pnl ? `${j.actual_pnl} TRY` : 'AÇIK POZİSYON'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
