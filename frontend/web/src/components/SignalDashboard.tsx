"use client";

import React, { useState, useEffect } from "react";

interface UnifiedSignal {
    symbol: string;
    direction: string;
    strength: string;
    confidence: number;
    sources: string[];
    source_details: Record<string, any>;
    suggested_quantity?: number;
    suggested_entry?: number;
    risk_level: string;
}

interface SignalDashboardProps {
    symbols?: string[];
    aggregatorUrl?: string;
}

export default function SignalDashboard({
    symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"],
    aggregatorUrl = "http://localhost:8011",
}: SignalDashboardProps) {
    const [signals, setSignals] = useState<UnifiedSignal[]>([]);
    const [loading, setLoading] = useState(false);
    const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
    const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

    const fetchSignals = async () => {
        setLoading(true);
        try {
            const resp = await fetch(`${aggregatorUrl}/signals`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    symbols,
                    include_orderflow: true,
                    include_scanner: true,
                }),
            });
            const data = await resp.json();
            setSignals(data.signals || []);
            setLastUpdate(new Date());
        } catch (error) {
            console.error("Failed to fetch signals:", error);
        }
        setLoading(false);
    };

    useEffect(() => {
        fetchSignals();
        const interval = setInterval(fetchSignals, 30000); // Refresh every 30s
        return () => clearInterval(interval);
    }, [symbols.join(",")]);

    const executeSignal = async (symbol: string) => {
        try {
            const resp = await fetch(`${aggregatorUrl}/execute`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ symbol }),
            });
            const result = await resp.json();
            alert(
                result.executed
                    ? `✅ Executed: Order ${result.order_id}`
                    : `❌ Not executed: ${result.reason || result.error}`
            );
        } catch (error) {
            alert(`Error: ${error}`);
        }
    };

    const getStrengthColor = (strength: string) => {
        switch (strength) {
            case "STRONG":
            case "strong":
                return "#10b981";
            case "MODERATE":
            case "moderate":
                return "#f59e0b";
            default:
                return "#6b7280";
        }
    };

    const getDirectionIcon = (direction: string) => {
        if (direction === "buy") return "📈";
        if (direction === "sell") return "📉";
        return "➖";
    };

    return (
        <div className="signal-dashboard">
            <style jsx>{`
        .signal-dashboard {
          font-family: "Inter", -apple-system, sans-serif;
          background: linear-gradient(135deg, #0a0a1a 0%, #1a1a3e 100%);
          color: #fff;
          padding: 24px;
          border-radius: 16px;
          min-height: 700px;
        }

        .header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 24px;
        }

        .title {
          font-size: 28px;
          font-weight: 800;
          background: linear-gradient(90deg, #00d4ff, #7c3aed, #ec4899);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }

        .refresh-btn {
          background: rgba(124, 58, 237, 0.2);
          border: 1px solid #7c3aed;
          color: #a78bfa;
          padding: 10px 20px;
          border-radius: 8px;
          cursor: pointer;
          font-weight: 600;
          transition: all 0.3s;
        }

        .refresh-btn:hover {
          background: rgba(124, 58, 237, 0.4);
        }

        .refresh-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .signals-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
          gap: 20px;
          margin-bottom: 24px;
        }

        .signal-card {
          background: rgba(255, 255, 255, 0.05);
          backdrop-filter: blur(10px);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 16px;
          padding: 20px;
          cursor: pointer;
          transition: all 0.3s;
        }

        .signal-card:hover {
          transform: translateY(-4px);
          border-color: rgba(124, 58, 237, 0.5);
          box-shadow: 0 10px 40px rgba(124, 58, 237, 0.2);
        }

        .signal-card.selected {
          border-color: #7c3aed;
          box-shadow: 0 0 20px rgba(124, 58, 237, 0.3);
        }

        .card-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
        }

        .symbol {
          font-size: 20px;
          font-weight: 700;
        }

        .direction-badge {
          font-size: 24px;
        }

        .strength-bar {
          height: 6px;
          background: rgba(255, 255, 255, 0.1);
          border-radius: 3px;
          margin-bottom: 16px;
          overflow: hidden;
        }

        .strength-fill {
          height: 100%;
          border-radius: 3px;
          transition: width 0.5s;
        }

        .metrics {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 12px;
        }

        .metric {
          text-align: center;
          padding: 8px;
          background: rgba(255, 255, 255, 0.03);
          border-radius: 8px;
        }

        .metric-value {
          font-size: 16px;
          font-weight: 700;
          color: #fff;
        }

        .metric-label {
          font-size: 10px;
          color: #64748b;
          text-transform: uppercase;
        }

        .sources {
          display: flex;
          gap: 6px;
          margin-top: 12px;
        }

        .source-tag {
          font-size: 10px;
          padding: 2px 8px;
          border-radius: 4px;
          background: rgba(255, 255, 255, 0.1);
          color: #94a3b8;
        }

        .source-tag.orderflow {
          background: rgba(16, 185, 129, 0.2);
          color: #10b981;
        }

        .source-tag.scanner {
          background: rgba(59, 130, 246, 0.2);
          color: #60a5fa;
        }

        .source-tag.brain {
          background: rgba(168, 85, 247, 0.2);
          color: #c084fc;
        }

        .detail-panel {
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 16px;
          padding: 24px;
          margin-top: 24px;
        }

        .detail-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 20px;
        }

        .execute-btn {
          background: linear-gradient(135deg, #10b981, #059669);
          border: none;
          color: white;
          padding: 12px 24px;
          border-radius: 8px;
          font-weight: 700;
          cursor: pointer;
          transition: all 0.3s;
        }

        .execute-btn:hover {
          transform: scale(1.05);
          box-shadow: 0 5px 20px rgba(16, 185, 129, 0.4);
        }

        .execute-btn.sell {
          background: linear-gradient(135deg, #ef4444, #dc2626);
        }

        .execute-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .source-detail {
          background: rgba(0, 0, 0, 0.2);
          padding: 16px;
          border-radius: 8px;
          margin-bottom: 12px;
        }

        .source-detail h4 {
          font-size: 14px;
          color: #94a3b8;
          margin-bottom: 8px;
        }

        .detail-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 12px;
        }

        .last-update {
          font-size: 12px;
          color: #64748b;
          text-align: right;
        }

        .no-signals {
          text-align: center;
          color: #64748b;
          padding: 60px;
        }
      `}</style>

            <div className="header">
                <h1 className="title">🎯 Unified Signal Dashboard</h1>
                <div>
                    <button
                        className="refresh-btn"
                        onClick={fetchSignals}
                        disabled={loading}
                    >
                        {loading ? "⏳ Loading..." : "🔄 Refresh"}
                    </button>
                    {lastUpdate && (
                        <span className="last-update" style={{ marginLeft: 12 }}>
                            Updated: {lastUpdate.toLocaleTimeString()}
                        </span>
                    )}
                </div>
            </div>

            {signals.length === 0 ? (
                <div className="no-signals">
                    <p>No signals available. Make sure services are running.</p>
                </div>
            ) : (
                <>
                    <div className="signals-grid">
                        {signals.map((signal, idx) => (
                            <div
                                key={idx}
                                className={`signal-card ${selectedSymbol === signal.symbol ? "selected" : ""
                                    }`}
                                onClick={() => setSelectedSymbol(signal.symbol)}
                            >
                                <div className="card-header">
                                    <span className="symbol">{signal.symbol}</span>
                                    <span className="direction-badge">
                                        {getDirectionIcon(signal.direction)}
                                    </span>
                                </div>

                                <div className="strength-bar">
                                    <div
                                        className="strength-fill"
                                        style={{
                                            width: `${signal.confidence * 100}%`,
                                            background: getStrengthColor(signal.strength),
                                        }}
                                    />
                                </div>

                                <div className="metrics">
                                    <div className="metric">
                                        <div
                                            className="metric-value"
                                            style={{ color: getStrengthColor(signal.strength) }}
                                        >
                                            {signal.strength}
                                        </div>
                                        <div className="metric-label">Strength</div>
                                    </div>
                                    <div className="metric">
                                        <div className="metric-value">
                                            {(signal.confidence * 100).toFixed(0)}%
                                        </div>
                                        <div className="metric-label">Confidence</div>
                                    </div>
                                    <div className="metric">
                                        <div
                                            className="metric-value"
                                            style={{
                                                color:
                                                    signal.direction === "buy" ? "#10b981" : "#ef4444",
                                            }}
                                        >
                                            {signal.direction.toUpperCase()}
                                        </div>
                                        <div className="metric-label">Direction</div>
                                    </div>
                                    <div className="metric">
                                        <div className="metric-value">{signal.risk_level}</div>
                                        <div className="metric-label">Risk</div>
                                    </div>
                                </div>

                                <div className="sources">
                                    {signal.sources.map((src, i) => (
                                        <span key={i} className={`source-tag ${src}`}>
                                            {src}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>

                    {selectedSymbol && (
                        <div className="detail-panel">
                            <div className="detail-header">
                                <h2>
                                    📊 {selectedSymbol} - Detailed Analysis
                                </h2>
                                <button
                                    className={`execute-btn ${signals.find((s) => s.symbol === selectedSymbol)
                                            ?.direction === "sell"
                                            ? "sell"
                                            : ""
                                        }`}
                                    onClick={() => executeSignal(selectedSymbol)}
                                    disabled={
                                        signals.find((s) => s.symbol === selectedSymbol)
                                            ?.strength === "weak"
                                    }
                                >
                                    Execute{" "}
                                    {signals
                                        .find((s) => s.symbol === selectedSymbol)
                                        ?.direction.toUpperCase()}
                                </button>
                            </div>

                            {(() => {
                                const sig = signals.find((s) => s.symbol === selectedSymbol);
                                if (!sig) return null;

                                return (
                                    <>
                                        {sig.source_details.orderflow && (
                                            <div className="source-detail">
                                                <h4>📊 Orderflow Analysis</h4>
                                                <div className="detail-grid">
                                                    <div className="metric">
                                                        <div className="metric-value">
                                                            {sig.source_details.orderflow.imbalance_ratio?.toFixed(
                                                                2
                                                            ) || "N/A"}
                                                        </div>
                                                        <div className="metric-label">Imbalance Ratio</div>
                                                    </div>
                                                    <div className="metric">
                                                        <div className="metric-value">
                                                            {sig.source_details.orderflow.bid_depth?.toLocaleString() ||
                                                                "N/A"}
                                                        </div>
                                                        <div className="metric-label">Bid Depth</div>
                                                    </div>
                                                    <div className="metric">
                                                        <div className="metric-value">
                                                            {sig.source_details.orderflow.ask_depth?.toLocaleString() ||
                                                                "N/A"}
                                                        </div>
                                                        <div className="metric-label">Ask Depth</div>
                                                    </div>
                                                </div>
                                            </div>
                                        )}

                                        {sig.source_details.scanner && (
                                            <div className="source-detail">
                                                <h4>📈 Technical Analysis</h4>
                                                <div className="detail-grid">
                                                    <div className="metric">
                                                        <div className="metric-value">
                                                            {sig.source_details.scanner.rsi?.toFixed(1) ||
                                                                "N/A"}
                                                        </div>
                                                        <div className="metric-label">RSI</div>
                                                    </div>
                                                    <div className="metric">
                                                        <div className="metric-value">
                                                            $
                                                            {sig.source_details.scanner.price?.toFixed(2) ||
                                                                "N/A"}
                                                        </div>
                                                        <div className="metric-label">Price</div>
                                                    </div>
                                                    <div className="metric">
                                                        <div className="metric-value">
                                                            $
                                                            {sig.source_details.scanner.sma_20?.toFixed(2) ||
                                                                "N/A"}
                                                        </div>
                                                        <div className="metric-label">SMA 20</div>
                                                    </div>
                                                </div>
                                            </div>
                                        )}

                                        {sig.source_details.brain && (
                                            <div className="source-detail">
                                                <h4>🧠 AI Brain Analysis</h4>
                                                <div className="detail-grid">
                                                    <div className="metric">
                                                        <div className="metric-value">
                                                            {sig.source_details.brain.entry_decision || "N/A"}
                                                        </div>
                                                        <div className="metric-label">Decision</div>
                                                    </div>
                                                    <div className="metric">
                                                        <div className="metric-value">
                                                            {sig.source_details.brain.entry_confidence?.toFixed(
                                                                0
                                                            ) || "N/A"}
                                                            %
                                                        </div>
                                                        <div className="metric-label">AI Confidence</div>
                                                    </div>
                                                    <div className="metric">
                                                        <div className="metric-value">
                                                            {sig.source_details.brain.position_size || "N/A"}
                                                        </div>
                                                        <div className="metric-label">Position Size</div>
                                                    </div>
                                                </div>
                                            </div>
                                        )}
                                    </>
                                );
                            })()}
                        </div>
                    )}
                </>
            )}
        </div>
    );
}
