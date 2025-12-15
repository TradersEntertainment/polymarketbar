import React from 'react';
import { Wallet } from 'lucide-react';
import { ConnectButton } from '@rainbow-me/rainbowkit';

const WalletConnectPanel = () => {
    return (
        <div className="w-full mb-6 bg-slate-900/40 backdrop-blur-md border border-slate-700/50 rounded-2xl p-6 relative overflow-hidden group">
            <div className="absolute inset-0 bg-gradient-to-r from-blue-500/5 to-violet-500/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>

            <div className="relative z-10 flex flex-col md:flex-row justify-between items-center gap-4">
                <div className="flex items-center gap-4">
                    <div className="p-3 bg-blue-500/10 rounded-xl border border-blue-500/20">
                        <Wallet className="text-blue-400" size={24} />
                    </div>
                    <div>
                        <h3 className="text-lg font-bold text-white flex items-center gap-2">
                            Polymarket Direct Execution
                            <span className="text-[10px] bg-blue-500/20 text-blue-400 px-2 py-0.5 rounded-full border border-blue-500/30 uppercase tracking-wider">
                                Polygon
                            </span>
                        </h3>
                        <p className="text-slate-400 text-sm">Trades are executed directly on Polymarket smart contracts.</p>
                    </div>
                </div>

                <div className="flex items-center gap-4">
                    <ConnectButton showBalance={false} chainStatus="icon" accountStatus="address" />
                </div>
            </div>
        </div>
    );
};

export default WalletConnectPanel;
