import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Star, Upload, X } from "lucide-react";
import { toast } from "sonner";
import {
  useGetCollectionSuspense,
  useLookupFragrances,
  usePreviewImport,
  useRemoveFromCollection,
  useSaveToCollection,
  useUpdateCollectionItem,
  type CollectionOut,
  type Fragrance,
  type ImportPreviewOut,
} from "@/lib/api";
import selector from "@/lib/selector";
import { cn } from "@/lib/utils";
import { ImportCard } from "./import-card";
import { refreshWardrobe } from "./refresh";

const STATUSES = ["owned", "wishlist", "sampled"] as const;
type Status = (typeof STATUSES)[number];

export function Wardrobe() {
  const { data } = useGetCollectionSuspense(selector<CollectionOut>());
  const [tab, setTab] = useState<Status>("owned");
  const items = data.items.filter((i) => i.my_status === tab);

  return (
    <section className="space-y-6">
      <div className="flex items-end justify-between gap-4">
        <h2 className="font-display text-4xl font-light tracking-tight">Wardrobe</h2>
        <div role="tablist" aria-label="Collection status" className="flex gap-5">
          {STATUSES.map((s) => (
            <button
              key={s}
              role="tab"
              aria-selected={tab === s}
              onClick={() => setTab(s)}
              className={cn(
                "label pb-1 border-b transition-colors",
                tab === s ? "!text-foreground border-foreground" : "border-transparent hover:!text-foreground",
              )}
            >
              {s} <span className="tabular-nums">{data.items.filter((i) => i.my_status === s).length}</span>
            </button>
          ))}
        </div>
      </div>

      {items.length === 0 ? (
        <p className="text-muted-foreground py-6">Nothing {tab} yet. Add some above.</p>
      ) : (
        <ul className="divide-y border-y">
          {items.map((f) => (
            <WardrobeRow key={f.id} f={f} />
          ))}
        </ul>
      )}
    </section>
  );
}

function WardrobeRow({ f }: { f: Fragrance }) {
  const queryClient = useQueryClient();
  const onSuccess = () => refreshWardrobe(queryClient);
  const onError = (e: Error) => toast.error(`Couldn't update ${f.name}: ${e.message}`);
  const update = useUpdateCollectionItem({ mutation: { onSuccess, onError } });
  const remove = useRemoveFromCollection({ mutation: { onSuccess, onError } });
  const id = f.id ?? 0;

  return (
    <li className="py-4 grid grid-cols-[1fr_auto] gap-x-6 gap-y-2 items-center">
      <div className="min-w-0">
        <p className="font-display text-2xl leading-tight truncate">{f.name}</p>
        <p className="label mt-1">
          {f.house} · {f.family}
          {f.times_worn ? ` · worn ${f.times_worn}×, last ${f.last_worn}` : ""}
        </p>
      </div>
      <div className="flex items-center gap-4">
        <div className="flex" role="radiogroup" aria-label={`Rate ${f.name}`}>
          {[1, 2, 3, 4, 5].map((n) => (
            <button
              key={n}
              role="radio"
              aria-checked={f.my_rating === n}
              aria-label={`${n} of 5`}
              onClick={() => update.mutate({ params: { fragrance_id: id }, data: { rating: n } })}
              className="p-0.5 text-muted-foreground hover:text-foreground"
            >
              <Star
                className="size-3.5"
                strokeWidth={1.25}
                fill={(f.my_rating ?? 0) >= n ? "currentColor" : "none"}
                color={(f.my_rating ?? 0) >= n ? "var(--foreground)" : "currentColor"}
              />
            </button>
          ))}
        </div>
        <select
          aria-label={`Status of ${f.name}`}
          value={f.my_status ?? "owned"}
          onChange={(e) => update.mutate({ params: { fragrance_id: id }, data: { status: e.target.value } })}
          className="label bg-transparent border px-2 py-1 !text-foreground"
        >
          {STATUSES.map((s) => (
            <option key={s} value={s} className="bg-background">
              {s}
            </option>
          ))}
        </select>
        <button
          aria-label={`Remove ${f.name}`}
          onClick={() => remove.mutate({ params: { fragrance_id: id } })}
          className="text-muted-foreground hover:text-foreground p-1"
        >
          <X className="size-4" strokeWidth={1.25} />
        </button>
      </div>
    </li>
  );
}

