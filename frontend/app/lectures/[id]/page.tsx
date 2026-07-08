import { QuizView } from "@/components/quiz-view";
import { StatusBadge } from "@/components/status-badge";
import { fetchLecture } from "@/lib/api";

export default async function LectureDetailPage({ params }: { params: { id: string } }) {
  const lecture = await fetchLecture(params.id);

  return (
    <main className="grid gap-6">
      <section className="rounded-xl border bg-white/75 p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="flex items-center gap-2 text-xl font-semibold">
              <span>{lecture.source_type === "youtube" ? "▶️" : "🎧"}</span>
              {lecture.title}
            </h2>
            <p className="mt-1 text-sm text-slate-500">{lecture.original_filename}</p>
          </div>
          <StatusBadge status={lecture.status} />
        </div>
        {lecture.subject_name || lecture.chapter_name || lecture.subsection || lecture.source_url ? (
          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
            {lecture.subject_name ? (
              <span className="inline-flex items-center rounded-full bg-lime-100 px-2.5 py-1 font-medium text-lime-800">
                {lecture.subject_name}
              </span>
            ) : null}
            {lecture.chapter_name ? (
              <span className="inline-flex items-center rounded-full bg-orange-100 px-2.5 py-1 font-medium text-orange-800">
                {lecture.chapter_name}
              </span>
            ) : null}
            {lecture.subsection ? (
              <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-1 font-medium text-slate-600">
                {lecture.subsection}
              </span>
            ) : null}
            {lecture.source_url ? (
              <a
                href={lecture.source_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center rounded-full bg-rose-50 px-2.5 py-1 font-medium text-rose-700 hover:bg-rose-100"
              >
                ▶️ Source on YouTube
              </a>
            ) : null}
          </div>
        ) : null}
        {lecture.error_message ? <p className="mt-4 text-sm text-rose-600">{lecture.error_message}</p> : null}
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.2fr,0.8fr]">
        <article className="rounded-xl border bg-white/75 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-800">Transcript</h3>
          <p className="mt-3 whitespace-pre-wrap text-sm text-slate-700">{lecture.transcript?.text ?? "Transcript not available yet."}</p>
        </article>
        <article className="rounded-xl border bg-white/75 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-800">Processing log</h3>
          <div className="mt-3 grid gap-3">
            {lecture.events.length ? (
              lecture.events.map((event) => (
                <div key={event.id} className="rounded-lg border bg-white p-3 text-sm shadow-sm">
                  <div className="font-medium text-slate-800">
                    {event.step} · {event.status}
                  </div>
                  {event.message ? <p className="mt-1 text-slate-600">{event.message}</p> : null}
                </div>
              ))
            ) : (
              <p className="text-sm text-slate-500">No processing events yet.</p>
            )}
          </div>
        </article>
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <article className="rounded-xl border bg-white/75 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-800">Structured notes</h3>
          <div className="mt-4 grid gap-4">
            {lecture.sections.length ? (
              lecture.sections.map((section) => (
                <div key={section.id} className="rounded-xl border bg-white p-4 shadow-sm">
                  <h4 className="text-sm font-semibold text-slate-800">{section.title}</h4>
                  <p className="mt-2 text-sm text-slate-600">{section.summary}</p>
                  <p className="mt-3 whitespace-pre-wrap text-sm text-slate-700">{section.text}</p>
                </div>
              ))
            ) : (
              <p className="text-sm text-slate-500">Sections will appear when processing completes.</p>
            )}
          </div>
        </article>

        <article className="rounded-xl border bg-white/75 p-5 shadow-sm">
          <h3 className="mb-4 text-sm font-semibold text-slate-800">Quiz</h3>
          <QuizView quizItems={lecture.quiz_items} />
        </article>
      </section>
    </main>
  );
}
