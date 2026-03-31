import { useEffect, useState, useRef, useCallback } from "react";
import { useParams } from "react-router-dom";
import type { Project, Page, WsMessage } from "../lib/types";
import {
  getProject,
  getPages,
  generateStory,
  generatePrompts,
  generateImages,
  exportProject,
} from "../lib/api";
import { connectWebSocket } from "../lib/ws";
import StatusBadge from "../components/StatusBadge";
import PageCard from "../components/PageCard";
import EditProjectModal from "../components/EditProjectModal";
import RegenerateModal from "../components/RegenerateModal";

export default function ProjectViewPage() {
  const { id } = useParams<{ id: string }>();
  const projectId = Number(id);

  const [project, setProject] = useState<Project | null>(null);
  const [pages, setPages] = useState<Page[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  const [showEditModal, setShowEditModal] = useState(false);
  const [regenPage, setRegenPage] = useState<Page | null>(null);
  const [streamingText, setStreamingText] = useState("");
  const [streamingPhase, setStreamingPhase] = useState<string | null>(null);
  const streamRef = useRef<HTMLPreElement | null>(null);

  const [imageStatuses, setImageStatuses] = useState<
    Record<number, "generating" | "completed" | "failed">
  >({});
  const wsRef = useRef<WebSocket | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([getProject(projectId), getPages(projectId)])
      .then(([proj, pgs]) => {
        setProject(proj);
        setPages(pgs);
      })
      .catch((e) => console.error("Błąd:", e))
      .finally(() => setLoading(false));
  }, [projectId]);

  useEffect(() => {
    load();
    return () => wsRef.current?.close();
  }, [load]);

  useEffect(() => {
    if (!project) return;

    const ws = connectWebSocket(projectId, (msg: WsMessage) => {
      if (msg.type === "image_progress" && msg.page_number !== undefined) {
        setImageStatuses((prev) => ({
          ...prev,
          [msg.page_number!]: msg.status as "generating" | "completed" | "failed",
        }));
        if (msg.status === "completed") {
          if (msg.page_number === 0) {
            getProject(projectId).then(setProject);
          } else {
            getPages(projectId).then(setPages);
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
    });
    wsRef.current = ws;

    return () => ws.close();
  }, [project?.id, projectId]);

  useEffect(() => {
    const completedCount = Object.values(imageStatuses).filter(
      (s) => s === "completed"
    ).length;
    if (completedCount === 18 && project?.status === "images_generating") {
      getProject(projectId).then(setProject);
    }
  }, [imageStatuses, project?.status, projectId]);

  const handleAction = async (action: () => Promise<Project | void>) => {
    setActionLoading(true);
    try {
      const result = await action();
      if (result && "id" in result) setProject(result);
      load();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Nieznany błąd";
      alert("Błąd: " + msg);
    } finally {
      setActionLoading(false);
    }
  };

  const handleRegenerate = (pageId: number) => {
    const page = pages.find((p) => p.id === pageId);
    if (page) setRegenPage(page);
  };

  const handleExport = (format: "zip" | "excel") => {
    exportProject(projectId, format).then((path) => {
      window.open(path, "_blank");
    });
  };

  if (loading || !project) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="spinner-warm" />
      </div>
    );
  }

  const completedImages = Object.values(imageStatuses).filter(
    (s) => s === "completed"
  ).length;
  const showProgress = project.status === "images_generating";

  return (
    <div className="animate-enter">
      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div className="flex items-start gap-4">
          {project.reference_image_path && (
            <img
              src={project.reference_image_path}
              alt="Ref"
              className="w-18 h-18 rounded-xl object-cover border-2 border-cream-300 shadow-md"
              title="Obrazek referencyjny postaci"
            />
          )}
          {showProgress && imageStatuses[0] === "generating" && !project.reference_image_path && (
            <div className="w-18 h-18 rounded-xl border-2 border-cream-300 flex items-center justify-center bg-cream-200/60">
              <div className="spinner-warm" style={{ width: "1.25rem", height: "1.25rem", borderWidth: "2px" }} />
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
          </div>
        </div>
        <StatusBadge status={project.status} />
      </div>

      {/* Actions */}
      <div className="flex gap-3 mb-8 flex-wrap">
        {project.status === "draft" && (
          <button
            onClick={() => handleAction(() => generateStory(projectId))}
            disabled={actionLoading}
            className="btn-primary"
          >
            {actionLoading ? (
              <>
                <div className="spinner-warm" style={{ width: "1rem", height: "1rem", borderWidth: "2px" }} />
                Generowanie...
              </>
            ) : (
              "Generuj historię"
            )}
          </button>
        )}
        {project.status === "story_generated" && (
          <button
            onClick={() => handleAction(() => generatePrompts(projectId))}
            disabled={actionLoading}
            className="btn-primary"
          >
            {actionLoading ? (
              <>
                <div className="spinner-warm" style={{ width: "1rem", height: "1rem", borderWidth: "2px" }} />
                Generowanie...
              </>
            ) : (
              "Generuj prompty obrazków"
            )}
          </button>
        )}
        {project.status === "prompts_generated" && (
          <button
            onClick={() =>
              handleAction(async () => {
                await generateImages(projectId);
                setImageStatuses({});
                setProject({ ...project, status: "images_generating" });
              })
            }
            disabled={actionLoading}
            className="btn-primary"
          >
            {actionLoading ? "Start..." : "Generuj obrazki"}
          </button>
        )}
        {(project.status === "review" || project.status === "exported") && (
          <>
            <button onClick={() => handleExport("zip")} className="btn-amber">
              Eksport ZIP
            </button>
            <button onClick={() => handleExport("excel")} className="btn-amber">
              Eksport Excel
            </button>
          </>
        )}
      </div>

      {/* Text streaming overlay */}
      {actionLoading && (streamingText || streamingPhase !== null) && (
        <div className="mb-8 bg-bark-700 rounded-2xl p-5 shadow-lg border border-bark-600/30 animate-enter">
          <div className="flex items-center gap-2.5 mb-3">
            <div className="spinner-warm" style={{ width: "1rem", height: "1rem", borderWidth: "2px", borderColor: "var(--color-bark-400)", borderTopColor: "var(--color-amber-400)" }} />
            <span className="text-amber-400 text-sm font-semibold">
              {streamingPhase === "story"
                ? "Tkanie historii..."
                : streamingPhase === "prompts"
                  ? "Tworzenie promptów..."
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
              {completedImages} / 18
            </span>
          </div>
          <div className="w-full bg-cream-300/60 rounded-full h-2 overflow-hidden">
            <div
              className="bg-gradient-to-r from-teal-500 to-teal-600 h-2 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${Math.round((completedImages / 18) * 100)}%` }}
            />
          </div>
          {Object.values(imageStatuses).filter((s) => s === "failed").length > 0 && (
            <p className="text-xs text-red-500 mt-1.5">
              Błędy: {Object.values(imageStatuses).filter((s) => s === "failed").length}
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
                project.status === "review" || project.status === "exported"
              }
              onRegenerate={handleRegenerate}
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
          }}
          onClose={() => setShowEditModal(false)}
        />
      )}

      {/* Regenerate image modal */}
      {regenPage && (
        <RegenerateModal
          page={regenPage}
          onDone={(updated) => {
            setPages((prev) =>
              prev.map((p) => (p.id === updated.id ? updated : p))
            );
            setRegenPage(null);
          }}
          onClose={() => setRegenPage(null)}
        />
      )}
    </div>
  );
}
