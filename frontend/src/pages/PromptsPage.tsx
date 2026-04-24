import { useEffect, useMemo, useState } from "react";
import type { Prompt, PromptKind } from "../lib/types";
import {
  listPrompts,
  createPrompt,
  updatePrompt,
  deletePrompt,
} from "../lib/api";
import { useToast } from "../context/ToastContext";

const KIND_LABELS: Record<PromptKind, string> = {
  story: "Historia",
  image: "Obrazki",
};

interface DraftState {
  id: number | null; // null for a new prompt being created
  kind: PromptKind;
  title: string;
  content: string;
  dirty: boolean;
}

export default function PromptsPage() {
  const { addToast } = useToast();
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeKind, setActiveKind] = useState<PromptKind>("story");
  const [draft, setDraft] = useState<DraftState | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    listPrompts()
      .then(setPrompts)
      .catch(() => addToast("Nie udało się załadować promptów", "error"))
      .finally(() => setLoading(false));
  }, [addToast]);

  const filtered = useMemo(
    () => prompts.filter((p) => p.kind === activeKind),
    [prompts, activeKind]
  );

  const startNew = () => {
    setDraft({
      id: null,
      kind: activeKind,
      title: "",
      content: "",
      dirty: true,
    });
  };

  const startEdit = (p: Prompt) => {
    setDraft({
      id: p.id,
      kind: p.kind,
      title: p.title,
      content: p.content,
      dirty: false,
    });
  };

  const cancelDraft = () => setDraft(null);

  const save = async () => {
    if (!draft) return;
    if (!draft.title.trim() || !draft.content.trim()) {
      addToast("Tytuł i treść są wymagane", "error");
      return;
    }
    setSaving(true);
    try {
      if (draft.id === null) {
        const created = await createPrompt({
          kind: draft.kind,
          title: draft.title.trim(),
          content: draft.content,
        });
        setPrompts((prev) => [created, ...prev]);
        addToast("Prompt zapisany", "success");
      } else {
        const updated = await updatePrompt(draft.id, {
          title: draft.title.trim(),
          content: draft.content,
        });
        setPrompts((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
        addToast("Prompt zaktualizowany", "success");
      }
      setDraft(null);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Nie udało się zapisać";
      addToast(msg, "error");
    } finally {
      setSaving(false);
    }
  };

  const remove = async (p: Prompt) => {
    if (p.is_default) {
      addToast("Nie można usunąć domyślnego promptu", "error");
      return;
    }
    if (!confirm(`Usunąć prompt „${p.title}”?`)) return;
    try {
      await deletePrompt(p.id);
      setPrompts((prev) => prev.filter((x) => x.id !== p.id));
      if (draft?.id === p.id) setDraft(null);
    } catch {
      addToast("Nie udało się usunąć", "error");
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="spinner-warm" />
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto animate-enter">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <span className="text-2xl">✎</span>
          <h1 className="text-2xl font-display font-bold text-bark-700">
            Biblioteka promptów
          </h1>
        </div>
        <button onClick={startNew} className="btn-primary">
          + Nowy prompt
        </button>
      </div>

      {/* Kind tabs */}
      <div className="flex gap-2 mb-6 border-b border-bark-200">
        {(Object.keys(KIND_LABELS) as PromptKind[]).map((k) => (
          <button
            key={k}
            onClick={() => setActiveKind(k)}
            className={`px-4 py-2 text-sm font-semibold transition-colors border-b-2 -mb-px ${
              activeKind === k
                ? "text-teal-600 border-teal-500"
                : "text-bark-400 border-transparent hover:text-bark-600"
            }`}
          >
            {KIND_LABELS[k]} ({prompts.filter((p) => p.kind === k).length})
          </button>
        ))}
      </div>

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
        {/* List */}
        <div className="space-y-3">
          {filtered.length === 0 && (
            <p className="text-sm text-bark-400 italic">
              Brak zapisanych promptów w tej kategorii.
            </p>
          )}
          {filtered.map((p) => {
            const isSelected = draft?.id === p.id;
            return (
              <div
                key={p.id}
                className={`card-storybook p-4 cursor-pointer transition-all ${
                  isSelected
                    ? "ring-2 ring-teal-500"
                    : "hover:shadow-md"
                }`}
                onClick={() => startEdit(p)}
              >
                <div className="flex items-start justify-between gap-3 mb-1">
                  <h3 className="font-display font-bold text-bark-700 truncate">
                    {p.title}
                  </h3>
                  {p.is_default && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 font-semibold whitespace-nowrap">
                      domyślny
                    </span>
                  )}
                </div>
                <p className="text-xs text-bark-400 line-clamp-2 font-mono">
                  {p.content.slice(0, 140)}
                  {p.content.length > 140 ? "…" : ""}
                </p>
                <div className="mt-2 flex items-center justify-between text-xs text-bark-300">
                  <span>zaktualizowano: {p.updated_at.slice(0, 10)}</span>
                  {!p.is_default && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        remove(p);
                      }}
                      className="text-red-400 hover:text-red-600 font-semibold"
                    >
                      Usuń
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Editor */}
        <div className="card-storybook p-5">
          {draft ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="font-display font-bold text-bark-700">
                  {draft.id === null
                    ? `Nowy prompt (${KIND_LABELS[draft.kind]})`
                    : "Edycja promptu"}
                </h2>
                <button
                  onClick={cancelDraft}
                  className="text-sm text-bark-400 hover:text-bark-600"
                >
                  Anuluj
                </button>
              </div>

              {draft.id === null && (
                <div>
                  <label className="label-warm">Kategoria</label>
                  <select
                    className="input-warm"
                    value={draft.kind}
                    onChange={(e) =>
                      setDraft({
                        ...draft,
                        kind: e.target.value as PromptKind,
                        dirty: true,
                      })
                    }
                  >
                    <option value="story">Historia</option>
                    <option value="image">Obrazki</option>
                  </select>
                </div>
              )}

              <div>
                <label className="label-warm">Tytuł</label>
                <input
                  className="input-warm"
                  value={draft.title}
                  onChange={(e) =>
                    setDraft({ ...draft, title: e.target.value, dirty: true })
                  }
                  placeholder="np. Wariant lżejszy dla 3-latka"
                />
              </div>

              <div>
                <label className="label-warm">Treść</label>
                <textarea
                  className="input-warm h-96 font-mono text-xs leading-relaxed resize-y scroll-warm"
                  value={draft.content}
                  onChange={(e) =>
                    setDraft({ ...draft, content: e.target.value, dirty: true })
                  }
                />
                <p className="text-xs text-bark-300 mt-1.5">
                  Możesz używać zmiennych: <code>{"{name}"}</code>,{" "}
                  <code>{"{age}"}</code>, <code>{"{gender}"}</code>,{" "}
                  <code>{"{hair_color}"}</code>, <code>{"{skin_tone}"}</code>,{" "}
                  <code>{"{eye_color}"}</code>, <code>{"{haircut}"}</code>,{" "}
                  <code>{"{outfit_description}"}</code>,{" "}
                  <code>{"{story_type}"}</code>, <code>{"{hobby}"}</code>,{" "}
                  <code>{"{moral}"}</code>.
                </p>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={save}
                  disabled={saving || !draft.dirty}
                  className="btn-primary"
                >
                  {saving ? "Zapisywanie..." : "Zapisz"}
                </button>
              </div>
            </div>
          ) : (
            <div className="text-center py-12 text-bark-400">
              <p className="text-sm">
                Wybierz prompt po lewej aby edytować, albo kliknij{" "}
                <strong>„+ Nowy prompt”</strong> żeby dodać kolejny.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
