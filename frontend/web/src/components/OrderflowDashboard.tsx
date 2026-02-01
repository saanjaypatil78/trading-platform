"use client";

import React, { useState, useEffect, useRef } from "react";

interface OrderBookLevel {
    price: number;
    size: number;
    order_count?: number;
}

interface OrderBookData {
    symbol: string;
    timestamp: string;
    bids: OrderBookLevel[];
    asks: OrderBookLevel[];
}

interface FootprintSignal {
    symbol: string;
    signal_type: string;
    direction: string;
    confidence: string;
    price_level: number;
    delta: number;
    description: string;
}

interface OrderflowDashboardProps {
    symbol?: string;
    orderflowServiceUrl?: string;
}

export default function OrderflowDashboard({
    symbol = "AAPL",
    orderflowServiceUrl = process.env.NEXT_PUBLIC_API_URL
        ? `${process.env.NEXT_PUBLIC_API_URL}/api/v1/orderflow`
        : "http://localhost:8000/api/v1/orderflow",
}: OrderflowDashboardProps) {
    const [orderbook, setOrderbook] = useState<OrderBookData | null>(null);
    const [signals, setSignals] = useState<FootprintSignal[]>([]);
    const [isConnected, setIsConnected] = useState(false);
    const [metrics, setMetrics] = useState<any>(null);
    const wsRef = useRef<WebSocket | null>(null);
    const signalWsRef = useRef<WebSocket | null>(null);

    // Connect to L2 WebSocket
    useEffect(() => {
        const wsBase = orderflowServiceUrl.replace(/^http/, "ws");
        const wsUrl = `${wsBase}/ws/l2/${symbol}`;
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log("L2 WebSocket connected");
            setIsConnected(true);
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            setOrderbook(data);
        };

        ws.onclose = () => {
            console.log("L2 WebSocket disconnected");
            setIsConnected(false);
        };

        ws.onerror = (error) => {
            console.error("L2 WebSocket error:", error);
        };

        wsRef.current = ws;

        return () => {
            ws.close();
        };
    }, [symbol]);

    // Connect to signals WebSocket
    useEffect(() => {
        const wsBase = orderflowServiceUrl.replace(/^http/, "ws");
        const wsUrl = `${wsBase}/ws/signals/${symbol}`;
        const ws = new WebSocket(wsUrl);

        ws.onmessage = (event) => {
            const signal = JSON.parse(event.data);
            setSignals((prev) => [signal, ...prev].slice(0, 10));
        };

        signalWsRef.current = ws;

        return () => {
            ws.close();
        };
    }, [symbol]);

    // Fetch metrics periodically
    useEffect(() => {
        const fetchMetrics = async () => {
            try {
                const resp = await fetch(`${orderflowServiceUrl}/metrics`);
                const data = await resp.json();
                setMetrics(data);
            } catch (error) {
                console.error("Failed to fetch metrics:", error);
            }
        };

        fetchMetrics();
        const interval = setInterval(fetchMetrics, 5000);
        return () => clearInterval(interval);
    }, [orderflowServiceUrl]);

    // Calculate derived values
    const spread = orderbook
        ? parseFloat(
            (orderbook.asks[0]?.price - orderbook.bids[0]?.price).toFixed(2)
        )
        : 0;

    const bidDepth = orderbook
        ? orderbook.bids.slice(0, 5).reduce((sum, l) => sum + l.size, 0)
        : 0;

    const askDepth = orderbook
        ? orderbook.asks.slice(0, 5).reduce((sum, l) => sum + l.size, 0)
        : 0;

    const imbalanceRatio = askDepth > 0 ? (bidDepth / askDepth).toFixed(2) : "N/A";

    return (
        <div className="orderflow-dashboard">
            <style jsx>{`
        .orderflow-dashboard {
          font-family: "Inter", -apple-system, BlinkMacSystemFont, sans-serif;
          background: linear-gradient(135deg, #0f0f23 0%, #1a1a3e 100%);
          color: #fff;
          padding: 24px;
          border-radius: 16px;
          min-height: 600px;
        }

        .header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 24px;
        }

        .title {
          font-size: 24px;
          font-weight: 700;
          background: linear-gradient(90deg, #00d4ff, #7c3aed);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }

        .connection-status {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 12px;
          color: ${isConnected ? "#10b981" : "#ef4444"};
        }

        .status-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: ${isConnected ? "#10b981" : "#ef4444"};
          animation: ${isConnected ? "pulse 2s infinite" : "none"};
        }

        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }

        .grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 24px;
        }

        .card {
          background: rgba(255, 255, 255, 0.05);
          backdrop-filter: blur(10px);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 12px;
          padding: 20px;
        }

        .card-title {
          font-size: 14px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          color: #94a3b8;
          margin-bottom: 16px;
        }

        .orderbook {
          display: flex;
          gap: 16px;
        }

        .orderbook-side {
          flex: 1;
        }

        .orderbook-side h4 {
          font-size: 12px;
          color: #64748b;
          margin-bottom: 8px;
        }

        .level {
          display: flex;
          justify-content: space-between;
          font-size: 13px;
          padding: 4px 8px;
          margin-bottom: 2px;
          border-radius: 4px;
        }

        .bid-level {
          background: rgba(16, 185, 129, 0.15);
        }

        .ask-level {
          background: rgba(239, 68, 68, 0.15);
        }

        .price-bid { color: #10b981; font-weight: 600; }
        .price-ask { color: #ef4444; font-weight: 600; }
        .size { color: #94a3b8; }

        .stats-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 16px;
        }

        .stat {
          text-align: center;
          padding: 12px;
          background: rgba(255, 255, 255, 0.03);
          border-radius: 8px;
        }

        .stat-value {
          font-size: 24px;
          font-weight: 700;
          color: #fff;
        }

        .stat-label {
          font-size: 11px;
          color: #64748b;
          text-transform: uppercase;
          margin-top: 4px;
        }

        .signals-list {
          max-height: 200px;
          overflow-y: auto;
        }

        .signal-item {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px;
          margin-bottom: 8px;
          background: rgba(255, 255, 255, 0.03);
          border-radius: 8px;
          border-left: 3px solid;
        }

        .signal-buy { border-left-color: #10b981; }
        .signal-sell { border-left-color: #ef4444; }

        .signal-type {
          font-size: 11px;
          padding: 2px 8px;
          border-radius: 4px;
          font-weight: 600;
          text-transform: uppercase;
        }

        .absorption { background: #7c3aed33; color: #a78bfa; }
        .exhaustion { background: #f59e0b33; color: #fbbf24; }
        .imbalance { background: #3b82f633; color: #60a5fa; }
        .sweep { background: #ec489933; color: #f472b6; }

        .confidence-high { color: #10b981; }
        .confidence-medium { color: #fbbf24; }
        .confidence-low { color: #94a3b8; }

        .metrics-bar {
          display: flex;
          gap: 24px;
          margin-top: 24px;
          padding: 16px;
          background: rgba(255, 255, 255, 0.03);
          border-radius: 8px;
        }

        .metric {
          flex: 1;
          text-align: center;
        }

        .metric-value {
          font-size: 18px;
          font-weight: 700;
        }

        .metric-label {
          font-size: 11px;
          color: #64748b;
        }

        .no-data {
          text-align: center;
          color: #64748b;
          padding: 40px;
        }
      `}</style>

            <div className="header">
                <h2 className="title">📊 Orderflow Analysis - {symbol}</h2>
                <div className="connection-status">
                    <span className="status-dot" />
                    {isConnected ? "Live" : "Disconnected"}
                </div>
            </div>

            <div className="grid">
                {/* Orderbook */}
                <div className="card">
                    <h3 className="card-title">Level 2 Orderbook</h3>
                    {orderbook ? (
                        <div className="orderbook">
                            <div className="orderbook-side">
                                <h4>Bids</h4>
                                {orderbook.bids.slice(0, 5).map((level, i) => (
                                    <div key={i} className="level bid-level">
                                        <span className="price-bid">${level.price.toFixed(2)}</span>
                                        <span className="size">{level.size.toLocaleString()}</span>
                                    </div>
                                ))}
                            </div>
                            <div className="orderbook-side">
                                <h4>Asks</h4>
                                {orderbook.asks.slice(0, 5).map((level, i) => (
                                    <div key={i} className="level ask-level">
                                        <span className="price-ask">${level.price.toFixed(2)}</span>
                                        <span className="size">{level.size.toLocaleString()}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ) : (
                        <div className="no-data">Waiting for data...</div>
                    )}
                </div>

                {/* Quick Stats */}
                <div className="card">
                    <h3 className="card-title">Market Microstructure</h3>
                    <div className="stats-grid">
                        <div className="stat">
                            <div className="stat-value" style={{ color: "#00d4ff" }}>
                                ${spread}
                            </div>
                            <div className="stat-label">Spread</div>
                        </div>
                        <div className="stat">
                            <div className="stat-value" style={{ color: imbalanceRatio > 1 ? "#10b981" : "#ef4444" }}>
                                {imbalanceRatio}
                            </div>
                            <div className="stat-label">Imbalance Ratio</div>
                        </div>
                        <div className="stat">
                            <div className="stat-value" style={{ color: "#10b981" }}>
                                {bidDepth.toLocaleString()}
                            </div>
                            <div className="stat-label">Bid Depth (5 lvls)</div>
                        </div>
                        <div className="stat">
                            <div className="stat-value" style={{ color: "#ef4444" }}>
                                {askDepth.toLocaleString()}
                            </div>
                            <div className="stat-label">Ask Depth (5 lvls)</div>
                        </div>
                    </div>
                </div>

                {/* Signals */}
                <div className="card" style={{ gridColumn: "span 2" }}>
                    <h3 className="card-title">Footprint Signals</h3>
                    {signals.length > 0 ? (
                        <div className="signals-list">
                            {signals.map((signal, i) => (
                                <div
                                    key={i}
                                    className={`signal-item signal-${signal.direction}`}
                                >
                                    <span className={`signal-type ${signal.signal_type}`}>
                                        {signal.signal_type}
                                    </span>
                                    <span className={`confidence-${signal.confidence}`}>
                                        {signal.confidence}
                                    </span>
                                    <span style={{ color: "#94a3b8", fontSize: "12px" }}>
                                        {signal.description}
                                    </span>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="no-data">No signals detected yet...</div>
                    )}
                </div>
            </div>

            {/* Metrics Bar */}
            {metrics && (
                <div className="metrics-bar">
                    <div className="metric">
                        <div className="metric-value">{metrics.total_requests}</div>
                        <div className="metric-label">Total Validations</div>
                    </div>
                    <div className="metric">
                        <div className="metric-value" style={{ color: "#10b981" }}>
                            {metrics.approved}
                        </div>
                        <div className="metric-label">Approved</div>
                    </div>
                    <div className="metric">
                        <div className="metric-value" style={{ color: "#ef4444" }}>
                            {metrics.rejected}
                        </div>
                        <div className="metric-label">Rejected</div>
                    </div>
                    <div className="metric">
                        <div className="metric-value" style={{ color: "#fbbf24" }}>
                            {metrics.total_requests > 0
                                ? ((metrics.approved / metrics.total_requests) * 100).toFixed(1)
                                : 0}
                            %
                        </div>
                        <div className="metric-label">Approval Rate</div>
                    </div>
                </div>
            )}
        </div>
    );
}
