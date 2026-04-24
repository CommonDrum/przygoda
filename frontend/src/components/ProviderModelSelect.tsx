import type { ModelEntry } from "../lib/types";

interface Props {
  label: string;
  kind: "llm" | "image";
  providerOptions: { value: string; label: string }[];
  provider: string;
  model: string | null;
  catalog: Record<string, ModelEntry[]> | null;
  onProviderChange: (provider: string) => void;
  onModelChange: (model: string | null) => void;
}

export default function ProviderModelSelect({
  label,
  providerOptions,
  provider,
  model,
  catalog,
  onProviderChange,
  onModelChange,
}: Props) {
  const models = catalog?.[provider] ?? [];

  return (
    <div>
      <label className="label-warm">{label}</label>
      <div className="grid grid-cols-[1fr_1.5fr] gap-2">
        <select
          className="input-warm"
          value={provider}
          onChange={(e) => {
            onProviderChange(e.target.value);
            onModelChange(null); // reset model when provider changes
          }}
        >
          {providerOptions.map((p) => (
            <option key={p.value} value={p.value}>
              {p.label}
            </option>
          ))}
        </select>
        <select
          className="input-warm"
          value={model ?? ""}
          onChange={(e) =>
            onModelChange(e.target.value === "" ? null : e.target.value)
          }
          disabled={models.length === 0}
        >
          <option value="">— domyślny —</option>
          {models.map((m) => (
            <option key={m.id} value={m.id}>
              {m.label}
              {m.is_default ? " ★" : ""}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
