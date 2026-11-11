import type { UsageItem } from "@/lib/types";

export function UsageBadge({ item, noun }: { item: UsageItem | undefined; noun: string }) {
  if (!item) return null;
  const out = item.remaining === 0;
  return (
    <span className={`chip ${out ? "bg-bad-soft text-bad" : ""}`} title={`Resets ${new Date(item.resets_at).toLocaleString()}`}>
      {out ? `No ${noun} left today` : `${item.remaining} of ${item.limit} ${noun} left today`}
    </span>
  );
}
