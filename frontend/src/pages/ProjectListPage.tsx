import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { Project } from "../lib/types";
import { getProjects, deleteProject } from "../lib/api";
import StatusBadge from "../components/StatusBadge";

export default function ProjectListPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    getProjects()
      .then(setProjects)
      .catch((e) => console.error("Błąd ładowania projektów:", e))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const handleDelete = (id: number, name: string) => {
    if (!confirm(`Usunąć projekt "${name}"?`)) return;
    deleteProject(id).then(load);
  };

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
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-2xl font-display font-bold text-bark-700">
          Projekty
        </h1>
        <Link to="/new" className="btn-primary">
          + Nowa książeczka
        </Link>
      </div>

      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {projects.map((p, i) => (
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
    </div>
  );
}
