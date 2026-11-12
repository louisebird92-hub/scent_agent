import { useGetScentDnaSuspense, type ScentDnaOut } from "@/lib/api";
import selector from "@/lib/selector";

export function ScentDna() {
  const { data } = useGetScentDnaSuspense(selector<ScentDnaOut | null>());
  if (!data) {
    return (
      <section className="space-y-3">
        <h2 className="font-display text-4xl font-light">Your scent DNA</h2>
        <p className="text-muted-foreground max-w-[52ch]">
          Nothing owned yet. Add a few bottles below and your profile appears here.
        </p>
      </section>
    );
  }
  const entries = Object.entries(data.profile);
  const max = Math.max(...entries.map(([, v]) => v), 1);
  return (
    <section className="space-y-10">
      <div className="space-y-2">
        <h2 className="font-display text-4xl font-light tracking-tight">Your scent DNA</h2>
        <p className="label">Read from {data.based_on}</p>
      </div>

      <ol className="space-y-3" aria-label="Accord profile">
        {entries.map(([accord, pct], i) => (
          <li key={accord} className="grid grid-cols-[7rem_1fr_2.5rem] items-center gap-4">
            <span className="label text-foreground">{accord}</span>
            <span className="h-2 bg-secondary" aria-hidden>
              <span
                className="block h-full bg-foreground origin-left reveal"
                style={{ width: `${(pct / max) * 100}%`, animationDelay: `${i * 60}ms` }}
              />
            </span>
            <span className="text-right text-sm tabular-nums text-muted-foreground">{pct}%</span>
          </li>
        ))}
      </ol>

      <div className="grid grid-cols-2 gap-8 border-t pt-6">
        <div className="space-y-3">
          <p className="label">You tend to like</p>
          <ul className="font-display text-2xl leading-snug">
            {data.you_tend_to_like.map((n) => (
              <li key={n}>{n}</li>
            ))}
          </ul>
        </div>
        <div className="space-y-3">
          <p className="label">Missing from your shelf</p>
          <ul className="font-display text-2xl leading-snug italic text-muted-foreground">
            {data.family_gaps.slice(0, 5).map((f) => (
              <li key={f}>{f}</li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
