/** Lightweight inline toast, reserved for successful Stage 1 notifications. */
export function Toast({ message }: { message: string }) {
  return <div className="toast" role="status">{message}</div>;
}
