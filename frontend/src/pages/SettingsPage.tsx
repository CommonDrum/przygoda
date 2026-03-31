import { useEffect, useState } from "react";
import type { AppSettings } from "../lib/types";
import { getSettings, updateSettings, validateApiKey } from "../lib/api";

const defaultStoryPrompt = `Jesteś mistrzem opowieści tworzącym spersonalizowane książeczki dla dzieci.

POSTAĆ:
- Imię: {name}
- Wiek: {age}
- Płeć: {gender}
- Wygląd: {hair_color} włosy, {skin_tone} karnacja, {eye_color} oczy, fryzura: {haircut}
- Osobowość: ciekawska, odważna, adekwatna do wieku {age}

ZADANIE:
Napisz historię w dokładnie 15 częściach. Każda część: ~150 słów.
Oddziel części separatorem: #########

MOTYW: {story_type}
HOBBY GŁÓWNE: {hobby}
PRZESŁANIE MORALNE: {moral}

STRUKTURA NARRACYJNA:
- Części 1-2: Wprowadzenie świata i bohatera. Zacznij od akcji lub intrygi.
- Części 3-4: Pojawia się wyzwanie związane z {hobby}.
- Części 5-10: Podróż i rozwój. {name} pokonuje przeciwności, zaczyna wierzyć w siebie coraz bardziej. Pokaż momenty zwątpienia i przełomu. "Wiara potrafi góry przenosić."
- Części 11-13: Kulminacja. Największa próba i triumf.
- Części 14-15: Refleksja. Przesłanie moralne wplecione naturalnie, nie jako kazanie.

ZASADY:
- Tylko {name} jako główna postać. Postacie drugoplanowe pojawiają się epizodycznie, NIGDY nie wracają w kolejnych częściach.
- Opisy sensoryczne: kolory, dźwięki, zapachy, tekstury.
- Język dostosowany do dziecka w wieku {age} lat.
- Podróż emocjonalna: napięcie → zachwyt → zwątpienie → triumf.
- Unikaj myślnika jako znaku interpunkcyjnego.
- Każda część to kompletna scena z początkiem, środkiem i końcem.`;

const defaultImagePrompt = `You are a visual prompt engineer creating image generation prompts for a children's storybook.

INPUT: A 15-part story about {name} + cover and back page.
OUTPUT: Exactly 18 prompts separated by #########

CHARACTER (must be identical in EVERY prompt):
- {name}, {age} years old, {gender}
- {hair_color} hair, {haircut} hairstyle
- {skin_tone} skin tone, {eye_color} eyes
- Clothing: {outfit_description}

STYLE LOCK:
- Art style: Warm children's book illustration, soft painterly textures
- Palette: Vibrant but not oversaturated
- Quality tags: high quality, detailed illustration, professional children's book art
- Lighting: Warm golden hour unless scene requires otherwise

PROMPT 1 (character reference sheet — generated FIRST, used as visual reference for all other images):
"Full-body character reference sheet. {name}, a {age}-year-old {gender} with {skin_tone} skin, {eye_color} eyes, and {hair_color} {haircut} hair, wearing {outfit_description}. Standing in a neutral pose, front-facing, clear full-body view. Plain white background. No text, no environment, no other characters. Children's book illustration style, high quality, detailed. --ar 1:1"

PROMPT 2 (cover):
"Children's book cover. {name}, a {age}-year-old {gender} with {skin_tone} skin, {eye_color} eyes, {hair_color} {haircut} hair, wearing {outfit_description}. [Dynamic pose in key environment]. Title text 'Przygoda {name}' at top in playful hand-drawn font. Vibrant, magical atmosphere, Pixar-inspired fairytale realism. --ar 1:1"

PROMPT TEMPLATE (prompts 3-17, story illustrations):
"[Scene from story segment]. {name}, a {age}-year-old {gender} with {skin_tone} skin, {eye_color} eyes, and {hair_color} {haircut} hair, wearing {outfit_description}. [Action and expression]. [Environment and lighting]. [Composition: wide/medium/close-up]. Children's book illustration style, high quality, detailed. --ar 1:1"

PROMPT 18 (back page):
"Children's book back cover. Soft, warm scene with symbolic object representing {moral}. Text 'Koniec' in center. Gentle sunset lighting, dreamy atmosphere. --ar 1:1"

CRITICAL RULES:
- Character description MUST be copy-pasted identically in every prompt. No variation. No new characters.
- ONLY {name} appears in illustrations. No other humanoid characters.
- One clear focal action per scene. No split scenes.
- Specify shot type: establishing wide, medium, or close-up.
- Include emotional state: expression of wonder, determination, etc.`;

type ValidationState = {
  loading: boolean;
  result: { valid: boolean; error?: string } | null;
};

