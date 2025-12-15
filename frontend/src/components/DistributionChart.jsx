import React from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, CartesianGrid } from 'recharts';

const DistributionChart = ({ data, currentStreakType }) => {
    const chartData = Object.entries(data).map(([length, info]) => ({
        length: parseInt(length),
        count: info.count,
        lastHappened: info.last_happened
    }));

    const color = currentStreakType === 'green' ? '#22c55e' : '#ef4444';

    return (
        <div className="h-48 w-full mt-6">
            <h4 className="text-xs text-slate-400 mb-2 uppercase tracking-wider flex items-center justify-between">
                <span>Streak Distribution</span>
                <span className="text-[10px] bg-slate-800 px-1.5 py-0.5 rounded text-slate-500">Last 1000 candles</span>
            </h4>
            <div className="h-full bg-slate-900/30 rounded-lg p-2 border border-slate-800">
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#334155" opacity={0.3} />
                        <XAxis
                            dataKey="length"
                            stroke="#64748b"
                            fontSize={10}
                            tickLine={false}
                            axisLine={false}
                            tickFormatter={(val) => `L${val}`}
                        />
                        <YAxis
                            stroke="#64748b"
                            fontSize={10}
                            tickLine={false}
                            axisLine={false}
                        />
                        <Tooltip
                            cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                            content={({ active, payload, label }) => {
                                if (active && payload && payload.length) {
                                    return (
                                        <div className="bg-slate-900 border border-slate-700 p-2 rounded-lg text-xs shadow-xl">
                                            <p className="text-white font-bold mb-1">Length: {label}</p>
                                            <p className="text-slate-300">Count: <span className="text-white font-mono">{payload[0].value}</span></p>
                                            <p className="text-slate-400 mt-1 border-t border-slate-800 pt-1">
                                                Last: <span className="text-blue-400">{payload[0].payload.lastHappened}</span>
                                            </p>
                                        </div>
                                    );
                                }
                                return null;
                            }}
                        />
                        <Bar dataKey="count" radius={[4, 4, 0, 0]} barSize={20}>
                            {chartData.map((entry, index) => (
                                <Cell
                                    key={`cell-${index}`}
                                    fill={color}
                                    fillOpacity={0.6}
                                    className="hover:opacity-100 transition-opacity duration-200"
                                />
                            ))}
                        </Bar>
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};

export default DistributionChart;
