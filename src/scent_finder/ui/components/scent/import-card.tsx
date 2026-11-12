import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { useSaveToCollection, type ImportPreviewOut } from "@/lib/api";
import { refreshWardrobe } from "./refresh";

export function ImportCard({ preview, onDone }: { preview: ImportPreviewOut; onDone?: () => void }) {
  const queryClient = useQueryClient();
  const [picked, setPicked] = useState<Set<number>>(
    () => new Set(preview.preview.filter((m) => m.already !== preview.status).map((m) => m.id)),
  );
  const [saved, setSaved] = useState(false);
  const save = useSaveToCollection({
    mutation: {
      onSuccess: async ({ data }) => {
        setSaved(true);
        toast(`Saved ${data.count} to ${preview.status}`);
        await refreshWardrobe(queryClient);
        onDone?.();
      },
      onError: (e) => toast.error(`Couldn't save: ${e.message}. Try again.`),
    },
  });

  const toggle = (id: number) =>
    setPicked((s) => {
      const n = new Set(s);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });

  return (
    <div className="border p-5 space-y-4">
      <p className="label">
        {preview.preview.length} matched · {preview.unmatched.length} not found · saving as {preview.status}
      </p>
      <ul className="divide-y">
        {preview.preview.map((m) => (
          <li key={`${m.id}-${m.input}`} className="py-2">
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                className="mt-1.5 accent-white"
                checked={picked.has(m.id)}
                disabled={saved}
                onChange={() => toggle(m.id)}
              />
              <span className="flex-1">
                <span className="font-display text-xl">{m.match}</span>
                <span className="block text-xs text-muted-foreground">
                  from “{m.input}”{m.score < 0.6 ? " · loose match, check it" : ""}
                  {m.already ? ` · already ${m.already}` : ""}
                </span>
              </span>
            </label>
          </li>
        ))}
        {preview.unmatched.map((u) => (
          <li key={u.input} className="py-2 text-sm text-muted-foreground">
            No match for “{u.input}”
            {(u.did_you_mean ?? []).length > 0 && <> · closest: {(u.did_you_mean ?? []).join(", ")}</>}
          </li>
        ))}
      </ul>
      <button
        type="button"
        disabled={saved || picked.size === 0 || save.isPending}
        onClick={() => save.mutate({ fragrance_ids: [...picked], status: preview.status })}
        className="label !text-background bg-foreground px-4 py-2.5 hover:opacity-85 disabled:opacity-40 transition-opacity"
      >
        {saved ? "Saved" : save.isPending ? "Saving…" : `Save ${picked.size} to ${preview.status}`}
      </button>
    </div>
  );
}
