import { Link } from "@tanstack/react-router";
import { useGetMe, type MeOut } from "@/lib/api";
import selector from "@/lib/selector";

export function Header() {
  const { data: me } = useGetMe(selector<MeOut>());
  return (
    <header className="flex items-baseline justify-between gap-6 px-6 md:px-12 pt-8 pb-6">
      <Link to="/" className="label !text-foreground !tracking-[0.3em] hover:opacity-80">
        Scent — Finder
      </Link>
      <nav className="flex items-baseline gap-6">
        <Link
          to="/shelf"
          className="label hover:!text-foreground"
          activeProps={{ className: "!text-foreground underline underline-offset-4" }}
        >
          {me && me.shelf_count > 0 ? (
            <>
              Your shelf <span className="tabular-nums">{me.shelf_count}</span>
            </>
          ) : (
            "Add your fragrances"
          )}
        </Link>
      </nav>
    </header>
  );
}
