import { formatDuration } from "@/lib/format";
import { Citation } from "@/lib/types";

export function Citations({ citations }: { citations: Citation[] }) {
  if (!citations.length) {
    return <p className="text-sm text-slate-500">No citations available.</p>;
  }

  return (
    <div className="grid gap-2">
      {citations.map((citation, index) => {
        const hasRange = citation.start_seconds != null && citation.end_seconds != null;
        return (
          <article
            key={`${citation.lecture_id}-${citation.section_id}-${index}`}
            className="rounded-lg border-l-2 border-orange-300 bg-orange-50/40 py-2.5 pl-3 pr-3"
          >
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="font-medium text-slate-800">{citation.lecture_title}</span>
              {citation.section_title ? (
                <span className="rounded-full bg-white px-2 py-0.5 text-slate-500">{citation.section_title}</span>
              ) : null}
              {hasRange ? (
                <span className="rounded-full bg-orange-100 px-2 py-0.5 font-mono text-[11px] text-orange-700">
                  {formatDuration(citation.start_seconds)}–{formatDuration(citation.end_seconds)}
                </span>
              ) : null}
            </div>
            <p className="mt-1.5 text-xs leading-relaxed text-slate-600">{citation.snippet}</p>
          </article>
        );
      })}
    </div>
  );
}
