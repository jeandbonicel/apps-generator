{% raw %}
import { useEffect, useState, createContext, useContext, useCallback, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { Toast, ToastTitle, ToastDescription } from "./toast";

type ToastVariant = "default" | "destructive" | "success";

interface ToastItem {
  id: string;
  title?: string;
  description: string;
  variant?: ToastVariant;
  duration?: number;
}

interface ToastContextValue {
  toast: (opts: Omit<ToastItem, "id">) => void;
}

const ToastContext = createContext<ToastContextValue>({ toast: () => {} });

export function useToast() {
  return useContext(ToastContext);
}

let toastCounter = 0;

export function Toaster({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const addToast = useCallback((opts: Omit<ToastItem, "id">) => {
    const id = String(++toastCounter);
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
          <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 w-full max-w-sm">
            {toasts.map((t) => (
              <ToastAutoClose key={t.id} item={t} onClose={() => removeToast(t.id)} />
            ))}
          </div>,
          document.body
        )}
    </ToastContext.Provider>
  );
}

function ToastAutoClose({ item, onClose }: { item: ToastItem; onClose: () => void }) {
  useEffect(() => {
    const timer = setTimeout(onClose, item.duration ?? 5000);
    return () => clearTimeout(timer);
  }, [item, onClose]);

  return (
    <Toast variant={item.variant} onClose={onClose}>
      {item.title && <ToastTitle>{item.title}</ToastTitle>}
      <ToastDescription>{item.description}</ToastDescription>
    </Toast>
  );
}
{% endraw %}
