import type { ProjectStatus } from "../lib/types";

const statusConfig: Record<ProjectStatus, { label: string; bg: string; text: string; dot: string }> = {
  draft:             { label: "Szkic",          bg: "bg-cream-300/50", text: "text-bark-400", dot: "bg-bark-300" },
  story_generated:   { label: "Historia",       bg: "bg-blue-50",     text: "text-blue-700", dot: "bg-blue-400" },
  prompts_generated: { label: "Prompty",        bg: "bg-purple-50",   text: "text-purple-700", dot: "bg-purple-400" },
  images_generating: { label: "Generowanie...", bg: "bg-amber-50",    text: "text-amber-700", dot: "bg-amber-400" },
  review:            { label: "Podgląd",        bg: "bg-emerald-50",  text: "text-emerald-700", dot: "bg-emerald-400" },
  exported:          { label: "Wyeksportowano", bg: "bg-teal-50",     text: "text-teal-700", dot: "bg-teal-500" },
};

export default function StatusBadge({ status }: { status: ProjectStatus }) {
  const cfg = statusConfig[status];
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${cfg.bg} ${cfg.text}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot} ${status === "images_generating" ? "animate-pulse" : ""}`} />
      {cfg.label}
    </span>
  );
}
