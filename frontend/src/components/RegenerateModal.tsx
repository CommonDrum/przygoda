import { useState } from "react";
import type { Page } from "../lib/types";
import { regenerateImage } from "../lib/api";

interface Props {
  page: Page;
  onDone: (updated: Page) => void;
  onClose: () => void;
}

export default function RegenerateModal({ page, onDone, onClose }: Props) {
  const [prompt, setPrompt] = useState(page.image_prompt || "");
  const [loading, setLoading] = useState(false);

  const pageLabel =
    page.page_number === 1
      ? "Okładka"
      : page.page_number === 17
        ? "Tył okładki"
        : `Strona ${page.page_number - 1}`;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    regenerateImage(page.id, prompt)
      .then(onDone)
      .catch((err) => alert("Błąd: " + err.message))
      .finally(() => setLoading(false));
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-bark-700/50 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="card-storybook w-full max-w-lg p-7 animate-enter"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2.5 mb-1">
          <span className="text-xl">&#x1F58C;&#xFE0F;</span>
          <h2 className="text-lg font-display font-bold text-bark-700">
            Regeneruj obrazek
          </h2>
        </div>
        <p className="text-sm text-bark-300 mb-5 ml-8">{pageLabel}</p>

        <form onSubmit={handleSubmit}>
          <label className="label-warm">Prompt obrazka</label>
          <textarea
            className="input-warm h-40 resize-y font-mono text-xs leading-relaxed"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            disabled={loading}
          />

          <div className="flex gap-3 mt-5">
            <button
              type="submit"
              disabled={loading || !prompt.trim()}
              className="btn-primary flex-1"
            >
              {loading ? "Generowanie..." : "Regeneruj"}
            </button>
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="btn-secondary flex-1"
            >
              Anuluj
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
