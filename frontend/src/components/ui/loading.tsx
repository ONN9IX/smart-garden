/** Accessible loading state while /auth/me checks the server-side session. */
export function Loading() {
  return <main className="center-screen" role="status"><div className="loading"><span className="spinner" aria-hidden="true" />Загрузка...</div></main>;
}
