import { useEffect, useState } from "react";
import type { ImageVersion } from "../lib/types";
import { useToast } from "../context/ToastContext";

interface Props {
  title: string;
  currentImagePath: string | null;
  loadVersions: () => Promise<ImageVersion[]>;
  onRestore: (versionId: number) => Promise<void>;
  onClose: () => void;
}

export default function ImageHistoryModal({
  title,
  currentImagePath,
  loadVersions,
  onRestore,
  onClose,
}: Props) {
  const { addToast } = useToast();
  const [versions, setVersions] = useState<ImageVersion[] | null>(null);
  const [restoring, setRestoring] = useState<number | null>(null);

  useEffect(() => {
    loadVersions()
      .then(setVersions)
      .catch(() => {
        addToast("Nie udało się załadować historii", "error");
        setVersions([]);
      });
  }, [loadVersions, addToast]);

  const restore = async (v: ImageVersion) => {
    if (v.image_path === currentImagePath) return;
    setRestoring(v.id);
    try {
      await onRestore(v.id);
      addToast("Wersja przywrócona", "success");
      onClose();
    } catch {
      addToast("Nie udało się przywrócić", "error");
    } finally {
      setRestoring(null);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-bark-700/50 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="card-storybook w-full max-w-3xl max-h-[85vh] overflow-y-auto scroll-warm p-6 animate-enter"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-display font-bold text-bark-700">
            Historia: {title}
          </h2>
          <button
            onClick={onClose}
            className="text-bark-400 hover:text-bark-600 text-xl leading-none"
            aria-label="Zamknij"
          >
            ×
          </button>
        </div>

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
              const isCurrent = v.image_path === currentImagePath;
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
    </div>
  );
}
