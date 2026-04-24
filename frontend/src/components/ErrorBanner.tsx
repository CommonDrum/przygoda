import type { FriendlyError } from "../lib/errors";

interface Props {
  error: FriendlyError;
  onRetry?: () => void;
  onDismiss?: () => void;
  compact?: boolean;
}

/**
 * Consistent error card for the app. Shows title + hint, and a "Spróbuj
 * ponownie" button for retryable errors. Non-technical users see this — no
 * status codes or stack traces.
 */
export default function ErrorBanner({ error, onRetry, onDismiss, compact }: Props) {
  return (
    <div
      className={`card-storybook border-l-4 border-l-rose-400 ${
        compact ? "p-3" : "p-5"
      } animate-enter`}
      role="alert"
    >
      <div className="flex items-start gap-3">
        <svg
          width={compact ? "18" : "22"}
          height={compact ? "18" : "22"}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="text-rose-500 shrink-0 mt-0.5"
        >
          <circle cx="12" cy="12" r="10" />
          <path d="M12 8v4" />
          <path d="M12 16h.01" />
        </svg>
        <div className="flex-1 min-w-0">
          <p className={`font-display font-bold text-bark-700 ${compact ? "text-sm" : ""}`}>
            {error.title}
          </p>
          {error.hint && (
            <p className={`text-bark-400 ${compact ? "text-xs mt-0.5" : "text-sm mt-1"}`}>
              {error.hint}
            </p>
          )}
          {(onRetry && error.retryable) || onDismiss ? (
            <div className="flex gap-2 mt-2.5">
              {onRetry && error.retryable && (
                <button onClick={onRetry} className="btn-secondary text-xs py-1 px-3">
                  Spróbuj ponownie
                </button>
              )}
              {onDismiss && (
                <button
                  onClick={onDismiss}
                  className="text-xs text-bark-300 hover:text-bark-500 transition-colors px-2"
                >
                  Zamknij
                </button>
              )}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
