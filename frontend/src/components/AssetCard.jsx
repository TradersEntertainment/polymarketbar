import React from 'react';
import { ArrowUp, ArrowDown, Activity, TrendingUp, Zap } from 'lucide-react';
import DistributionChart from './DistributionChart';
import LiveCandleWidget from './LiveCandleWidget';
import { motion } from 'framer-motion';

const MiniMetric = ({ label, value, icon: Icon, color }) => (
    <div className="flex flex-col items-center bg-slate-900/50 p-2 rounded-lg border border-slate-800/50">
        <div className="flex items-center gap-1 text-[10px] text-slate-500 uppercase tracking-wider mb-1">
            <Icon size={10} /> {label}
        </div>
        <div className={`text-sm font-bold ${color}`}>{value}</div>
    </div>
);

const AssetCard = ({ data }) => {
    if (!data) return <div className="animate-pulse bg-surface h-[500px] rounded-2xl border border-slate-800"></div>;

    const {
        symbol, timeframe, current_price, candle_open, candle_close_time,
        current_streak, next_candle_prob, distribution, probability_curve, stats
    } = data;

    const isGreen = current_streak.type === 'green';
    const streakColor = isGreen ? 'text-success' : 'text-danger';
    const borderColor = isGreen ? 'border-success/30' : 'border-danger/30';
    const shadowColor = isGreen ? 'shadow-success/10' : 'shadow-danger/10';

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.3 }}
            className={`relative overflow-hidden rounded-2xl border ${borderColor} bg-surface p-5 shadow-xl ${shadowColor} hover:scale-[1.01] transition-transform duration-300 min-h-[550px] flex flex-col justify-between`}
        >
            {/* Header */}
            <div className="flex justify-between items-start mb-4">
                <div>
                    <h3 className="text-3xl font-black text-white flex items-center gap-2 tracking-tight">
                        {symbol}
                        <span className="text-xs font-bold text-slate-400 bg-slate-800/80 px-2 py-1 rounded-md border border-slate-700">{timeframe}</span>
                    </h3>
                    <p className="text-slate-400 font-mono text-sm mt-1 opacity-80">${current_price.toLocaleString()}</p>
                </div>
                <div className={`flex flex-col items-end ${streakColor}`}>
                    <div className="flex items-center gap-1 text-4xl font-black drop-shadow-lg">
                        {isGreen ? <ArrowUp size={36} strokeWidth={3} /> : <ArrowDown size={36} strokeWidth={3} />}
                        {current_streak.length}
                    </div>
                    <span className={`text-[10px] font-bold tracking-widest uppercase opacity-90 bg-slate-900/50 px-2 py-0.5 rounded-full ${isGreen ? 'text-green-500' : 'text-red-500'}`}>
                        {isGreen ? 'Green Streak' : 'Red Streak'}
                    </span>
                </div>
            </div>

            {/* Mini Metrics */}
            <div className="grid grid-cols-3 gap-2 mb-5">
                <MiniMetric label="Vol (24h)" value={`${stats?.volatility}%`} icon={Activity} color="text-blue-400" />
                <MiniMetric label="Avg Streak" value={stats?.avg_streak} icon={TrendingUp} color="text-violet-400" />
                <MiniMetric label="Max Streak" value={stats?.max_streak} icon={Zap} color="text-yellow-400" />
            </div>

            {/* Live Widget */}
            <LiveCandleWidget
                symbol={symbol}
                currentPrice={current_price}
                openPrice={candle_open}
                closeTime={candle_close_time}
                timeframe={timeframe}
            />

            {/* Probabilities */}
            <div className="grid grid-cols-2 gap-3 my-5">
                <div className="bg-slate-900/40 p-3 rounded-xl border border-slate-700/30 relative overflow-hidden group">
                    <div className="absolute inset-0 bg-gradient-to-br from-success/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
                    <span className="text-[10px] text-slate-400 uppercase block mb-1 font-bold">Chance to Continue</span>
                    <div className="flex items-center gap-2">
                        {next_candle_prob.continue !== null ? (
                            <>
                                <span className={`text-2xl font-black ${streakColor}`}>{next_candle_prob.continue}%</span>
                                <span className="text-xs text-slate-500">↗</span>
                            </>
                        ) : (
                            <span className="text-lg font-bold text-yellow-500">New Record!</span>
                        )}
                    </div>
                </div>
                <div className="bg-slate-900/40 p-3 rounded-xl border border-slate-700/30 relative overflow-hidden group">
                    <div className="absolute inset-0 bg-gradient-to-br from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
                    <span className="text-[10px] text-slate-400 uppercase block mb-1 font-bold">Chance of Reversal</span>
                    <div className="flex items-center gap-2">
                        {next_candle_prob.reverse !== null ? (
                            <>
                                <span className="text-2xl font-black text-white">{next_candle_prob.reverse}%</span>
                                <span className="text-xs text-slate-500">↘</span>
                            </>
                        ) : (
                            <span className="text-lg font-bold text-slate-500">Unknown</span>
                        )}
                    </div>
                </div>
            </div>

            {/* Charts Section */}
            <div className="space-y-6">
                {/* Next Candle Bias Panel */}
                <div className="bg-slate-900/30 rounded-xl border border-slate-800/50 p-4">
                    <div className="flex items-center justify-between mb-4">
                        <h4 className="text-sm font-black text-white uppercase tracking-wider">Next Candle Bias</h4>
                        <span className="text-[10px] text-slate-500 font-mono">Based on last 1000 samples</span>
                    </div>

                    <div className="grid grid-cols-3 gap-3">
                        {/* Box 1: Current Streak */}
                        <div className="bg-slate-900/50 p-3 rounded-lg border border-slate-800 flex flex-col justify-between">
                            <span className="text-[10px] text-slate-500 uppercase font-bold">Current Streak</span>
                            <div>
                                <div className={`text-xl font-black ${streakColor}`}>
                                    L{current_streak.length} {isGreen ? 'GREEN' : 'RED'}
                                </div>
                                <div className="text-[10px] text-slate-500 mt-1">
                                    {distribution[current_streak.length]?.count || 0} occurrences
                                </div>
                            </div>
                        </div>

                        {/* Box 2: Prob Green */}
                        <div className="bg-slate-900/50 p-3 rounded-lg border border-slate-800 flex flex-col justify-between relative overflow-hidden">
                            <div className="absolute bottom-0 left-0 h-1 bg-green-500/50" style={{ width: `${isGreen ? (next_candle_prob.continue || 0) : (next_candle_prob.reverse || 0)}%` }}></div>
                            <span className="text-[10px] text-slate-500 uppercase font-bold">Prob. Next Green</span>
                            <div className="text-xl font-black text-green-400">
                                {next_candle_prob.continue !== null ? (
                                    `${isGreen ? next_candle_prob.continue : next_candle_prob.reverse}%`
                                ) : (
                                    <span className="text-sm text-slate-500">N/A</span>
                                )}
                            </div>
                        </div>

                        {/* Box 3: Prob Red */}
                        <div className="bg-slate-900/50 p-3 rounded-lg border border-slate-800 flex flex-col justify-between relative overflow-hidden">
                            <div className="absolute bottom-0 left-0 h-1 bg-red-500/50" style={{ width: `${!isGreen ? (next_candle_prob.continue || 0) : (next_candle_prob.reverse || 0)}%` }}></div>
                            <span className="text-[10px] text-slate-500 uppercase font-bold">Prob. Next Red</span>
                            <div className="text-xl font-black text-red-400">
                                {next_candle_prob.continue !== null ? (
                                    `${!isGreen ? next_candle_prob.continue : next_candle_prob.reverse}%`
                                ) : (
                                    <span className="text-sm text-slate-500">N/A</span>
                                )}
                            </div>
                        </div>
                    </div>
                </div>

                {/* Distribution Chart */}
                <div>
                    <div className="flex items-center justify-between mb-2">
                        <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Streak Distribution</h4>
                        <span className="text-[10px] text-slate-500">Frequency of streak lengths</span>
                    </div>
                    <DistributionChart data={distribution} currentStreakType={current_streak.type} />
                    <p className="text-[10px] text-slate-500 mt-1 italic">
                        Histogram showing how often streaks of different lengths have occurred in the last 1000 candles.
                    </p>
                </div>
            </div>

        </motion.div>
    );
};

export default AssetCard;
