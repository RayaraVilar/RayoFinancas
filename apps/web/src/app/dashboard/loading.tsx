export default function DashboardLoading() {
  return (
    <main
      aria-busy="true"
      aria-label="Carregando dashboard financeiro"
      className="min-h-screen bg-[#f3f5ef] px-5 py-8 text-[#173f35]"
    >
      <div className="mx-auto max-w-[1180px] animate-pulse">
        <div className="h-12 w-56 rounded-2xl bg-[#dfe7df]" />
        <div className="mt-8 grid gap-4 sm:grid-cols-3">
          {[0, 1, 2].map((item) => (
            <div className="h-32 rounded-3xl bg-white" key={item} />
          ))}
        </div>
        <div className="mt-5 grid gap-5 lg:grid-cols-2">
          <div className="h-80 rounded-3xl bg-white" />
          <div className="h-80 rounded-3xl bg-white" />
        </div>
        <p className="sr-only">Preparando métricas, compromissos e projeções.</p>
      </div>
    </main>
  );
}
