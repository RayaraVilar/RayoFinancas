"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import type { PluggyConnectProps } from "react-pluggy-connect";

import { Button } from "@/components/ui/button";

const PluggyConnect = dynamic(
  () => import("react-pluggy-connect").then((module) => module.PluggyConnect),
  { ssr: false },
);

type ConnectTokenPayload = {
  connection: { id: string };
  connect_token: string;
};

export function BankConnect({
  profileId,
  configured,
}: {
  profileId: string;
  configured: boolean;
}) {
  const [token, setToken] = useState<string | null>(null);
  const [connectionId, setConnectionId] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function startConnection() {
    setPending(true);
    setError(null);
    try {
      const response = await fetch("/api/banking/connect-token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile_id: profileId }),
      });
      const payload = (await response.json()) as ConnectTokenPayload & { detail?: string };
      if (!response.ok) throw new Error(payload.detail ?? "Falha ao iniciar conexão.");
      setConnectionId(payload.connection.id);
      setToken(payload.connect_token);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao iniciar conexão.");
    } finally {
      setPending(false);
    }
  }

  const onSuccess: NonNullable<PluggyConnectProps["onSuccess"]> = async ({ item }) => {
    if (!connectionId) return;
    const response = await fetch("/api/banking/complete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ connection_id: connectionId, item_id: item.id }),
    });
    if (!response.ok) {
      const payload = (await response.json()) as { detail?: string };
      setError(payload.detail ?? "A conexão foi criada, mas ainda não pôde ser confirmada.");
      return;
    }
    window.location.reload();
  };

  return (
    <div>
      <Button disabled={!configured || pending} onClick={startConnection} type="button">
        {pending ? "Preparando conexão…" : "Conectar instituição"}
      </Button>
      {!configured ? (
        <p className="mt-2 text-[11px] leading-4 text-[#8a7667]">
          A conexão bancária está temporariamente indisponível.
        </p>
      ) : null}
      {error ? <p className="mt-2 text-xs text-[#9a4639]">{error}</p> : null}
      {token ? (
        <PluggyConnect
          allowConnectInBackground
          connectToken={token}
          includeSandbox
          language="pt"
          onClose={() => setToken(null)}
          onError={() => setError("A instituição não concluiu a conexão. Tente novamente.")}
          onSuccess={onSuccess}
          theme="light"
        />
      ) : null}
    </div>
  );
}
