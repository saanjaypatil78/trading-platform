"use client";

import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Plus, Trash2, Play, Save, Search, TrendingUp, TrendingDown, Activity } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8008';

// Available indicators for the builder
const INDICATORS = [
    { id: 'close', name: 'Close Price', category: 'price' },
    { id: 'open', name: 'Open Price', category: 'price' },
    { id: 'high', name: 'High Price', category: 'price' },
    { id: 'low', name: 'Low Price', category: 'price' },
    { id: 'volume', name: 'Volume', category: 'volume' },
    { id: 'rsi(14)', name: 'RSI (14)', category: 'momentum' },
    { id: 'rsi(7)', name: 'RSI (7)', category: 'momentum' },
    { id: 'sma(close, 20)', name: 'SMA (20)', category: 'trend' },
    { id: 'sma(close, 50)', name: 'SMA (50)', category: 'trend' },
    { id: 'sma(close, 200)', name: 'SMA (200)', category: 'trend' },
    { id: 'ema(close, 12)', name: 'EMA (12)', category: 'trend' },
    { id: 'ema(close, 26)', name: 'EMA (26)', category: 'trend' },
    { id: 'macd()', name: 'MACD Line', category: 'momentum' },
    { id: 'macd_signal()', name: 'MACD Signal', category: 'momentum' },
    { id: 'bb_upper()', name: 'Bollinger Upper', category: 'volatility' },
    { id: 'bb_lower()', name: 'Bollinger Lower', category: 'volatility' },
];

const OPERATORS = [
    { id: '>', name: 'Greater Than', symbol: '>' },
    { id: '>=', name: 'Greater or Equal', symbol: '>=' },
    { id: '<', name: 'Less Than', symbol: '<' },
    { id: '<=', name: 'Less or Equal', symbol: '<=' },
    { id: '==', name: 'Equals', symbol: '=' },
    { id: 'crosses_above', name: 'Crosses Above', symbol: '↗' },
    { id: 'crosses_below', name: 'Crosses Below', symbol: '↘' },
];

const TEMPLATES = [
    { id: 'rsi_overbought', name: 'RSI Overbought (>70)', description: 'Stocks with RSI above 70' },
    { id: 'rsi_oversold', name: 'RSI Oversold (<30)', description: 'Stocks with RSI below 30' },
    { id: 'golden_cross', name: 'Golden Cross', description: 'SMA 50 above SMA 200' },
    { id: 'death_cross', name: 'Death Cross', description: 'SMA 50 below SMA 200' },
];

interface Condition {
    id: string;
    left: string;
    operator: string;
    right: string;
}

interface ScanResult {
    symbol: string;
    current_price: number;
    indicator_values: { [key: string]: number };
}

