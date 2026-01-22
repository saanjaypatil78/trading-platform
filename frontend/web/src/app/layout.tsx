import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
    title: "Trading Platform",
    description: "Advanced Algorithmic Trading",
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en" className="dark">
            <body className={inter.className}>
                <div className="flex h-screen overflow-hidden bg-background text-foreground">
                    <Sidebar />
                    <main className="flex-1 overflow-y-auto bg-slate-50/50 dark:bg-slate-950/50 p-6">
                        {children}
                    </main>
                </div>
            </body>
        </html>
    );
}
