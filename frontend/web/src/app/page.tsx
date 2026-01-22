export default function Home() {
    return (
        <main className="flex min-h-screen flex-col items-center justify-between p-24 bg-gray-950 text-white">
            <div className="z-10 max-w-5xl w-full items-center justify-between font-mono text-sm lg:flex">
                <p className="fixed left-0 top-0 flex w-full justify-center border-b border-gray-300 bg-gradient-to-b from-zinc-200 pb-6 pt-8 backdrop-blur-2xl dark:border-neutral-800 dark:bg-zinc-800/30 dark:from-inherit lg:static lg:w-auto lg:rounded-xl lg:border lg:bg-gray-200 lg:p-4 lg:dark:bg-zinc-800/30">
                    Trading Platform
                </p>
            </div>

            <div className="relative flex place-items-center before:absolute before:h-[300px] before:w-full sm:before:w-[480px] before:-translate-x-1/2 before:rounded-full before:bg-gradient-to-br before:from-transparent before:to-blue-700 before:opacity-10 before:blur-2xl after:absolute after:-z-20 after:h-[180px] after:w-full sm:after:w-[240px] after:translate-x-1/3 after:bg-gradient-to-tr after:from-emerald-900 after:to-teal-700 after:opacity-40 after:blur-2xl after:content-[''] z-[-1]">
                <h1 className="text-6xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-emerald-400">
                    Advanced<br />Algorithmic<br />Trading
                </h1>
            </div>

            <div className="mb-32 grid text-center lg:max-w-5xl lg:w-full lg:mb-0 lg:grid-cols-3 lg:text-left gap-4">
                {/* Scanner */}
                <a
                    href="/scanner"
                    className="group rounded-lg border border-transparent px-5 py-4 transition-colors hover:border-blue-500 hover:bg-blue-900/20"
                >
                    <h2 className="mb-3 text-2xl font-semibold text-blue-400">
                        Scanner{" "}
                        <span className="inline-block transition-transform group-hover:translate-x-1">
                            -&gt;
                        </span>
                    </h2>
                    <p className="m-0 max-w-[30ch] text-sm opacity-50">
                        Build custom screeners like Chartink with RSI, MACD, SMA conditions.
                    </p>
                </a>

                {/* Orders */}
                <a
                    href="/orders"
                    className="group rounded-lg border border-transparent px-5 py-4 transition-colors hover:border-green-500 hover:bg-green-900/20"
                >
                    <h2 className="mb-3 text-2xl font-semibold text-green-400">
                        Orders{" "}
                        <span className="inline-block transition-transform group-hover:translate-x-1">
                            -&gt;
                        </span>
                    </h2>
                    <p className="m-0 max-w-[30ch] text-sm opacity-50">
                        Place trades, manage positions, and track P&L in real-time.
                    </p>
                </a>

                {/* AI Brain */}
                <a
                    href="/brain"
                    className="group rounded-lg border border-transparent px-5 py-4 transition-colors hover:border-purple-500 hover:bg-purple-900/20"
                >
                    <h2 className="mb-3 text-2xl font-semibold text-purple-400">
                        AI Brain{" "}
                        <span className="inline-block transition-transform group-hover:translate-x-1">
                            -&gt;
                        </span>
                    </h2>
                    <p className="m-0 max-w-[30ch] text-sm opacity-50">
                        Chain-of-thought reasoning for explainable trade decisions.
                    </p>
                </a>

                {/* Backtest */}
                <a
                    href="/backtest"
                    className="group rounded-lg border border-transparent px-5 py-4 transition-colors hover:border-orange-500 hover:bg-orange-900/20"
                >
                    <h2 className="mb-3 text-2xl font-semibold text-orange-400">
                        Backtest{" "}
                        <span className="inline-block transition-transform group-hover:translate-x-1">
                            -&gt;
                        </span>
                    </h2>
                    <p className="m-0 max-w-[30ch] text-sm opacity-50">
                        Test strategies with historical data using VectorBT and Backtrader.
                    </p>
                </a>

                {/* DeFi */}
                <a
                    href="/defi"
                    className="group rounded-lg border border-transparent px-5 py-4 transition-colors hover:border-teal-500 hover:bg-teal-900/20"
                >
                    <h2 className="mb-3 text-2xl font-semibold text-teal-400">
                        DeFi & Earn{" "}
                        <span className="inline-block transition-transform group-hover:translate-x-1">
                            -&gt;
                        </span>
                    </h2>
                    <p className="m-0 max-w-[30ch] text-sm opacity-50">
                        Stake assets, auto-compound rewards, and referral bonuses.
                    </p>
                </a>

                {/* Webhook */}
                <a
                    href="/webhook"
                    className="group rounded-lg border border-transparent px-5 py-4 transition-colors hover:border-yellow-500 hover:bg-yellow-900/20"
                >
                    <h2 className="mb-3 text-2xl font-semibold text-yellow-400">
                        Webhooks{" "}
                        <span className="inline-block transition-transform group-hover:translate-x-1">
                            -&gt;
                        </span>
                    </h2>
                    <p className="m-0 max-w-[30ch] text-sm opacity-50">
                        Connect TradingView alerts and external signals to auto-trade.
                    </p>
                </a>
            </div>
        </main>
    );
}
