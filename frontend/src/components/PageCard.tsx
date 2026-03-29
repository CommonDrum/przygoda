import type { Page } from "../lib/types";

function pageLabel(page: Page): string {
  if (page.page_number === 1) return "Okładka";
  if (page.page_number === 17) return "Tył okładki";
  return `Strona ${page.page_number - 1}`;
}

interface Props {
  page: Page;
  generating?: boolean;
  showRegenerate?: boolean;
  onRegenerate?: (pageId: number) => void;
}

export default function PageCard({
  page,
  generating,
  showRegenerate,
  onRegenerate,
}: Props) {
  return (
    <div className="card-storybook overflow-hidden group">
      {/* Image area */}
      <div className="aspect-square bg-cream-200/60 relative flex items-center justify-center overflow-hidden">
        {generating ? (
          <div className="flex flex-col items-center gap-2">
            <div className="spinner-warm" />
            <span className="text-bark-300 text-xs font-medium">Tworzenie...</span>
          </div>
        ) : page.current_image_path ? (
          <img
            src={page.current_image_path}
            alt={pageLabel(page)}
            className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-[1.03]"
          />
        ) : (
          <div className="flex flex-col items-center gap-1.5 text-bark-300">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2" />
              <circle cx="8.5" cy="8.5" r="1.5" />
              <path d="m21 15-5-5L5 21" />
            </svg>
            <span className="text-xs">Brak obrazka</span>
          </div>
        )}
        {page.version > 0 && (
          <span className="absolute top-2 right-2 bg-bark-700/60 text-cream-50 text-[10px] font-bold px-1.5 py-0.5 rounded-md backdrop-blur-sm">
            v{page.version}
          </span>
        )}
      </div>

      {/* Content */}
      <div className="p-3">
        <div className="flex items-center justify-between mb-1">
          <span className="font-semibold text-sm text-bark-600 font-display">
            {pageLabel(page)}
          </span>
        </div>
        {page.text && (
          <p className="text-xs text-bark-300 leading-relaxed line-clamp-3">
            {page.text}
          </p>
        )}
        {showRegenerate && onRegenerate && (
          <button
            onClick={() => onRegenerate(page.id)}
            className="mt-2.5 w-full text-xs bg-teal-500/8 text-teal-600 hover:bg-teal-500/15 py-1.5 rounded-lg font-semibold transition-colors duration-200"
          >
            Regeneruj obrazek
          </button>
        )}
      </div>
    </div>
  );
}
