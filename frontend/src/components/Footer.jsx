import React from 'react';
import { ShieldCheck } from 'lucide-react';

const Footer = () => {
    return (
        <footer className="w-full mt-12 py-8 border-t border-slate-800/50 text-center">
            <div className="flex items-center justify-center gap-2 text-slate-500 text-sm mb-2">
                <ShieldCheck size={16} />
                <span className="font-bold">Secure On-Chain Execution</span>
            </div>
            <p className="text-slate-600 text-xs max-w-2xl mx-auto">
                This is an enhanced Polymarket trading interface. All transactions are executed directly on-chain using your connected wallet via the Polygon network.
                We do not hold custody of your funds.
            </p>
        </footer>
    );
};

export default Footer;
