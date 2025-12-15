import React, { useState } from 'react';
import { Zap, AlertTriangle, CheckCircle2 } from 'lucide-react';

const SmartExitEngine = ({ data }) => {
    const [enabled, setEnabled] = useState(true);

    if (!data || !data.smart_trading) return null;
    const { smart_exit } = data.smart_trading;

    return (
        <div className="w-full mb-6 bg-slate-900/40 backdrop-blur-md border border-slate-700/50 rounded-2xl p-6 relative overflow-hidden">
            <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-yellow-400 to-orange-500"></div>

            <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
                <div>
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                        <Zap className="text-yellow-400" size={20} fill="currentColor" />
                        Smart Exit Engine
                        <span className="text-[10px] bg-yellow-500/20 text-yellow-400 px-2 py-0.5 rounded-full border border-yellow-500/30 uppercase tracking-wider">
                            Instant Close System
                        </span>
                    </h3>
                    <p className="text-slate-400 text-sm mt-1 max-w-xl">
                        Automatically sets an optimized limit order to guarantee instant fill, bypassing Polymarket's market-sell failures.
                    </p>
                </div>

                <div
                    onClick={() => setEnabled(!enabled)}
                    className={`cursor-pointer flex items-center gap-3 px-4 py-2 rounded-xl border transition-all duration-300 ${enabled ? 'bg-yellow-500/10 border-yellow-500/50' : 'bg-slate-800/50 border-slate-700'}`}
                >
                    <div className={`w-10 h-5 rounded-full relative transition-colors duration-300 ${enabled ? 'bg-yellow-500' : 'bg-slate-600'}`}>
                        <div className={`absolute top-1 w-3 h-3 bg-white rounded-full transition-transform duration-300 ${enabled ? 'left-6' : 'left-1'}`}></div>
                    </div>
                    <span className={`text-sm font-bold ${enabled ? 'text-yellow-400' : 'text-slate-500'}`}>
                        {enabled ? 'ENGINE ACTIVE' : 'ENGINE OFF'}
                    </span>
                </div>
            </div>

            <div className={`grid grid-cols-2 md:grid-cols-4 gap-4 transition-opacity duration-300 ${enabled ? 'opacity-100' : 'opacity-40 grayscale'}`}>
                <div className="bg-slate-950/50 p-4 rounded-xl border border-slate-800">
                    <div className="text-[10px] text-slate-500 uppercase font-bold mb-1">Optimal Exit Limit</div>
                    <div className="text-xl font-mono font-bold text-white">${smart_exit.optimal_price}</div>
                </div>

                <div className="bg-slate-950/50 p-4 rounded-xl border border-slate-800">
                    <div className="text-[10px] text-slate-500 uppercase font-bold mb-1">Offset %</div>
                    <div className="text-xl font-mono font-bold text-blue-400">+{smart_exit.offset_pct}%</div>
                </div>

                <div className="bg-slate-950/50 p-4 rounded-xl border border-slate-800">
                    <div className="text-[10px] text-slate-500 uppercase font-bold mb-1">Liquidity Tightness</div>
                    <div className={`text-xl font-bold ${smart_exit.liquidity_tightness === 'High' ? 'text-red-400' : 'text-green-400'}`}>
                        {smart_exit.liquidity_tightness}
                    </div>
                </div>

                <div className="bg-slate-950/50 p-4 rounded-xl border border-slate-800">
                    <div className="text-[10px] text-slate-500 uppercase font-bold mb-1">Est. Fill Time</div>
                    <div className="text-xl font-mono font-bold text-white flex items-center gap-2">
                        {smart_exit.est_fill_time_ms}ms
                        <CheckCircle2 size={16} className="text-green-500" />
                    </div>
                </div>
            </div>
        </div>
    );
};

export default SmartExitEngine;
