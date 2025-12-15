import React from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

const ProbabilityCurve = ({ data }) => {
    if (!data || data.length === 0) return null;

    return (
        <div className="mt-6">
            <h4 className="text-xs text-slate-400 mb-2 uppercase tracking-wider flex items-center justify-between">
                <span>Probability of Continuation</span>
                <span className="text-[10px] bg-slate-800 px-1.5 py-0.5 rounded text-slate-500">Last 1000 candles</span>
            </h4>
            <div className="h-32 w-full bg-slate-900/30 rounded-lg p-2 border border-slate-800">
                <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={data}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.3} />
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
                            domain={[0, 100]}
                            hide
                        />
                        <Tooltip
                            contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '8px', fontSize: '12px' }}
                            itemStyle={{ color: '#fff' }}
                            formatter={(value) => [`${value}%`, 'Prob.']}
                            labelFormatter={(label) => `Streak Length: ${label}`}
                        />
                        <Line
                            type="monotone"
                            dataKey="prob"
                            stroke="#8b5cf6"
                            strokeWidth={2}
                            dot={{ r: 2, fill: '#8b5cf6' }}
                            activeDot={{ r: 4, fill: '#fff' }}
                        />
                    </LineChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};

export default ProbabilityCurve;
