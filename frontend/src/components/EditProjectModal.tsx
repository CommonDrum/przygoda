import { useEffect, useState } from "react";
import type {
  ModelCatalog,
  Project,
  ProjectUpdateInput,
  Prompt,
} from "../lib/types";
import { updateProject, listPrompts, getModelCatalog } from "../lib/api";
import { useToast } from "../context/ToastContext";
import ProviderModelSelect from "./ProviderModelSelect";

const LLM_PROVIDERS = [
  { value: "anthropic", label: "Anthropic" },
  { value: "openai", label: "OpenAI" },
  { value: "google", label: "Google" },
];

const IMAGE_PROVIDERS = [
  { value: "google", label: "Google (Gemini)" },
  { value: "openai", label: "OpenAI (GPT-Image / DALL·E)" },
];

interface Props {
  project: Project;
  onSave: (updated: Project) => void;
  onClose: () => void;
}

export default function EditProjectModal({ project, onSave, onClose }: Props) {
  const { addToast } = useToast();
  const [form, setForm] = useState<ProjectUpdateInput>({
    child_name: project.child_name,
    child_age: project.child_age,
    child_gender: project.child_gender,
    hair_color: project.hair_color,
    hair_style: project.hair_style,
    skin_tone: project.skin_tone,
    eye_color: project.eye_color,
    outfit_description: project.outfit_description,
    story_type: project.story_type,
    hobby: project.hobby,
    moral: project.moral,
    llm_provider: project.llm_provider,
    llm_model: project.llm_model,
    image_provider: project.image_provider,
    image_model: project.image_model,
    story_prompt_id: project.story_prompt_id,
    image_prompt_id: project.image_prompt_id,
  });
  const [saving, setSaving] = useState(false);
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const [catalog, setCatalog] = useState<ModelCatalog | null>(null);

  useEffect(() => {
    listPrompts().then(setPrompts).catch(() => {});
    getModelCatalog().then(setCatalog).catch(() => {});
  }, []);

  const storyPrompts = prompts.filter((p) => p.kind === "story");
  const imagePrompts = prompts.filter((p) => p.kind === "image");

  const set = (
    field: keyof ProjectUpdateInput,
    value: string | number | null,
  ) => setForm((prev) => ({ ...prev, [field]: value }));

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    updateProject(project.id, form)
      .then(onSave)
      .catch((err) => addToast("Błąd: " + err.message, "error"))
      .finally(() => setSaving(false));
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-bark-700/50 backdrop-blur-sm"
      onClick={saving ? undefined : onClose}
    >
      <div
        className="card-storybook w-full max-w-lg max-h-[90vh] overflow-y-auto scroll-warm p-7 animate-enter"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2.5 mb-5">
          <span className="text-xl">&#x270F;&#xFE0F;</span>
          <h2 className="text-lg font-display font-bold text-bark-700">
            Edytuj projekt
          </h2>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3.5">
          <div className="grid grid-cols-2 gap-3.5">
            <div>
              <label className="label-warm">Imię</label>
              <input className="input-warm" value={form.child_name ?? ""} onChange={(e) => set("child_name", e.target.value)} required />
            </div>
            <div>
              <label className="label-warm">Wiek</label>
              <input type="number" className="input-warm" min={2} max={12} value={form.child_age ?? 5} onChange={(e) => set("child_age", Number(e.target.value))} required />
            </div>
          </div>

          <div>
            <label className="label-warm">Płeć</label>
            <select className="input-warm" value={form.child_gender ?? ""} onChange={(e) => set("child_gender", e.target.value)}>
              <option value="dziewczynka">Dziewczynka</option>
              <option value="chłopiec">Chłopiec</option>
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3.5">
            <div>
              <label className="label-warm">Kolor włosów</label>
              <input className="input-warm" value={form.hair_color ?? ""} onChange={(e) => set("hair_color", e.target.value)} required />
            </div>
            <div>
              <label className="label-warm">Fryzura</label>
              <input className="input-warm" value={form.hair_style ?? ""} onChange={(e) => set("hair_style", e.target.value)} required />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3.5">
            <div>
              <label className="label-warm">Karnacja</label>
              <input className="input-warm" value={form.skin_tone ?? ""} onChange={(e) => set("skin_tone", e.target.value)} required />
            </div>
            <div>
              <label className="label-warm">Kolor oczu</label>
              <input className="input-warm" value={form.eye_color ?? ""} onChange={(e) => set("eye_color", e.target.value)} required />
            </div>
          </div>

          <div>
            <label className="label-warm">Ubiór</label>
            <input className="input-warm" value={form.outfit_description ?? ""} onChange={(e) => set("outfit_description", e.target.value)} required />
          </div>

          <div>
            <label className="label-warm">Motyw historii</label>
            <input className="input-warm" value={form.story_type ?? ""} onChange={(e) => set("story_type", e.target.value)} required />
          </div>

          <div>
            <label className="label-warm">Hobby</label>
            <input className="input-warm" value={form.hobby ?? ""} onChange={(e) => set("hobby", e.target.value)} required />
          </div>

          <div>
            <label className="label-warm">Przesłanie moralne</label>
            <input className="input-warm" value={form.moral ?? ""} onChange={(e) => set("moral", e.target.value)} required />
          </div>

          <ProviderModelSelect
            label="Tekst (LLM)"
            kind="llm"
            providerOptions={LLM_PROVIDERS}
            provider={form.llm_provider ?? project.llm_provider}
            model={form.llm_model ?? null}
            catalog={catalog?.llm ?? null}
            onProviderChange={(p) =>
              setForm((prev) => ({ ...prev, llm_provider: p, llm_model: null }))
            }
            onModelChange={(m) => set("llm_model", m)}
          />

          <ProviderModelSelect
            label="Obrazki"
            kind="image"
            providerOptions={IMAGE_PROVIDERS}
            provider={form.image_provider ?? project.image_provider}
            model={form.image_model ?? null}
            catalog={catalog?.image ?? null}
            onProviderChange={(p) =>
              setForm((prev) => ({
                ...prev,
                image_provider: p,
                image_model: null,
              }))
            }
            onModelChange={(m) => set("image_model", m)}
          />

          <div className="grid grid-cols-2 gap-3.5">
            <div>
              <label className="label-warm">Prompt historii</label>
              <select
                className="input-warm"
                value={form.story_prompt_id ?? ""}
                onChange={(e) =>
                  set(
                    "story_prompt_id",
                    e.target.value ? Number(e.target.value) : null,
                  )
                }
              >
                <option value="">— domyślny —</option>
                {storyPrompts.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.title}
                    {p.is_default ? " (domyślny)" : ""}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="label-warm">Prompt obrazków</label>
              <select
                className="input-warm"
                value={form.image_prompt_id ?? ""}
                onChange={(e) =>
                  set(
                    "image_prompt_id",
                    e.target.value ? Number(e.target.value) : null,
                  )
                }
              >
                <option value="">— domyślny —</option>
                {imagePrompts.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.title}
                    {p.is_default ? " (domyślny)" : ""}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex gap-3 pt-3">
            <button type="submit" disabled={saving} className="btn-primary flex-1">
              {saving ? "Zapisywanie..." : "Zapisz"}
            </button>
            <button type="button" onClick={onClose} disabled={saving} className="btn-secondary flex-1">
              Anuluj
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