export function ScannerBuilder() {
    const [conditions, setConditions] = useState<Condition[]>([
        { id: '1', left: 'rsi(14)', operator: '>', right: '70' }
    ]);
    const [logic, setLogic] = useState<'AND' | 'OR'>('AND');
    const [loading, setLoading] = useState(false);
    const [results, setResults] = useState<ScanResult[]>([]);
    const [totalScanned, setTotalScanned] = useState(0);

    const addCondition = () => {
        setConditions([...conditions, {
            id: Date.now().toString(),
            left: 'close',
            operator: '>',
            right: '0'
        }]);
    };

    const removeCondition = (id: string) => {
        setConditions(conditions.filter(c => c.id !== id));
    };

    const updateCondition = (id: string, field: keyof Condition, value: string) => {
        setConditions(conditions.map(c =>
            c.id === id ? { ...c, [field]: value } : c
        ));
    };

    const loadTemplate = (templateId: string) => {
        // Pre-define conditions based on template
        switch (templateId) {
            case 'rsi_overbought':
                setConditions([{ id: '1', left: 'rsi(14)', operator: '>', right: '70' }]);
                break;
            case 'rsi_oversold':
                setConditions([{ id: '1', left: 'rsi(14)', operator: '<', right: '30' }]);
                break;
            case 'golden_cross':
                setConditions([{ id: '1', left: 'sma(close, 50)', operator: '>', right: 'sma(close, 200)' }]);
                break;
            case 'death_cross':
                setConditions([{ id: '1', left: 'sma(close, 50)', operator: '<', right: 'sma(close, 200)' }]);
                break;
        }
    };

    const runScan = async () => {
        setLoading(true);
        setResults([]);

        try {
            const payload = {
                conditions: conditions.map(c => ({
                    left: c.left,
                    operator: c.operator,
                    right: c.right
                })),
                logic: logic
            };

            const res = await fetch(`${API_BASE}/api/v1/scanner/scan`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const data = await res.json();
            setResults(data.results || []);
            setTotalScanned(data.total_scanned || 0);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const getCategoryColor = (category: string) => {
        switch (category) {
            case 'price': return 'bg-blue-100 text-blue-800';
            case 'volume': return 'bg-purple-100 text-purple-800';
            case 'momentum': return 'bg-orange-100 text-orange-800';
            case 'trend': return 'bg-green-100 text-green-800';
            case 'volatility': return 'bg-red-100 text-red-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <Search className="h-8 w-8 text-blue-500" />
                    <div>
                        <h2 className="text-2xl font-bold">Stock Scanner</h2>
                        <p className="text-sm text-muted-foreground">Build custom screening criteria</p>
                    </div>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline" onClick={() => setConditions([])}>
                        Clear All
                    </Button>
                    <Button onClick={runScan} disabled={loading || conditions.length === 0} className="bg-blue-600 hover:bg-blue-700">
                        <Play className="h-4 w-4 mr-2" />
                        {loading ? 'Scanning...' : 'Run Scan'}
                    </Button>
                </div>
            </div>

            {/* Templates */}
            <Card>
                <CardHeader className="py-3">
                    <CardTitle className="text-sm font-medium">Quick Templates</CardTitle>
                </CardHeader>
                <CardContent className="py-3">
                    <div className="flex flex-wrap gap-2">
                        {TEMPLATES.map(t => (
                            <Button
                                key={t.id}
                                variant="outline"
                                size="sm"
                                onClick={() => loadTemplate(t.id)}
                            >
                                {t.name}
                            </Button>
                        ))}
                    </div>
                </CardContent>
            </Card>

            {/* Condition Builder */}
            <Card>
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <CardTitle>Scan Conditions</CardTitle>
                        <div className="flex items-center gap-2">
                            <span className="text-sm text-muted-foreground">Logic:</span>
                            <select
                                value={logic}
                                onChange={(e) => setLogic(e.target.value as 'AND' | 'OR')}
                                className="rounded-md border px-2 py-1 text-sm"
                            >
                                <option value="AND">AND (All must match)</option>
                                <option value="OR">OR (Any can match)</option>
                            </select>
                        </div>
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="space-y-3">
                        {conditions.map((cond, idx) => (
                            <div key={cond.id} className="flex items-center gap-2 p-3 rounded-lg border bg-secondary/30">
                                {idx > 0 && (
                                    <Badge variant="outline" className="shrink-0">{logic}</Badge>
                                )}

                                {/* Left operand */}
                                <select
                                    value={cond.left}
                                    onChange={(e) => updateCondition(cond.id, 'left', e.target.value)}
                                    className="flex-1 rounded-md border px-2 py-1.5 text-sm"
                                >
                                    {INDICATORS.map(ind => (
                                        <option key={ind.id} value={ind.id}>{ind.name}</option>
                                    ))}
                                </select>

                                {/* Operator */}
                                <select
                                    value={cond.operator}
                                    onChange={(e) => updateCondition(cond.id, 'operator', e.target.value)}
                                    className="w-40 rounded-md border px-2 py-1.5 text-sm"
                                >
                                    {OPERATORS.map(op => (
                                        <option key={op.id} value={op.id}>{op.name}</option>
                                    ))}
                                </select>

                                {/* Right operand */}
                                <input
                                    type="text"
                                    value={cond.right}
                                    onChange={(e) => updateCondition(cond.id, 'right', e.target.value)}
                                    placeholder="Value or indicator"
                                    className="flex-1 rounded-md border px-2 py-1.5 text-sm"
                                />

                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => removeCondition(cond.id)}
                                    className="text-red-500 hover:text-red-700"
                                >
                                    <Trash2 className="h-4 w-4" />
                                </Button>
                            </div>
                        ))}

                        <Button variant="outline" onClick={addCondition} className="w-full">
                            <Plus className="h-4 w-4 mr-2" />
                            Add Condition
                        </Button>
                    </div>
                </CardContent>
            </Card>

            {/* Results */}
            {results.length > 0 && (
                <Card>
                    <CardHeader>
                        <div className="flex items-center justify-between">
                            <CardTitle>Scan Results</CardTitle>
                            <Badge variant="secondary">
                                {results.length} of {totalScanned} stocks matched
                            </Badge>
                        </div>
                    </CardHeader>
                    <CardContent>
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="border-b">
                                        <th className="text-left py-2 px-3">Symbol</th>
                                        <th className="text-right py-2 px-3">Price</th>
                                        <th className="text-right py-2 px-3">RSI</th>
                                        <th className="text-right py-2 px-3">SMA 50</th>
                                        <th className="text-right py-2 px-3">SMA 200</th>
                                        <th className="text-center py-2 px-3">Action</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {results.map((r, idx) => (
                                        <tr key={idx} className="border-b hover:bg-secondary/50">
                                            <td className="py-2 px-3 font-medium">{r.symbol}</td>
                                            <td className="text-right py-2 px-3">{r.current_price?.toFixed(2)}</td>
                                            <td className="text-right py-2 px-3">
                                                <span className={r.indicator_values?.rsi > 70 ? 'text-red-500' : r.indicator_values?.rsi < 30 ? 'text-green-500' : ''}>
                                                    {r.indicator_values?.rsi?.toFixed(1) || '-'}
                                                </span>
                                            </td>
                                            <td className="text-right py-2 px-3">{r.indicator_values?.sma_50?.toFixed(2) || '-'}</td>
                                            <td className="text-right py-2 px-3">{r.indicator_values?.sma_200?.toFixed(2) || '-'}</td>
                                            <td className="text-center py-2 px-3">
                                                <div className="flex justify-center gap-1">
                                                    <Button size="sm" variant="outline" className="text-green-600 border-green-600 h-7 text-xs">
                                                        <TrendingUp className="h-3 w-3 mr-1" />
                                                        Buy
                                                    </Button>
                                                    <Button size="sm" variant="outline" className="text-red-600 border-red-600 h-7 text-xs">
                                                        <TrendingDown className="h-3 w-3 mr-1" />
                                                        Sell
                                                    </Button>
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Available Indicators Reference */}
            <Card>
                <CardHeader>
                    <CardTitle className="text-sm">Available Indicators</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="flex flex-wrap gap-2">
                        {INDICATORS.map(ind => (
                            <Badge
                                key={ind.id}
                                variant="outline"
                                className={getCategoryColor(ind.category)}
                            >
                                {ind.name}
                            </Badge>
                        ))}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
