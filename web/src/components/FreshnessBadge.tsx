import type { Freshness } from "@/lib/api";

export function FreshnessBadge({ freshness }: { freshness: Freshness }) {
  return (
    <span className={`text-sm fresh-${freshness.level}`}>{freshness.label}</span>
  );
}
