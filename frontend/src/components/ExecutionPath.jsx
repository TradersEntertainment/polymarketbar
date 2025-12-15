import React from 'react';
import { Wallet, ArrowRight, Server, FileCode, CheckCircle, Loader2 } from 'lucide-react';

const ExecutionPath = ({ status, onSimulate }) => {
    // Status: 'idle', 'simulating', 'ready', 'signing', 'confirming', 'success', 'error'

    const Step = ({ icon: Icon, label, active, completed }) => (
        <div className={`flex flex-col items-center gap-2 ${active ? 'opacity-100 scale-105' : completed ? 'opacity-80' : 'opacity-40'} transition-all duration-300`}>
            <div className={`w-10 h-10 rounded-full flex items-center justify-center border-2 ${completed ? 'bg-green-500/20 border-green-500 text-green-400' :
                    active ? 'bg-blue-500/20 border-blue-500 text-blue-400 animate-pulse' :
                        'bg-slate-800 border-slate-700 text-slate-500'
                }`}>
                {completed ? <CheckCircle size={20} /> : <Icon size={20} />}
            </div>
            <span className="text-[10px] uppercase font-bold tracking-wider text-center">{label}</span>
        </div>
    );

    const Connector = ({ active }) => (
        <div className="flex-1 h-0.5 bg-slate-800 relative mx-2">
            <div className={`absolute left-0 top-0 bottom-0 bg-blue-500 transition-all duration-1000 ${active ? 'w-full' : 'w-0'}`}></div>
        </div>
    );

    return (
        <div className="mt-6 bg-slate-900/40 border border-slate-700/50 rounded-xl p-5">
            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">Execution Path (Polygon PoS)</h4>

            <div className="flex items-center justify-between mb-6">
                <Step
                    icon={Wallet}
                    label="Wallet"
                    active={status === 'signing'}
                    completed={['confirming', 'success'].includes(status)}
                />
                <Connector active={['signing', 'confirming', 'success'].includes(status)} />
                <Step
                    icon={Server}
                    label="Router"
                    active={status === 'confirming'}
                    completed={status === 'success'}
                />
                <Connector active={status === 'success'} />
                <Step
                    icon={FileCode}
                    label="Contract"
                    active={false}
                    completed={status === 'success'}
                />
            </div>

            <div className="flex justify-between items-center bg-slate-950/50 rounded-lg p-3 border border-slate-800">
                <div className="flex flex-col">
                    <span className="text-[10px] text-slate-500 uppercase font-bold">Network Cost</span>
                    <span className="text-sm font-mono text-slate-300">~0.01 MATIC ($0.005)</span>
                </div>

                {status === 'idle' && (
                    <button
                        onClick={onSimulate}
                        className="text-xs bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 border border-blue-500/30 px-3 py-1.5 rounded-lg transition-colors font-bold"
                    >
                        Simulate Transaction
                    </button>
                )}

                {status === 'simulating' && (
                    <div className="flex items-center gap-2 text-xs text-blue-400 font-bold">
                        <Loader2 size={12} className="animate-spin" /> Simulating...
                    </div>
                )}

                {status === 'ready' && (
                    <div className="text-xs text-green-400 font-bold flex items-center gap-1">
                        <CheckCircle size={12} /> Simulation Valid
                    </div>
                )}
            </div>
        </div>
    );
};

export default ExecutionPath;
