import { useState } from "react";
import { useNavigate } from "react-router-dom";
import type { ProjectCreateInput } from "../lib/types";
import { createProject } from "../lib/api";

const defaults: ProjectCreateInput = {
  child_name: "",
  child_age: 5,
  child_gender: "dziewczynka",
  hair_color: "",
  hair_style: "",
  skin_tone: "",
  eye_color: "",
  outfit_description: "",
  story_type: "",
  hobby: "",
  moral: "",
};

export default function NewProjectPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState<ProjectCreateInput>({ ...defaults });
  const [submitting, setSubmitting] = useState(false);

  const set = (field: keyof ProjectCreateInput, value: string | number) =>
    setForm((prev) => ({ ...prev, [field]: value }));

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    createProject(form)
      .then((p) => navigate(`/project/${p.id}`))
      .catch((err) => {
        alert("Błąd tworzenia projektu: " + err.message);
        setSubmitting(false);
      });
  };

  return (
    <div className="max-w-2xl mx-auto animate-enter">
      <div className="flex items-center gap-3 mb-8">
        <span className="text-3xl">&#x2728;</span>
        <h1 className="text-2xl font-display font-bold text-bark-700">
          Nowa książeczka
        </h1>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Character info */}
        <div className="card-storybook p-6 space-y-4">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-lg">&#x1F9D2;</span>
            <h2 className="font-display font-bold text-bark-600">Postać</h2>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label-warm">Imię dziecka</label>
              <input
                className="input-warm"
                value={form.child_name}
                onChange={(e) => set("child_name", e.target.value)}
                required
              />
            </div>
            <div>
              <label className="label-warm">Wiek</label>
              <input
                type="number"
                className="input-warm"
                min={2}
                max={12}
                value={form.child_age}
                onChange={(e) => set("child_age", Number(e.target.value))}
                required
              />
            </div>
          </div>

          <div>
            <label className="label-warm">Płeć</label>
            <select
              className="input-warm"
              value={form.child_gender}
              onChange={(e) => set("child_gender", e.target.value)}
            >
              <option value="dziewczynka">Dziewczynka</option>
              <option value="chłopiec">Chłopiec</option>
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label-warm">Kolor włosów</label>
              <input
                className="input-warm"
                value={form.hair_color}
                onChange={(e) => set("hair_color", e.target.value)}
                placeholder="np. blond, brązowe"
                required
              />
            </div>
            <div>
              <label className="label-warm">Fryzura</label>
              <input
                className="input-warm"
                value={form.hair_style}
                onChange={(e) => set("hair_style", e.target.value)}
                placeholder="np. kucyk, krótkie"
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label-warm">Karnacja</label>
              <input
                className="input-warm"
                value={form.skin_tone}
                onChange={(e) => set("skin_tone", e.target.value)}
                placeholder="np. jasna, oliwkowa"
                required
              />
            </div>
            <div>
              <label className="label-warm">Kolor oczu</label>
              <input
                className="input-warm"
                value={form.eye_color}
                onChange={(e) => set("eye_color", e.target.value)}
                placeholder="np. niebieskie, brązowe"
                required
              />
            </div>
          </div>

          <div>
            <label className="label-warm">Ubiór</label>
            <input
              className="input-warm"
              value={form.outfit_description}
              onChange={(e) => set("outfit_description", e.target.value)}
              placeholder="np. czerwona sukienka z białymi kropkami"
              required
            />
          </div>
        </div>

        {/* Story info */}
        <div className="card-storybook p-6 space-y-4">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-lg">&#x1F4D6;</span>
            <h2 className="font-display font-bold text-bark-600">Historia</h2>
          </div>

          <div>
            <label className="label-warm">Motyw historii</label>
            <input
              className="input-warm"
              value={form.story_type}
              onChange={(e) => set("story_type", e.target.value)}
              placeholder="np. magiczna podróż, podwodna przygoda"
              required
            />
          </div>

          <div>
            <label className="label-warm">Hobby / zainteresowanie</label>
            <input
              className="input-warm"
              value={form.hobby}
              onChange={(e) => set("hobby", e.target.value)}
              placeholder="np. malowanie, piłka nożna, taniec"
              required
            />
          </div>

          <div>
            <label className="label-warm">Przesłanie moralne</label>
            <input
              className="input-warm"
              value={form.moral}
              onChange={(e) => set("moral", e.target.value)}
              placeholder="np. wiara w siebie, przyjaźń, odwaga"
              required
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={submitting}
          className="btn-primary w-full py-3.5 text-base"
        >
          {submitting ? "Tworzenie..." : "Stwórz książeczkę"}
        </button>
      </form>
    </div>
  );
}
