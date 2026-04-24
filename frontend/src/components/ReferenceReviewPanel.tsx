import { useEffect, useRef, useState } from "react";
import type { Project } from "../lib/types";
import {
  approveReference,
  regenerateReference,
  uploadReferenceImage,
} from "../lib/api";
import { useToast } from "../context/ToastContext";

interface Props {
  project: Project;
  onUpdate: (p: Project) => void;
  onShowHistory: () => void;
}

export default function ReferenceReviewPanel({
  project,
  onUpdate,
  onShowHistory,
}: Props) {
  const { addToast } = useToast();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [prompt, setPrompt] = useState(project.reference_image_prompt ?? "");
  const [busy, setBusy] = useState<null | "regen" | "approve" | "upload">(null);

  useEffect(() => {
    setPrompt(project.reference_image_prompt ?? "");
  }, [project.reference_image_prompt]);

  const dirtyPrompt = prompt !== (project.reference_image_prompt ?? "");

  const handleRegenerate = async () => {
    setBusy("regen");
    try {
      const updated = await regenerateReference(
        project.id,
        dirtyPrompt ? prompt : undefined,
      );
      onUpdate(updated);
      addToast("Wygenerowano nową wersję postaci", "success");
    } catch {
      addToast("Nie udało się wygenerować", "error");
    } finally {
      setBusy(null);
    }
  };

  const handleApprove = async () => {
    setBusy("approve");
    try {
      const updated = await approveReference(project.id);
      onUpdate(updated);
    } catch {
      addToast("Nie udało się zaakceptować", "error");
    } finally {
      setBusy(null);
    }
  };

  const handleUpload = async (file: File) => {
    setBusy("upload");
    try {
      const updated = await uploadReferenceImage(project.id, file);
      onUpdate(updated);
      addToast("Wgrano własny obraz postaci", "success");
    } catch {
      addToast("Nie udało się wgrać obrazka", "error");
    } finally {
      setBusy(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  return (
    <div className="card-storybook p-5 mb-8 animate-enter">
      <input
        ref={fileInputRef}
        type="file"
        accept="image/png,image/jpeg,image/webp"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) handleUpload(f);
        }}
        className="hidden"
      />

      <div className="flex items-start gap-5">
        {project.reference_image_path ? (
          <div className="relative flex-shrink-0">
            <img
              src={project.reference_image_path}
              alt="Ref"
              className="w-48 h-48 rounded-xl object-cover border-2 border-cream-300 shadow-md"
            />
            <button
              onClick={onShowHistory}
              className="absolute bottom-2 right-2 bg-bark-700/80 text-cream-50 text-xs font-bold px-2 py-1 rounded-md hover:bg-bark-700 transition-colors"
              title="Historia"
            >
              v{project.reference_image_version} · historia
            </button>
          </div>
        ) : (
          <div className="w-48 h-48 rounded-xl bg-cream-200/60 flex items-center justify-center flex-shrink-0">
            <div className="spinner-warm" />
          </div>
        )}

        <div className="flex-1 min-w-0 space-y-3">
          <div>
            <h2 className="font-display font-bold text-bark-700 text-lg">
              Akceptuj obraz postaci
            </h2>
            <p className="text-xs text-bark-400 leading-relaxed mt-0.5">
              {project.reference_image_is_custom
                ? "Używasz własnego wgranego obrazka — prompt AI jest niedostępny. Możesz wgrać inny plik lub kontynuować."
                : "Doprecyzuj prompt, regeneruj aż uzyskasz wygląd postaci, a potem przejdź do generowania historii. Możesz też wgrać własne zdjęcie."}
            </p>
          </div>

          {!project.reference_image_is_custom && (
            <div>
              <label className="label-warm">Prompt obrazka postaci</label>
              <textarea
                className="input-warm h-32 resize-y font-mono text-xs leading-relaxed scroll-warm"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Opis postaci dla generatora obrazków..."
                disabled={busy !== null}
              />
              {dirtyPrompt && (
                <p className="text-xs text-amber-600 mt-1">
                  Zmieniony prompt zostanie użyty przy następnej regeneracji.
                </p>
              )}
            </div>
          )}

          <div className="flex flex-wrap gap-2">
            <button
              onClick={handleRegenerate}
              disabled={busy !== null}
              className="btn-secondary"
            >
              {busy === "regen" ? "Generowanie..." : "Wygeneruj ponownie"}
            </button>
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={busy !== null}
              className="btn-secondary"
            >
              {busy === "upload" ? "Wgrywanie..." : "Wgraj własny obraz"}
            </button>
            <button
              onClick={handleApprove}
              disabled={busy !== null}
              className="btn-primary"
            >
              {busy === "approve" ? "..." : "Akceptuję — generuj historię"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
