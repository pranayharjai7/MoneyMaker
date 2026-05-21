from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from statistics import fmean


@dataclass
class MetricsRegistry:
    counters: dict[str, float] = field(default_factory=lambda: defaultdict(float))
    histograms: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))

    def increment(self, name: str, value: float = 1.0) -> None:
        self.counters[name] += value

    def observe(self, name: str, value: float) -> None:
        self.histograms[name].append(float(value))
        if len(self.histograms[name]) > 1000:
            self.histograms[name] = self.histograms[name][-1000:]

    def snapshot(self) -> dict[str, object]:
        histogram_summary = {}
        for name, values in self.histograms.items():
            sorted_values = sorted(values)
            p95_index = max(0, min(len(sorted_values) - 1, int(len(sorted_values) * 0.95) - 1))
            histogram_summary[name] = {
                "count": len(values),
                "avg": fmean(values) if values else 0.0,
                "p95": sorted_values[p95_index] if values else 0.0,
            }
        return {
            "counters": dict(self.counters),
            "histograms": histogram_summary,
        }


metrics_registry = MetricsRegistry()
