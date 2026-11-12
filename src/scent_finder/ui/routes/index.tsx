import { createFileRoute } from "@tanstack/react-router";
import { Header } from "@/components/scent/header";
import { Guide } from "@/components/scent/guide";

export const Route = createFileRoute("/")({
  component: () => (
    <div className="h-dvh flex flex-col">
      <Header />
      <Guide />
      <p className="px-6 md:px-12 pb-5 text-xs text-muted-foreground">
        Fragrance notes are approximate and price bands are estimates.
      </p>
    </div>
  ),
});
