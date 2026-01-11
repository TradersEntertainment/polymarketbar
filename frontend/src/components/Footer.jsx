import React, { useState } from 'react';
import { ShieldCheck, Trash2, Lock, Check, X } from 'lucide-react';
import axios from 'axios';

const Footer = () => {
    const [showAdminPanel, setShowAdminPanel] = useState(false);
    const [password, setPassword] = useState('');
    const [status, setStatus] = useState(null); // 'success', 'error', 'loading'
    const [message, setMessage] = useState('');

    const handleClearCache = async () => {
        if (password !== 'admin') {
            setStatus('error');
            setMessage('Yanlış şifre!');
            return;
        }

        setStatus('loading');
        try {
            const res = await axios.post('/api/clear-cache');
            if (res.data.status === 'ok') {
                setStatus('success');
                setMessage(`Cache temizlendi: ${res.data.cleared.join(', ')}`);
                setPassword('');
                setTimeout(() => {
                    setShowAdminPanel(false);
                    setStatus(null);
                }, 3000);
            }
        } catch (err) {
            setStatus('error');
            setMessage('Hata: ' + (err.response?.data?.detail || err.message));
        }
    };

    return (
        <footer className="w-full mt-12 py-8 border-t border-slate-800/50 text-center">
            <div className="flex items-center justify-center gap-2 text-slate-500 text-sm mb-2">
                <ShieldCheck size={16} />
                <span className="font-bold">Secure On-Chain Execution</span>
            </div>
            <p className="text-slate-600 text-xs max-w-2xl mx-auto mb-4">
                This is an enhanced Polymarket trading interface. All transactions are executed directly on-chain using your connected wallet via the Polygon network.
                We do not hold custody of your funds.
            </p>

            {/* Admin Clear Cache Button */}
            <div className="flex justify-center">
                {!showAdminPanel ? (
                    <button
                        onClick={() => setShowAdminPanel(true)}
                        className="flex items-center gap-1 text-[10px] text-slate-600 hover:text-slate-400 transition-colors opacity-50 hover:opacity-100"
                    >
                        <Lock size={10} />
                        Admin
                    </button>
                ) : (
                    <div className="flex items-center gap-2 bg-slate-900/80 px-4 py-2 rounded-lg border border-slate-700 animate-in fade-in">
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="Şifre"
                            className="bg-slate-800 text-white text-xs px-2 py-1 rounded border border-slate-600 w-20 focus:outline-none focus:border-blue-500"
                            onKeyDown={(e) => e.key === 'Enter' && handleClearCache()}
                        />
                        <button
                            onClick={handleClearCache}
                            disabled={status === 'loading'}
                            className={`flex items-center gap-1 text-xs px-2 py-1 rounded transition-colors ${status === 'loading'
                                    ? 'bg-slate-700 text-slate-400'
                                    : 'bg-red-500/20 hover:bg-red-500/30 text-red-400 border border-red-500/30'
                                }`}
                        >
                            <Trash2 size={12} />
                            {status === 'loading' ? '...' : 'Clear Cache'}
                        </button>
                        <button
                            onClick={() => { setShowAdminPanel(false); setPassword(''); setStatus(null); }}
                            className="text-slate-500 hover:text-slate-300"
                        >
                            <X size={14} />
                        </button>

                        {status && (
                            <span className={`text-xs ${status === 'success' ? 'text-green-400' : 'text-red-400'}`}>
                                {status === 'success' && <Check size={12} className="inline mr-1" />}
                                {message}
                            </span>
                        )}
                    </div>
                )}
            </div>
        </footer>
    );
};

export default Footer;

