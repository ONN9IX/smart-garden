/** Accessible field wrapper with an associated label and local validation text. */
import type { ReactNode } from "react";

export function FormField({ id, label, error, children }: { id: string; label: string; error?: string; children: ReactNode }) {
  return <div className="field">
    <label htmlFor={id}>{label}</label>
    {children}
    {error && <span id={`${id}-error`} className="field-error">{error}</span>}
  </div>;
}
