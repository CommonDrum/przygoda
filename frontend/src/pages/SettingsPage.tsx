import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { AppSettings } from "../lib/types";
import { getSettings, updateSettings, validateApiKey } from "../lib/api";
import { useToast } from "../context/ToastContext";

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
    google_api_key: "",
    default_llm_provider: "anthropic",
    default_image_provider: "google",
    image_aspect_ratio: "1:1",
    image_size: "1K",
  });
  const { addToast } = useToast();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [validation, setValidation] = useState<
    Record<string, ValidationState>
  >({
    anthropic: { loading: false, result: null },
    openai: { loading: false, result: null },
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
      .then((s) => {
        setSettings(s);
        addToast("Zapisano", "success");
      })
      .catch((e) => addToast("Błąd zapisu: " + e.message, "error"))
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
              <option value="google">Google (Gemini)</option>
              <option value="openai">OpenAI (GPT-Image / DALL·E)</option>
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
              <option value="1K">1K (~1024px)</option>
              <option value="2K">2K (~2048px)</option>
            </select>
          </div>
        </div>
      </section>

      {/* Prompts library link */}
      <section className="card-storybook p-6">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-base">&#x1F4DD;</span>
          <h2 className="font-display font-bold text-bark-600">Prompty systemowe</h2>
        </div>
        <p className="text-sm text-bark-400 mb-4">
          Biblioteka promptów historii i obrazków ma osobny ekran — możesz zapisywać wiele wariantów
          z tytułem i wybierać je przy tworzeniu projektu.
        </p>
        <Link
          to="/prompts"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold bg-bark-700 text-cream-50 hover:bg-bark-600 transition-colors"
        >
          Otwórz bibliotekę promptów →
        </Link>
      </section>
    </div>
  );
}
