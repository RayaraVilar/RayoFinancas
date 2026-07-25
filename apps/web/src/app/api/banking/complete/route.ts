import { NextResponse } from "next/server";

import { ApiError, serverApi } from "@/lib/server-api";

type RequestPayload = {
  connection_id?: string;
  item_id?: string;
};

export async function POST(request: Request) {
  const payload = (await request.json()) as RequestPayload;
  if (!payload.connection_id || !payload.item_id) {
    return NextResponse.json({ detail: "Conexão bancária inválida." }, { status: 422 });
  }
  try {
    const response = await serverApi(`/bank-connections/${payload.connection_id}/complete`, {
      method: "POST",
      body: JSON.stringify({ item_id: payload.item_id }),
    });
    return NextResponse.json(response);
  } catch (error) {
    const status = error instanceof ApiError ? error.status : 500;
    const detail =
      error instanceof Error ? error.message : "Não foi possível confirmar a conexão.";
    return NextResponse.json({ detail }, { status });
  }
}
