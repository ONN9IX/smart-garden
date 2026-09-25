"use client";

/** Password input starts hidden and offers a keyboard-accessible visibility toggle. */
import { useState } from "react";
import type { InputHTMLAttributes } from "react";
import { Input } from "./input";

export function PasswordInput(props: Omit<InputHTMLAttributes<HTMLInputElement>, "type">) {
  const [visible, setVisible] = useState(false);
  return <div className="password-wrap">
    <Input {...props} type={visible ? "text" : "password"} />
    <button className="password-toggle" type="button" aria-label={visible ? "Скрыть пароль" : "Показать пароль"} aria-pressed={visible} onClick={() => setVisible(!visible)}>
      {visible ? "Скрыть" : "Показать"}
    </button>
  </div>;
}
