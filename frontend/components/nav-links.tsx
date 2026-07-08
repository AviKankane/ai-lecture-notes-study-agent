"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Dashboard" },
  { href: "/chat", label: "Chat" },
];

export function NavLinks() {
  const pathname = usePathname();
  return (
    <nav className="flex gap-1.5 text-sm">
      {links.map((link) => {
        const active = link.href === "/" ? pathname === "/" : pathname.startsWith(link.href);
        return (
          <Link
            key={link.href}
            href={link.href}
            className={`rounded-lg px-4 py-2 font-medium transition ${
              active
                ? "bg-gradient-to-r from-orange-500 to-amber-500 text-white shadow-sm"
                : "border bg-white text-slate-700 hover:bg-orange-50"
            }`}
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}
