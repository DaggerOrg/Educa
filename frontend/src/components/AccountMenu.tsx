import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import type { Session } from "../auth.ts";
import type { AccountModalKind } from "./AccountModal.tsx";
import {
  IconChevronDown,
  IconChevronRight,
  IconChat,
  IconDocument,
  IconGlobe,
  IconHelp,
  IconLogout,
  IconSettings,
} from "./icons.tsx";

interface AccountMenuProps {
  session: Session;
  onOpenSettings: () => void;
  onOpenModal: (kind: AccountModalKind) => void;
  onLogOut: () => void;
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  return (parts[0][0] + (parts[1]?.[0] ?? "")).toUpperCase();
}

export default function AccountMenu({ session, onOpenSettings, onOpenModal, onLogOut }: AccountMenuProps) {
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState({ top: 0, right: 0 });
  const triggerRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  // Rendered through a portal (below) rather than as a plain child, because
  // .topbar-right has overflow-x:auto for narrow viewports -- which per the
  // overflow spec forces overflow-y to auto too, clipping any in-flow
  // dropdown that opens below it. Fixed-position + portal escapes that.
  useEffect(() => {
    if (!open || !triggerRef.current) return;
    const rect = triggerRef.current.getBoundingClientRect();
    setPosition({ top: rect.bottom + 8, right: window.innerWidth - rect.right });
  }, [open]);

  useEffect(() => {
    if (!open) return;
    function onPointerDown(e: MouseEvent) {
      const target = e.target as Node;
      if (triggerRef.current?.contains(target) || panelRef.current?.contains(target)) return;
      setOpen(false);
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    function onResize() {
      setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    window.addEventListener("resize", onResize);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("resize", onResize);
    };
  }, [open]);

  function openModal(kind: AccountModalKind) {
    setOpen(false);
    onOpenModal(kind);
  }

  return (
    <div className="account-menu">
      <button
        type="button"
        ref={triggerRef}
        className={`account-trigger${open ? " is-open" : ""}`}
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
      >
        <span className="account-trigger-avatar">{initials(session.user.name)}</span>
        <span className="account-trigger-name">{session.user.name}</span>
        <IconChevronDown />
      </button>

      {open &&
        createPortal(
          <div
            className="account-menu-panel"
            role="menu"
            ref={panelRef}
            style={{ position: "fixed", top: position.top, right: position.right }}
          >
            <div className="account-menu-identity">
              <div className="account-menu-name">{session.user.name}</div>
              <div className="account-menu-email">{session.user.email}</div>
            </div>
            <div className="account-menu-plan-row">
              <span>{session.user.role === "teacher" ? "Educator" : "Student"} plan</span>
              <span className="plan-pill">Free · early access</span>
            </div>
            <div className="account-menu-rule" />
            <button
              type="button"
              className="account-menu-item"
              role="menuitem"
              onClick={() => {
                setOpen(false);
                onOpenSettings();
              }}
            >
              <IconSettings />
              Settings
            </button>
            <button type="button" className="account-menu-item" role="menuitem" onClick={() => openModal("language")}>
              <IconGlobe />
              Language
              <span className="account-menu-item-chevron"><IconChevronRight /></span>
            </button>
            <button type="button" className="account-menu-item" role="menuitem" onClick={() => openModal("legal")}>
              <IconDocument />
              Legal &amp; privacy
              <span className="account-menu-item-chevron"><IconChevronRight /></span>
            </button>
            <div className="account-menu-rule" />
            <button type="button" className="account-menu-item" role="menuitem" onClick={() => openModal("feedback")}>
              <IconChat />
              Give feedback
            </button>
            <button type="button" className="account-menu-item" role="menuitem" onClick={() => openModal("help")}>
              <IconHelp />
              Help &amp; docs
            </button>
            <div className="account-menu-rule" />
            <button
              type="button"
              className="account-menu-item is-danger"
              role="menuitem"
              onClick={() => {
                setOpen(false);
                onLogOut();
              }}
            >
              <IconLogout />
              Log out
            </button>
          </div>,
          document.body,
        )}
    </div>
  );
}
