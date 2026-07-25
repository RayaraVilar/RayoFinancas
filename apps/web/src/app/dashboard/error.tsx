"use client";

import { useEffect } from "react";

import { Button } from "@/components/ui/button";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("dashboard_render_failed", { digest: error.digest });
  }, [error.digest]);

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#f3f5ef] p-5">
      <div className="max-w-md rounded-3xl border border-[#dce5dc] bg-white p-8 text-[#173f35]">
        <p className="text-xs font-bold uppercase tracking-[.14em] text-[#79905d]">
          Falha temporária
        </p>
        <h1 className="mt-3 text-2xl font-semibold">Não foi possível montar o dashboard.</h1>
        <p className="mt-3 text-sm leading-6 text-[#71817a]">
          Seus dados não foram alterados. Tente novamente; se a falha persistir, use o
          identificador exibido pelo suporte nos logs seguros.
        </p>
        <Button className="mt-6" onClick={reset}>
          Tentar novamente
        </Button>
      </div>
    </main>
  );
}
