"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import {
    TrendingUp, TrendingDown, RefreshCw, DollarSign,
    BarChart2, Wallet, Clock, AlertCircle
} from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8009';

interface Position {
    symbol: string;
    quantity: number;
    average_price: number;
    last_price: number;
    pnl: number;
    pnl_percent: number;
    product: string;
}

interface Order {
    order_id: string;
    symbol: string;
    side: string;
    order_type: string;
    quantity: number;
    price: number | null;
    status: string;
    average_price: number;
    filled_quantity: number;
    placed_at: string;
    message: string;
}

interface Funds {
    total_capital: number;
    available_cash: number;
    used_margin: number;
}

export function OrderTerminal() {
    const [symbol, setSymbol] = useState('RELIANCE');
    const [quantity, setQuantity] = useState(1);
    const [orderType, setOrderType] = useState('MARKET');
    const [price, setPrice] = useState<number | undefined>();
    const [product, setProduct] = useState('MIS');

    const [positions, setPositions] = useState<Position[]>([]);
    const [orders, setOrders] = useState<Order[]>([]);
    const [funds, setFunds] = useState<Funds | null>(null);
    const [loading, setLoading] = useState(false);
    const [quote, setQuote] = useState<any>(null);

    // Fetch data on mount
    useEffect(() => {
        refreshData();
    }, []);

    // Fetch quote when symbol changes
    useEffect(() => {
        fetchQuote();
    }, [symbol]);

    const refreshData = async () => {
        try {
            const [posRes, ordRes, funRes] = await Promise.all([
                fetch(`${API_BASE}/api/v1/positions`),
                fetch(`${API_BASE}/api/v1/orders`),
                fetch(`${API_BASE}/api/v1/funds`)
            ]);

            setPositions((await posRes.json()).positions || []);
            setOrders((await ordRes.json()).orders || []);
            setFunds(await funRes.json());
        } catch (err) {
            console.error(err);
        }
    };

    const fetchQuote = async () => {
        try {
            const res = await fetch(`${API_BASE}/api/v1/quote/${symbol}`);
            setQuote(await res.json());
        } catch (err) {
            console.error(err);
        }
    };

    const placeOrder = async (side: 'BUY' | 'SELL') => {
        setLoading(true);
        try {
            const payload = {
                symbol,
                side,
                quantity,
                order_type: orderType,
                product,
                price: orderType === 'LIMIT' ? price : null
            };

            const res = await fetch(`${API_BASE}/api/v1/orders/place`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const order = await res.json();

            if (order.order_id) {
                await refreshData();
            }
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const cancelOrder = async (orderId: string) => {
        try {
            await fetch(`${API_BASE}/api/v1/orders/${orderId}`, { method: 'DELETE' });
            await refreshData();
        } catch (err) {
            console.error(err);
        }
    };

    const totalPnL = positions.reduce((sum, p) => sum + p.pnl, 0);

    return (
        <div className="space-y-6">
            {/* Header with Funds */}
            <div className="grid gap-4 md:grid-cols-4">
                <Card>
                    <CardContent className="pt-4">
                        <div className="flex items-center gap-2">
                            <Wallet className="h-5 w-5 text-blue-500" />
                            <div>
                                <p className="text-xs text-muted-foreground">Available Cash</p>
                                <p className="text-xl font-bold">₹{funds?.available_cash?.toLocaleString() || 0}</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="pt-4">
                        <div className="flex items-center gap-2">
                            <BarChart2 className="h-5 w-5 text-purple-500" />
                            <div>
                                <p className="text-xs text-muted-foreground">Used Margin</p>
                                <p className="text-xl font-bold">₹{funds?.used_margin?.toLocaleString() || 0}</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="pt-4">
                        <div className="flex items-center gap-2">
                            <DollarSign className={`h-5 w-5 ${totalPnL >= 0 ? 'text-green-500' : 'text-red-500'}`} />
                            <div>
                                <p className="text-xs text-muted-foreground">Day P&L</p>
                                <p className={`text-xl font-bold ${totalPnL >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                    {totalPnL >= 0 ? '+' : ''}₹{totalPnL.toFixed(2)}
                                </p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="pt-4">
                        <div className="flex items-center gap-2">
                            <Clock className="h-5 w-5 text-orange-500" />
                            <div>
                                <p className="text-xs text-muted-foreground">Open Orders</p>
                                <p className="text-xl font-bold">{orders.filter(o => o.status === 'OPEN').length}</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Order Entry */}
            <Card>
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <CardTitle>Place Order</CardTitle>
                        <Button variant="ghost" size="sm" onClick={refreshData}>
                            <RefreshCw className="h-4 w-4" />
                        </Button>
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="grid gap-4 md:grid-cols-6">
                        {/* Symbol */}
                        <div>
                            <label className="text-xs font-medium mb-1 block">Symbol</label>
                            <input
                                type="text"
                                value={symbol}
                                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                                className="w-full rounded-md border px-3 py-2 text-sm"
                            />
                        </div>

                        {/* Quantity */}
                        <div>
                            <label className="text-xs font-medium mb-1 block">Quantity</label>
                            <input
                                type="number"
                                value={quantity}
                                onChange={(e) => setQuantity(parseInt(e.target.value) || 1)}
                                min={1}
                                className="w-full rounded-md border px-3 py-2 text-sm"
                            />
                        </div>

                        {/* Order Type */}
                        <div>
                            <label className="text-xs font-medium mb-1 block">Order Type</label>
                            <select
                                value={orderType}
                                onChange={(e) => setOrderType(e.target.value)}
                                className="w-full rounded-md border px-3 py-2 text-sm"
                            >
                                <option value="MARKET">Market</option>
                                <option value="LIMIT">Limit</option>
                                <option value="SL">Stop Loss</option>
                                <option value="SL-M">SL-Market</option>
                            </select>
                        </div>

                        {/* Price (for limit orders) */}
                        <div>
                            <label className="text-xs font-medium mb-1 block">Price</label>
                            <input
                                type="number"
                                value={price || ''}
                                onChange={(e) => setPrice(parseFloat(e.target.value))}
                                disabled={orderType === 'MARKET'}
                                placeholder={quote?.last_price?.toFixed(2) || '0.00'}
                                className="w-full rounded-md border px-3 py-2 text-sm disabled:opacity-50"
                            />
                        </div>

                        {/* Product */}
                        <div>
                            <label className="text-xs font-medium mb-1 block">Product</label>
                            <select
                                value={product}
                                onChange={(e) => setProduct(e.target.value)}
                                className="w-full rounded-md border px-3 py-2 text-sm"
                            >
                                <option value="MIS">MIS (Intraday)</option>
                                <option value="CNC">CNC (Delivery)</option>
                                <option value="NRML">NRML (F&O)</option>
                            </select>
                        </div>

                        {/* LTP */}
                        <div>
                            <label className="text-xs font-medium mb-1 block">LTP</label>
                            <div className="w-full rounded-md border px-3 py-2 text-sm bg-secondary">
                                ₹{quote?.last_price?.toFixed(2) || '---'}
                            </div>
                        </div>
                    </div>

                    {/* Buy/Sell Buttons */}
                    <div className="flex gap-3 mt-4">
                        <Button
                            onClick={() => placeOrder('BUY')}
                            disabled={loading}
                            className="flex-1 bg-green-600 hover:bg-green-700"
                        >
                            <TrendingUp className="h-4 w-4 mr-2" />
                            BUY
                        </Button>
                        <Button
                            onClick={() => placeOrder('SELL')}
                            disabled={loading}
                            className="flex-1 bg-red-600 hover:bg-red-700"
                        >
                            <TrendingDown className="h-4 w-4 mr-2" />
                            SELL
                        </Button>
                    </div>
                </CardContent>
            </Card>

            {/* Positions */}
            <Card>
                <CardHeader>
                    <CardTitle>Positions ({positions.length})</CardTitle>
                </CardHeader>
                <CardContent>
                    {positions.length === 0 ? (
                        <p className="text-sm text-muted-foreground text-center py-4">No open positions</p>
                    ) : (
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b">
                                    <th className="text-left py-2">Symbol</th>
                                    <th className="text-right py-2">Qty</th>
                                    <th className="text-right py-2">Avg Price</th>
                                    <th className="text-right py-2">LTP</th>
                                    <th className="text-right py-2">P&L</th>
                                    <th className="text-right py-2">P&L %</th>
                                </tr>
                            </thead>
                            <tbody>
                                {positions.map((pos, idx) => (
                                    <tr key={idx} className="border-b">
                                        <td className="py-2 font-medium">{pos.symbol}</td>
                                        <td className="text-right py-2">{pos.quantity}</td>
                                        <td className="text-right py-2">₹{pos.average_price?.toFixed(2)}</td>
                                        <td className="text-right py-2">₹{pos.last_price?.toFixed(2)}</td>
                                        <td className={`text-right py-2 ${pos.pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                            {pos.pnl >= 0 ? '+' : ''}₹{pos.pnl?.toFixed(2)}
                                        </td>
                                        <td className={`text-right py-2 ${pos.pnl_percent >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                            {pos.pnl_percent >= 0 ? '+' : ''}{pos.pnl_percent?.toFixed(2)}%
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </CardContent>
            </Card>

            {/* Order Book */}
            <Card>
                <CardHeader>
                    <CardTitle>Order Book ({orders.length})</CardTitle>
                </CardHeader>
                <CardContent>
                    {orders.length === 0 ? (
                        <p className="text-sm text-muted-foreground text-center py-4">No orders today</p>
                    ) : (
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b">
                                    <th className="text-left py-2">Order ID</th>
                                    <th className="text-left py-2">Symbol</th>
                                    <th className="text-center py-2">Side</th>
                                    <th className="text-right py-2">Qty</th>
                                    <th className="text-right py-2">Price</th>
                                    <th className="text-center py-2">Status</th>
                                    <th className="text-center py-2">Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                {orders.map((ord, idx) => (
                                    <tr key={idx} className="border-b">
                                        <td className="py-2 font-mono text-xs">{ord.order_id}</td>
                                        <td className="py-2">{ord.symbol}</td>
                                        <td className="text-center py-2">
                                            <Badge className={ord.side === 'BUY' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}>
                                                {ord.side}
                                            </Badge>
                                        </td>
                                        <td className="text-right py-2">{ord.quantity}</td>
                                        <td className="text-right py-2">
                                            ₹{ord.average_price?.toFixed(2) || ord.price?.toFixed(2) || 'MKT'}
                                        </td>
                                        <td className="text-center py-2">
                                            <Badge variant={ord.status === 'COMPLETE' ? 'default' : ord.status === 'REJECTED' ? 'destructive' : 'secondary'}>
                                                {ord.status}
                                            </Badge>
                                        </td>
                                        <td className="text-center py-2">
                                            {ord.status === 'OPEN' && (
                                                <Button
                                                    size="sm"
                                                    variant="ghost"
                                                    onClick={() => cancelOrder(ord.order_id)}
                                                    className="text-red-500 h-7 text-xs"
                                                >
                                                    Cancel
                                                </Button>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
