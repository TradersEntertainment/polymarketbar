import React, { useState, useEffect, useRef } from 'react';
import { Search, ChevronDown, Clock, ArrowRight } from 'lucide-react';
import axios from 'axios';
import { prefetchOrderbook } from './OrderbookPanel';

// Module-level cache to persist across re-renders/remounts
let globalMarketCache = null;
let lastCacheUpdate = 0;
const CACHE_DURATION = 60000; // 60 seconds

const MarketSelector = ({ onSelect, activeAsset, onAssetChange, selectedTimeframe = '15m' }) => {
    const [markets, setMarkets] = useState([]);
    const [filteredMarkets, setFilteredMarkets] = useState([]);
    const [isOpen, setIsOpen] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');
    const [loading, setLoading] = useState(false);
    const [selectedMarket, setSelectedMarket] = useState(null);
    const dropdownRef = useRef(null);

    const ASSETS = ['BTC', 'ETH', 'SOL', 'XRP'];

    useEffect(() => {
        // Initial load
        loadMarkets();

        // Close dropdown when clicking outside
        const handleClickOutside = (event) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setIsOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    // Refetch/Filter when asset changes
    useEffect(() => {
        setMarkets([]);
        setSelectedMarket(null);
        onSelect(null);

        // Load broad markets, then specifically fetch and select the LIVE (0) market
        loadMarkets().then(() => {
            console.log("Auto-fetch LIVE triggered.");
            handleQuickLink(0).then(() => {
                // Background Prefetch for other slots
                [0, 1, 2, 3].forEach(offset => {
                    // Start small delay to not block main thread immediately
                    setTimeout(() => prefetchSlot(offset), 1000 + (offset + 1) * 500);
                });
            });
        });
    }, [activeAsset, selectedTimeframe]);

    // PREFETCH HELPER
    const prefetchSlot = async (offset) => {
        try {
            const targetSlug = generatePredictedSlug(offset, activeAsset, selectedTimeframe);
            if (!targetSlug) return;

            // 1. Fetch Event/Market Data
            const response = await axios.get(`/api/poly/events?slug=${targetSlug}`);
            if (response.data && Array.isArray(response.data) && response.data.length > 0) {
                const event = response.data[0];
                if (event.markets && event.markets.length > 0) {
                    const market = event.markets[0];
                    if (market.clobTokenIds) {
                        let parsedIds;
                        if (typeof market.clobTokenIds === 'string') {
                            parsedIds = JSON.parse(market.clobTokenIds);
                        } else if (Array.isArray(market.clobTokenIds)) {
                            parsedIds = market.clobTokenIds;
                        }

                        if (Array.isArray(parsedIds) && parsedIds.length >= 2) {
                            // 2. Prefetch Orderbooks
                            // console.log(`[Prefetch] Triggering for offset ${offset} (${market.question})`);
                            prefetchOrderbook(parsedIds[0]); // YES
                            prefetchOrderbook(parsedIds[1]); // NO
                        }
                    }
                }
            }
        } catch (e) {
            // silent fail
        }
    };

    // Auto-select soonest expiring market (Current) when markets load
    useEffect(() => {
        if (markets.length > 0 && !selectedMarket) {
            // Sort by end date to find the soonest expiring (Current)
            const sorted = [...markets].sort((a, b) => {
                const dA = new Date(a.end_date_iso || a.endDate).getTime();
                const dB = new Date(b.end_date_iso || b.endDate).getTime();
                return dA - dB;
            });

            // Prefer a market that matches the selected timeframe in slug/question
            const best = sorted.find(m =>
                (m.market_slug && m.market_slug.includes(selectedTimeframe)) ||
                (m.question && m.question.includes(selectedTimeframe))
            ) || sorted[0];

            if (best) {
                console.log("Auto-selecting market:", best.question);
                handleSelect(best);
            }
        }
    }, [markets, activeAsset, selectedTimeframe]);

    useEffect(() => {
        filterMarkets(searchTerm);
    }, [searchTerm, markets]);

    const loadMarkets = async () => {
        setLoading(true);
        try {
            const now = Date.now();

            // 1. Check Global Cache
            if (!globalMarketCache || (now - lastCacheUpdate > CACHE_DURATION)) {
                console.log("Fetching fresh markets from API...");
                const response = await axios.get('/api/poly/markets?active=true&limit=1000'); // Fetch ALL active
                if (response.data && Array.isArray(response.data)) {
                    globalMarketCache = response.data;
                    lastCacheUpdate = now;
                }
            } else {
                console.log("Using cached markets");
            }

            // 2. Filter from Cache for Current Asset
            if (globalMarketCache) {
                const slugPattern = `${activeAsset.toLowerCase()}-updown-`;
                const candleMarkets = globalMarketCache.filter(m => {
                    const slug = m.market_slug || '';
                    return slug.includes(slugPattern);
                });

                // Fallback / Broad search
                const finalMarkets = candleMarkets.length > 0 ? candleMarkets : globalMarketCache.filter(m =>
                    m.question.includes(activeAsset) || m.question.includes(activeAsset === 'BTC' ? 'Bitcoin' : activeAsset === 'ETH' ? 'Ethereum' : activeAsset)
                );

                setMarkets(finalMarkets);
            }
        } catch (error) {
            console.error("Error fetching markets:", error);
        } finally {
            setLoading(false);
        }
    };

    const filterMarkets = (term) => {
        if (!term) {
            setFilteredMarkets(markets);
            return;
        }
        const lowerTerm = term.toLowerCase();
        const filtered = markets.filter(m =>
            m.question.toLowerCase().includes(lowerTerm) ||
            (m.market_slug && m.market_slug.toLowerCase().includes(lowerTerm))
        );
        setFilteredMarkets(filtered);
    };

    const handleSelect = (market) => {
        setSelectedMarket(market);
        onSelect(market);
        setIsOpen(false);
        setSearchTerm('');
    };

    // --- NEW: Predictive Slug Logic ---
    const generateNaturalLangSlug = (offset, asset, timeframe) => {
        const ASSET_MAP = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'SOL': 'solana',
            'XRP': 'xrp',
            'DOGE': 'dogecoin',
            'AVAX': 'avalanche'
        };

        const slugAsset = ASSET_MAP[asset] || asset.toLowerCase();

        // Calculate Target UTC Start Time
        const now = new Date();
        let targetStart; // UTC start of bucket

        if (timeframe === '1h') {
            const startOfHour = new Date(now);
            startOfHour.setUTCMinutes(0, 0, 0);
            targetStart = new Date(startOfHour.getTime() + offset * 60 * 60000);
        } else if (timeframe === '4h') {
            const hour = now.getUTCHours();
            const remainder = hour % 4;
            const startOfBlock = new Date(now);
            startOfBlock.setUTCHours(hour - remainder, 0, 0, 0);
            targetStart = new Date(startOfBlock.getTime() + offset * 4 * 60 * 60000);
        } else if (timeframe === '1d') {
            const today = new Date(now);
            today.setUTCHours(0, 0, 0, 0);
            targetStart = new Date(today.getTime() + offset * 24 * 60 * 60000);
        } else {
            return null;
        }

        // Convert Target Start to ET (Eastern Time)
        const formatter = new Intl.DateTimeFormat('en-US', {
            timeZone: 'America/New_York',
            month: 'long',
            day: 'numeric',
            hour: 'numeric',
            hour12: true,
            minute: 'numeric' // implicit, mostly 0
        });

        // HACK: Format to parts to assemble
        const parts = formatter.formatToParts(targetStart);
        const getPart = (type) => parts.find(p => p.type === type)?.value;

        const month = getPart('month').toLowerCase(); // december
        const day = getPart('day'); // 8
        const dayPeriod = getPart('dayPeriod').toLowerCase(); // am/pm
        let hour = getPart('hour'); // 3

        const timeStr = `${hour}${dayPeriod}-et`;

        if (timeframe === '1d') {
            return `${slugAsset}-up-or-down-on-${month}-${day}`;
        }

        return `${slugAsset}-up-or-down-${month}-${day}-${timeStr}`;
    };

    const generatePredictedSlug = (offset, asset, timeframe) => {
        // 15m uses older timestamp format
        if (timeframe === '15m') {
            const now = new Date();
            const assetLower = asset.toLowerCase();
            let slugAsset = assetLower;
            let expiryTime;

            const minutes = now.getUTCMinutes();
            const remainder = minutes % 15;
            const startOfCurrent = new Date(now.getTime() - remainder * 60000);
            startOfCurrent.setSeconds(0);
            startOfCurrent.setMilliseconds(0);

            // For 15m: 
            // offset 0 (Current) -> Expiry is start + 15m
            // offset 1 (Next) -> Expiry is start + 30m
            // EDITED: Remove +1 because offset 0 (LIVE) should map to start time of current bucket.
            expiryTime = new Date(startOfCurrent.getTime() + offset * 15 * 60000);

            const ts = Math.floor(expiryTime.getTime() / 1000);
            return `${slugAsset}-updown-15m-${ts}`;
        }

        // 1h, 4h, 1d use Natural Language format
        return generateNaturalLangSlug(offset, asset, timeframe);
    };

    const handleQuickLink = async (offset, assetOverride = null) => {
        const asset = assetOverride || activeAsset;
        setLoading(true);
        try {
            // NEW: Use centralized generator specifically for the current timeframe
            const targetSlug = generatePredictedSlug(offset, asset, selectedTimeframe);

            console.log(`[QuickLink] Predicted slug for offset ${offset} (${selectedTimeframe}):`, targetSlug);

            if (targetSlug) {
                console.log("Searching for slug:", targetSlug);
                try {
                    const response = await axios.get(`/api/poly/events?slug=${targetSlug}`);
                    if (response.data && Array.isArray(response.data) && response.data.length > 0) {
                        const event = response.data[0];
                        if (event.markets && event.markets.length > 0) {
                            // Found it! Select the first market in this event
                            const market = event.markets[0];
                            // Ensure market has necessary fields (map endDate if needed)
                            if (!market.end_date_iso && market.endDate) {
                                market.end_date_iso = market.endDate;
                            }

                            handleSelect(market);
                            // Also add to our list if not present
                            setMarkets(prev => {
                                if (!prev.find(m => m.id === market.id)) {
                                    return [market, ...prev];
                                }
                                return prev;
                            });
                            setLoading(false);
                            return;
                        }
                    }
                } catch (err) {
                    console.warn("Could not fetch specific event by slug:", err);
                }
            }

            // Fallback: Filter list for asset slug pattern
            setSearchTerm(`${asset.toLowerCase()}`);
            // Don't open dropdown if we are auto-switching assets, unless failed
            if (!assetOverride) setIsOpen(true);

        } catch (error) {
            console.error("Error finding quick link market:", error);
        } finally {
            setLoading(false);
        }
    };

    const getTimeLabel = (offset) => {
        if (offset === 0) return "LIVE";

        const now = new Date();
        const tf = selectedTimeframe;
        let targetStart;

        // Calculate START time for label
        if (tf === '15m') {
            const minutes = now.getMinutes();
            const remainder = minutes % 15;
            targetStart = new Date(now.getTime() - remainder * 60000 + offset * 15 * 60000);
        } else if (tf === '1h') {
            const startOfHour = new Date(now);
            startOfHour.setMinutes(0, 0, 0);
            targetStart = new Date(startOfHour.getTime() + offset * 60 * 60000);
        } else if (tf === '4h') {
            const hour = now.getHours();
            const remainder = hour % 4;
            const startOfBlock = new Date(now);
            startOfBlock.setHours(hour - remainder, 0, 0, 0);
            targetStart = new Date(startOfBlock.getTime() + offset * 4 * 60 * 60000);
        } else if (tf === '1d') {
            const today = new Date(now);
            today.setHours(0, 0, 0, 0);
            targetStart = new Date(today.getTime() + offset * 24 * 60 * 60000);
            // Daily format: "Dec 8"
            return targetStart.toLocaleDateString([], { month: 'short', day: 'numeric' });
        }

        return targetStart.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    };

    // Generate timeline offsets: 0 (LIVE), 1, 2, 3
    const timeSlots = [0, 1, 2, 3];

    return (
        <div className="relative mb-6" ref={dropdownRef}>
            <div className="flex items-center justify-between mb-2">
                <label className="text-slate-400 text-xs font-bold uppercase tracking-wider">
                    Select Market ({selectedTimeframe})
                </label>
                {/* Asset Toggles */}
                <div className="flex bg-slate-900 rounded-lg p-0.5 border border-slate-800">
                    {ASSETS.map(asset => (
                        <button
                            key={asset}
                            onClick={() => onAssetChange(asset)}
                            className={`px-2 py-0.5 rounded-md text-[10px] font-bold transition-all ${activeAsset === asset
                                ? 'bg-blue-500 text-white shadow-sm'
                                : 'text-slate-500 hover:text-slate-300'
                                }`}
                        >
                            {asset}
                        </button>
                    ))}
                </div>
            </div>

            {/* Timeline Buttons */}
            <div className="flex gap-2 mb-4 overflow-x-auto pb-2 custom-scrollbar">
                {timeSlots.map(offset => {
                    const label = getTimeLabel(offset);
                    const isLive = offset === 0;

                    return (
                        <button
                            key={offset}
                            onClick={() => handleQuickLink(offset)}
                            className={`flex-none px-4 py-2 rounded-full text-xs font-bold transition-all border ${isLive
                                ? 'bg-red-500/20 text-red-400 border-red-500/50 hover:bg-red-500/30' // LIVE style
                                : 'bg-slate-900 text-slate-400 border-slate-800 hover:bg-slate-800 hover:text-white'
                                }`}
                        >
                            {isLive && <span className="inline-block w-1.5 h-1.5 rounded-full bg-red-500 mr-1.5 animate-pulse"></span>}
                            {label}
                        </button>
                    );
                })}
            </div>

            {/* Selected Market Display / Trigger */}
            <div
                onClick={() => setIsOpen(!isOpen)}
                className="bg-slate-950/50 border border-slate-700 rounded-xl p-4 flex items-center justify-between cursor-pointer hover:border-blue-500/50 transition-colors group"
            >
                <div className="flex items-center gap-3 overflow-hidden">
                    <div className="w-8 h-8 rounded-full bg-blue-500/10 flex items-center justify-center text-blue-400 group-hover:scale-110 transition-transform">
                        {/* Dynamic Icon based on Asset */}
                        <span className="text-xs font-black">{activeAsset}</span>
                    </div>
                    <div className="flex flex-col truncate">
                        <span className="text-white font-bold truncate">
                            {selectedMarket ? selectedMarket.question : "Select a Market..."}
                        </span>
                        {selectedMarket && (
                            <span className="text-xs text-slate-500 truncate">
                                Expires: {new Date(selectedMarket.end_date_iso || selectedMarket.endDate).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                        )}
                    </div>
                </div>
                <ChevronDown size={16} className={`text-slate-500 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
            </div>

            {/* Dropdown List */}
            {isOpen && (
                <div className="absolute top-full left-0 right-0 mt-2 bg-slate-900 border border-slate-700 rounded-xl shadow-2xl z-50 max-h-80 flex flex-col overflow-hidden">
                    <div className="p-3 border-b border-slate-800">
                        <div className="relative">
                            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                            <input
                                type="text"
                                placeholder={`Search ${activeAsset} markets...`}
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                className="w-full bg-slate-950 border border-slate-800 rounded-lg py-2 pl-9 pr-3 text-sm text-white focus:outline-none focus:border-blue-500/50"
                                autoFocus
                            />
                        </div>
                    </div>

                    <div className="overflow-y-auto flex-1 p-1 custom-scrollbar">
                        {loading ? (
                            <div className="p-4 text-center text-slate-500 text-sm">Loading markets...</div>
                        ) : filteredMarkets.length === 0 ? (
                            <div className="p-4 text-center text-slate-500 text-sm">No relevant markets found.</div>
                        ) : (
                            filteredMarkets.map((market) => (
                                <div
                                    key={market.id}
                                    onClick={() => handleSelect(market)}
                                    className={`p-3 rounded-lg cursor-pointer transition-colors flex flex-col gap-1 ${selectedMarket?.id === market.id
                                        ? 'bg-blue-500/10 border border-blue-500/20'
                                        : 'hover:bg-slate-800/50 border border-transparent'
                                        }`}
                                >
                                    <span className="text-sm font-medium text-slate-200 line-clamp-2">
                                        {market.question}
                                    </span>
                                    <div className="flex items-center justify-between text-xs text-slate-500">
                                        <span>Vol: ${(market.volume_24h || 0).toLocaleString()}</span>
                                        <span>{new Date(market.end_date_iso || market.endDate).toLocaleDateString()}</span>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

export default MarketSelector;
