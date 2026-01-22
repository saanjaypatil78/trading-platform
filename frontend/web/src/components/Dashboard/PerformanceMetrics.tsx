"use strict";

import React from 'react';
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    AreaChart, Area, BarChart, Bar, Cell
} from 'recharts';
import { Activity, TrendingUp, ShieldAlert, Zap, Globe } from 'lucide-react';

// Mock data for initial view
const equityData = [
    { time: '09:30', equity: 100000 },
    { time: '10:00', equity: 100500 },
    { time: '11:00', equity: 99800 },
    { time: '12:00', equity: 101200 },
    { time: '13:00', equity: 102500 },
    { time: '14:00', equity: 102100 },
    { time: '15:00', equity: 103800 },
    { time: '15:30', equity: 104500 },
];

const PerformanceMetrics = () => {
    return (
        <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <MetricCard
                    title="Total Return"
                    value="+4.5%"
                    change="+1.2% today"
                    icon={<TrendingUp className="text-green-400" />}
                />
                <MetricCard
                    title="Max Drawdown"
                    value="-2.1%"
                    change="Within limits"
                    icon={<ShieldAlert className="text-yellow-400" />}
                />
                <MetricCard
                    title="Execution Latency"
                    value="12ms"
                    change="-2ms avg"
                    icon={<Zap className="text-blue-400" />}
                />
                <MetricCard
                    title="Win Rate"
                    value="68%"
                    change="Last 50 trades"
                    icon={<Activity className="text-purple-400" />}
                />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="bg-slate-900/50 backdrop-blur-md border border-slate-800 rounded-xl p-6 shadow-2xl">
                    <h3 className="text-lg font-semibold text-slate-100 mb-6 flex items-center gap-2">
                        <Globe className="w-5 h-5 text-indigo-400" />
                        Equity Curve (Live)
                    </h3>
                    <div className="h-[300px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={equityData}>
                                <defs>
                                    <linearGradient id="colorEquity" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                                        <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                                <XAxis dataKey="time" stroke="#64748b" />
                                <YAxis stroke="#64748b" domain={['dataMin - 1000', 'dataMax + 1000']} />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px' }}
                                    itemStyle={{ color: '#f1f5f9' }}
                                />
                                <Area
                                    type="monotone"
                                    dataKey="equity"
                                    stroke="#6366f1"
                                    strokeWidth={2}
                                    fillOpacity={1}
                                    fill="url(#colorEquity)"
                                />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                <div className="bg-slate-900/50 backdrop-blur-md border border-slate-800 rounded-xl p-6 shadow-2xl">
                    <h3 className="text-lg font-semibold text-slate-100 mb-6 flex items-center gap-2">
                        <Activity className="w-5 h-5 text-emerald-400" />
                        Trade Distribution
                    </h3>
                    {/* Detailed distribution bar chart could go here */}
                    <div className="h-[300px] w-full flex items-center justify-center text-slate-500 italic">
                        Visualizing PnL distribution per strategy...
                    </div>
                </div>
            </div>
        </div>
    );
};

const MetricCard = ({ title, value, change, icon }) => (
    <div className="bg-slate-900/50 backdrop-blur-md border border-slate-800 rounded-xl p-4 shadow-lg">
        <div className="flex justify-between items-start mb-2">
            <span className="text-sm font-medium text-slate-400">{title}</span>
            {icon}
        </div>
        <div className="text-2xl font-bold text-slate-100 mb-1">{value}</div>
        <div className="text-xs text-slate-500 font-medium">{change}</div>
    </div>
);

export default PerformanceMetrics;
