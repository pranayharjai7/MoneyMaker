import type { Metadata } from "next";
import { DashboardShell } from "@/components/layout/DashboardShell";
import "./globals.css";

export const metadata: Metadata = {
  title: "MoneyMaker Quant Control Center",
  description: "Internal operational intelligence for adaptive AI trading",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <DashboardShell>{children}</DashboardShell>
      </body>
    </html>
  );
}
