import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { ArrowUp } from "lucide-react";
import Markdown from "react-markdown";
import { useChat, useGetMe, type ImportPreviewOut, type MeOut, type ToolCall } from "@/lib/api";
import selector from "@/lib/selector";
import { cn } from "@/lib/utils";
import { ImportCard } from "./import-card";
import { refreshWardrobe } from "./refresh";

type Msg = { role: "user" | "assistant"; content: string; tools?: ToolCall[]; pending?: ImportPreviewOut | null };

const SUGGESTIONS = ["Like Santal 33, but fresher", "Smoky and resinous for winter", "A signature scent under $200"];
const SHELF_SUGGESTIONS = ["Find the gap in my collection", "What should I wear tonight?", "Something different from what I own"];

const TOOL_LABEL: Record<string, string> = {
  get_my_collection: "read your shelf",
  get_scent_dna: "read your scent DNA",
  find_similar: "compared note profiles",
  search_by_notes: "searched by notes",
  log_wear: "logged a wear",
  add_to_collection: "matched names",
};

const MAX_CHARS = 1000;

export function Guide() {
  const queryClient = useQueryClient();
  const { data: me } = useGetMe(selector<MeOut>());
  const [messages, setMessages] = useState<Msg[]>([]);
  const [draft, setDraft] = useState("");
  const end = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLTextAreaElement>(null);
  const chat = useChat({
    mutation: {
      onSuccess: ({ data }) => {
        setMessages((m) => [...m, { role: "assistant", content: data.reply, tools: data.tool_calls, pending: data.pending_import }]);
        if (data.tool_calls.some((t) => t.name === "log_wear")) refreshWardrobe(queryClient);
      },
      onError: (e) => {
        const detail = (e.body as { detail?: unknown } | undefined)?.detail;
        const text = typeof detail === "string" ? detail : `The guide couldn't answer (${e.message}). Ask again in a moment.`;
        setMessages((m) => [...m, { role: "assistant", content: text }]);
      },
    },
  });

  useEffect(() => {
    end.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, chat.isPending]);

  const hasShelf = (me?.shelf_count ?? 0) > 0;
  const started = messages.length > 0;

  const send = (text: string) => {
    const t = text.trim().slice(0, MAX_CHARS);
    if (!t || chat.isPending) return;
    const next: Msg[] = [...messages, { role: "user", content: t }];
    setMessages(next);
    setDraft("");
    chat.mutate({ messages: next.map(({ role, content }) => ({ role, content })) });
  };

  const composer = (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        send(draft);
      }}
      className="flex items-end gap-3 border-b border-foreground/60 focus-within:border-foreground pb-3"
    >
      <textarea
        ref={input}
        value={draft}
        maxLength={MAX_CHARS}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            send(draft);
          }
        }}
        rows={1}
        autoFocus
        aria-label="Describe a scent, or name one you love"
        placeholder={started ? "Ask a follow-up…" : "Describe a scent, or name one you love"}
        className={cn(
          "flex-1 resize-none bg-transparent placeholder:text-muted-foreground focus:outline-none field-sizing-content max-h-40",
          started ? "text-lg" : "font-display text-2xl md:text-3xl font-light",
        )}
      />
      <button
        type="submit"
        aria-label="Ask"
        disabled={!draft.trim() || chat.isPending}
        className="size-10 shrink-0 grid place-items-center border hover:bg-foreground hover:text-background disabled:opacity-30 transition-colors"
      >
        <ArrowUp className="size-4" strokeWidth={1.25} />
      </button>
    </form>
  );

  if (!started) {
    return (
      <section className="flex-1 flex flex-col justify-center px-6 pb-[12vh]">
        <div className="w-full max-w-2xl mx-auto space-y-8">
          <h1 className="font-display text-5xl md:text-6xl font-light tracking-tight text-balance">
            What do you want to smell like?
          </h1>
          {composer}
          <ul className="flex flex-wrap gap-2" aria-label="Suggestions">
            {(hasShelf ? SHELF_SUGGESTIONS : SUGGESTIONS).map((s) => (
              <li key={s}>
                <button
                  onClick={() => send(s)}
                  className="text-sm border px-3 py-1.5 text-muted-foreground hover:text-foreground hover:border-foreground transition-colors"
                >
                  {s}
                </button>
              </li>
            ))}
          </ul>
          <p className="text-sm text-muted-foreground">
            {hasShelf ? (
              <>
                Picks are personalised from your {me?.shelf_count} fragrances.{" "}
                <Link to="/shelf" className="underline hover:text-foreground">Edit your shelf</Link>
              </>
            ) : (
              <>
                <Link to="/shelf" className="underline hover:text-foreground">Add the fragrances you own</Link> for
                personal picks. Optional.
              </>
            )}
          </p>
        </div>
      </section>
    );
  }

  return (
    <section className="flex-1 min-h-0 flex flex-col px-6">
      <div className="flex-1 min-h-0 overflow-y-auto">
        <div className="max-w-2xl mx-auto space-y-10 py-8">
          {messages.map((m, i) =>
            m.role === "user" ? (
              <p key={i} className="font-display text-3xl font-light italic text-balance">{m.content}</p>
            ) : (
              <div key={i} className="space-y-3 reveal">
                {m.tools && m.tools.length > 0 && (
                  <p className="label">{[...new Set(m.tools.map((t) => TOOL_LABEL[t.name] ?? t.name))].join(" · ")}</p>
                )}
                <div className="prose-guide leading-relaxed">
                  <Markdown>{m.content}</Markdown>
                </div>
                {m.pending && <ImportCard preview={m.pending} />}
              </div>
            ),
          )}
          {chat.isPending && <p className="label animate-pulse">Reading the notes…</p>}
          <div ref={end} />
        </div>
      </div>
      <div className="max-w-2xl w-full mx-auto py-6">{composer}</div>
    </section>
  );
}
