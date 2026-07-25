import { NextResponse } from "next/server";

import { ApiError, serverApi } from "@/lib/server-api";

type RequestPayload = {
  profile_id?: string;
};

export async function POST(request: Request) {
  const payload = (await request.json()) as RequestPayload;
  if (!payload.profile_id) {
    return NextResponse.json({ detail: "Perfil financeiro obrigatório." }, { status: 422 });
  }
  try {
    const response = await serverApi(
      `/financial-profiles/${payload.profile_id}/bank-connections/connect-token`,
      { method: "POST" },
    );
    return NextResponse.json(response, { status: 201 });
  } catch (error) {
    const status = error instanceof ApiError ? error.status : 500;
    const detail =
      error instanceof Error ? error.message : "Não foi possível iniciar a conexão.";
    return NextResponse.json({ detail }, { status });
  }
}
