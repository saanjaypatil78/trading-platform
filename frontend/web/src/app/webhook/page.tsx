"use client";

import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Webhook, Play, CheckCircle, AlertTriangle, Link as LinkIcon } from 'lucide-react';

export default function WebhookPage() {
    const [webhookUrl, setWebhookUrl] = useState(
        process.env.NEXT_PUBLIC_API_URL
            ? `${process.env.NEXT_PUBLIC_API_URL}/api/v1/webhook`
            : 'https://your-backend-host/api/v1/webhook'
    );

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Webhooks</h1>
                <p className="text-muted-foreground">Connect external signal providers like TradingView to automate your trades.</p>
            </div>

            <div className="grid gap-6 md:grid-cols-2">
                {/* Configuration Card */}
                <Card className="md:col-span-2">
                    <CardHeader>
                        <div className="flex items-center gap-2">
                            <LinkIcon className="h-5 w-5 text-purple-500" />
                            <CardTitle>Webhook URL Configuration</CardTitle>
                        </div>
                        <CardDescription>Paste this URL into your TradingView Alert settings</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="flex gap-2">
                            <div className="flex-1 p-3 bg-secondary/50 rounded-md font-mono text-sm break-all border">
                                {webhookUrl}
                            </div>
                            <Button variant="outline" onClick={() => navigator.clipboard.writeText(webhookUrl)}>
                                Copy
                            </Button>
                        </div>
                        <div className="p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-lg flex gap-3 text-sm text-yellow-500">
                            <AlertTriangle className="h-5 w-5 shrink-0" />
                            <p>
                                Ensure you send the payload in <strong>JSON format</strong>. Supported fields:
                                <code className="mx-1 bg-black/20 rounded px-1">symbol</code>,
                                <code className="mx-1 bg-black/20 rounded px-1">action</code> (BUY/SELL),
                                <code className="mx-1 bg-black/20 rounded px-1">price</code>.
                            </p>
                        </div>
                    </CardContent>
                </Card>

                {/* Recent Events */}
                <Card className="md:col-span-2">
                    <CardHeader>
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                <Webhook className="h-5 w-5 text-blue-500" />
                                <CardTitle>Recent Events</CardTitle>
                            </div>
                            <Badge variant="outline" className="bg-green-500/10 text-green-500 border-green-500/20">
                                System Online
                            </Badge>
                        </div>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-4">
                            <div className="flex items-center justify-between p-4 border rounded-lg bg-card hover:bg-accent/50 transition-colors">
                                <div className="flex items-center gap-3">
                                    <div className="h-8 w-8 rounded-full bg-green-500/20 flex items-center justify-center">
                                        <CheckCircle className="h-4 w-4 text-green-500" />
                                    </div>
                                    <div>
                                        <p className="font-medium">TradingView Alert: RELIANCE</p>
                                        <p className="text-xs text-muted-foreground">Received 2 mins ago</p>
                                    </div>
                                </div>
                                <div className="text-right">
                                    <Badge>Processed</Badge>
                                </div>
                            </div>

                            <div className="flex items-center justify-between p-4 border rounded-lg bg-card hover:bg-accent/50 transition-colors">
                                <div className="flex items-center gap-3">
                                    <div className="h-8 w-8 rounded-full bg-blue-500/20 flex items-center justify-center">
                                        <Play className="h-4 w-4 text-blue-500" />
                                    </div>
                                    <div>
                                        <p className="font-medium">System Health Check</p>
                                        <p className="text-xs text-muted-foreground">Auto-run 1 hour ago</p>
                                    </div>
                                </div>
                                <div className="text-right">
                                    <Badge variant="secondary">Info</Badge>
                                </div>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
