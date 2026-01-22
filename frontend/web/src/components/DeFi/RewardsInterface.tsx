'use client';

import React, { useState } from 'react';
import { Card, CardContent } from '../ui/card';
import { Button } from '../ui/button';
import { Coins, RefreshCw, Trophy } from 'lucide-react';

export function RewardsInterface() {
    const [isClaiming, setIsClaiming] = useState(false);
    const [isCompounding, setIsCompounding] = useState(false);
    const [rewards, setRewards] = useState({
        pending: '1,245.82',
        claimed: '8,450.00',
        apy: '15.5'
    });

    const handleClaim = () => {
        setIsClaiming(true);
        setTimeout(() => {
            alert('Rewards claimed successfully!');
            setIsClaiming(false);
        }, 1500);
    };

    const handleCompound = () => {
        setIsCompounding(true);
        setTimeout(() => {
            alert('Rewards compounded into your active stakes!');
            setIsCompounding(false);
        }, 1500);
    };

    return (
        <div className="space-y-6">
            {/* Hero Stats */}
            <div className="bg-gradient-to-br from-green-600/20 to-emerald-600/20 rounded-2xl p-8 border border-green-500/20">
                <div className="flex justify-between items-center mb-8">
                    <div>
                        <h2 className="text-3xl font-bold text-white flex items-center gap-3">
                            Rewards Dashboard
                        </h2>
                        <p className="text-slate-400 mt-1">Track and grow your passive income with FACT tokens.</p>
                    </div>
                    <div className="text-right">
                        <p className="text-xs text-slate-500 uppercase font-bold tracking-wider">Current APY</p>
                        <p className="text-4xl font-black text-green-400">{rewards.apy}%</p>
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <Card className="bg-slate-950/50 border-emerald-500/20">
                        <CardContent className="pt-6">
                            <p className="text-sm text-slate-400 mb-2">Pending Rewards</p>
                            <div className="flex items-end gap-2">
                                <p className="text-4xl font-bold text-white">{rewards.pending}</p>
                                <p className="text-lg text-slate-500 mb-1">FACT</p>
                            </div>
                            <p className="text-xs text-slate-500 mt-2">≈ $124.58 USD</p>
                        </CardContent>
                    </Card>

                    <Card className="bg-slate-950/50 border-emerald-500/20">
                        <CardContent className="pt-6">
                            <p className="text-sm text-slate-400 mb-2">Total Claimed</p>
                            <div className="flex items-end gap-2">
                                <p className="text-4xl font-bold text-blue-400">{rewards.claimed}</p>
                                <p className="text-lg text-slate-500 mb-1">FACT</p>
                            </div>
                            <p className="text-xs text-slate-500 mt-2">Lifetime earnings</p>
                        </CardContent>
                    </Card>
                </div>
            </div>

            {/* Action Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Card className="bg-slate-900/50 border-slate-800 p-6">
                    <div className="flex items-center gap-4 mb-6">
                        <div className="p-3 bg-green-500/10 rounded-xl">
                            <Coins className="w-6 h-6 text-green-400" />
                        </div>
                        <div>
                            <h3 className="text-lg font-bold text-white">Withdraw Rewards</h3>
                            <p className="text-sm text-slate-400">Transfer pending rewards to your wallet.</p>
                        </div>
                    </div>
                    <Button
                        className="w-full bg-green-600 hover:bg-green-700 text-white font-bold h-12"
                        onClick={handleClaim}
                        disabled={isClaiming}
                    >
                        {isClaiming ? 'Processing...' : 'Claim FACT'}
                    </Button>
                </Card>

                <Card className="bg-slate-900/50 border-slate-800 p-6">
                    <div className="flex items-center gap-4 mb-6">
                        <div className="p-3 bg-purple-500/10 rounded-xl">
                            <RefreshCw className="w-6 h-6 text-purple-400" />
                        </div>
                        <div>
                            <h3 className="text-lg font-bold text-white">Auto-Compound</h3>
                            <p className="text-sm text-slate-400">Reinvest rewards to maximize APR.</p>
                        </div>
                    </div>
                    <Button
                        className="w-full bg-purple-600 hover:bg-purple-700 text-white font-bold h-12"
                        onClick={handleCompound}
                        disabled={isCompounding}
                    >
                        {isCompounding ? 'Processing...' : 'Compound Now'}
                    </Button>
                </Card>
            </div>

            {/* Dynamic APY Chart Simulation (Simple list for now) */}
            <Card className="bg-slate-900/50 border-slate-800 p-6">
                <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
                    <Trophy className="w-5 h-5 text-yellow-400" />
                    APY Tiers
                </h3>
                <div className="space-y-4">
                    <div className="flex justify-between items-center p-4 bg-slate-950/50 rounded-lg border border-slate-800">
                        <div>
                            <p className="font-bold text-white">Bronze Tier</p>
                            <p className="text-xs text-slate-500">Staking &lt; 10,000 FACT</p>
                        </div>
                        <p className="text-xl font-bold text-slate-400">12% APR</p>
                    </div>
                    <div className="flex justify-between items-center p-4 bg-purple-500/5 rounded-lg border border-purple-500/20 scale-105">
                        <div>
                            <p className="font-bold text-purple-400">Silver Tier (Current)</p>
                            <p className="text-xs text-slate-500">Staking 10,000 - 50,000 FACT</p>
                        </div>
                        <p className="text-xl font-bold text-green-400">15.5% APR</p>
                    </div>
                    <div className="flex justify-between items-center p-4 bg-slate-950/50 rounded-lg border border-slate-800 opacity-60">
                        <div>
                            <p className="font-bold text-white">Gold Tier</p>
                            <p className="text-xs text-slate-500">Staking &gt; 50,000 FACT</p>
                        </div>
                        <p className="text-xl font-bold text-yellow-400">22% APR</p>
                    </div>
                </div>
            </Card>
        </div>
    );
}
