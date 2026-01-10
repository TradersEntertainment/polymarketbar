import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import AssetCard from './AssetCard';
import WalletConnectPanel from './WalletConnectPanel';
import SmartTradingPanel from './SmartTradingPanel';
import SmartExitEngine from './SmartExitEngine';
import WhipsawRiskPanel from './WhipsawRiskPanel';
import Footer from './Footer';
import ProfitCalculatorModal from './ProfitCalculatorModal';
import { RefreshCw, Activity, BarChart3, AlertCircle, WifiOff, Calculator } from 'lucide-react';

const ASSETS = ['BTC', 'ETH', 'SOL', 'XRP'];
const TIMEFRAMES = ['15m', '1h', '4h', '1d'];

const Logo = () => {
    const [isRising, setIsRising] = useState(true);

    useEffect(() => {
        const interval = setInterval(() => {
            setIsRising(prev => !prev);
        }, 5000);
        return () => clearInterval(interval);
    }, []);

    return (
        <h1 className="text-5xl md:text-6xl font-black tracking-tighter flex items-center gap-2">
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-violet-400 to-indigo-400 drop-shadow-[0_0_15px_rgba(59,130,246,0.5)]">
                POLYMARKET
            </span>
            <div className="relative flex items-center">
                <span className="text-white mr-3">CANDLES</span>

                {/* Animated Bars */}
                <div className="flex items-end gap-1 h-10">
                    {isRising ? (
                        <>
                            {/* Rising Pattern (Green) */}
                            <div className="w-2 h-4 bg-green-600 rounded-sm opacity-50 transition-all duration-500"></div>
                            <div className="w-2 h-6 bg-green-500 rounded-sm opacity-75 transition-all duration-500 delay-75"></div>
                            <div className="w-2 h-10 bg-green-400 rounded-sm shadow-[0_0_10px_rgba(74,222,128,0.8)] animate-pulse transition-all duration-500 delay-150"></div>
                        </>
                    ) : (
                        <>
                            {/* Falling Pattern (Red) */}
                            <div className="w-2 h-10 bg-red-400 rounded-sm shadow-[0_0_10px_rgba(248,113,113,0.8)] animate-pulse transition-all duration-500"></div>
                            <div className="w-2 h-6 bg-red-500 rounded-sm opacity-75 transition-all duration-500 delay-75"></div>
                            <div className="w-2 h-4 bg-red-600 rounded-sm opacity-50 transition-all duration-500 delay-150"></div>
                        </>
                    )}
                </div>
            </div>
        </h1>
    );
};

