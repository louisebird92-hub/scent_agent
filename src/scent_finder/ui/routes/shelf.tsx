import { Suspense } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { QueryErrorResetBoundary } from "@tanstack/react-query";
import { ErrorBoundary } from "react-error-boundary";
import { Header } from "@/components/scent/header";
import { ScentDna } from "@/components/scent/dna";
import { AddFragrance, Wardrobe } from "@/components/scent/wardrobe";

export const Route = createFileRoute("/shelf")({
  component: () => <Shelf />,
});

function Panel({ children, what }: { children: React.ReactNode; what: string }) {
  return (
    <QueryErrorResetBoundary>
      {({ reset }) => (
        <ErrorBoundary
          onReset={reset}
          fallbackRender={({ error, resetErrorBoundary }) => (
            <div className="space-y-3 py-6">
              <p>Couldn't load {what}: {error instanceof Error ? error.message : "unknown error"}.</p>
              <button onClick={resetErrorBoundary} className="label underline !text-foreground">Try again</button>
            </div>
          )}
        >
          <Suspense fallback={<p className="label animate-pulse py-6">Loading {what}…</p>}>{children}</Suspense>
        </ErrorBoundary>
      )}
    </QueryErrorResetBoundary>
  );
}

function Shelf() {
  return (
    <div className="min-h-dvh flex flex-col">
      <Header />
      <main className="flex-1 grid lg:grid-cols-[minmax(0,6fr)_minmax(0,5fr)] gap-x-16 gap-y-16 px-6 md:px-12 py-10">
        <div className="space-y-12 min-w-0">
          <section className="space-y-4">
            <h1 className="font-display text-5xl font-light tracking-tight">Your shelf</h1>
            <p className="text-muted-foreground max-w-[60ch]">
              Add what you own, have tried or want. The guide uses it to skip bottles you have and to match what you
              love. Only you can see your shelf.
            </p>
          </section>
          <AddFragrance />
          <Panel what="your shelf">
            <Wardrobe />
          </Panel>
        </div>
        <aside className="min-w-0 lg:border-l lg:pl-16">
          <Panel what="your scent DNA">
            <ScentDna />
          </Panel>
        </aside>
      </main>
      <p className="px-6 md:px-12 pb-6 text-xs text-muted-foreground max-w-[90ch]">
        Notes are approximate: 164 entries written from model knowledge plus 26k from the public doevent/perfume
        dataset. Seasons on imported entries and all price bands are inferred.
      </p>
    </div>
  );
}
