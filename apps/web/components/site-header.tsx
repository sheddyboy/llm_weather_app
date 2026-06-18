"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { CloudSun } from "lucide-react";
import { cn } from "@/lib/utils";
import { UnitToggle } from "@/components/unit-toggle";
import { ConnectionIndicator } from "@/components/connection-indicator";

const NAV = [
  { href: "/", label: "Live" },
  { href: "/records", label: "Records" },
];

export function SiteHeader() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-30 px-3 pt-3 sm:px-6 sm:pt-4">
      <div className="glass mx-auto flex flex-wrap max-w-6xl items-center justify-between gap-2 rounded-2xl px-3 py-2.5 sm:px-5">
        <Link href="/" className="flex items-center gap-2 text-white">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-white/15">
            <CloudSun className="h-5 w-5" aria-hidden="true" />
          </span>
          <span className="text-lg font-semibold tracking-tight">Skyglass</span>
        </Link>

        <nav aria-label="Primary" className="flex items-center gap-1">
          {NAV.map((item) => {
            const active =
              item.href === "/"
                ? pathname === "/"
                : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "rounded-full px-3 py-1.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/60",
                  active
                    ? "bg-white/20 text-white"
                    : "text-white/70 hover:bg-white/10 hover:text-white",
                )}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-2 ml-auto">
          <ConnectionIndicator />
          <UnitToggle />
        </div>
      </div>
    </header>
  );
}
