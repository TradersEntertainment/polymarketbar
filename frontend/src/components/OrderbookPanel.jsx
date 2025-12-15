import React, { useState, useEffect } from 'react';
import axios from 'axios';

// Global Cache for Orderbooks
const globalOrderbookCache = new Map();

// Exported Prefetch Function
export const prefetchOrderbook = async (tokenId) => {
    if (!tokenId || globalOrderbookCache.has(tokenId)) return;

    try {
        const res = await axios.get(`/api/poly/clob/book?token_id=${tokenId}`);
        if (res.data) {
            const processed = {
                bids: (res.data.bids || []).sort((a, b) => parseFloat(b.price) - parseFloat(a.price)),
                asks: (res.data.asks || []).sort((a, b) => parseFloat(a.price) - parseFloat(b.price)),
                timestamp: Date.now()
            };
            globalOrderbookCache.set(tokenId, processed);
            // console.log(`[Prefetch] Cached orderbook for ${tokenId}`);
        }
    } catch (err) {
        // Silent fail for prefetch
    }
};

const OrderbookPanel = ({ yesTokenId, noTokenId }) => {
    const [yesBook, setYesBook] = useState({ bids: [], asks: [] });
    const [noBook, setNoBook] = useState({ bids: [], asks: [] });

    useEffect(() => {
        if (yesTokenId && noTokenId) {
            // 1. Check Cache Immediately
            if (globalOrderbookCache.has(yesTokenId)) setYesBook(globalOrderbookCache.get(yesTokenId));
            if (globalOrderbookCache.has(noTokenId)) setNoBook(globalOrderbookCache.get(noTokenId));

            // 2. Fetch Fresh Data
            fetchOrderbooks();
            const interval = setInterval(fetchOrderbooks, 2000); // Live update
            return () => clearInterval(interval);
        }
    }, [yesTokenId, noTokenId]);

    const fetchOrderbooks = async () => {
        try {
            const [yesRes, noRes] = await Promise.all([
                axios.get(`/api/poly/clob/book?token_id=${yesTokenId}`),
                axios.get(`/api/poly/clob/book?token_id=${noTokenId}`)
            ]);

            if (yesRes.data) {
                const processedYes = {
                    bids: (yesRes.data.bids || []).sort((a, b) => parseFloat(b.price) - parseFloat(a.price)),
                    asks: (yesRes.data.asks || []).sort((a, b) => parseFloat(a.price) - parseFloat(b.price)),
                    timestamp: Date.now()
                };
                setYesBook(processedYes);
                globalOrderbookCache.set(yesTokenId, processedYes); // Update Cache
            }
            if (noRes.data) {
                const processedNo = {
                    bids: (noRes.data.bids || []).sort((a, b) => parseFloat(b.price) - parseFloat(a.price)),
                    asks: (noRes.data.asks || []).sort((a, b) => parseFloat(a.price) - parseFloat(b.price)),
                    timestamp: Date.now()
                };
                setNoBook(processedNo);
                globalOrderbookCache.set(noTokenId, processedNo); // Update Cache
            }
        } catch (error) {
            console.error("Error fetching orderbooks:", error);
        }
    };

    if (!yesTokenId || !noTokenId) return null;

    const OrderColumn = ({ title, bids, asks, color }) => {
        // Calculations for depth bars
        // Flatten both sides to find max size for relative bar width
        const allSizes = [...bids, ...asks].map(o => parseFloat(o.size));
        const maxDepth = Math.max(...allSizes, 1);

        const bestBid = bids.length > 0 ? parseFloat(bids[0].price) : 0;
        const bestAsk = asks.length > 0 ? parseFloat(asks[asks.length - 1].price) : 0; // Last is best (sorted asc)
        // Note: Asks passed in are sorted ASC price (Lowest price first). 
        // For display we often want the "Best Ask" (Lowest) closest to the spread.

        // Re-sort for display (Ladder View)
        // Asks: Highest at TOP, Lowest (Best) at BOTTOM
        const displayAsks = [...asks].sort((a, b) => parseFloat(b.price) - parseFloat(a.price));
        const displayBids = [...bids].sort((a, b) => parseFloat(b.price) - parseFloat(a.price));

        const OrderRow = ({ item, type }) => {
            const size = parseFloat(item.size);
            const price = parseFloat(item.price);
            const width = (size / maxDepth) * 100;

            return (
                <div className="flex justify-between items-center text-2xl font-mono py-2 px-4 relative hover:bg-slate-800/50 transition-colors">
                    <div
                        className={`absolute top-0 bottom-0 ${type === 'ask' ? 'right-0 bg-red-500/10' : 'left-0 bg-green-500/10'}`}
                        style={{ width: `${width}%` }}
                    />
                    <span className={`relative z-10 w-28 text-right ${type === 'ask' ? 'text-red-400' : 'text-green-400'} font-bold`}>
                        {price.toFixed(2)}¢
                    </span>
                    <span className="relative z-10 w-36 text-right text-slate-400">
                        {size.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </span>
                </div>
            );
        };

        return (
            <div className="flex-1 flex flex-col border-r border-slate-800/50 last:border-0 hover:bg-slate-800/20 transition-colors">
                {/* Column Header */}
                <div className={`text-lg font-black text-center py-3 uppercase tracking-wide border-b border-slate-800/50 ${color}`}>
                    {title}
                </div>

                {/* Headers */}
                <div className="flex justify-between px-4 py-2 bg-slate-950/30 text-sm text-slate-500 uppercase font-bold tracking-wider">
                    <span className="w-28 text-right">Price</span>
                    <span className="w-36 text-right">Qty</span>
                </div>

                <div className="flex-1 flex flex-col min-h-[200px]">
                    {/* Asks (Red) */}
                    <div className="flex flex-col justify-end flex-1 overflow-hidden">
                        {displayAsks.slice(-6).map((ask, i) => (
                            <OrderRow key={i} item={ask} type="ask" />
                        ))}
                    </div>

                    {/* Spread Divider */}
                    <div className="py-0.5 bg-slate-800/50 text-center"></div>

                    {/* Bids (Green) */}
                    <div className="flex flex-col flex-1 overflow-hidden">
                        {displayBids.slice(0, 6).map((bid, i) => (
                            <OrderRow key={i} item={bid} type="bid" />
                        ))}
                    </div>
                </div>
            </div>
        );
    };

    return (
        <div className="mb-6 bg-slate-900/40 backdrop-blur-md border border-slate-700/50 rounded-xl overflow-hidden shadow-sm">
            <div className="flex">
                <OrderColumn
                    title="BUY (UP)"
                    bids={yesBook.bids}
                    asks={yesBook.asks}
                    color="text-green-400"
                />
                <OrderColumn
                    title="BUY (DOWN)"
                    bids={noBook.bids}
                    asks={noBook.asks}
                    color="text-red-400"
                />
            </div>
        </div>
    );
};

export default OrderbookPanel;
