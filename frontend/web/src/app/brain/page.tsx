import { AIReasoningDashboard } from "@/components/AIReasoningDashboard";

export default function BrainPage() {
    return (
        <main className="min-h-screen bg-gray-50 dark:bg-zinc-950 p-8">
            <div className="max-w-6xl mx-auto">
                <AIReasoningDashboard />
            </div>
        </main>
    );
}
