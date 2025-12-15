import React, { useState, useEffect } from 'react';
import { Clock } from 'lucide-react';
import axios from 'axios';
import { LineChart, Line, ReferenceLine, ResponsiveContainer, YAxis, XAxis, Tooltip } from 'recharts';

const LiveCandleWidget = ({ symbol, currentPrice, openPrice, closeTime, timeframe, variant = 'simple', priceHistory: externalHistory }) => {
    const [timeLeft, setTimeLeft] = useState('');
    const [probGreen, setProbGreen] = useState(50);
    const [internalHistory, setInternalHistory] = useState([]);
    const [livePrice, setLivePrice] = useState(currentPrice);

    // Use external history if provided, otherwise internal
    const priceHistory = Array.isArray(externalHistory) && externalHistory.length > 0 ? externalHistory : internalHistory;

    useEffect(() => {
        setLivePrice(currentPrice);
    }, [currentPrice]);

    useEffect(() => {
        if (externalHistory && externalHistory.length > 0) return;

        const fetchLivePrice = async () => {
            try {
                const res = await axios.get(`/api/live/${symbol}`, { params: { _t: Date.now() } });
                if (res.data && res.data.price) setLivePrice(res.data.price);
            } catch (error) { console.error(error); }
        };

        const fetchHistory = async () => {
            try {
                const res = await axios.get(`/api/history/${symbol}/1m`, { params: { _t: Date.now() } });
                if (res.data && Array.isArray(res.data)) setInternalHistory(res.data);
            } catch (error) { console.error(error); }
        };

        fetchHistory();
        const interval = setInterval(fetchLivePrice, 1000);
        return () => clearInterval(interval);
    }, [symbol, timeframe, externalHistory]);

    useEffect(() => {
        if (!livePrice || (externalHistory && externalHistory.length > 0)) return;

        setInternalHistory(prev => {
            const now = Math.floor(Date.now() / 1000);
            const newPoint = { time: now, price: livePrice };
            const last = prev[prev.length - 1];
            if (last && last.time === now) {
                const updated = [...prev];
                updated[updated.length - 1] = newPoint;
                return updated;
            }
            return [...prev, newPoint].slice(-100);
        });
    }, [livePrice]);

    useEffect(() => {
        const timer = setInterval(() => {
            const now = Date.now();
            const diff = closeTime - now;

            if (diff <= 0) {
                setTimeLeft('00m 00s');
            } else {
                const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
                const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
                const seconds = Math.floor((diff % (1000 * 60)) / 1000);
                setTimeLeft(`${hours > 0 ? hours + 'h ' : ''}${minutes}m ${seconds}s`);
            }

            const delta = livePrice - openPrice;
            const percentChange = (delta / openPrice) * 100;
            let prob = 50 + (percentChange * 100);
            prob = Math.max(1, Math.min(99, prob));
            setProbGreen(prob);

        }, 1000);
        return () => clearInterval(timer);
    }, [closeTime, livePrice, openPrice, timeframe]);

    const isGreen = livePrice >= openPrice;

    // Domain calc
    const safeOpen = Number.isFinite(parseFloat(openPrice)) ? parseFloat(openPrice) : 0;
    const safeHistory = Array.isArray(priceHistory) ? priceHistory : [];
    const prices = safeHistory.length > 0 ? safeHistory.map(p => parseFloat(p.price)) : [safeOpen * 0.99, safeOpen * 1.01];
    const validPrices = prices.filter(p => Number.isFinite(p));
    if (safeOpen) validPrices.push(safeOpen);

    const minPrice = validPrices.length ? Math.min(...validPrices) * 0.9995 : 0;
    const maxPrice = validPrices.length ? Math.max(...validPrices) * 1.0005 : 100;


    // Target Line Calculation
    const targetVal = parseFloat(openPrice);
    const currentVal = parseFloat(livePrice);
    const diff = currentVal - targetVal;
    const pctDiff = targetVal ? ((diff / targetVal) * 100) : 0;
    const sign = pctDiff >= 0 ? '+' : '';
    const decimals = targetVal < 10 ? 4 : 2;
    const labelText = `TARGET: ${targetVal.toFixed(decimals)} (${sign}${pctDiff.toFixed(2)}%)`;
    // If Price > Target, show label BELOW line. Else ABOVE.
    const labelPos = currentVal >= targetVal ? 'insideBottomLeft' : 'insideTopLeft';

    return (
        <div className="mt-4 p-4 rounded-xl bg-slate-900/50 border border-slate-700/50 flex flex-col h-full relative group">
            {/* Header Stats */}
            <div className="flex justify-between items-center mb-4 z-20 relative">
                <div className="flex items-center gap-3">
                    <div className={`px-3 py-1.5 rounded-lg text-sm font-black uppercase tracking-wider ${isGreen ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'} animate-pulse`}>
                        LIVE: {isGreen ? 'GREEN' : 'RED'}
                    </div>
                    <div className={`text-xs flex items-center gap-1 font-mono bg-slate-800/50 px-2 py-1 rounded ${timeLeft === '00m 00s' ? 'text-red-400 animate-pulse' : 'text-slate-400'}`}>
                        <Clock size={12} />
                        {timeLeft}
                    </div>
                </div>
                <div className="text-right">
                    <div className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Prob. Green</div>
                    <div className={`text-lg font-black ${probGreen > 50 ? 'text-green-400' : 'text-red-400'}`}>
                        {probGreen.toFixed(1)}%
                    </div>
                </div>
            </div>

            {/* Chart Area */}
            <div className="flex-1 min-h-[300px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={priceHistory} margin={{ top: 20, right: 10, left: 10, bottom: 20 }}>
                        <XAxis
                            dataKey="time"
                            type="number"
                            domain={['dataMin', 'dataMax']}
                            tickFormatter={(time) => {
                                try {
                                    return new Date(time * 1000).toLocaleTimeString('en-US', {
                                        timeZone: 'America/New_York',
                                        hour: '2-digit',
                                        minute: '2-digit',
                                        hour12: false
                                    });
                                } catch (e) { return ''; }
                            }}
                            tick={{ fill: '#64748b', fontSize: 10, fontFamily: 'monospace' }}
                            axisLine={false}
                            tickLine={false}
                            minTickGap={40}
                            dy={10}
                        />
                        <YAxis
                            orientation="right"
                            domain={[minPrice, maxPrice]}
                            tickFormatter={(val) => {
                                const decimals = val < 10 ? 4 : 2;
                                return val.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
                            }}
                            tick={{ fill: '#64748b', fontSize: 10, fontFamily: 'monospace' }}
                            axisLine={false}
                            tickLine={false}
                            width={50}
                        />
                        {/* Target Line - Solid Red */}
                        <ReferenceLine
                            y={openPrice}
                            stroke="#ef4444"
                            strokeWidth={2}
                            strokeOpacity={1}
                            label={{
                                value: labelText,
                                position: labelPos,
                                fill: '#ef4444',
                                fontSize: 12,
                                fontWeight: 'bold'
                            }}
                        />
                        <Tooltip
                            contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', color: '#f8fafc' }}
                            itemStyle={{ color: '#f8fafc' }}
                            labelFormatter={(label) => new Date(label * 1000).toLocaleTimeString()}
                            formatter={(value) => [value, 'Price']}
                        />
                        <Line
                            type="monotone"
                            dataKey="price"
                            stroke={isGreen ? '#4ade80' : '#f87171'}
                            strokeWidth={2}
                            dot={false}
                            isAnimationActive={false}
                        />
                    </LineChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};

export default LiveCandleWidget;
