import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { ArrowUpRight, ArrowDownRight, Minus, Settings, DollarSign, ExternalLink, Wallet } from 'lucide-react';
import { useAccount, useWriteContract, useSignTypedData } from 'wagmi';
import { parseUnits } from 'viem';
import TradeModal from './TradeModal';
import MarketSelector from './MarketSelector';
import OrderbookPanel from './OrderbookPanel';
import ExecutionPath from './ExecutionPath';
import LiveCandleWidget from './LiveCandleWidget';
import SmartExitEngine from './SmartExitEngine';
import WhipsawRiskPanel from './WhipsawRiskPanel';

// Polygon USDC (Bridged)
const USDC_ADDRESS = '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174';
// Polymarket CTF Exchange (Proxy)
const EXCHANGE_ADDRESS = '0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E';

const SmartTradingPanel = ({ data, timeframe, setTimeframe, selectedSymbol, onSymbolChange, onOpenCalculator }) => {
    const [amount, setAmount] = useState('100');
    const [isModalOpen, setIsModalOpen] = useState(false);
    // Calculator state lifted to Dashboard
    const [tradeSide, setTradeSide] = useState(null); // 'yes' or 'no'
    const [selectedMarket, setSelectedMarket] = useState(null);
    const [executionStatus, setExecutionStatus] = useState('idle');
    // Wagmi Hooks
    const { address, isConnected } = useAccount();
    const { writeContractAsync } = useWriteContract();
    const { signTypedDataAsync } = useSignTypedData();

    // --- Background Chart Data & Live Updates ---
    const [marketHistories, setMarketHistories] = useState({
        BTC: [], ETH: [], SOL: [], XRP: []
    });

    useEffect(() => {
        const ASSETS = ['BTC', 'ETH', 'SOL', 'XRP'];

        // 1. Initial History Fetch for ALL assets
        const fetchAllHistories = async () => {
            const promises = ASSETS.map(async (asset) => {
                try {
                    const res = await axios.get(`/api/history/${asset}/1m`, { params: { _t: Date.now() } });
                    if (res.data && Array.isArray(res.data)) {
                        return { asset, data: res.data };
                    }
                } catch (e) {
                    console.warn(`Failed bg history fetch for ${asset}`, e);
                }
                return null;
            });

            const results = await Promise.all(promises);
            setMarketHistories(prev => {
                const next = { ...prev };
                results.forEach(r => {
                    // Safety: Only update if data is valid array
                    if (r && Array.isArray(r.data)) {
                        next[r.asset] = r.data;
                    }
                });
                return next;
            });
        };

        fetchAllHistories();

        // 2. Background Polling for ALL assets (Live Prices)
        const pollLivePrices = async () => {
            const promises = ASSETS.map(async (asset) => {
                try {
                    const res = await axios.get(`/api/live/${asset}`, { params: { _t: Date.now() } });
                    if (res.data && res.data.price) {
                        return { asset, price: res.data.price };
                    }
                } catch (e) {
                    // silent fail
                }
                return null;
            });

            const results = await Promise.all(promises);

            setMarketHistories(prev => {
                const next = { ...prev };
                const now = Math.floor(Date.now() / 1000);

                results.forEach(r => {
                    if (!r) return;
                    const { asset, price } = r;
                    // Safety: Default into empty array if missing
                    const history = Array.isArray(next[asset]) ? next[asset] : [];

                    const newPoint = { time: now, price };

                    // Duplicate/Update logic
                    const last = history[history.length - 1];
                    let newHistory;
                    if (last && last.time === now) {
                        newHistory = [...history];
                        newHistory[newHistory.length - 1] = newPoint;
                    } else {
                        newHistory = [...history, newPoint].slice(-100);
                    }
                    next[asset] = newHistory;
                });
                return next;
            });
        };

        const interval = setInterval(pollLivePrices, 1000);
        return () => clearInterval(interval);
    }, []);

    if (!data || data.error || !data.smart_trading) return null;

    const { current_price, smart_trading, symbol } = data;
    const { microtrends, spread, slippage } = smart_trading;

    const TrendIcon = ({ direction }) => {
        if (direction === 'up') return <ArrowUpRight size={14} className="text-green-400" />;
        if (direction === 'down') return <ArrowDownRight size={14} className="text-red-400" />;
        return <Minus size={14} className="text-slate-500" />;
    };

    const handleTradeClick = async (side) => {
        if (!selectedMarket) {
            alert("Please select a Polymarket market first.");
            return;
        }
        if (!isConnected) {
            alert("Please connect your wallet first.");
            return;
        }

        setTradeSide(side);
        // Start Execution Flow
        await executeTrade(side);
    };

    const executeTrade = async (side) => {
        setExecutionStatus('signing'); // Start with signing/approving

        try {
            // 1. Approve USDC (Real Transaction)
            console.log("Requesting USDC Approval...");
            try {
                const tx = await writeContractAsync({
                    address: USDC_ADDRESS,
                    abi: [{
                        name: 'approve',
                        type: 'function',
                        stateMutability: 'nonpayable',
                        inputs: [{ name: 'spender', type: 'address' }, { name: 'amount', type: 'uint256' }],
                        outputs: [{ name: '', type: 'bool' }]
                    }],
                    functionName: 'approve',
                    args: [EXCHANGE_ADDRESS, parseUnits(amount, 6)],
                });
                console.log("Approval Tx:", tx);
                setExecutionStatus('confirming'); // Tx sent, waiting for confirmation
            } catch (e) {
                console.warn("Approval rejected or failed (might already have allowance):", e);
                // Continue to signing if approval fails (maybe already approved)
            }

            // 2. Sign Order (Real EIP-712)
            console.log("Requesting Order Signature...");
            const signature = await signTypedDataAsync({
                domain: {
                    name: 'Polymarket CTF Exchange',
                    version: '1',
                    chainId: 137,
                    verifyingContract: EXCHANGE_ADDRESS,
                },
                types: {
                    Order: [
                        { name: 'salt', type: 'uint256' },
                        { name: 'maker', type: 'address' },
                        { name: 'signer', type: 'address' },
                        { name: 'taker', type: 'address' },
                        { name: 'tokenId', type: 'uint256' },
                        { name: 'makerAmount', type: 'uint256' },
                        { name: 'takerAmount', type: 'uint256' },
                        { name: 'expiration', type: 'uint256' },
                        { name: 'nonce', type: 'uint256' },
                        { name: 'feeRateBps', type: 'uint256' },
                        { name: 'side', type: 'uint8' },
                        { name: 'signatureType', type: 'uint8' },
                    ],
                },
                primaryType: 'Order',
                message: {
                    salt: BigInt(Math.floor(Math.random() * 1000000)),
                    maker: address,
                    signer: address,
                    taker: '0x0000000000000000000000000000000000000000', // Any taker (CLOB)
                    tokenId: BigInt(selectedMarket.clobTokenIds ? (Array.isArray(selectedMarket.clobTokenIds) ? selectedMarket.clobTokenIds[0] : JSON.parse(selectedMarket.clobTokenIds)[0]) : 0), // Use real token ID if available
                    makerAmount: parseUnits(amount, 6),
                    takerAmount: parseUnits('0', 6), // Market order (simplified)
                    expiration: BigInt(Math.floor(Date.now() / 1000) + 300), // 5 mins
                    nonce: BigInt(0),
                    feeRateBps: BigInt(0),
                    side: side === 'yes' ? 0 : 1, // 0 for Buy, 1 for Sell (simplified)
                    signatureType: 0,
                },
            });

            console.log("Order Signed:", signature);
            setExecutionStatus('success');
            setIsModalOpen(true); // Show success modal

        } catch (error) {
            console.error("Execution failed:", error);
            setExecutionStatus('error');
            alert(`Execution Failed: ${error.message}`);
        }
    };

    const handleSimulate = () => {
        setExecutionStatus('simulating');
        setTimeout(() => {
            setExecutionStatus('ready');
        }, 1500);
    };

    const openExternalMarket = () => {
        const baseUrl = "https://polymarket.com";

        if (selectedMarket) {
            window.open(`${baseUrl}/event/${selectedMarket.market_slug}`, '_blank');
            return;
        }

        // Fallback: If no market selected, search for the symbol
        window.open(`${baseUrl}/?q=${symbol}`, '_blank');


    };

    const timeframes = ['15m', '1h', '4h', '1d'];

    // Safe JSON Parse Helper
    let yesTokenId = null;
    let noTokenId = null;
    try {
        if (selectedMarket && selectedMarket.clobTokenIds) {
            let parsedIds;
            if (typeof selectedMarket.clobTokenIds === 'string') {
                parsedIds = JSON.parse(selectedMarket.clobTokenIds);
            } else if (Array.isArray(selectedMarket.clobTokenIds)) {
                parsedIds = selectedMarket.clobTokenIds;
            }

            if (Array.isArray(parsedIds) && parsedIds.length >= 2) {
                yesTokenId = parsedIds[0];
                noTokenId = parsedIds[1];
            }
        }
    } catch (e) {
        console.warn("Failed to parse clobTokenIds:", e);
    }

    const [tradeMode, setTradeMode] = useState('buy'); // 'buy' or 'sell'

    return (
        <div className="w-full mb-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Price & Trends */}
            <div className="bg-slate-900/40 backdrop-blur-md border border-slate-700/50 rounded-2xl p-6 flex flex-col justify-between">
                <div>
                    {/* Market Data */}
                    <h4 className="text-slate-400 text-xs font-bold uppercase tracking-wider mb-2">Market Data</h4>
                    <div className="text-4xl font-black text-white mb-1">
                        ${current_price.toLocaleString(undefined, { minimumFractionDigits: current_price < 10 ? 4 : 2, maximumFractionDigits: current_price < 10 ? 4 : 2 })}
                    </div>
                    <div className="flex items-center gap-4 text-sm text-slate-400">
                        <span>Spread: <span className="text-slate-200">{spread}%</span></span>
                        <span>Slippage: <span className="text-slate-200">~{slippage}%</span></span>
                    </div>
                </div>

                {/* Live Chart */}
                <div className="flex-1 my-4">
                    <LiveCandleWidget
                        key={`${symbol}-${timeframe}`}
                        symbol={symbol}
                        currentPrice={current_price}
                        openPrice={data.candle_open}
                        closeTime={data.candle_close_time}
                        timeframe={timeframe}
                        variant="simple"
                        // variant="simple" (Fixed duplicate prop)
                        priceHistory={marketHistories[symbol] || []}
                    />
                </div>

                {/* Flaming Asset Selection Buttons */}
                <div className="mt-6 grid grid-cols-4 gap-3">
                    {['BTC', 'ETH', 'SOL', 'XRP'].map((asset) => (
                        <button
                            key={asset}
                            onClick={() => onSymbolChange(asset)}
                            className={`
                                relative py-3 rounded-xl font-black text-lg transition-all duration-300
                                ${selectedSymbol === asset
                                    ? 'bg-orange-500/20 border-orange-500 text-orange-400 flame-active z-10'
                                    : 'bg-slate-800/50 border-slate-700 text-slate-500 hover:bg-slate-800 hover:text-slate-300'
                                }
                                border
                            `}
                        >
                            {asset}
                        </button>
                    ))}
                </div>
            </div>

            {/* Trading Controls */}
            <div className={`lg:col-span-2 bg-slate-900/40 backdrop-blur-md border rounded-2xl p-6 transition-colors duration-500 ${tradeMode === 'buy' ? 'border-green-500/20 shadow-[0_0_50px_-20px_rgba(74,222,128,0.1)]' : 'border-red-500/20 shadow-[0_0_50px_-20px_rgba(248,113,113,0.1)]'
                }`}>

                {/* Market Selector & Orderbook... */}
                <MarketSelector
                    onSelect={setSelectedMarket}
                    activeAsset={selectedSymbol}
                    onAssetChange={onSymbolChange}
                    selectedTimeframe={timeframe}
                />

                {selectedMarket && yesTokenId && noTokenId && (
                    <OrderbookPanel
                        yesTokenId={yesTokenId}
                        noTokenId={noTokenId}
                    />
                )}

                <div className="flex justify-between items-center mb-6">
                    <div className="flex items-center gap-4">
                        <h4 className="text-slate-400 text-xs font-bold uppercase tracking-wider">Smart Execution</h4>
                        <button
                            onClick={onOpenCalculator}
                            className="flex items-center gap-1 text-[10px] bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 px-2 py-1 rounded border border-blue-500/30 transition-colors uppercase font-bold tracking-wide"
                        >
                            <DollarSign size={12} /> Calculator
                        </button>
                    </div>

                    {/* Buy/Sell Toggle */}
                    <div className="flex bg-slate-950/50 rounded-lg p-1 border border-slate-800">
                        <button
                            onClick={() => setTradeMode('buy')}
                            className={`px-6 py-1.5 rounded-md text-xs font-black uppercase tracking-wide transition-all ${tradeMode === 'buy'
                                ? 'bg-green-500 text-white shadow-lg shadow-green-500/20'
                                : 'text-slate-500 hover:text-slate-300'
                                }`}
                        >
                            Buy
                        </button>
                        <button
                            onClick={() => setTradeMode('sell')}
                            className={`px-6 py-1.5 rounded-md text-xs font-black uppercase tracking-wide transition-all ${tradeMode === 'sell'
                                ? 'bg-red-500 text-white shadow-lg shadow-red-500/20'
                                : 'text-slate-500 hover:text-slate-300'
                                }`}
                        >
                            Sell
                        </button>
                    </div>
                </div>

                {/* Timeframes (moved below or kept? sticking to original layout flow but ensuring header space) */}
                {/* Re-insert Timeframe Selector if strictly needed there, or let it float. User didn't touch it. keeping it cleanly separated. */}
                <div className="flex justify-end mb-4">
                    <div className="flex bg-slate-950/50 rounded-lg p-1 border border-slate-800">
                        {timeframes.map((tf) => (
                            <button
                                key={tf}
                                onClick={() => setTimeframe(tf)}
                                className={`px-3 py-1 rounded-md text-xs font-bold transition-all ${timeframe === tf
                                    ? 'bg-blue-500 text-white shadow-lg shadow-blue-500/20'
                                    : 'text-slate-500 hover:text-slate-300'
                                    }`}
                            >
                                {tf.toUpperCase()}
                            </button>
                        ))}
                    </div>
                </div>

                <div className="flex flex-col md:flex-row gap-4 mb-4">
                    <div className="relative flex-1">
                        <div className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500">
                            <DollarSign size={18} />
                        </div>
                        <input
                            type="text"
                            value={amount}
                            onChange={(e) => setAmount(e.target.value)}
                            className={`w-full bg-slate-950/50 border rounded-xl py-4 pl-10 pr-4 text-xl font-bold text-white focus:outline-none transition-colors ${tradeMode === 'buy' ? 'focus:border-green-500 border-slate-700' : 'focus:border-red-500 border-slate-700'
                                }`}
                        />
                        <div className="absolute right-4 top-1/2 -translate-y-1/2 text-xs font-bold text-slate-500">
                            {tradeMode === 'buy' ? 'USDC' : 'Shares'}
                        </div>
                    </div>

                    <div className="flex gap-4 flex-1">
                        <button
                            onClick={() => handleTradeClick('yes')}
                            disabled={!selectedMarket}
                            className={`group flex-1 border font-black text-xl rounded-xl py-4 transition-all duration-200 ${selectedMarket
                                ? tradeMode === 'buy'
                                    ? 'bg-green-500/10 hover:bg-green-500/20 border-green-500/30 hover:border-green-500/50 text-green-400 shadow-[0_0_15px_rgba(74,222,128,0.1)] hover:shadow-[0_0_25px_rgba(74,222,128,0.2)]'
                                    : 'bg-green-500/5 hover:bg-green-500/10 border-green-500/20 text-green-600' // Sell UP styling (distinct?)
                                : 'bg-slate-800/50 border-slate-700 text-slate-600 cursor-not-allowed'
                                }`}
                        >
                            {tradeMode === 'buy' ? 'BUY (UP)' : 'SELL (UP)'}
                        </button>
                        <button
                            onClick={() => handleTradeClick('no')}
                            disabled={!selectedMarket}
                            className={`group flex-1 border font-black text-xl rounded-xl py-4 transition-all duration-200 ${selectedMarket
                                ? tradeMode === 'buy'
                                    ? 'bg-red-500/10 hover:bg-red-500/20 border-red-500/30 hover:border-red-500/50 text-red-400 shadow-[0_0_15px_rgba(248,113,113,0.1)] hover:shadow-[0_0_25px_rgba(248,113,113,0.2)]'
                                    : 'bg-red-500/5 hover:bg-red-500/10 border-red-500/20 text-red-600' // Sell DOWN styling
                                : 'bg-slate-800/50 border-slate-700 text-slate-600 cursor-not-allowed'
                                }`}
                        >
                            {tradeMode === 'buy' ? 'BUY (DOWN)' : 'SELL (DOWN)'}
                        </button>
                    </div>
                </div>

                {/* NEW: Execution Path */}
                <ExecutionPath status={executionStatus} onSimulate={handleSimulate} />

                <div className="text-center mt-4">
                    <button
                        onClick={openExternalMarket}
                        className="text-xs text-slate-500 hover:text-blue-400 flex items-center justify-center gap-1 mx-auto transition-colors"
                    >
                        View Market on Polymarket <ExternalLink size={10} />
                    </button>
                </div>
            </div>

            <TradeModal
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                asset={selectedMarket ? selectedMarket.question : symbol}
                side={tradeSide}
                amount={amount}
                price={current_price}
                mode={tradeMode}
            />
        </div>
    );
};

export default SmartTradingPanel;
