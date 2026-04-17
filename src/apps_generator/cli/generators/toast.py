"""Toast provider generation — writes the appropriate version based on --uikit flag."""

from pathlib import Path

from apps_generator.utils.console import console


def generate_toast_provider(project_root: Path, has_uikit: bool, uikit_name: str = "") -> None:
    """Generate the ToastProvider component in the shell project.

    If ui-kit is linked, imports Toaster/useToast from the ui-kit package.
    Otherwise generates a self-contained lightweight version.
    """
    dest = project_root / "src" / "shell" / "ToastProvider.tsx"
    if dest.exists():
        return

    dest.parent.mkdir(parents=True, exist_ok=True)

    if has_uikit and uikit_name:
        dest.write_text(_UIKIT_VERSION.replace("__UIKIT_NAME__", uikit_name))
        console.print(f"  Created: src/shell/ToastProvider.tsx (using {uikit_name} Toast)")
    else:
        dest.write_text(_BUILTIN_VERSION)
        console.print("  Created: src/shell/ToastProvider.tsx (built-in)")


# ── ui-kit version: imports shadcn Toast from ui-kit ─────────────────────────

_UIKIT_VERSION = """import { Toaster, useToast } from "__UIKIT_NAME__";
export { useToast };

/**
 * Toast provider using shadcn Toast from the ui-kit.
 * Wrap your app with this to enable `useToast()` in any component.
 */
export function ToastProvider({ children }: { children: React.ReactNode }) {
  return (
    <Toaster>
      {children}
    </Toaster>
  );
}
"""

# ── built-in version: self-contained, no external deps ───────────────────────

_BUILTIN_VERSION = """import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";

type ToastVariant = "default" | "destructive" | "success";

interface ToastItem {
  id: string;
  title?: string;
  description: string;
  variant?: ToastVariant;
}

interface ToastContextValue {
  toast: (opts: Omit<ToastItem, "id">) => void;
}

const ToastContext = createContext<ToastContextValue>({ toast: () => {} });

export function useToast() {
  return useContext(ToastContext);
}

let counter = 0;

/**
 * Lightweight toast provider — no external dependencies.
 * Wrap your app with this to enable `useToast()` in any component.
 */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const addToast = useCallback((opts: Omit<ToastItem, "id">) => {
    const id = String(++counter);
    setToasts((prev) => [...prev, { id, ...opts }]);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ toast: addToast }}>
      {children}
      {typeof document !== "undefined" &&
        createPortal(
          <div style={{ position: "fixed", bottom: 16, right: 16, zIndex: 100, display: "flex", flexDirection: "column", gap: 8, width: "100%", maxWidth: 384 }}>
            {toasts.map((t) => (
              <ToastAutoClose key={t.id} item={t} onClose={() => removeToast(t.id)} />
            ))}
          </div>,
          document.body
        )}
    </ToastContext.Provider>
  );
}

const variantStyles: Record<ToastVariant, string> = {
  default: "border-gray-200 bg-white text-gray-900",
  destructive: "border-red-200 bg-red-50 text-red-900",
  success: "border-green-200 bg-green-50 text-green-900",
};

function ToastAutoClose({ item, onClose }: { item: ToastItem; onClose: () => void }) {
  useEffect(() => {
    const timer = setTimeout(onClose, 5000);
    return () => clearTimeout(timer);
  }, [item, onClose]);

  const variant = item.variant ?? "default";

  return (
    <div
      className={`pointer-events-auto flex items-center justify-between gap-3 rounded-md border p-4 shadow-lg ${variantStyles[variant]}`}
      role="alert"
    >
      <div className="flex-1">
        {item.title && <p className="text-sm font-semibold">{item.title}</p>}
        <p className="text-sm opacity-90">{item.description}</p>
      </div>
      <button onClick={onClose} className="shrink-0 opacity-70 hover:opacity-100 text-sm">
        \\u2715
      </button>
    </div>
  );
}
"""
