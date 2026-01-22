'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/card';
import { Button } from '../ui/button';
import { Activity, Lock, TrendingUp, Wallet } from 'lucide-react';

type LockPeriod = '7' | '14' | '30';

export function StakingInterface() {
    const [amount, setAmount] = useState('');
    const [selectedPeriod, setSelectedPeriod] = useState<LockPeriod>('7');
    const [isStaking, setIsStaking] = useState(false);
    const [stats, setStats] = useState({
        tvl: '456.7M',
        userStaked: '0',
        activeStakers: '12,485'
    });

    const lockPeriods = [
        { days: '7', apr: '5%', multiplier: '1x', unbonding: '7 days' },
        { days: '14', apr: '10%', multiplier: '1.5x', unbonding: '14 days' },
        { days: '30', apr: '20%', multiplier: '2x', unbonding: '30 days' },
    ];

    const handleStake = async () => {
        setIsStaking(true);
        // Simulate API call to our new DeFi service
        setTimeout(() => {
            alert(`Successfully staked ${amount} FACT for ${selectedPeriod} days!`);
            setIsStaking(false);
            setAmount('');
        }, 1500);
    };

    return (
        <div className="space-y-6">
            {/* Overview Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card className="bg-slate-900/50 border-slate-800">
                    <CardContent className="pt-6">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-purple-500/10 rounded-lg">
                                <Lock className="w-5 h-5 text-purple-400" />
                            </div>
                            <div>
                                <p className="text-xs text-slate-400">Total Value Locked</p>
                                <p className="text-xl font-bold text-white">{stats.tvl} FACT</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <Card className="bg-slate-900/50 border-slate-800">
                    <CardContent className="pt-6">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-blue-500/10 rounded-lg">
                                <Wallet className="w-5 h-5 text-blue-400" />
                            </div>
                            <div>
                                <p className="text-xs text-slate-400">Your Staked</p>
                                <p className="text-xl font-bold text-white">{stats.userStaked} FACT</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <Card className="bg-slate-900/50 border-slate-800">
                    <CardContent className="pt-6">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-green-500/10 rounded-lg">
                                <Activity className="w-5 h-5 text-green-400" />
                            </div>
                            <div>
                                <p className="text-xs text-slate-400">Active Stakers</p>
                                <p className="text-xl font-bold text-white">{stats.activeStakers}</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Main Staking Card */}
            <Card className="bg-slate-900/50 border-slate-800 p-8">
                <div className="max-w-2xl mx-auto space-y-8">
                    <div>
                        <h2 className="text-2xl font-bold text-white mb-2">Stake & Earn Passive Income</h2>
                        <p className="text-slate-400">Lock your FACT tokens to earn rewards. Longer lock periods yield higher APR.</p>
                    </div>

                    <div className="grid grid-cols-3 gap-4">
                        {lockPeriods.map((period) => (
                            <button
                                key={period.days}
                                onClick={() => setSelectedPeriod(period.days as LockPeriod)}
                                className={`p-6 rounded-xl border-2 transition-all text-center ${selectedPeriod === period.days
                                        ? 'border-purple-500 bg-purple-500/10'
                                        : 'border-slate-800 bg-slate-900/50 hover:border-slate-700'
                                    }`}
                            >
                                <p className="text-3xl font-bold text-purple-400 mb-1">{period.days}</p>
                                <p className="text-xs text-slate-500 uppercase mb-4">Days</p>
                                <div className="space-y-1">
                                    <p className="text-sm font-bold text-green-400">{period.apr} APR</p>
                                    <p className="text-xs text-slate-400">{period.multiplier} Multiplier</p>
                                </div>
                            </button>
                        ))}
                    </div>

                    <div className="space-y-4">
                        <div className="space-y-2">
                            <label className="text-sm text-slate-400">Amount to Stake</label>
                            <div className="relative">
                                <input
                                    type="number"
                                    value={amount}
                                    onChange={(e) => setAmount(e.target.value)}
                                    placeholder="0.00"
                                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-3 text-white outline-none focus:border-purple-500"
                                />
                                <span className="absolute right-4 top-3 text-slate-500 font-bold">FACT</span>
                            </div>
                            <div className="flex justify-between text-xs">
                                <span className="text-slate-500">Available: 4,500 FACT</span>
                                <button className="text-purple-400 hover:text-purple-300">Max</button>
                            </div>
                        </div>

                        <Button
                            className="w-full py-6 text-lg font-bold bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700"
                            onClick={handleStake}
                            disabled={!amount || isStaking}
                        >
                            {isStaking ? 'Processing...' : `Stake for ${selectedPeriod} Days`}
                        </Button>
                    </div>

                    <div className="p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg">
                        <p className="text-xs text-blue-300 leading-relaxed">
                            <strong>Note:</strong> Your tokens will be locked for {selectedPeriod} days. Unstaking before this period or after it ends involves a {
                                lockPeriods.find(p => p.days === selectedPeriod)?.unbonding
                            } unbonding period.
                        </p>
                    </div>
                </div>
            </Card>
        </div>
    );
}
