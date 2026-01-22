"use client";

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
    LayoutDashboard,
    Search,
    ShoppingCart,
    BrainCircuit,
    History,
    Wallet,
    Webhook,
    Settings,
    Menu
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from './ui/button';
import { TokenBalance } from './TokenBalance';

const navItems = [
    { name: 'Dashboard', href: '/', icon: LayoutDashboard },
    { name: 'Scanner', href: '/scanner', icon: Search },
    { name: 'Orders', href: '/orders', icon: ShoppingCart },
    { name: 'AI Brain', href: '/brain', icon: BrainCircuit },
    { name: 'Backtest', href: '/backtest', icon: History },
    { name: 'DeFi & Earn', href: '/defi', icon: Wallet },
    { name: 'Webhooks', href: '/webhook', icon: Webhook },
];

export function Sidebar() {
    const pathname = usePathname();
    const [isCollapsed, setIsCollapsed] = React.useState(false);

    return (
        <div className={cn(
            "flex flex-col h-screen border-r bg-background transition-all duration-300",
            isCollapsed ? "w-16" : "w-64"
        )}>
            {/* Header */}
            <div className="flex items-center p-4 border-b h-16 justify-between">
                {!isCollapsed && (
                    <span className="font-bold text-xl bg-gradient-to-r from-blue-500 to-teal-400 bg-clip-text text-transparent">
                        WhaleCode
                    </span>
                )}
                <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setIsCollapsed(!isCollapsed)}
                    className="ml-auto"
                >
                    <Menu className="h-5 w-5" />
                </Button>
            </div>

            {/* Nav Links */}
            <nav className="flex-1 p-2 space-y-1 overflow-y-auto">
                {navItems.map((item) => {
                    const isActive = pathname === item.href;
                    return (
                        <Link key={item.href} href={item.href}>
                            <div className={cn(
                                "flex items-center gap-3 px-3 py-2 rounded-md transition-colors cursor-pointer",
                                isActive
                                    ? "bg-primary/10 text-primary font-medium"
                                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                                isCollapsed && "justify-center px-2"
                            )}>
                                <item.icon className={cn("h-5 w-5", isActive && "text-primary")} />
                                {!isCollapsed && <span>{item.name}</span>}
                            </div>
                        </Link>
                    );
                })}
            </nav>

            {/* Footer / Balance */}
            <div className="p-4 border-t">
                {!isCollapsed ? (
                    <div className="space-y-2">
                        <TokenBalance />
                        <Link href="/settings">
                            <div className="flex items-center gap-3 px-3 py-2 rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground cursor-pointer">
                                <Settings className="h-5 w-5" />
                                <span>Settings</span>
                            </div>
                        </Link>
                    </div>
                ) : (
                    <div className="flex justify-center">
                        <Settings className="h-5 w-5 text-muted-foreground" />
                    </div>
                )}
            </div>
        </div>
    );
}
