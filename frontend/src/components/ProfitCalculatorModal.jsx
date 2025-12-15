import React, { useState, useEffect, useRef } from 'react';
import { X, Calculator, TrendingUp, ArrowRight } from 'lucide-react';

const ProfitCalculatorModal = ({ isOpen, onClose, currentPrice = 0 }) => {
    const [balance, setBalance] = useState(1000);
    const [buyPrice, setBuyPrice] = useState(0.50);
    const [sellPrice, setSellPrice] = useState(0.75); // Default setup
    
    const [streakCount, setStreakCount] = useState(10); // Editable streak
    
    // Results
    const [roi, setRoi] = useState(0);
    const [singleProfit, setSingleProfit] = useState(0);
    const [compoundedTotal, setCompoundedTotal] = useState(0);

    // Draggable Logic
    const [position, setPosition] = useState({ x: 0, y: 0 });
    const [isDragging, setIsDragging] = useState(false);
    const dragOffset = useRef({ x: 0, y: 0 });
    const hasPositioned = useRef(false);

    // Center on first open
    useEffect(() => {
        if (isOpen && !hasPositioned.current) {
            setPosition({ 
                x: window.innerWidth / 2 - 250, // Center based on approx width 500px
                y: 100 
            });
            hasPositioned.current = true;
        }
    }, [isOpen]);

    useEffect(() => {
        const handleMouseMove = (e) => {
            if (!isDragging) return;
            setPosition({
                x: e.clientX - dragOffset.current.x,
                y: e.clientY - dragOffset.current.y
            });
        };
        
        const handleMouseUp = () => {
            setIsDragging(false);
        };

        if (isDragging) {
            window.addEventListener('mousemove', handleMouseMove);
            window.addEventListener('mouseup', handleMouseUp);
        }
        return () => {
            window.removeEventListener('mousemove', handleMouseMove);
            window.removeEventListener('mouseup', handleMouseUp);
        };
    }, [isDragging]);

    const handleMouseDown = (e) => {
        setIsDragging(true);
        dragOffset.current = {
            x: e.clientX - position.x,
            y: e.clientY - position.y
        };
    };

    // Handlers
    const calculateForward = (newBalance, newBuy, newSell, newStreak) => {
        if (!newBuy || newBuy === 0) return;
        
        const rawRoi = ((newSell - newBuy) / newBuy);
        const roiPercent = rawRoi * 100;
        const profit = newBalance * rawRoi;
        
        const multiplier = newSell / newBuy;
        const totalAfterStreak = newBalance * Math.pow(multiplier, newStreak);

        setRoi(roiPercent);
        setSingleProfit(profit);
        setCompoundedTotal(totalAfterStreak);
    };

    const calculateReverse = (targetTotal, currentBalance, currentBuy, currentStreak) => {
        if (currentBalance === 0 || currentStreak === 0) return;
        
        const ratio = targetTotal / currentBalance;
        if (ratio <= 0) return; 

        const multiplier = Math.pow(ratio, 1 / currentStreak);
        const newSell = currentBuy * multiplier;
        
        setSellPrice(newSell);
        
        const rawRoi = ((newSell - currentBuy) / currentBuy);
        setRoi(rawRoi * 100);
        setSingleProfit(currentBalance * rawRoi);
    };

    // Initial Calculation on Mount
    useEffect(() => {
        calculateForward(balance, buyPrice, sellPrice, streakCount);
    }, []); 

    const onInputChange = (field, value) => {
        const val = parseFloat(value) || 0;
        if (field === 'balance') {
            setBalance(val);
            calculateForward(val, buyPrice, sellPrice, streakCount);
        } else if (field === 'buy') {
            setBuyPrice(val);
            calculateForward(balance, val, sellPrice, streakCount);
        } else if (field === 'sell') {
            setSellPrice(val);
            calculateForward(balance, buyPrice, val, streakCount);
        } else if (field === 'streak') {
            const s = Math.max(1, parseInt(value) || 1);
            setStreakCount(s);
            calculateForward(balance, buyPrice, sellPrice, s);
        }
    };

    const onTargetChange = (e) => {
        const val = parseFloat(e.target.value) || 0;
        setCompoundedTotal(val);
        calculateReverse(val, balance, buyPrice, streakCount);
    };

    if (!isOpen) return null;

    return (
        <div 
            style={{ left: position.x, top: position.y }}
            className="fixed z-[100] animate-in fade-in zoom-in duration-200"
        >
            <div className="bg-slate-900/95 backdrop-blur-xl border border-blue-500/30 shadow-[0_0_50px_rgba(0,0,0,0.5)] rounded-2xl w-full max-w-lg flex flex-col max-h-[85vh] overflow-y-auto">
                {/* Header */}
                <div 
                    onMouseDown={handleMouseDown}
                    className="flex items-center justify-between p-4 border-b border-slate-700 bg-slate-800/80 cursor-move select-none"
                    title="Drag to move"
                >
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-gradient-to-br from-blue-500 to-violet-600 rounded-lg text-white shadow-lg shadow-blue-500/20">
                            <Calculator size={20} />
                        </div>
                        <div>
                            <h2 className="text-lg font-black text-white uppercase tracking-tight leading-none">Profit Simulator</h2>
                            <p className="text-[10px] text-blue-300 font-mono tracking-wider font-bold">DRAG ME • PLAN • EXECUTE</p>
                        </div>
                    </div>
                    <button 
                        onClick={onClose} 
                        className="p-1 rounded-lg hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
                    >
                        <X size={20} />
                    </button>
                </div>

                {/* Content */}
                <div className="p-6 space-y-6">
                    
                    {/* Inputs */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="space-y-2">
                            <label className="text-xs font-bold text-slate-500 uppercase">Initial Balance ($)</label>
                            <input 
                                type="number" 
                                value={balance} 
                                onChange={(e) => onInputChange('balance', e.target.value)}
                                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white font-mono focus:outline-none focus:border-blue-500 transition-colors"
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-xs font-bold text-slate-500 uppercase">Buy Price ($)</label>
                            <input 
                                type="number" 
                                step="0.01"
                                value={buyPrice} 
                                onChange={(e) => onInputChange('buy', e.target.value)}
                                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white font-mono focus:outline-none focus:border-blue-500 transition-colors"
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-xs font-bold text-slate-500 uppercase">Sell Price ($)</label>
                            <input 
                                type="number" 
                                step="0.01"
                                value={sellPrice} 
                                onChange={(e) => onInputChange('sell', e.target.value)}
                                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-blue-400 font-bold font-mono focus:outline-none focus:border-blue-500 transition-colors"
                            />
                        </div>
                    </div>

                    {/* Single Trade Result */}
                    <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                        <div className="flex justify-between items-center mb-2">
                            <span className="text-sm text-slate-400 font-medium">Single Trade ROI</span>
                            <span className={`text-lg font-black ${roi >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                {roi >= 0 ? '+' : ''}{roi.toFixed(2)}%
                            </span>
                        </div>
                        <div className="flex justify-between items-center">
                            <span className="text-sm text-slate-400 font-medium">Profit</span>
                            <span className={`text-lg font-mono font-bold ${singleProfit >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                {singleProfit >= 0 ? '+' : ''}${singleProfit.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                            </span>
                        </div>
                    </div>

                    {/* Exponential Growth Showcase */}
                    <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-indigo-900 to-purple-900 border border-indigo-500/30 p-6 text-center shadow-lg group">
                        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-purple-400 to-transparent opacity-50"></div>
                        
                        <div className="flex items-center justify-center gap-2 mb-4">
                            <TrendingUp size={16} className="text-indigo-300"/>
                            <span className="text-sm font-bold text-indigo-300 uppercase tracking-widest">
                                IF REPEATED 
                            </span>
                            <input 
                                type="number" 
                                value={streakCount}
                                onChange={(e) => onInputChange('streak', e.target.value)}
                                className="w-16 bg-indigo-950/50 border border-indigo-500/50 rounded px-2 py-0.5 text-center text-white font-bold text-sm focus:outline-none focus:border-indigo-400 transition-colors"
                            />
                            <span className="text-sm font-bold text-indigo-300 uppercase tracking-widest">
                                TIMES
                            </span>
                        </div>
                        
                        <div className="flex items-center justify-center gap-4 mb-4 opacity-50">
                             <div className="text-xs font-mono text-white">${balance.toLocaleString()}</div>
                             <ArrowRight size={12} className="text-indigo-400" />
                             <div className="text-xs font-mono text-white">...</div>
                             <ArrowRight size={12} className="text-indigo-400" />
                        </div>

                        <div className="flex flex-col items-center justify-center gap-1 mb-2">
                             <div className="text-xs font-bold text-indigo-300/50 tracking-wider">TARGET BALANCE (EDITABLE)</div>
                             <div className="flex items-center justify-center gap-1 relative z-10">
                                <span className="text-3xl font-bold text-indigo-300">$</span>
                                <input 
                                    type="number"
                                    value={Math.floor(compoundedTotal)}
                                    onChange={onTargetChange}
                                    className="w-full max-w-[300px] text-5xl font-black text-center bg-transparent border-b-2 border-indigo-500/30 focus:border-indigo-400 focus:outline-none text-white placeholder-indigo-500/30 transition-all hover:border-indigo-500/50 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                                />
                             </div>
                        </div>
                        
                        <div className="text-xs text-indigo-300/80 font-medium max-w-xs mx-auto">
                            By consistently hitting a <strong>{roi.toFixed(1)}%</strong> gain {streakCount} times, your capital grows exponentially.
                        </div>
                    </div>

                    <button 
                        onClick={onClose}
                        className="w-full py-4 bg-slate-800 hover:bg-slate-700 text-white font-bold rounded-xl transition-all border border-slate-700 hover:border-slate-600"
                    >
                        Close Calculator
                    </button>
                    
                </div>
            </div>
        </div>
    );
};

export default ProfitCalculatorModal;
