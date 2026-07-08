import "./globals.css";
import type { Metadata } from "next";

import { NavLinks } from "@/components/nav-links";

export const metadata: Metadata = {
  title: "AI Lecture Notes & Study Agent",
  description: "Upload lectures, generate notes, and chat with cited answers.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="font-sans">
        <div className="mx-auto min-h-screen max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <header className="mb-8 rounded-2xl border border-white/60 bg-white/70 p-5 shadow-sm backdrop-blur">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-orange-500 to-lime-500 text-xl shadow-sm">
                  🎓
                </div>
                <div>
                  <h1 className="text-2xl font-semibold tracking-tight">AI Lecture Notes &amp; Study Agent</h1>
                  <p className="mt-0.5 text-sm text-slate-600">
                    Local transcription, structured notes, interactive quizzes, and cited lecture chat.
                  </p>
                </div>
              </div>
              <NavLinks />
            </div>
          </header>
          {children}
        </div>
      </body>
    </html>
  );
}
