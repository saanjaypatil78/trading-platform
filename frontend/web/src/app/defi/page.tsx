import { StakingInterface } from "@/components/DeFi/StakingInterface";
import { RewardsInterface } from "@/components/DeFi/RewardsInterface";

export default function DeFiPage() {
    return (
        <main className="min-h-screen bg-gray-50 dark:bg-zinc-950 p-8">
            <div className="max-w-6xl mx-auto space-y-8">
                <div className="flex flex-col gap-2">
                    <h1 className="text-3xl font-bold tracking-tight">DeFi Dashboard</h1>
                    <p className="text-muted-foreground">
                        Manage your assets, stake tokens, and track your passive income.
                    </p>
                </div>

                <section className="space-y-4">
                    <h2 className="text-xl font-semibold">Rewards & Overview</h2>
                    <RewardsInterface />
                </section>

                <section className="space-y-4">
                    <h2 className="text-xl font-semibold">Staking Pools</h2>
                    <StakingInterface />
                </section>

                <section className="space-y-4">
                    <h2 className="text-xl font-semibold">Referral Program</h2>
                    <div className="rounded-xl border bg-card p-6 text-card-foreground shadow">
                        <div className="flex items-center justify-between">
                            <div>
                                <h3 className="font-semibold">Invite Friends</h3>
                                <p className="text-sm text-muted-foreground">Earn up to 40% of trading fees from your referrals.</p>
                            </div>
                            <button className="inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground shadow hover:bg-primary/90 h-9 px-4 py-2">
                                Get Referral Link
                            </button>
                        </div>
                    </div>
                </section>
            </div>
        </main>
    );
}
