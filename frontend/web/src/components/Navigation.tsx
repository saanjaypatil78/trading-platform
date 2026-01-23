"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
    { href: "/", label: "Home", icon: "🏠" },
    { href: "/signals", label: "Signals", icon: "🎯" },
    { href: "/orderflow", label: "Orderflow", icon: "📊" },
    { href: "/scanner", label: "Scanner", icon: "🔍" },
    { href: "/brain", label: "AI Brain", icon: "🧠" },
    { href: "/backtest", label: "Backtest", icon: "📈" },
];

export default function Navigation() {
    const pathname = usePathname();

    return (
        <nav className="navigation">
            <style jsx>{`
        .navigation {
          display: flex;
          gap: 8px;
          padding: 12px 24px;
          background: rgba(10, 10, 26, 0.95);
          backdrop-filter: blur(10px);
          border-bottom: 1px solid rgba(255, 255, 255, 0.1);
          position: sticky;
          top: 0;
          z-index: 100;
        }

        .nav-link {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 8px 16px;
          border-radius: 8px;
          text-decoration: none;
          color: #94a3b8;
          font-weight: 500;
          font-size: 14px;
          transition: all 0.2s;
        }

        .nav-link:hover {
          background: rgba(124, 58, 237, 0.15);
          color: #a78bfa;
        }

        .nav-link.active {
          background: linear-gradient(135deg, rgba(124, 58, 237, 0.3), rgba(236, 72, 153, 0.2));
          color: #fff;
          border: 1px solid rgba(124, 58, 237, 0.5);
        }

        .logo {
          font-size: 20px;
          font-weight: 800;
          margin-right: 24px;
          background: linear-gradient(90deg, #00d4ff, #7c3aed);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }
      `}</style>

            <span className="logo">⚡ TradePro</span>

            {navItems.map((item) => (
                <Link
                    key={item.href}
                    href={item.href}
                    className={`nav-link ${pathname === item.href ? "active" : ""}`}
                >
                    <span>{item.icon}</span>
                    <span>{item.label}</span>
                </Link>
            ))}
        </nav>
    );
}
