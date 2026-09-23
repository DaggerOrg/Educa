import { useEffect, useState } from "react";
import { dismissToast, subscribeToasts, type Toast } from "../toast.ts";
import { IconCheck, IconClose } from "./icons.tsx";

export default function ToastStack() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  useEffect(() => subscribeToasts(setToasts), []);

  if (toasts.length === 0) return null;

  return (
    <div className="toast-stack">
      {toasts.map((t) => (
        <div className={`toast toast-${t.tone}`} key={t.id}>
          {t.tone === "success" && <IconCheck />}
          <span>{t.message}</span>
          <button type="button" className="toast-close" onClick={() => dismissToast(t.id)} aria-label="Dismiss">
            <IconClose />
          </button>
        </div>
      ))}
    </div>
  );
}
