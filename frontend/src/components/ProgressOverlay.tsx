interface Props {
  total: number;
  completed: number;
  statuses: Record<number, "generating" | "completed" | "failed">;
}

export default function ProgressOverlay({ total, completed, statuses }: Props) {
  const pct = Math.round((completed / total) * 100);

  return (
    <div className="fixed inset-0 bg-bark-700/50 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="card-storybook w-full max-w-md p-7 animate-enter">
        <div className="flex items-center gap-3 mb-5">
          <span className="text-2xl">&#x1F3A8;</span>
          <div>
            <h3 className="text-lg font-display font-bold text-bark-700">
              Malowanie ilustracji
            </h3>
            <p className="text-sm text-bark-300">
              {completed} z {total} gotowych ({pct}%)
            </p>
          </div>
        </div>

        {/* Progress bar */}
        <div className="w-full bg-cream-300/60 rounded-full h-2.5 mb-5 overflow-hidden">
          <div
            className="bg-gradient-to-r from-teal-500 to-teal-600 h-2.5 rounded-full transition-all duration-500 ease-out"
            style={{ width: `${pct}%` }}
          />
        </div>

        {/* Page slots */}
        <div className="grid grid-cols-6 gap-2">
          {Array.from({ length: total }, (_, i) => {
            const pageNum = i + 1;
            const status = statuses[pageNum];
            return (
              <div
                key={pageNum}
                className={`w-full aspect-square rounded-lg flex items-center justify-center text-xs font-bold transition-all duration-300 ${
                  status === "completed"
                    ? "bg-emerald-100 text-emerald-600 scale-95"
                    : status === "generating"
                    ? "bg-amber-100 text-amber-600 animate-pulse"
                    : status === "failed"
                    ? "bg-red-100 text-red-600"
                    : "bg-cream-200/80 text-bark-300"
                }`}
              >
                {status === "completed"
                  ? "\u2713"
                  : status === "failed"
                  ? "!"
                  : pageNum}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
