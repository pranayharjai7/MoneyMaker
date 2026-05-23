"use client";

import type { ReactNode } from "react";
import { ResponsiveContainer } from "recharts";

export function ChartFrame({ children, height = 260 }: { children: ReactNode; height?: number }) {
  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer>{children}</ResponsiveContainer>
    </div>
  );
}
