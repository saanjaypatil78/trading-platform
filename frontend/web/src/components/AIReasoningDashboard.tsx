"use client";

import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { TokenBalance } from './TokenBalance';
import { Brain, TrendingUp, TrendingDown, AlertTriangle, CheckCircle, ChevronRight } from 'lucide-react';

import { fetchWithFailover } from '../lib/api';

interface ThoughtStep {
    thought_number: number;
    thought: string;
    branch_id?: string;
}

interface AnalysisResult {
    decision?: string;
    confidence?: string;
    regime?: string;
    position_size?: number;
    recommended_strategy?: string;
    [key: string]: any;
}

export function AIReasoningDashboard() {
    const [symbol, setSymbol] = useState('NVDA');
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<AnalysisResult | null>(null);
    const [trace, setTrace] = useState<ThoughtStep[]>([]);
    const [strategy, setStrategy] = useState('entry-analysis');

    // Mock market data for demo
    const mockData = {
        'entry-analysis': { symbol, rsi: 28, macd: 5.2, macd_signal: 4.8, volume: 50000000, avg_volume: 30000000 },
        'risk-assessment': { account_size: 50000, risk_percent: 2, entry_price: 150, stop_loss: 145 },
        'regime-detection': { price: 450, sma_50: 440, sma_200: 400, atr: 8 },
        'earnings-play': { symbol, iv: 85, iv_rank: 78, expected_move: 8 }
    };

    const runAnalysis = async () => {
        setLoading(true);
        setResult(null);
        setTrace([]);

        try {
            const payload = mockData[strategy as keyof typeof mockData] || mockData['entry-analysis'];
            const res = await fetchWithFailover(`/api/v1/brain/${strategy}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            setResult(data.result);
            setTrace(data.trace || []);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const getDecisionColor = (decision?: string) => {
        if (decision === 'BUY' || decision === 'BULL') return 'text-green-500';
        if (decision === 'SELL' || decision === 'BEAR') return 'text-red-500';
        return 'text-yellow-500';
    };

    const getDecisionIcon = (decision?: string) => {
        if (decision === 'BUY' || decision === 'BULL') return <TrendingUp className="h-6 w-6 text-green-500" />;
        if (decision === 'SELL' || decision === 'BEAR') return <TrendingDown className="h-6 w-6 text-red-500" />;
        return <AlertTriangle className="h-6 w-6 text-yellow-500" />;
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <Brain className="h-8 w-8 text-purple-500" />
                    <div>
                        <h2 className="text-2xl font-bold">AI Reasoning Engine</h2>
                        <p className="text-sm text-muted-foreground">Watch the AI think step-by-step</p>
                    </div>
                </div>
                <TokenBalance />
            </div>

            {/* Controls */}
            <Card>
                <CardContent className="pt-6">
                    <div className="flex flex-wrap gap-4 items-end">
                        <div className="flex-1 min-w-[200px]">
                            <label className="text-sm font-medium mb-2 block">Symbol</label>
                            <input
                                type="text"
                                value={symbol}
                                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                                className="w-full rounded-md border px-3 py-2 text-sm"
                            />
                        </div>
                        <div className="flex-1 min-w-[200px]">
                            <label className="text-sm font-medium mb-2 block">Strategy</label>
                            <select
                                value={strategy}
                                onChange={(e) => setStrategy(e.target.value)}
                                className="w-full rounded-md border px-3 py-2 text-sm"
                            >
                                <option value="entry-analysis">Entry Analysis (Buy/Sell)</option>
                                <option value="risk-assessment">Risk Assessment</option>
                                <option value="regime-detection">Regime Detection</option>
                                <option value="earnings-play">Earnings Play</option>
                            </select>
                        </div>
                        <Button onClick={runAnalysis} disabled={loading} className="bg-purple-600 hover:bg-purple-700">
                            {loading ? 'Thinking...' : 'Run Analysis'}
                        </Button>
                    </div>
                </CardContent>
            </Card>

            {/* Results */}
            {result && (
                <div className="grid gap-4 md:grid-cols-2">
                    {/* Decision Card */}
                    <Card className="border-l-4 border-l-purple-500">
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                {getDecisionIcon(result.decision || result.regime)}
                                Decision
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className={`text-4xl font-bold ${getDecisionColor(result.decision || result.regime)}`}>
                                {result.decision || result.regime || result.recommended_strategy || 'N/A'}
                            </div>
                            {result.confidence && (
                                <Badge className="mt-2">{result.confidence} Confidence</Badge>
                            )}
                            {result.position_size && (
                                <div className="mt-2 text-sm">
                                    Position: <span className="font-mono">{result.position_size} shares</span>
                                </div>
                            )}
                            {result.rationale && (
                                <p className="mt-2 text-sm text-muted-foreground">{result.rationale}</p>
                            )}
                        </CardContent>
                    </Card>

                    {/* Thinking Trace */}
                    <Card>
                        <CardHeader>
                            <CardTitle>Reasoning Trace</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-3 max-h-[300px] overflow-y-auto">
                                {trace.map((step, idx) => (
                                    <div key={idx} className="flex items-start gap-2">
                                        <div className="flex-shrink-0 w-6 h-6 rounded-full bg-purple-100 dark:bg-purple-900 flex items-center justify-center text-xs font-bold text-purple-600">
                                            {step.thought_number}
                                        </div>
                                        <div className="flex-1">
                                            <p className="text-sm">{step.thought}</p>
                                            {step.branch_id && step.branch_id !== 'main' && (
                                                <Badge variant="outline" className="mt-1 text-xs">
                                                    Branch: {step.branch_id}
                                                </Badge>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    </Card>
                </div>
            )}
        </div>
    );
}
