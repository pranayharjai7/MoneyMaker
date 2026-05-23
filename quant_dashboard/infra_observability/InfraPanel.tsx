"use client";

import { Card } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/StatusBadge";

export function InfraPanel({ data }: { data: Record<string, unknown> | null }) {
  const cards = (data?.health_cards as { component: string; status: string }[]) ?? [];

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {cards.map((card) => (
        <Card key={card.component} title={card.component}>
          <StatusBadge status={card.status} />
        </Card>
      ))}
    </div>
  );
}