function useDebounced<T>(value: T, ms = 250) {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

export function AddFragrance() {
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<"search" | "paste">("search");
  const [q, setQ] = useState("");
  const dq = useDebounced(q.trim());
  const results = useLookupFragrances({
    params: { q: dq },
    query: { enabled: mode === "search" && dq.length >= 2, select: (r) => r.data },
  });
  const save = useSaveToCollection({
    mutation: {
      onSuccess: () => refreshWardrobe(queryClient),
      onError: (e) => toast.error(`Couldn't add: ${e.message}`),
    },
  });

  const [text, setText] = useState("");
  const [status, setStatus] = useState<Status>("owned");
  const [preview, setPreview] = useState<ImportPreviewOut | null>(null);
  const match = usePreviewImport({
    mutation: {
      onSuccess: ({ data }) => setPreview(data),
      onError: (e) => toast.error(`Couldn't read that list: ${e.message}`),
    },
  });

  return (
    <div className="space-y-4">
      <div className="flex gap-5">
        {(["search", "paste"] as const).map((m) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={cn("label", mode === m && "!text-foreground underline underline-offset-4")}
          >
            {m === "search" ? "Search & add" : "Paste or upload a list"}
          </button>
        ))}
      </div>

      {mode === "search" ? (
        <div className="space-y-1">
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search 26,287 fragrances: santal 33, black uddu…"
            aria-label="Search fragrances"
            className="w-full bg-transparent border-b py-2 text-lg placeholder:text-muted-foreground focus:outline-none focus:border-foreground"
          />
          {dq.length >= 2 && (
            <ul className="divide-y" aria-live="polite">
              {results.isFetching && !results.data && <li className="py-2 label">Searching…</li>}
              {results.data?.length === 0 && <li className="py-2 text-muted-foreground">No fragrance by that name.</li>}
              {results.data?.map((r) => (
                <li key={r.id} className="py-2 flex items-center justify-between gap-4">
                  <span className="min-w-0">
                    <span className="font-display text-xl">{r.name}</span>
                    <span className="label ml-3">
                      {r.house}
                      {r.year ? ` · ${r.year}` : ""}
                    </span>
                  </span>
                  {r.my_status ? (
                    <span className="label">{r.my_status}</span>
                  ) : (
                    <span className="flex gap-3 shrink-0">
                      {STATUSES.map((s) => (
                        <button
                          key={s}
                          disabled={save.isPending}
                          onClick={() => {
                            save.mutate(
                              { fragrance_ids: [r.id ?? 0], status: s },
                              { onSuccess: () => toast(`${r.name} added to ${s}`) },
                            );
                          }}
                          className="label border px-2 py-1 hover:!text-foreground hover:border-foreground disabled:opacity-40"
                        >
                          + {s}
                        </button>
                      ))}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          <label className="label inline-flex items-center gap-2 border px-3 py-2 cursor-pointer hover:!text-foreground hover:border-foreground">
            <Upload className="size-3.5" strokeWidth={1.25} />
            Upload a .csv or .txt
            <input
              type="file"
              accept=".csv,.txt,text/csv,text/plain"
              className="sr-only"
              onChange={async (e) => {
                const file = e.target.files?.[0];
                if (!file) return;
                if (file.size > 200_000) {
                  toast.error("That file is over 200 KB. Upload a shorter list.");
                  return;
                }
                setText(await file.text());
                e.target.value = "";
              }}
            />
          </label>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={5}
            aria-label="Paste a list of fragrances"
            placeholder={"One per line, or a CSV with name and brand columns:\nSantal 33 by Le Labo for women and men\nDiptyque – Tam Dao\nGypsy Water"}
            className="w-full bg-transparent border p-3 placeholder:text-muted-foreground focus:outline-none focus:border-foreground"
          />
          <div className="flex items-center gap-4">
            <select
              aria-label="Save as"
              value={status}
              onChange={(e) => setStatus(e.target.value as Status)}
              className="label bg-transparent border px-2 py-2 !text-foreground"
            >
              {STATUSES.map((s) => (
                <option key={s} value={s} className="bg-background">
                  {s}
                </option>
              ))}
            </select>
            <button
              disabled={!text.trim() || match.isPending}
              onClick={() => match.mutate({ text, status })}
              className="label !text-background bg-foreground px-4 py-2.5 hover:opacity-85 disabled:opacity-40"
            >
              {match.isPending ? "Matching…" : "Match list"}
            </button>
          </div>
          {preview && (
            <ImportCard
              key={JSON.stringify(preview.preview.map((p) => p.id))}
              preview={preview}
              onDone={() => setText("")}
            />
          )}
        </div>
      )}
    </div>
  );
}
