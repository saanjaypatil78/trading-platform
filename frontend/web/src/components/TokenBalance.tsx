
import React, { useEffect, useState } from 'react';
import { Coins } from 'lucide-react';
import { fetchWithFailover } from '../lib/api';

export function TokenBalance() {
    const [balance, setBalance] = useState<number | null>(null);

    useEffect(() => {
        const loadBalance = async () => {
            try {
                const res = await fetchWithFailover('/auth/credits/balance');
                if (res.ok) {
                    const data = await res.json();
                    setBalance(data.balance);
                }
            } catch (err) {
                console.error("Failed to load token balance", err);
            }
        };
        loadBalance();

        // Refresh every 10 seconds to show updates after actions
        const interval = setInterval(loadBalance, 10000);
        return () => clearInterval(interval);
    }, []);

    if (balance === null) return null;

    return (
        <div className="flex items-center gap-2 bg-yellow-50 dark:bg-yellow-900/20 px-3 py-1.5 rounded-full border border-yellow-200 dark:border-yellow-800">
            <Coins className="h-4 w-4 text-yellow-600 dark:text-yellow-400" />
            <span className="font-mono font-bold text-sm text-yellow-700 dark:text-yellow-400">
                {balance.toFixed(2)} FACT
            </span>
        </div>
    );
}
