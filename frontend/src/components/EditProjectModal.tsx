import { useState } from "react";
import type { Project, ProjectCreateInput } from "../lib/types";
import { updateProject } from "../lib/api";

interface Props {
  project: Project;
  onSave: (updated: Project) => void;
  onClose: () => void;
}

export default function EditProjectModal({ project, onSave, onClose }: Props) {
  const [form, setForm] = useState<ProjectCreateInput>({
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
  });
  const [saving, setSaving] = useState(false);

  const set = (field: keyof ProjectCreateInput, value: string | number) =>
    setForm((prev) => ({ ...prev, [field]: value }));

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    updateProject(project.id, form)
      .then(onSave)
      .catch((err) => alert("Błąd: " + err.message))
      .finally(() => setSaving(false));
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-bark-700/50 backdrop-blur-sm"
      onClick={onClose}
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
              <input className="input-warm" value={form.child_name} onChange={(e) => set("child_name", e.target.value)} required />
            </div>
            <div>
              <label className="label-warm">Wiek</label>
              <input type="number" className="input-warm" min={2} max={12} value={form.child_age} onChange={(e) => set("child_age", Number(e.target.value))} required />
            </div>
          </div>

          <div>
            <label className="label-warm">Płeć</label>
            <select className="input-warm" value={form.child_gender} onChange={(e) => set("child_gender", e.target.value)}>
              <option value="dziewczynka">Dziewczynka</option>
              <option value="chłopiec">Chłopiec</option>
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3.5">
            <div>
              <label className="label-warm">Kolor włosów</label>
              <input className="input-warm" value={form.hair_color} onChange={(e) => set("hair_color", e.target.value)} required />
            </div>
            <div>
              <label className="label-warm">Fryzura</label>
              <input className="input-warm" value={form.hair_style} onChange={(e) => set("hair_style", e.target.value)} required />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3.5">
            <div>
              <label className="label-warm">Karnacja</label>
              <input className="input-warm" value={form.skin_tone} onChange={(e) => set("skin_tone", e.target.value)} required />
            </div>
            <div>
              <label className="label-warm">Kolor oczu</label>
              <input className="input-warm" value={form.eye_color} onChange={(e) => set("eye_color", e.target.value)} required />
            </div>
          </div>

          <div>
            <label className="label-warm">Ubiór</label>
            <input className="input-warm" value={form.outfit_description} onChange={(e) => set("outfit_description", e.target.value)} required />
          </div>

          <div>
            <label className="label-warm">Motyw historii</label>
            <input className="input-warm" value={form.story_type} onChange={(e) => set("story_type", e.target.value)} required />
          </div>

          <div>
            <label className="label-warm">Hobby</label>
            <input className="input-warm" value={form.hobby} onChange={(e) => set("hobby", e.target.value)} required />
          </div>

          <div>
            <label className="label-warm">Przesłanie moralne</label>
            <input className="input-warm" value={form.moral} onChange={(e) => set("moral", e.target.value)} required />
          </div>

          <div className="flex gap-3 pt-3">
            <button type="submit" disabled={saving} className="btn-primary flex-1">
              {saving ? "Zapisywanie..." : "Zapisz"}
            </button>
            <button type="button" onClick={onClose} className="btn-secondary flex-1">
              Anuluj
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
