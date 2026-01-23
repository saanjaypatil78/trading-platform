import SignalDashboard from "@/components/SignalDashboard";

export const metadata = {
    title: "Signal Dashboard | Trading Platform",
    description: "Unified trading signals from orderflow, scanner, and AI analysis",
};

export default function SignalsPage() {
    return (
        <main className="min-h-screen bg-gray-950 p-6">
            <div className="max-w-7xl mx-auto">
                <SignalDashboard
                    symbols={["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META"]}
                />
            </div>
        </main>
    );
}
