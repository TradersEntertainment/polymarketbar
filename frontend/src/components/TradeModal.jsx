import React, { useState, useEffect } from 'react';
import { X, Loader2, CheckCircle, ShieldCheck, ArrowRight } from 'lucide-react';

const TradeModal = ({ isOpen, onClose, asset, side, amount, price, mode = 'buy' }) => {
    const [step, setStep] = useState('review'); // review, approving, confirming, success

    useEffect(() => {
        if (isOpen) setStep('review');
    }, [isOpen]);

    if (!isOpen) return null;

    const handleExecute = async () => {
        setStep('approving');
        // Simulate network delays
        setTimeout(() => {
            setStep('confirming');
            setTimeout(() => {
                setStep('success');
            }, 2000);
        }, 1500);
    };

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
            <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={onClose}></div>

            <div className="relative bg-slate-900 border border-slate-700 w-full max-w-md rounded-2xl overflow-hidden shadow-2xl animate-in fade-in zoom-in-95 duration-200">
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-slate-800 bg-slate-950/50">
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                        <ShieldCheck className="text-blue-500" size={20} />
                        Confirm {mode === 'buy' ? 'Buy' : 'Sell'}
                    </h3>
                    <button onClick={onClose} className="text-slate-500 hover:text-white transition-colors">
                        <X size={20} />
                    </button>
                </div>

                {/* Content */}
                <div className="p-6">
                    {step === 'review' && (
                        <div className="space-y-6">
                            <div className="flex items-center justify-between p-4 bg-slate-800/50 rounded-xl border border-slate-700">
                                {mode === 'buy' ? (
                                    <>
                                        <div>
                                            <div className="text-xs text-slate-400 font-bold uppercase mb-1">You Pay</div>
                                            <div className="text-2xl font-black text-white">{amount} USDC</div>
                                        </div>
                                        <ArrowRight className="text-slate-600" />
                                        <div className="text-right">
                                            <div className="text-xs text-slate-400 font-bold uppercase mb-1">You Receive</div>
                                            <div className={`text-2xl font-black ${side === 'yes' ? 'text-green-400' : 'text-red-400'}`}>
                                                {side === 'yes' ? 'UP (YES)' : 'DOWN (NO)'}
                                            </div>
                                            <div className="text-xs text-slate-500 font-mono">@ ${price < 10 ? price.toFixed(4) : price.toLocaleString()}</div>
                                        </div>
                                    </>
                                ) : (
                                    <>
                                        <div>
                                            <div className="text-xs text-slate-400 font-bold uppercase mb-1">You Sell</div>
                                            <div className={`text-2xl font-black ${side === 'yes' ? 'text-green-400' : 'text-red-400'}`}>
                                                {amount} {side === 'yes' ? 'UP' : 'DOWN'}
                                            </div>
                                        </div>
                                        <ArrowRight className="text-slate-600" />
                                        <div className="text-right">
                                            <div className="text-xs text-slate-400 font-bold uppercase mb-1">You Receive</div>
                                            <div className="text-2xl font-black text-white">
                                                ~${(parseFloat(amount || 0) * price).toFixed(2)} USDC
                                            </div>
                                            <div className="text-xs text-slate-500 font-mono">@ ${price < 10 ? price.toFixed(4) : price.toLocaleString()}</div>
                                        </div>
                                    </>
                                )}
                            </div>

                            <div className="space-y-2 text-sm">
                                <div className="flex justify-between text-slate-400">
                                    <span>Network Fee</span>
                                    <span className="text-slate-200">~$0.01</span>
                                </div>
                                <div className="flex justify-between text-slate-400">
                                    <span>Price Impact</span>
                                    <span className="text-green-400">0.05%</span>
                                </div>
                            </div>

                            <button
                                onClick={handleExecute}
                                className="w-full py-4 bg-blue-600 hover:bg-blue-500 text-white font-bold rounded-xl transition-all shadow-lg shadow-blue-600/20"
                            >
                                Confirm Transaction
                            </button>
                        </div>
                    )}

                    {(step === 'approving' || step === 'confirming') && (
                        <div className="flex flex-col items-center justify-center py-8 space-y-4">
                            <div className="relative">
                                <div className="w-16 h-16 border-4 border-blue-500/30 rounded-full"></div>
                                <div className="absolute inset-0 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                            </div>
                            <div className="text-center">
                                <h4 className="text-xl font-bold text-white mb-1">
                                    {step === 'approving' ? 'Approving USDC...' : 'Confirming Trade...'}
                                </h4>
                                <p className="text-slate-400 text-sm">Please sign the request in your wallet</p>
                            </div>
                        </div>
                    )}

                    {step === 'success' && (
                        <div className="flex flex-col items-center justify-center py-8 space-y-4 animate-in fade-in slide-in-from-bottom-4">
                            <div className="w-16 h-16 bg-green-500/20 text-green-500 rounded-full flex items-center justify-center border border-green-500/50">
                                <CheckCircle size={32} />
                            </div>
                            <div className="text-center">
                                <h4 className="text-xl font-bold text-white mb-1">Trade Executed!</h4>
                                <p className="text-slate-400 text-sm">Your position has been opened successfully.</p>
                            </div>
                            <button
                                onClick={onClose}
                                className="mt-4 px-8 py-2 bg-slate-800 hover:bg-slate-700 text-white font-bold rounded-lg transition-colors"
                            >
                                Close
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default TradeModal;
