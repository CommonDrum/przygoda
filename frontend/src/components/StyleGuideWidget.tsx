import { useRef, useState } from "react";
import { deleteStyleGuide, uploadStyleGuide } from "../lib/api";
import { useToast } from "../context/ToastContext";
import type { Project } from "../lib/types";

interface Props {
  project: Project;
  onUpdate: (p: Project) => void;
}

export default function StyleGuideWidget({ project, onUpdate }: Props) {
  const { addToast } = useToast();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [busy, setBusy] = useState(false);

  const pickFile = () => inputRef.current?.click();

  const handleFile = async (file: File) => {
    setBusy(true);
    try {
      const updated = await uploadStyleGuide(project.id, file);
      onUpdate(updated);
      addToast("Style guide wgrany", "success");
    } catch {
      addToast("Nie udało się wgrać obrazka stylu", "error");
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  const handleRemove = async () => {
    if (!confirm("Usunąć style guide? Przyszłe generacje obrazków nie będą go używać.")) return;
    setBusy(true);
    try {
      const updated = await deleteStyleGuide(project.id);
      onUpdate(updated);
      addToast("Style guide usunięty", "success");
    } catch {
      addToast("Nie udało się usunąć", "error");
    } finally {
      setBusy(false);
    }
  };

  const hasImage = !!project.style_guide_image_path;

  return (
    <div className="card-storybook p-4 flex items-center gap-4">
      <input
        ref={inputRef}
        type="file"
        accept="image/png,image/jpeg,image/webp"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) handleFile(f);
        }}
        className="hidden"
      />

      {hasImage ? (
        <img
          src={project.style_guide_image_path!}
          alt="Style guide"
          className="w-16 h-16 rounded-lg object-cover border-2 border-cream-300 flex-shrink-0"
          title="Przewodnik stylu książki"
        />
      ) : (
        <div className="w-16 h-16 rounded-lg bg-cream-200/60 border-2 border-dashed border-bark-200 flex items-center justify-center flex-shrink-0 text-bark-300 text-xl">
          ✧
        </div>
      )}

      <div className="flex-1 min-w-0">
        <p className="text-sm font-display font-bold text-bark-700">
          Style guide <span className="text-bark-300 font-normal">(opcjonalny)</span>
        </p>
        <p className="text-xs text-bark-400 leading-relaxed">
          {hasImage
            ? "Ten obrazek nadaje styl wszystkim ilustracjom w książce."
            : "Wgraj obraz referencyjny, który zadecyduje o stylu całej książki (paleta, kreska, atmosfera)."}
        </p>
      </div>

      <div className="flex flex-col gap-1.5 flex-shrink-0">
        <button
          onClick={pickFile}
          disabled={busy}
          className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-teal-500/10 text-teal-600 hover:bg-teal-500/20 transition-colors disabled:opacity-50"
        >
          {hasImage ? "Zmień" : "Wgraj"}
        </button>
        {hasImage && (
          <button
            onClick={handleRemove}
            disabled={busy}
            className="text-xs font-semibold px-3 py-1.5 rounded-lg text-rose-400 hover:bg-rose-50 transition-colors disabled:opacity-50"
          >
            Usuń
          </button>
        )}
      </div>
    </div>
  );
}
