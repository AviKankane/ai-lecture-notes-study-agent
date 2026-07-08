"use client";

import { useState } from "react";

import { QuizItem } from "@/lib/types";

type SelectionMap = Record<number, string>;

export function QuizView({ quizItems }: { quizItems: QuizItem[] }) {
  const [selectedAnswers, setSelectedAnswers] = useState<SelectionMap>({});

  if (!quizItems.length) {
    return <div className="rounded-lg border bg-white/70 p-5 text-sm text-slate-600">Quiz items will appear after lecture processing completes.</div>;
  }

  function selectAnswer(questionId: number, option: string) {
    setSelectedAnswers((current) => {
      if (current[questionId]) {
        return current;
      }
      return { ...current, [questionId]: option };
    });
  }

  return (
    <div className="grid gap-4">
      {quizItems.map((item, index) => (
        <article key={item.id} className="rounded-xl border bg-white/80 p-5 shadow-sm">
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-sm font-semibold text-slate-800">
              {index + 1}. {item.question}
            </h3>
            <span className="rounded-full bg-orange-50 px-2.5 py-1 text-xs font-medium text-orange-700">
              {selectedAnswers[item.id] ? "Answered" : "Choose one"}
            </span>
          </div>
          <div className="mt-4 grid gap-2 text-sm text-slate-700">
            {item.options_json.map((option) => {
              const selected = selectedAnswers[item.id];
              const hasAnswered = Boolean(selected);
              const isPicked = selected === option;
              const isCorrect = option === item.correct_answer;
              const stateClass = hasAnswered
                ? isCorrect
                  ? "border-emerald-300 bg-emerald-50 text-emerald-900"
                  : isPicked
                    ? "border-rose-300 bg-rose-50 text-rose-900"
                    : "border-slate-200 bg-slate-50 text-slate-500"
                : "border-slate-200 bg-white hover:border-orange-300 hover:bg-orange-50";

              return (
                <button
                  key={option}
                  className={`rounded-lg border px-3 py-3 text-left transition ${stateClass}`}
                  disabled={hasAnswered}
                  onClick={() => selectAnswer(item.id, option)}
                  type="button"
                >
                  <div className="flex items-center justify-between gap-3">
                    <span>{option}</span>
                    {hasAnswered && isCorrect ? <span className="text-xs font-semibold uppercase tracking-wide">Correct</span> : null}
                    {hasAnswered && isPicked && !isCorrect ? <span className="text-xs font-semibold uppercase tracking-wide">Your pick</span> : null}
                  </div>
                </button>
              );
            })}
          </div>
          {selectedAnswers[item.id] ? (
            <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
              <p className="text-sm font-medium text-slate-800">
                {selectedAnswers[item.id] === item.correct_answer ? "Correct answer" : "Right answer"}: {item.correct_answer}
              </p>
              <p className="mt-2 text-sm text-slate-600">{item.explanation}</p>
            </div>
          ) : (
            <p className="mt-4 text-xs uppercase tracking-wide text-slate-400">Answer reveals after you choose an option.</p>
          )}
        </article>
      ))}
    </div>
  );
}
