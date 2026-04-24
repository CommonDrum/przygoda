import { useEffect, useState, useRef, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import axios from "axios";
import type {
  ExportFormat,
  FulfillmentStatus,
  Page,
  Project,
  ProjectStatus,
  WsMessage,
} from "../lib/types";
import { FULFILLMENT_LABELS, FULFILLMENT_ORDER } from "../lib/types";
import {
  exportProject,
  generateImages,
  generatePrompts,
  generateReference,
  generateStory,
  getPageVersions,
  getPages,
  getProject,
  getReferenceVersions,
  restorePageVersion,
  restoreReference,
  updateProject,
  uploadReferenceImage,
} from "../lib/api";
import { connectWebSocket } from "../lib/ws";
import type { WsConnection, WsStatus } from "../lib/ws";
import { useToast } from "../context/ToastContext";
import StatusBadge from "../components/StatusBadge";
import PageCard from "../components/PageCard";
import EditProjectModal from "../components/EditProjectModal";
import EditPageModal from "../components/EditPageModal";
import ImageHistoryModal from "../components/ImageHistoryModal";
import StyleGuideWidget from "../components/StyleGuideWidget";
import ReferenceReviewPanel from "../components/ReferenceReviewPanel";

type ImageProgressMap = Record<number, "generating" | "completed" | "failed">;

type HistoryTarget =
  | { kind: "page"; pageId: number; title: string; currentImagePath: string | null }
  | { kind: "reference"; title: string; currentImagePath: string | null };

export default function ProjectViewPage() {
  const { id } = useParams<{ id: string }>();
  const projectId = Number(id);
  const { addToast } = useToast();

  const [project, setProject] = useState<Project | null>(null);
  const [pages, setPages] = useState<Page[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [exportLoading, setExportLoading] = useState<ExportFormat | null>(null);

  const [showEditModal, setShowEditModal] = useState(false);
  const [editingPage, setEditingPage] = useState<Page | null>(null);
  const draftUploadRef = useRef<HTMLInputElement | null>(null);
  const [historyTarget, setHistoryTarget] = useState<HistoryTarget | null>(null);
  const [streamingText, setStreamingText] = useState("");
  const [streamingPhase, setStreamingPhase] = useState<string | null>(null);
  const streamRef = useRef<HTMLPreElement | null>(null);

  const [imageStatuses, setImageStatuses] = useState<ImageProgressMap>({});
  const [wsStatus, setWsStatus] = useState<WsStatus>("connected");
  const wsRef = useRef<WsConnection | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([getProject(projectId), getPages(projectId)])
      .then(([proj, pgs]) => {
        setProject(proj);
        setPages(pgs);
      })
      .catch(() => addToast("Nie udało się załadować projektu", "error"))
      .finally(() => setLoading(false));
  }, [projectId, addToast]);

  useEffect(() => {
    load();
    return () => wsRef.current?.close();
  }, [load]);

  // WebSocket — connect once per projectId, rely on WS as source of truth.
  useEffect(() => {
    if (!projectId) return;

    const conn = connectWebSocket(
      projectId,
      (msg: WsMessage) => {
        if (msg.type === "project_status" && msg.status) {
          setProject((prev) =>
            prev ? { ...prev, status: msg.status as ProjectStatus } : prev,
          );
          return;
        }

        if (msg.type === "image_progress" && msg.page_number !== undefined) {
          setImageStatuses((prev) => ({
            ...prev,
            [msg.page_number!]: msg.status as "generating" | "completed" | "failed",
          }));

          if (msg.status === "completed" && msg.image_path) {
            if (msg.page_number === 0) {
              // Reference image — update project locally.
              setProject((prev) =>
                prev
                  ? {
                      ...prev,
                      reference_image_path: msg.image_path!,
                      reference_image_version:
                        msg.version ?? prev.reference_image_version + 1,
                    }
                  : prev,
              );
            } else {
              // Page image — update the page locally. No HTTP fetch.
              setPages((prev) =>
                prev.map((p) =>
                  p.page_number === msg.page_number
                    ? {
                        ...p,
                        current_image_path: msg.image_path!,
                        version: msg.version ?? p.version + 1,
                      }
                    : p,
                ),
              );
            }
          }
        } else if (msg.type === "text_stream" && msg.chunk) {
          setStreamingPhase(msg.phase || null);
          setStreamingText((prev) => prev + msg.chunk);
          requestAnimationFrame(() => {
            if (streamRef.current) {
              streamRef.current.scrollTop = streamRef.current.scrollHeight;
            }
          });
        } else if (msg.type === "text_done") {
          setStreamingText("");
          setStreamingPhase(null);
        }
      },
      setWsStatus,
    );
    wsRef.current = conn;

    return () => conn.close();
  }, [projectId]);

  const runAction = async <T,>(action: () => Promise<T>) => {
    setActionLoading(true);
    try {
      return await action();
    } catch (e: unknown) {
      let msg = "Nieznany błąd";
      if (axios.isAxiosError(e)) {
        msg = e.response?.data?.detail || e.message;
      } else if (e instanceof Error) {
        msg = e.message;
      }
      addToast(msg, "error");
      throw e;
    } finally {
      setActionLoading(false);
    }
  };

  const handleGenerateReference = () =>
    runAction(async () => {
      const updated = await generateReference(projectId);
      setProject(updated);
    }).catch(() => {});

  const handleUploadDraft = async (file: File) => {
    try {
      const updated = await uploadReferenceImage(projectId, file);
      setProject(updated);
      addToast("Wgrano własny obraz postaci", "success");
    } catch {
      addToast("Nie udało się wgrać obrazka", "error");
    } finally {
      if (draftUploadRef.current) draftUploadRef.current.value = "";
    }
  };

  const handleGenerateStory = () =>
    runAction(async () => {
      const updated = await generateStory(projectId);
      setProject(updated);
      // Story text lives on pages — one fetch is OK here (just story completion,
      // no streaming of page images)
      const refreshed = await getPages(projectId);
      setPages(refreshed);
    }).catch(() => {});

  const handleGeneratePrompts = () =>
    runAction(async () => {
      const updated = await generatePrompts(projectId);
      setProject(updated);
      const refreshed = await getPages(projectId);
      setPages(refreshed);
    }).catch(() => {});

  const handleGenerateImages = () =>
    runAction(async () => {
      await generateImages(projectId);
      setImageStatuses({});
      setProject((prev) => (prev ? { ...prev, status: "images_generating" } : prev));
    }).catch(() => {});

  const handleFulfillmentChange = async (next: FulfillmentStatus) => {
    if (!project) return;
    setProject({ ...project, fulfillment_status: next });
    try {
      await updateProject(project.id, { fulfillment_status: next });
    } catch {
      addToast("Nie udało się zapisać statusu", "error");
      load();
    }
  };

  const handleEditPage = (pageId: number) => {
    const page = pages.find((p) => p.id === pageId);
    if (page) setEditingPage(page);
  };

  const handleShowHistory = (pageId: number) => {
    const page = pages.find((p) => p.id === pageId);
    if (!page) return;
    setHistoryTarget({
      kind: "page",
      pageId,
      title: page.page_type === "cover"
        ? "Okładka"
        : page.page_type === "back"
          ? "Tył okładki"
          : `Strona ${page.page_number - 1}`,
      currentImagePath: page.current_image_path,
    });
  };

  const handleExport = (format: ExportFormat) => {
    setExportLoading(format);
    exportProject(projectId, format)
      .then((path) => {
        window.open(path, "_blank");
        addToast("Eksport gotowy", "success");
      })
      .catch(() => addToast("Błąd eksportu", "error"))
      .finally(() => setExportLoading(null));
  };

  if (loading || !project) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="spinner-warm" />
      </div>
    );
  }

  const completedImages = Object.keys(imageStatuses)
    .filter((k) => Number(k) > 0 && imageStatuses[Number(k)] === "completed")
    .length;
  const failedImages = Object.values(imageStatuses).filter((s) => s === "failed").length;
  const showProgress = project.status === "images_generating";

  return (
    <div className="animate-enter">
      {/* Back link */}
      <Link
        to="/"
        className="inline-flex items-center gap-1.5 text-sm font-semibold text-bark-300 hover:text-teal-500 transition-colors mb-5"
      >
        &larr; Projekty
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between mb-8 gap-4">
        <div className="flex items-start gap-4">
          {project.reference_image_path && (
            <div className="relative">
              <img
                src={project.reference_image_path}
                alt="Ref"
                className="w-18 h-18 rounded-xl object-cover border-2 border-cream-300 shadow-md"
                title="Obrazek referencyjny postaci"
              />
              {project.reference_image_version > 0 && (
                <button
                  onClick={() =>
                    setHistoryTarget({
                      kind: "reference",
                      title: "Obrazek postaci",
                      currentImagePath: project.reference_image_path,
                    })
                  }
                  className="absolute -bottom-1 -right-1 bg-bark-700/80 text-cream-50 text-[10px] font-bold px-1.5 py-0.5 rounded-md hover:bg-bark-700 transition-colors"
                  title="Historia"
                >
                  v{project.reference_image_version}
                </button>
              )}
            </div>
          )}
          {(project.status === "ref_pic_generating" ||
            (showProgress && imageStatuses[0] === "generating")) &&
            !project.reference_image_path && (
              <div className="w-18 h-18 rounded-xl border-2 border-cream-300 flex items-center justify-center bg-cream-200/60">
                <div
                  className="spinner-warm"
                  style={{ width: "1.25rem", height: "1.25rem", borderWidth: "2px" }}
                />
              </div>
            )}
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-2xl font-display font-bold text-bark-700">
                {project.child_name}
              </h1>
              <button
                onClick={() => setShowEditModal(true)}
                className="text-bark-300 hover:text-teal-500 transition-colors"
                title="Edytuj projekt"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M17 3a2.85 2.85 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z" />
                </svg>
              </button>
            </div>
            <p className="text-bark-300 text-sm mt-0.5">
              {project.story_type} &middot; {project.hobby}
            </p>
            <p className="text-bark-200 text-xs mt-1">
              LLM: {project.llm_provider} &middot; Obrazki: {project.image_provider}
            </p>
          </div>
        </div>

        <div className="flex flex-col items-end gap-2">
          <StatusBadge status={project.status} />
          <select
            value={project.fulfillment_status}
            onChange={(e) =>
              handleFulfillmentChange(e.target.value as FulfillmentStatus)
            }
            className="text-xs font-semibold px-2 py-1 rounded-lg border border-bark-200 bg-white hover:bg-bark-50 transition-colors"
            title="Status wysyłki"
          >
            {FULFILLMENT_ORDER.map((s) => (
              <option key={s} value={s}>
                {FULFILLMENT_LABELS[s]}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Style guide (shown during editable phases) */}
      {project.status !== "images_generating" && (
        <div className="mb-6">
          <StyleGuideWidget project={project} onUpdate={setProject} />
        </div>
      )}

      {/* Reference review panel — full UI for editing/approving the character ref */}
      {project.status === "ref_pic_review" && (
        <ReferenceReviewPanel
          project={project}
          onUpdate={setProject}
          onShowHistory={() =>
            setHistoryTarget({
              kind: "reference",
              title: "Obrazek postaci",
              currentImagePath: project.reference_image_path,
            })
          }
        />
      )}

      {/* Actions */}
      <div className="flex gap-3 mb-8 flex-wrap">
        {project.status === "draft" && (
          <>
            <input
              ref={draftUploadRef}
              type="file"
              accept="image/png,image/jpeg,image/webp"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) handleUploadDraft(f);
              }}
            />
            <button
              onClick={handleGenerateReference}
              disabled={actionLoading}
              className="btn-primary"
            >
              {actionLoading ? "Generowanie..." : "Generuj obraz postaci"}
            </button>
            <button
              onClick={() => draftUploadRef.current?.click()}
              disabled={actionLoading}
              className="btn-secondary"
              title="Pomiń AI i wgraj własne zdjęcie/szkic postaci"
            >
              Wgraj własny obraz postaci
            </button>
          </>
        )}

        {project.status === "story_generating" && (
          <button
            onClick={handleGenerateStory}
            disabled={actionLoading}
            className="btn-primary"
          >
            {actionLoading ? "Generowanie..." : "Generuj historię"}
          </button>
        )}

        {project.status === "story_generated" && (
          <button
            onClick={handleGeneratePrompts}
            disabled={actionLoading}
            className="btn-primary"
          >
            {actionLoading ? "Generowanie..." : "Generuj opisy obrazków"}
          </button>
        )}

        {project.status === "prompts_generated" && (
          <button
            onClick={handleGenerateImages}
            disabled={actionLoading}
            className="btn-primary"
          >
            {actionLoading ? "Start..." : "Generuj obrazki"}
          </button>
        )}

        {(project.status === "review" || project.status === "exported") && (
          <>
            <button
              onClick={() => handleExport("zip")}
              disabled={exportLoading !== null}
              className="btn-amber"
            >
              {exportLoading === "zip" ? "Eksport..." : "Eksport ZIP"}
            </button>
            <button
              onClick={() => handleExport("txt")}
              disabled={exportLoading !== null}
              className="btn-amber"
            >
              {exportLoading === "txt" ? "Eksport..." : "Eksport TXT"}
            </button>
            <button
              onClick={() => handleExport("excel")}
              disabled={exportLoading !== null}
              className="btn-amber"
            >
              {exportLoading === "excel" ? "Eksport..." : "Eksport Excel"}
            </button>
          </>
        )}
      </div>

      {/* Text streaming overlay */}
      {actionLoading && (streamingText || streamingPhase !== null) && (
        <div className="mb-8 bg-bark-700 rounded-2xl p-5 shadow-lg border border-bark-600/30 animate-enter">
          <div className="flex items-center gap-2.5 mb-3">
            <div
              className="spinner-warm"
              style={{
                width: "1rem",
                height: "1rem",
                borderWidth: "2px",
                borderColor: "var(--color-bark-400)",
                borderTopColor: "var(--color-amber-400)",
              }}
            />
            <span className="text-amber-400 text-sm font-semibold">
              {streamingPhase === "story"
                ? "Tkanie historii..."
                : streamingPhase === "prompts"
                  ? "Tworzenie opisów obrazków..."
                  : streamingPhase === "reference"
                    ? "Opisuję postać..."
                    : "Generowanie..."}
            </span>
          </div>
          <pre
            ref={streamRef}
            className="text-cream-200 text-xs leading-relaxed whitespace-pre-wrap max-h-64 overflow-y-auto font-mono scroll-warm"
          >
            {streamingText || "Czekam na odpowiedź..."}
          </pre>
        </div>
      )}

      {/* WebSocket status banners */}
      {showProgress && wsStatus === "reconnecting" && (
        <div className="mb-4 card-storybook p-4 border-l-4 border-l-amber-400 animate-enter">
          <div className="flex items-center gap-2.5">
            <div className="spinner-warm" style={{ width: "1rem", height: "1rem", borderWidth: "2px" }} />
            <span className="text-sm font-semibold text-amber-500">
              Utracono połączenie, ponawiam...
            </span>
          </div>
        </div>
      )}
      {showProgress && wsStatus === "disconnected" && (
        <div className="mb-4 card-storybook p-4 border-l-4 border-l-rose-400 animate-enter">
          <span className="text-sm font-semibold text-rose-400">
            Nie udało się połączyć. Odśwież stronę.
          </span>
        </div>
      )}

      {/* Inline progress bar */}
      {showProgress && (
        <div className="mb-8 card-storybook p-5 animate-enter">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2.5">
              <div className="spinner-warm" style={{ width: "1rem", height: "1rem", borderWidth: "2px" }} />
              <span className="font-display font-bold text-bark-600">
                Generowanie obrazków
              </span>
            </div>
            <span className="text-sm text-bark-400 font-semibold">
              {completedImages} / 17
            </span>
          </div>
          <div className="w-full bg-cream-300/60 rounded-full h-2 overflow-hidden">
            <div
              className="bg-gradient-to-r from-teal-500 to-teal-600 h-2 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${Math.round((completedImages / 17) * 100)}%` }}
            />
          </div>
          {failedImages > 0 && (
            <p className="text-xs text-red-500 mt-1.5">
              Błędy: {failedImages}
            </p>
          )}
        </div>
      )}

      {/* Pages grid */}
      <div className="grid gap-5 grid-cols-2 sm:grid-cols-3 lg:grid-cols-4">
        {pages.map((page, i) => (
          <div key={page.id} className="animate-enter" style={{ animationDelay: `${i * 40}ms` }}>
            <PageCard
              page={page}
              generating={
                showProgress &&
                imageStatuses[page.page_number] === "generating"
              }
              showRegenerate={
                project.status === "prompts_generated" ||
                project.status === "review" ||
                project.status === "exported"
              }
              showHistory={
                project.status === "review" || project.status === "exported"
              }
              onRegenerate={handleEditPage}
              onShowHistory={handleShowHistory}
            />
          </div>
        ))}
      </div>

      {/* Edit project modal */}
      {showEditModal && (
        <EditProjectModal
          project={project}
          onSave={(updated) => {
            setProject(updated);
            setShowEditModal(false);
            addToast("Projekt zaktualizowany", "success");
          }}
          onClose={() => setShowEditModal(false)}
        />
      )}

      {/* Edit page modal (text + prompt + history) */}
      {editingPage && (
        <EditPageModal
          page={editingPage}
          onUpdate={(updated) => {
            setPages((prev) =>
              prev.map((p) => (p.id === updated.id ? updated : p))
            );
            setEditingPage(updated);
          }}
          onClose={() => setEditingPage(null)}
        />
      )}

      {/* Image history modal */}
      {historyTarget && (
        <ImageHistoryModal
          title={historyTarget.title}
          currentImagePath={historyTarget.currentImagePath}
          loadVersions={() =>
            historyTarget.kind === "page"
              ? getPageVersions(historyTarget.pageId)
              : getReferenceVersions(projectId)
          }
          onRestore={async (versionId) => {
            if (historyTarget.kind === "page") {
              const updated = await restorePageVersion(historyTarget.pageId, versionId);
              setPages((prev) =>
                prev.map((p) => (p.id === updated.id ? updated : p))
              );
            } else {
              const updated = await restoreReference(projectId, versionId);
              setProject(updated);
            }
          }}
          onClose={() => setHistoryTarget(null)}
        />
      )}
    </div>
  );
}
