import OrderflowDashboard from "@/components/OrderflowDashboard";

export const metadata = {
    title: "Orderflow Analysis | Trading Platform",
    description: "Real-time Level 2 market depth and footprint pattern detection",
};

export default function OrderflowPage() {
    return (
        <main className="min-h-screen bg-gray-950 p-6">
            <div className="max-w-7xl mx-auto">
                <OrderflowDashboard symbol="AAPL" />
            </div>
        </main>
    );
}
