import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import type { FulfillmentStatus, Project } from "../lib/types";
import { FULFILLMENT_LABELS, FULFILLMENT_ORDER } from "../lib/types";
import { getProjects, deleteProject, updateProject } from "../lib/api";
import { useToast } from "../context/ToastContext";
import StatusBadge from "../components/StatusBadge";

type FilterValue = FulfillmentStatus | "all";

const FULFILLMENT_ACCENTS: Record<FulfillmentStatus, string> = {
  oczekuje: "bg-amber-100 text-amber-800 border-amber-300",
  w_drukarni: "bg-blue-100 text-blue-800 border-blue-300",
  wyslane: "bg-purple-100 text-purple-800 border-purple-300",
  doreczone: "bg-emerald-100 text-emerald-800 border-emerald-300",
};

export default function ProjectListPage() {
  const { addToast } = useToast();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<FilterValue>("all");

  const load = () => {
    setLoading(true);
    getProjects()
      .then(setProjects)
      .catch((e) => console.error("Błąd ładowania projektów:", e))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const handleDelete = (id: number, name: string) => {
    if (!confirm(`Usunąć projekt "${name}"? Tego nie można cofnąć.`)) return;
    deleteProject(id)
      .then(() => {
        setProjects((prev) => prev.filter((p) => p.id !== id));
        addToast("Projekt usunięty", "success");
      })
      .catch(() => addToast("Błąd usuwania projektu", "error"));
  };

  const changeFulfillment = async (
    projectId: number,
    next: FulfillmentStatus,
  ) => {
    setProjects((prev) =>
      prev.map((p) => (p.id === projectId ? { ...p, fulfillment_status: next } : p)),
    );
    try {
      await updateProject(projectId, { fulfillment_status: next });
    } catch {
      addToast("Nie udało się zapisać statusu", "error");
      load();
    }
  };

  const filtered = useMemo(
    () =>
      filter === "all"
        ? projects
        : projects.filter((p) => p.fulfillment_status === filter),
    [projects, filter],
  );

  const counts = useMemo(() => {
    const map: Record<FilterValue, number> = {
      all: projects.length,
      oczekuje: 0,
      w_drukarni: 0,
      wyslane: 0,
      doreczone: 0,
    };
    for (const p of projects) map[p.fulfillment_status]++;
    return map;
  }, [projects]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="spinner-warm" />
      </div>
    );
  }

  if (projects.length === 0) {
    return (
      <div className="text-center py-24 animate-enter">
        <div className="text-5xl mb-4">&#x1F4DA;</div>
        <h2 className="text-2xl font-display font-bold text-bark-600 mb-2">
          Brak projektów
        </h2>
        <p className="text-bark-300 mb-8 max-w-sm mx-auto">
          Stwórz swoją pierwszą magiczną książeczkę dla dziecka
        </p>
        <Link to="/new" className="btn-primary text-base px-8 py-3">
          Nowa książeczka
        </Link>
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-display font-bold text-bark-700">
          Projekty
        </h1>
        <Link to="/new" className="btn-primary">
          + Nowa książeczka
        </Link>
      </div>

      {/* Fulfillment filter tabs */}
      <div className="flex flex-wrap gap-2 mb-6 text-sm">
        <button
          onClick={() => setFilter("all")}
          className={`px-3 py-1.5 rounded-lg font-semibold border transition-colors ${
            filter === "all"
              ? "bg-bark-700 text-cream-50 border-bark-700"
              : "bg-white text-bark-500 border-bark-200 hover:bg-bark-50"
          }`}
        >
          Wszystkie ({counts.all})
        </button>
        {FULFILLMENT_ORDER.map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`px-3 py-1.5 rounded-lg font-semibold border transition-colors ${
              filter === s
                ? "bg-bark-700 text-cream-50 border-bark-700"
                : "bg-white text-bark-500 border-bark-200 hover:bg-bark-50"
            }`}
          >
            {FULFILLMENT_LABELS[s]} ({counts[s]})
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <p className="text-sm text-bark-400 italic py-8 text-center">
          Brak projektów w tej kategorii.
        </p>
      ) : (
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((p, i) => (
            <div
              key={p.id}
              className="card-storybook p-5 animate-enter"
              style={{ animationDelay: `${i * 60}ms` }}
            >
              <div className="flex justify-between items-start mb-3">
                <Link
                  to={`/project/${p.id}`}
                  className="text-lg font-display font-bold text-teal-500 hover:text-teal-600 transition-colors"
                >
                  {p.child_name}
                </Link>
                <StatusBadge status={p.status} />
              </div>
              <div className="space-y-1 mb-4">
                <p className="text-sm text-bark-300">
                  <span className="text-bark-400 font-medium">Motyw:</span>{" "}
                  {p.story_type}
                </p>
                <p className="text-sm text-bark-300">
                  <span className="text-bark-400 font-medium">Hobby:</span>{" "}
                  {p.hobby}
                </p>
              </div>

              {/* Fulfillment dropdown */}
              <div className="mb-3">
                <label className="block text-[11px] font-semibold text-bark-400 uppercase tracking-wider mb-1">
                  Status wysyłki
                </label>
                <select
                  value={p.fulfillment_status}
                  onChange={(e) =>
                    changeFulfillment(p.id, e.target.value as FulfillmentStatus)
                  }
                  className={`w-full text-sm font-semibold px-2.5 py-1.5 rounded-lg border transition-colors cursor-pointer ${
                    FULFILLMENT_ACCENTS[p.fulfillment_status]
                  }`}
                >
                  {FULFILLMENT_ORDER.map((s) => (
                    <option key={s} value={s}>
                      {FULFILLMENT_LABELS[s]}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex justify-between items-center pt-3 border-t border-cream-300/60">
                <span className="text-xs text-bark-200 font-medium">
                  {new Date(p.created_at).toLocaleDateString("pl", {
                    day: "numeric",
                    month: "long",
                    year: "numeric",
                  })}
                </span>
                <button
                  onClick={() => handleDelete(p.id, p.child_name)}
                  className="text-xs text-rose-400 hover:text-rose-500 font-medium transition-colors"
                >
                  Usuń
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
