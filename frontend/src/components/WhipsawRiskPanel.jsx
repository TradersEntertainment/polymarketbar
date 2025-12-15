import React from 'react';
import { AlertOctagon, Info } from 'lucide-react';

const WhipsawRiskPanel = ({ data }) => {
    if (!data || !data.smart_trading) return null;
    const { whipsaw_risk } = data.smart_trading;

    const getRiskColor = (cat) => {
        if (cat === 'High') return 'text-red-500';
        if (cat === 'Normal') return 'text-yellow-500';
        return 'text-green-500';
    };

    const getRiskBg = (cat) => {
        if (cat === 'High') return 'bg-red-500/10 border-red-500/30';
        if (cat === 'Normal') return 'bg-yellow-500/10 border-yellow-500/30';
        return 'bg-green-500/10 border-green-500/30';
    };

    return (
        <div className="w-full mb-6 bg-slate-900/40 backdrop-blur-md border border-slate-700/50 rounded-2xl p-6 flex items-center justify-between">
            <div className="flex items-center gap-4">
                <div className={`p-3 rounded-xl border ${getRiskBg(whipsaw_risk.category)}`}>
                    <AlertOctagon className={getRiskColor(whipsaw_risk.category)} size={24} />
                </div>
                <div>
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                        Whipsaw Risk
                        <div className="group relative">
                            <Info size={14} className="text-slate-500 cursor-help" />
                            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 bg-slate-900 border border-slate-700 p-3 rounded-lg text-xs text-slate-300 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50 shadow-xl">
                                Whipsaw = Candle moves strongly in one direction, then instantly reverses. Calculated as % of candles with &gt;40% wick reversal ratio.
                            </div>
                        </div>
                    </h3>
                    <p className="text-slate-400 text-sm">High-frequency reversal probability based on last 1000 candles.</p>
                </div>
            </div>

            <div className="text-right">
                <div className={`text-2xl font-black ${getRiskColor(whipsaw_risk.category)}`}>
                    {whipsaw_risk.category} Risk
                </div>
                <div className="text-sm font-mono text-slate-500">
                    Prob: {whipsaw_risk.probability}%
                </div>
            </div>
        </div>
    );
};

export default WhipsawRiskPanel;