const Dashboard = () => {
    const [timeframe, setTimeframe] = useState('1h');
    const [data, setData] = useState({});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [connectionError, setConnectionError] = useState(false);
    const [lastUpdated, setLastUpdated] = useState(new Date());
    const [refreshing, setRefreshing] = useState(false);
    const [showReload, setShowReload] = useState(false);
    const hasDataRef = useRef(false);
    // Cache: { '15m': dataObj, '1h': dataObj, ... }
    const dataCache = useRef({});
    const [selectedSymbol, setSelectedSymbol] = useState('BTC');
    const [isCalculatorOpen, setIsCalculatorOpen] = useState(false);

    useEffect(() => {
        let timer;
        if (loading) {
            timer = setTimeout(() => setShowReload(true), 10000);
        } else {
            setShowReload(false);
        }
        return () => clearTimeout(timer);
    }, [loading]);

    // Handle Timeframe Change with Optimistic Cache
    const handleTimeframeChange = (newTf) => {
        setTimeframe(newTf);
        if (dataCache.current[newTf]) {
            console.log(`[Cache] Hit for ${newTf}`);
            setData(dataCache.current[newTf]); // Instant switch
            // Still fetch fresh data in background? Optional, but good practice.
            // Let the main effect handle the fetch.
        } else {
            console.log(`[Cache] Miss for ${newTf}, showing loading if generic...`);
            // If cache miss, maybe show partial loading or just keep old data until new arrives? 
            // Better to just let the effect run.
            setLoading(true);
        }
    };

    const consecutiveErrors = useRef(0);

    // ...

    useEffect(() => {
        let isMounted = true;
        const controller = new AbortController();

        const fetchData = async (tf = timeframe, isBackground = false) => {
            if (!isBackground) {
                console.log("Fetching data for:", tf);
                if (!hasDataRef.current && !dataCache.current[tf]) setLoading(true);
                else setRefreshing(true);
            }

            try {
                const res = await axios.get(`/api/batch-stats/${tf}`, {
                    params: { _t: Date.now() },
                    timeout: 15000,
                    signal: controller.signal
                });

                if (isMounted && res.data && Object.keys(res.data).length > 0) {
                    // Update Cache
                    dataCache.current[tf] = res.data;
                    consecutiveErrors.current = 0; // Reset errors on success

                    // Only update State if this fetch matches the CURRENT timeframe
                    // OR if it's the initial load filling the screen
                    if (tf === timeframe) {
                        setData(res.data);
                        hasDataRef.current = true;
                        setLastUpdated(new Date());
                        setLoading(false);
                        setRefreshing(false);
                        setError(null);
                        setConnectionError(false);
                    }
                }
            } catch (error) {
                if (!axios.isCancel(error) && isMounted && tf === timeframe) {
                    console.error("Fetch error:", error);
                    consecutiveErrors.current += 1;

                    // Auto-reload removed to prevent disrupting user experience (e.g. closing calculator)
                    // if (consecutiveErrors.current >= 5) { ... }

                    // Only show error if we have NO data at all
                    if (!hasDataRef.current && !dataCache.current[tf]) {
                        setError(`Network error: ${error.message}`);
                    }
                }
            }
        };

        // 1. Fetch current timeframe immediately
        fetchData(timeframe);

        // 2. Prefetch others (Background) - "Turbo Mode"
        const prefetchOthers = async () => {
            const others = TIMEFRAMES.filter(t => t !== timeframe);
            for (const tf of others) {
                if (!dataCache.current[tf]) {
                    // Stagger slightly to avoid backend spam
                    await new Promise(r => setTimeout(r, 500));
                    if (!isMounted) return;
                    fetchData(tf, true);
                }
            }
        };
        // Trigger prefetch after a short delay
        const prefetchTimer = setTimeout(prefetchOthers, 2000);

        // 3. Poll current timeframe (Live updates)
        // Reduced to 3s to match backend cache and provide "Live" feeling for streaks
        const interval = setInterval(() => fetchData(timeframe), 3000);

        return () => {
            isMounted = false;
            controller.abort();
            clearTimeout(prefetchTimer);
            clearInterval(interval);
        };
    }, [timeframe]); // Re-run when timeframe changes (to set up poll for NEW timeframe)



    return (
        <div className="min-h-screen bg-[#0b1121] bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-slate-900 via-[#0b1121] to-black text-white p-2 md:p-10 font-sans selection:bg-blue-500/30">

            {/* Navbar / Header */}
            <header className="max-w-[1600px] mx-auto mb-12 flex flex-col md:flex-row justify-between items-center gap-8 relative z-10">
                <div className="text-center md:text-left">
                    <Logo />
                    <p className="text-slate-400 mt-3 text-lg font-medium flex items-center gap-2 justify-center md:justify-start">
                        <Activity size={18} className="text-blue-500" />
                        Advanced Streak Analytics & Probability Engine
                    </p>
                </div>

                <div className="flex flex-col items-end gap-4">
                    {/* Timeframe Selector */}
                    <div className="flex items-center p-1.5 bg-slate-900/80 backdrop-blur-md rounded-2xl border border-slate-700/50 shadow-2xl">
                        {TIMEFRAMES.map((tf) => (
                            <button
                                key={tf}
                                onClick={() => handleTimeframeChange(tf)}
                                className={`relative px-6 py-2.5 rounded-xl text-sm font-bold transition-all duration-300 ${timeframe === tf
                                    ? 'text-white shadow-[0_0_20px_rgba(59,130,246,0.5)]'
                                    : 'text-slate-500 hover:text-slate-300 hover:bg-white/5'
                                    }`}
                            >
                                {timeframe === tf && (
                                    <div className="absolute inset-0 bg-gradient-to-r from-blue-600 to-violet-600 rounded-xl -z-10"></div>
                                )}
                                {tf}
                            </button>
                        ))}
                    </div>

                    {/* Status Badges */}
                    <div className="flex items-center gap-3">
                        {connectionError && (
                            <div className="flex items-center gap-2 text-xs font-bold text-red-400 bg-red-500/10 px-3 py-1.5 rounded-full border border-red-500/20 animate-pulse">
                                <WifiOff size={14} />
                                Connection Lost
                            </div>
                        )}

                        <div className="flex items-center gap-2 text-xs font-mono text-slate-500 bg-slate-900/50 px-3 py-1.5 rounded-full border border-slate-800">
                            <div className={`w-2 h-2 rounded-full ${connectionError ? 'bg-red-500' : 'bg-green-500'} ${refreshing ? 'animate-ping' : ''}`}></div>
                            Updated: {lastUpdated.toLocaleTimeString()}
                        </div>
                    </div>
                </div>
            </header>

            {/* Main Grid */}
            <main className="max-w-[1600px] mx-auto relative z-10 min-h-[500px]">
                {loading && !error && (
                    <div className="absolute inset-0 z-50 flex items-center justify-center bg-[#0b1121]/90 backdrop-blur-md rounded-3xl transition-all duration-300">
                        <div className="flex flex-col items-center gap-6">
                            {/* Trading Bars Animation */}
                            <div className="flex items-end gap-2 h-16">
                                {[...Array(5)].map((_, i) => (
                                    <div
                                        key={i}
                                        className="w-3 rounded-sm animate-trading-bar"
                                        style={{
                                            animationDelay: `${i * 0.1}s`,
                                            height: '40%',
                                            backgroundColor: i % 2 === 0 ? '#4ade80' : '#f87171' // Initial colors
                                        }}
                                    ></div>
                                ))}
                            </div>

                            <div className="text-center">
                                <div className="text-blue-400 font-bold tracking-[0.2em] text-sm animate-pulse">INITIALIZING MARKET DATA</div>
                                <div className="text-slate-500 text-xs mt-2 font-mono">Connecting to Exchange Aggregator...</div>
                            </div>

                            {showReload && (
                                <button
                                    onClick={() => window.location.reload()}
                                    className="mt-2 px-6 py-2 bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 rounded-lg transition-colors font-bold text-xs border border-blue-500/20 animate-in fade-in slide-in-from-bottom-4"
                                >
                                    Taking too long? Reload
                                </button>
                            )}
                        </div>

                        {/* Custom Styles for the animation */}
                        <style jsx>{`
                            @keyframes trading-bar {
                                0%, 100% { height: 20%; background-color: #f87171; }
                                50% { height: 100%; background-color: #4ade80; }
                            }
                            .animate-trading-bar {
                                animation: trading-bar 0.6s ease-in-out infinite alternate;
                            }
                        `}</style>
                    </div>
                )}

                {error && (
                    <div className="absolute inset-0 z-40 flex items-center justify-center bg-[#0b1121]/90 backdrop-blur-md rounded-3xl">
                        <div className="flex flex-col items-center gap-4 text-center p-8 bg-red-500/10 border border-red-500/20 rounded-2xl">
                            <AlertCircle size={48} className="text-red-500" />
                            <h3 className="text-xl font-bold text-red-400">Unable to Load Data</h3>
                            <p className="text-slate-400">{error}</p>
                            <button
                                onClick={() => window.location.reload()}
                                className="px-6 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg transition-colors font-bold"
                            >
                                Retry Connection
                            </button>
                        </div>
                    </div>
                )}

                <div className={`grid grid-cols-2 md:grid-cols-2 xl:grid-cols-4 gap-2 md:gap-8 transition-opacity duration-300 ${loading ? 'opacity-20' : 'opacity-100'}`}>
                    {ASSETS.map((asset) => (
                        <AssetCard key={asset} data={data[asset]} />
                    ))}
                </div>

                {/* Extended Smart Trading Section */}
                {!loading && !error && data[selectedSymbol] && (
                    <div className="mt-16 animate-in fade-in slide-in-from-bottom-8 duration-700">
                        <div className="flex items-center gap-4 mb-8">
                            <div className="h-px flex-1 bg-gradient-to-r from-transparent via-slate-700 to-transparent"></div>
                            <h2 className="text-2xl font-black text-white uppercase tracking-widest text-center">
                                Smart Execution Layer
                            </h2>
                            <div className="h-px flex-1 bg-gradient-to-r from-transparent via-slate-700 to-transparent"></div>
                        </div>

                        <WalletConnectPanel />

                        {/* We show Smart Trading Panel for the selected asset */}
                        <SmartTradingPanel
                            data={data[selectedSymbol]}
                            timeframe={timeframe}
                            setTimeframe={handleTimeframeChange}
                            selectedSymbol={selectedSymbol}
                            onSymbolChange={setSelectedSymbol}
                            onOpenCalculator={() => setIsCalculatorOpen(true)}
                        />
                        <SmartExitEngine data={data[selectedSymbol]} />
                        <WhipsawRiskPanel data={data[selectedSymbol]} />
                    </div>
                )}
            </main>

            <Footer />

            {/* Floating FOMO Calculator Button */}
            <button
                onClick={() => setIsCalculatorOpen(true)}
                className="fixed bottom-10 right-10 z-[60] group hover:scale-110 transition-transform duration-300"
            >
                <div className="absolute inset-0 bg-gradient-to-r from-blue-600 to-violet-600 rounded-full blur-xl opacity-50 group-hover:opacity-100 group-hover:blur-2xl transition-all duration-500 animate-pulse"></div>
                <div className="relative bg-[#0F172A] p-1 rounded-full border-2 border-indigo-500/50 shadow-2xl overflow-hidden group-hover:border-indigo-400 transition-colors">
                    {/* Inner Gradient Border/Bg */}
                    <div className="bg-gradient-to-br from-indigo-600 via-violet-600 to-fuchsia-600 rounded-full px-6 py-4 flex items-center gap-4">
                        <div className="bg-white/10 p-2.5 rounded-full border border-white/20 shadow-inner backdrop-blur-sm">
                            <Calculator size={28} className="text-white drop-shadow-lg" />
                        </div>
                        <div className="flex flex-col items-start">
                            <span className="text-[10px] font-bold text-indigo-100 uppercase tracking-[0.2em] leading-tight">Dream Big</span>
                            <span className="text-2xl font-black italic text-transparent bg-clip-text bg-gradient-to-r from-white via-blue-100 to-indigo-200 drop-shadow-sm leading-none">
                                100x SIM
                            </span>
                        </div>
                    </div>
                    {/* Shine Effect */}
                    <div className="absolute top-0 -left-[100%] w-full h-full bg-gradient-to-r from-transparent via-white/20 to-transparent skew-x-12 group-hover:animate-shine"></div>
                </div>
                {/* Badge */}
                <div className="absolute -top-2 -right-2 bg-red-500 text-white text-[10px] font-black px-2 py-0.5 rounded-full border-2 border-[#0F172A] shadow-lg animate-bounce">
                    NEW
                </div>
            </button>
            <style jsx>{`
                @keyframes shine {
                    0% { left: -100%; }
                    100% { left: 200%; }
                }
                .group:hover .group-hover\:animate-shine {
                    animation: shine 1s;
                }
            `}</style>

            <ProfitCalculatorModal
                isOpen={isCalculatorOpen}
                onClose={() => setIsCalculatorOpen(false)}
                currentPrice={data[selectedSymbol]?.current_price}
            />

            {/* Background Glows */}
            <div className="fixed top-0 left-0 w-full h-full overflow-hidden pointer-events-none -z-0">
                <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-blue-500/10 rounded-full blur-[120px]"></div>
                <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-violet-500/10 rounded-full blur-[120px]"></div>
            </div>
        </div>
    );
};

export default Dashboard;
