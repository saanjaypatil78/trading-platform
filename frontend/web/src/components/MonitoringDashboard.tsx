"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import {
    Activity, Clock, AlertTriangle, TrendingUp,
    Zap, Server, BarChart2, CheckCircle, XCircle
} from 'lucide-react';

interface LatencyStats {
    avg_ms: number;
    p50_ms: number;
    p95_ms: number;
    p99_ms: number;
    count: number;
}

interface TrafficOverview {
    total_requests: number;
    last_hour: number;
    last_24h: number;
    error_count: number;
    avg_latency_ms: number;
}

interface EndpointStat {
    endpoint: string;
    requests: number;
    errors: number;
    error_rate: string;
    avg_latency_ms: number;
}

export function MonitoringDashboard() {
    const [latencyStats, setLatencyStats] = useState<LatencyStats | null>(null);
    const [trafficOverview, setTrafficOverview] = useState<TrafficOverview | null>(null);
    const [endpointStats, setEndpointStats] = useState<EndpointStat[]>([]);
    const [systemStatus, setSystemStatus] = useState<'healthy' | 'degraded' | 'down'>('healthy');

    // Mock data for demonstration
    useEffect(() => {
        setLatencyStats({
            avg_ms: 18.5,
            p50_ms: 15.0,
            p95_ms: 45.0,
            p99_ms: 120.0,
            count: 15420
        });

        setTrafficOverview({
            total_requests: 15420,
            last_hour: 542,
            last_24h: 12850,
            error_count: 23,
            avg_latency_ms: 18.5
        });

        setEndpointStats([
            { endpoint: "POST /api/v1/orders/place", requests: 4520, errors: 12, error_rate: "0.3%", avg_latency_ms: 25.4 },
            { endpoint: "GET /api/v1/positions", requests: 3840, errors: 2, error_rate: "0.1%", avg_latency_ms: 8.2 },
            { endpoint: "POST /api/v1/scanner/scan", requests: 2100, errors: 5, error_rate: "0.2%", avg_latency_ms: 145.3 },
            { endpoint: "GET /api/v1/quote/{symbol}", requests: 5200, errors: 4, error_rate: "0.1%", avg_latency_ms: 5.1 },
        ]);
    }, []);

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'healthy': return 'text-green-500';
            case 'degraded': return 'text-yellow-500';
            case 'down': return 'text-red-500';
            default: return 'text-gray-500';
        }
    };

    const getLatencyColor = (ms: number) => {
        if (ms < 20) return 'text-green-500';
        if (ms < 50) return 'text-yellow-500';
        return 'text-red-500';
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <Activity className="h-8 w-8 text-blue-500" />
                    <div>
                        <h2 className="text-2xl font-bold">System Monitor</h2>
                        <p className="text-sm text-muted-foreground">Real-time platform health and performance</p>
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <div className={`h-3 w-3 rounded-full ${systemStatus === 'healthy' ? 'bg-green-500' : systemStatus === 'degraded' ? 'bg-yellow-500' : 'bg-red-500'} animate-pulse`} />
                    <span className={`font-medium ${getStatusColor(systemStatus)}`}>
                        {systemStatus === 'healthy' ? 'All Systems Operational' :
                            systemStatus === 'degraded' ? 'Degraded Performance' : 'System Down'}
                    </span>
                </div>
            </div>

            {/* Overview Cards */}
            <div className="grid gap-4 md:grid-cols-5">
                <Card>
                    <CardContent className="pt-4">
                        <div className="flex items-center gap-2">
                            <Zap className="h-5 w-5 text-yellow-500" />
                            <div>
                                <p className="text-xs text-muted-foreground">Avg Latency</p>
                                <p className={`text-xl font-bold ${getLatencyColor(latencyStats?.avg_ms || 0)}`}>
                                    {latencyStats?.avg_ms?.toFixed(1)}ms
                                </p>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardContent className="pt-4">
                        <div className="flex items-center gap-2">
                            <Clock className="h-5 w-5 text-blue-500" />
                            <div>
                                <p className="text-xs text-muted-foreground">P95 Latency</p>
                                <p className={`text-xl font-bold ${getLatencyColor(latencyStats?.p95_ms || 0)}`}>
                                    {latencyStats?.p95_ms?.toFixed(1)}ms
                                </p>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardContent className="pt-4">
                        <div className="flex items-center gap-2">
                            <BarChart2 className="h-5 w-5 text-purple-500" />
                            <div>
                                <p className="text-xs text-muted-foreground">Requests/hr</p>
                                <p className="text-xl font-bold">{trafficOverview?.last_hour?.toLocaleString()}</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardContent className="pt-4">
                        <div className="flex items-center gap-2">
                            <CheckCircle className="h-5 w-5 text-green-500" />
                            <div>
                                <p className="text-xs text-muted-foreground">Success Rate</p>
                                <p className="text-xl font-bold text-green-600">
                                    {trafficOverview ?
                                        ((1 - trafficOverview.error_count / trafficOverview.total_requests) * 100).toFixed(2)
                                        : 0}%
                                </p>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardContent className="pt-4">
                        <div className="flex items-center gap-2">
                            <AlertTriangle className="h-5 w-5 text-red-500" />
                            <div>
                                <p className="text-xs text-muted-foreground">Errors (24h)</p>
                                <p className="text-xl font-bold text-red-600">{trafficOverview?.error_count}</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Latency Percentiles */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Zap className="h-5 w-5" />
                        Latency Distribution
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="grid grid-cols-4 gap-4">
                        {[
                            { label: 'P50', value: latencyStats?.p50_ms, threshold: 20 },
                            { label: 'P75', value: (latencyStats?.p50_ms || 0) * 1.5, threshold: 30 },
                            { label: 'P95', value: latencyStats?.p95_ms, threshold: 50 },
                            { label: 'P99', value: latencyStats?.p99_ms, threshold: 100 }
                        ].map((p, idx) => (
                            <div key={idx} className="text-center p-4 rounded-lg bg-secondary/50">
                                <p className="text-sm text-muted-foreground">{p.label}</p>
                                <p className={`text-2xl font-bold ${getLatencyColor(p.value || 0)}`}>
                                    {p.value?.toFixed(1)}ms
                                </p>
                                <div className="mt-2 h-2 bg-gray-200 rounded-full overflow-hidden">
                                    <div
                                        className={`h-full ${(p.value || 0) < p.threshold ? 'bg-green-500' : 'bg-red-500'}`}
                                        style={{ width: `${Math.min((p.value || 0) / p.threshold * 100, 100)}%` }}
                                    />
                                </div>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>

            {/* Endpoint Stats */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Server className="h-5 w-5" />
                        Endpoint Performance
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b">
                                <th className="text-left py-2">Endpoint</th>
                                <th className="text-right py-2">Requests</th>
                                <th className="text-right py-2">Errors</th>
                                <th className="text-right py-2">Error Rate</th>
                                <th className="text-right py-2">Avg Latency</th>
                                <th className="text-center py-2">Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {endpointStats.map((stat, idx) => (
                                <tr key={idx} className="border-b hover:bg-secondary/30">
                                    <td className="py-2 font-mono text-xs">{stat.endpoint}</td>
                                    <td className="text-right py-2">{stat.requests.toLocaleString()}</td>
                                    <td className="text-right py-2 text-red-500">{stat.errors}</td>
                                    <td className="text-right py-2">
                                        <Badge variant={parseFloat(stat.error_rate) < 1 ? 'default' : 'destructive'}>
                                            {stat.error_rate}
                                        </Badge>
                                    </td>
                                    <td className={`text-right py-2 ${getLatencyColor(stat.avg_latency_ms)}`}>
                                        {stat.avg_latency_ms.toFixed(1)}ms
                                    </td>
                                    <td className="text-center py-2">
                                        {parseFloat(stat.error_rate) < 1 ? (
                                            <CheckCircle className="h-4 w-4 text-green-500 inline" />
                                        ) : (
                                            <XCircle className="h-4 w-4 text-red-500 inline" />
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </CardContent>
            </Card>

            {/* Services Status */}
            <Card>
                <CardHeader>
                    <CardTitle>Services Status</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="grid gap-3">
                        {[
                            { name: 'Brain Service', port: 8007, status: 'healthy' },
                            { name: 'Scanner Service', port: 8008, status: 'healthy' },
                            { name: 'Order Service', port: 8009, status: 'healthy' },
                            { name: 'WebSocket Server', port: 8765, status: 'healthy' },
                            { name: 'Market Data Feed', port: 8010, status: 'degraded' }
                        ].map((service, idx) => (
                            <div key={idx} className="flex items-center justify-between p-3 rounded-lg bg-secondary/30">
                                <div className="flex items-center gap-3">
                                    <div className={`h-2 w-2 rounded-full ${service.status === 'healthy' ? 'bg-green-500' :
                                        service.status === 'degraded' ? 'bg-yellow-500' : 'bg-red-500'
                                        }`} />
                                    <span className="font-medium">{service.name}</span>
                                    <span className="text-xs text-muted-foreground">:{service.port}</span>
                                </div>
                                <Badge variant={service.status === 'healthy' ? 'default' : 'secondary'}>
                                    {service.status}
                                </Badge>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
