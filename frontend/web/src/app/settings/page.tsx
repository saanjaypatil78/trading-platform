"use client";

import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Save, Key, Globe, Shield, Bell } from 'lucide-react';

export default function SettingsPage() {
    const [apiKey, setApiKey] = useState('**********************');

    return (
        <div className="space-y-6 max-w-4xl mx-auto">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
                <p className="text-muted-foreground">Manage your API keys, preferences, and account security.</p>
            </div>

            <div className="grid gap-6">
                {/* API Configuration */}
                <Card>
                    <CardHeader>
                        <div className="flex items-center gap-2">
                            <Key className="h-5 w-5 text-blue-500" />
                            <CardTitle>Broker & API Configuration</CardTitle>
                        </div>
                        <CardDescription>Connect your brokerage accounts (Upstox, Zerodha, Alpaca)</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="grid gap-4 md:grid-cols-2">
                            <div className="space-y-2">
                                <label className="text-sm font-medium">Upstox API Key</label>
                                <input
                                    type="password"
                                    className="w-full p-2 rounded-md border bg-background"
                                    value={apiKey}
                                    readOnly
                                />
                            </div>
                            <div className="space-y-2">
                                <label className="text-sm font-medium">Upstox API Secret</label>
                                <input
                                    type="password"
                                    className="w-full p-2 rounded-md border bg-background"
                                    value={apiKey}
                                    readOnly
                                />
                            </div>
                        </div>
                        <div className="flex justify-end">
                            <Button>
                                <Save className="h-4 w-4 mr-2" />
                                Save Credentials
                            </Button>
                        </div>
                    </CardContent>
                </Card>

                {/* General Preferences */}
                <Card>
                    <CardHeader>
                        <div className="flex items-center gap-2">
                            <Globe className="h-5 w-5 text-green-500" />
                            <CardTitle>Platform Preferences</CardTitle>
                        </div>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="flex items-center justify-between p-3 border rounded-lg">
                            <div className="space-y-0.5">
                                <label className="text-base font-medium">Dark Mode</label>
                                <p className="text-sm text-muted-foreground">Enable dark theme for the dashboard</p>
                            </div>
                            <Badge variant="outline" className="bg-green-500/10 text-green-500 border-green-500/20">Enabled</Badge>
                        </div>
                        <div className="flex items-center justify-between p-3 border rounded-lg">
                            <div className="space-y-0.5">
                                <label className="text-base font-medium">Notifications</label>
                                <p className="text-sm text-muted-foreground">Receive browser alerts for trade signals</p>
                            </div>
                            <Badge variant="outline" className="bg-green-500/10 text-green-500 border-green-500/20">Active</Badge>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
