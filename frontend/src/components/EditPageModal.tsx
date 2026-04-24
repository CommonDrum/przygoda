import { useEffect, useState } from "react";
import type { ImageVersion, Page } from "../lib/types";
import {
  getPageVersions,
  regenerateImage,
  restorePageVersion,
  updatePage,
} from "../lib/api";
import { showErrorToast } from "../lib/errors";
import { useToast } from "../context/ToastContext";

interface Props {
  page: Page;
  onUpdate: (updated: Page) => void;
  onClose: () => void;
}

type Tab = "text" | "prompt" | "history";

function pageLabel(page: Page): string {
  if (page.page_number === 1) return "Okładka";
  if (page.page_number === 17) return "Tył okładki";
  return `Strona ${page.page_number - 1}`;
}

export default function EditPageModal({ page, onUpdate, onClose }: Props) {
  const { addToast } = useToast();
  const [tab, setTab] = useState<Tab>("text");
  const [text, setText] = useState(page.text ?? "");
  const [prompt, setPrompt] = useState(page.image_prompt ?? "");
  const [savingText, setSavingText] = useState(false);
  const [savingPrompt, setSavingPrompt] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [versions, setVersions] = useState<ImageVersion[] | null>(null);
  const [restoring, setRestoring] = useState<number | null>(null);

  const dirtyText = text !== (page.text ?? "");
  const dirtyPrompt = prompt !== (page.image_prompt ?? "");

  useEffect(() => {
    if (tab !== "history" || versions !== null) return;
    getPageVersions(page.id).then(setVersions).catch(() => setVersions([]));
  }, [tab, versions, page.id]);

  const saveText = async () => {
    setSavingText(true);
    try {
      const updated = await updatePage(page.id, { text });
      onUpdate(updated);
      addToast("Tekst zapisany", "success");
    } catch (e) {
      showErrorToast(addToast, e);
    } finally {
      setSavingText(false);
    }
  };

  const savePrompt = async () => {
    setSavingPrompt(true);
    try {
      const updated = await updatePage(page.id, { image_prompt: prompt });
      onUpdate(updated);
      addToast("Prompt zapisany", "success");
    } catch (e) {
      showErrorToast(addToast, e);
    } finally {
      setSavingPrompt(false);
    }
  };

  const regenerate = async () => {
    setRegenerating(true);
    try {
      const updated = await regenerateImage(page.id, prompt);
      onUpdate(updated);
      setVersions(null); // force reload on next history view
      addToast("Wygenerowano nową wersję", "success");
    } catch (e) {
      showErrorToast(addToast, e);
    } finally {
      setRegenerating(false);
    }
  };

  const restore = async (v: ImageVersion) => {
    if (v.image_path === page.current_image_path) return;
    setRestoring(v.id);
    try {
      const updated = await restorePageVersion(page.id, v.id);
      onUpdate(updated);
      addToast("Wersja przywrócona", "success");
    } catch (e) {
      showErrorToast(addToast, e);
    } finally {
      setRestoring(null);
    }
  };

  const tabButton = (id: Tab, label: string) => (
    <button
      onClick={() => setTab(id)}
      className={`px-3 py-2 text-sm font-semibold border-b-2 -mb-px transition-colors ${
        tab === id
          ? "text-teal-600 border-teal-500"
          : "text-bark-400 border-transparent hover:text-bark-600"
      }`}
    >
      {label}
    </button>
  );

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-bark-700/50 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="card-storybook w-full max-w-3xl max-h-[90vh] overflow-y-auto scroll-warm p-6 animate-enter"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start gap-4 mb-5">
          {page.current_image_path ? (
            <img
              src={page.current_image_path}
              alt={pageLabel(page)}
              className="w-20 h-20 rounded-lg object-cover border-2 border-cream-300 flex-shrink-0"
            />
          ) : (
            <div className="w-20 h-20 rounded-lg bg-cream-200 flex-shrink-0" />
          )}
          <div className="flex-1">
            <h2 className="text-lg font-display font-bold text-bark-700">
              {pageLabel(page)}
            </h2>
            <p className="text-xs text-bark-300 mt-0.5">
              wersja v{page.version} · id #{page.id}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-bark-400 hover:text-bark-600 text-xl leading-none"
            aria-label="Zamknij"
          >
            ×
          </button>
        </div>

        <div className="flex gap-1 mb-5 border-b border-bark-200">
          {tabButton("text", "Tekst")}
          {tabButton("prompt", "Prompt obrazka")}
          {tabButton("history", `Historia${page.version > 0 ? ` (${page.version})` : ""}`)}
        </div>

        {tab === "text" && (
          <div className="space-y-3">
            <label className="label-warm">Tekst strony</label>
            <textarea
              className="input-warm h-56 resize-y scroll-warm leading-relaxed"
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Wpisz tekst tej strony..."
            />
            <div className="flex gap-2">
              <button
                onClick={saveText}
                disabled={!dirtyText || savingText}
                className="btn-primary"
              >
                {savingText ? "Zapisywanie..." : "Zapisz tekst"}
              </button>
              {dirtyText && (
                <button
                  onClick={() => setText(page.text ?? "")}
                  className="btn-secondary"
                >
                  Cofnij zmiany
                </button>
              )}
            </div>
          </div>
        )}

        {tab === "prompt" && (
          <div className="space-y-3">
            <label className="label-warm">Prompt do obrazka</label>
            <textarea
              className="input-warm h-56 resize-y font-mono text-xs leading-relaxed scroll-warm"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Opis sceny dla generatora obrazków..."
            />
            <div className="flex flex-wrap gap-2">
              <button
                onClick={savePrompt}
                disabled={!dirtyPrompt || savingPrompt || regenerating}
                className="btn-secondary"
              >
                {savingPrompt ? "Zapisywanie..." : "Zapisz prompt"}
              </button>
              <button
                onClick={regenerate}
                disabled={regenerating || !prompt.trim()}
                className="btn-primary"
                title="Zapisuje prompt i od razu generuje nową wersję obrazka"
              >
                {regenerating ? "Generowanie..." : "Regeneruj obrazek"}
              </button>
              {dirtyPrompt && (
                <button
                  onClick={() => setPrompt(page.image_prompt ?? "")}
                  className="btn-secondary"
                  disabled={savingPrompt || regenerating}
                >
                  Cofnij
                </button>
              )}
            </div>
          </div>
        )}

        {tab === "history" && (
          <div>
            {versions === null ? (
              <div className="flex items-center justify-center py-12">
                <div className="spinner-warm" />
              </div>
            ) : versions.length === 0 ? (
              <p className="text-sm text-bark-400 italic py-8 text-center">
                Brak zapisanych wersji.
              </p>
            ) : (
              <div className="grid gap-4 grid-cols-2 sm:grid-cols-3">
                {versions.map((v) => {
                  const isCurrent = v.image_path === page.current_image_path;
                  return (
                    <div
                      key={v.id}
                      className={`rounded-lg overflow-hidden border-2 ${
                        isCurrent ? "border-teal-500" : "border-transparent"
                      }`}
                    >
                      <div className="aspect-square bg-cream-200 overflow-hidden">
                        <img
                          src={v.image_path}
                          alt={`v${v.version_number}`}
                          className="w-full h-full object-cover"
                        />
                      </div>
                      <div className="p-2 bg-cream-100">
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="text-xs font-bold text-bark-600">
                            v{v.version_number}
                          </span>
                          {isCurrent && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-teal-100 text-teal-700 font-semibold">
                              aktualna
                            </span>
                          )}
                        </div>
                        <p className="text-[10px] text-bark-300">
                          {v.created_at.slice(0, 16).replace("T", " ")}
                        </p>
                        {!isCurrent && (
                          <button
                            onClick={() => restore(v)}
                            disabled={restoring !== null}
                            className="mt-1.5 w-full text-[11px] bg-teal-500/10 text-teal-600 hover:bg-teal-500/20 py-1 rounded font-semibold transition-colors disabled:opacity-50"
                          >
                            {restoring === v.id ? "Przywracanie..." : "Przywróć"}
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
