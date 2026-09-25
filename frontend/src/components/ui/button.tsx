/** Shared button with pending state for Stage 1 forms and navigation. */
import type { ButtonHTMLAttributes } from "react";

export function Button({ children, className = "", variant = "primary", ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" }) {
  return <button className={`button button-${variant} ${className}`} {...props}>{children}</button>;
}