function ApiKeyField({
  label,
  placeholder,
  value,
  onChange,
  provider,
  validationState,
  onTest,
}: {
  label: string;
  placeholder?: string;
  value: string;
  onChange: (val: string) => void;
  provider: string;
  validationState: ValidationState;
  onTest: (provider: string) => void;
}) {
  const hasSavedKey = value.includes("•");

  return (
    <div>
      <label className="label-warm">{label}</label>
      <div className="flex gap-2">
        <input
          type="password"
          className="input-warm font-mono flex-1"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
        />
        <button
          type="button"
          onClick={() => onTest(provider)}
          disabled={validationState.loading}
          className="px-3 py-1.5 text-sm font-semibold rounded-lg border border-bark-200 bg-white hover:bg-bark-50 text-bark-600 transition-colors disabled:opacity-50 whitespace-nowrap"
        >
          {validationState.loading ? "..." : "Testuj"}
        </button>
      </div>
      <div className="flex items-center gap-2 mt-1 min-h-[1.25rem]">
        {hasSavedKey && (
          <span className="text-xs text-bark-400 font-mono">
            {value.replace(/•+/, "•••")}
          </span>
        )}
        {validationState.result && (
          <span
            className={`text-xs font-semibold ${validationState.result.valid ? "text-green-600" : "text-red-500"}`}
          >
            {validationState.result.valid
              ? "Klucz działa"
              : validationState.result.error || "Nieprawidłowy klucz"}
          </span>
        )}
      </div>
    </div>
  );
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<AppSettings>({
    anthropic_api_key: "",
    openai_api_key: "",
    nano_banana_api_key: "",
    google_api_key: "",
    default_llm_provider: "anthropic",
    default_image_provider: "nano_banana",
    image_aspect_ratio: "1:1",
    image_size: "1K",
    story_system_prompt: defaultStoryPrompt,
    image_system_prompt: defaultImagePrompt,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [validation, setValidation] = useState<
    Record<string, ValidationState>
  >({
    anthropic: { loading: false, result: null },
    openai: { loading: false, result: null },
    nano_banana: { loading: false, result: null },
    google: { loading: false, result: null },
  });

  const testKey = async (provider: string) => {
    setValidation((v) => ({
      ...v,
      [provider]: { loading: true, result: null },
    }));
    try {
      const result = await validateApiKey(provider);
      setValidation((v) => ({ ...v, [provider]: { loading: false, result } }));
    } catch {
      setValidation((v) => ({
        ...v,
        [provider]: {
          loading: false,
          result: { valid: false, error: "Błąd połączenia" },
        },
      }));
    }
  };

  useEffect(() => {
    getSettings()
      .then(setSettings)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const save = (partial: Partial<AppSettings>) => {
    setSaving(true);
    updateSettings(partial)
      .then(setSettings)
      .catch((e) => alert("Błąd zapisu: " + e.message))
      .finally(() => setSaving(false));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="spinner-warm" />
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-enter">
      <div className="flex items-center gap-3 mb-2">
        <span className="text-2xl">&#x2699;&#xFE0F;</span>
        <h1 className="text-2xl font-display font-bold text-bark-700">Opcje</h1>
      </div>

      {/* API Keys */}
      <section className="card-storybook p-6 space-y-4">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-base">&#x1F511;</span>
          <h2 className="font-display font-bold text-bark-600">Klucze API</h2>
        </div>

        <ApiKeyField
          label="Anthropic API Key"
          placeholder="sk-ant-..."
          value={settings.anthropic_api_key}
          onChange={(val) =>
            setSettings((s) => ({ ...s, anthropic_api_key: val }))
          }
          provider="anthropic"
          validationState={validation.anthropic}
          onTest={testKey}
        />

        <ApiKeyField
          label="OpenAI API Key"
          placeholder="sk-..."
          value={settings.openai_api_key}
          onChange={(val) =>
            setSettings((s) => ({ ...s, openai_api_key: val }))
          }
          provider="openai"
          validationState={validation.openai}
          onTest={testKey}
        />

        <ApiKeyField
          label="Nano Banana API Key"
          value={settings.nano_banana_api_key}
          onChange={(val) =>
            setSettings((s) => ({ ...s, nano_banana_api_key: val }))
          }
          provider="nano_banana"
          validationState={validation.nano_banana}
          onTest={testKey}
        />

        <ApiKeyField
          label="Google API Key (Gemini)"
          placeholder="AIzaSy..."
          value={settings.google_api_key}
          onChange={(val) =>
            setSettings((s) => ({ ...s, google_api_key: val }))
          }
          provider="google"
          validationState={validation.google}
          onTest={testKey}
        />

        <button
          onClick={() =>
            save({
              anthropic_api_key: settings.anthropic_api_key,
              openai_api_key: settings.openai_api_key,
              nano_banana_api_key: settings.nano_banana_api_key,
              google_api_key: settings.google_api_key,
            })
          }
          disabled={saving}
          className="btn-primary"
        >
          {saving ? "Zapisywanie..." : "Zapisz klucze"}
        </button>
      </section>

      {/* Default providers */}
      <section className="card-storybook p-6 space-y-4">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-base">&#x1F527;</span>
          <h2 className="font-display font-bold text-bark-600">Domyślne providery</h2>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="label-warm">LLM Provider</label>
            <select
              className="input-warm"
              value={settings.default_llm_provider}
              onChange={(e) => {
                const val = e.target.value;
                setSettings((s) => ({ ...s, default_llm_provider: val }));
                save({ default_llm_provider: val });
              }}
            >
              <option value="anthropic">Anthropic (Claude)</option>
              <option value="openai">OpenAI (GPT)</option>
              <option value="google">Google (Gemini)</option>
            </select>
          </div>
          <div>
            <label className="label-warm">Image Provider</label>
            <select
              className="input-warm"
              value={settings.default_image_provider}
              onChange={(e) => {
                const val = e.target.value;
                setSettings((s) => ({ ...s, default_image_provider: val }));
                save({ default_image_provider: val });
              }}
            >
              <option value="nano_banana">Nano Banana</option>
              <option value="dalle">DALL-E 3</option>
              <option value="google">Google (Gemini)</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="label-warm">Aspect Ratio</label>
            <select
              className="input-warm"
              value={settings.image_aspect_ratio}
              onChange={(e) => {
                const val = e.target.value;
                setSettings((s) => ({ ...s, image_aspect_ratio: val }));
                save({ image_aspect_ratio: val });
              }}
            >
              <option value="1:1">1:1 (kwadrat)</option>
              <option value="3:4">3:4 (portret)</option>
              <option value="4:3">4:3 (krajobraz)</option>
              <option value="9:16">9:16 (portret wąski)</option>
              <option value="16:9">16:9 (panorama)</option>
              <option value="2:3">2:3</option>
              <option value="3:2">3:2</option>
            </select>
          </div>
          <div>
            <label className="label-warm">Rozdzielczość</label>
            <select
              className="input-warm"
              value={settings.image_size}
              onChange={(e) => {
                const val = e.target.value;
                setSettings((s) => ({ ...s, image_size: val }));
                save({ image_size: val });
              }}
            >
              <option value="512">512 (0.5K)</option>
              <option value="1K">1K</option>
              <option value="2K">2K</option>
              <option value="4K">4K</option>
            </select>
          </div>
        </div>
      </section>

      {/* Prompts */}
      <section className="card-storybook p-6 space-y-4">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-base">&#x1F4DD;</span>
          <h2 className="font-display font-bold text-bark-600">Prompty systemowe</h2>
        </div>

        <div>
          <div className="flex justify-between items-center mb-1.5">
            <label className="label-warm mb-0">Prompt generowania historii</label>
            <button
              onClick={() => {
                setSettings((s) => ({
                  ...s,
                  story_system_prompt: defaultStoryPrompt,
                }));
              }}
              className="text-xs text-teal-500 hover:text-teal-600 font-semibold transition-colors"
            >
              Przywróć domyślne
            </button>
          </div>
          <textarea
            className="input-warm h-64 font-mono text-xs leading-relaxed resize-y scroll-warm"
            value={settings.story_system_prompt}
            onChange={(e) =>
              setSettings((s) => ({
                ...s,
                story_system_prompt: e.target.value,
              }))
            }
          />
        </div>

        <div>
          <div className="flex justify-between items-center mb-1.5">
            <label className="label-warm mb-0">Prompt generowania obrazków</label>
            <button
              onClick={() => {
                setSettings((s) => ({
                  ...s,
                  image_system_prompt: defaultImagePrompt,
                }));
              }}
              className="text-xs text-teal-500 hover:text-teal-600 font-semibold transition-colors"
            >
              Przywróć domyślne
            </button>
          </div>
          <textarea
            className="input-warm h-64 font-mono text-xs leading-relaxed resize-y scroll-warm"
            value={settings.image_system_prompt}
            onChange={(e) =>
              setSettings((s) => ({
                ...s,
                image_system_prompt: e.target.value,
              }))
            }
          />
        </div>

        <button
          onClick={() =>
            save({
              story_system_prompt: settings.story_system_prompt,
              image_system_prompt: settings.image_system_prompt,
            })
          }
          disabled={saving}
          className="btn-primary"
        >
          {saving ? "Zapisywanie..." : "Zapisz prompty"}
        </button>
      </section>
    </div>
  );
}
