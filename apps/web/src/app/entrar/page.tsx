import { ArrowLeft, CheckCircle2, Eye, LockKeyhole } from "lucide-react";
import Link from "next/link";

import { Brand } from "@/components/brand";
import { buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { serverApi } from "@/lib/server-api";

type AuthStatus = {
  google_configured: boolean;
  implementation_status: string;
};

export const dynamic = "force-dynamic";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const { error } = await searchParams;
  const errorMessage =
    error === "demo"
      ? "Não foi possível abrir a demonstração agora. Tente novamente."
      : "Não foi possível entrar com o Google. Tente novamente.";
  let authStatus: AuthStatus = {
    google_configured: false,
    implementation_status: "API_UNAVAILABLE",
  };
  try {
    authStatus = await serverApi<AuthStatus>("/auth/status");
  } catch {
    // The page remains useful and accurately reports the unavailable state.
  }

  return (
    <main className="grid min-h-screen grid-cols-[minmax(0,1fr)] bg-[#f4f6ef] lg:grid-cols-[1fr_.82fr]">
      <section className="relative hidden overflow-hidden bg-[#173f35] p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="absolute -right-24 top-24 size-[460px] rounded-full border border-white/10" />
        <div className="absolute -bottom-32 -left-24 size-[380px] rounded-full bg-[#d9ff65]/10 blur-3xl" />
        <Brand />
        <div className="relative max-w-xl">
          <p className="text-xs font-bold uppercase tracking-[.2em] text-[#d9ff65]">
            Clareza antes da decisão
          </p>
          <h1 className="mt-6 text-5xl font-semibold leading-[1.02] tracking-[-.06em]">
            Um lugar seguro para entender sua vida financeira.
          </h1>
          <div className="mt-10 space-y-4 text-sm text-white/70">
            {[
              "Seus perfis pessoal e empresarial permanecem separados.",
              "A Rayo nunca armazena sua senha bancária.",
              "Nenhuma movimentação acontece sem sua autorização.",
            ].map((item) => (
              <p className="flex items-center gap-3" key={item}>
                <CheckCircle2 className="size-4 text-[#d9ff65]" />
                {item}
              </p>
            ))}
          </div>
        </div>
        <p className="relative text-xs text-white/45">
          Seus dados permanecem sob seu controle.
        </p>
      </section>

      <section className="flex min-h-screen min-w-0 items-center justify-center overflow-x-hidden px-5 py-10 sm:px-8">
        <div className="min-w-0 w-full max-w-md">
          <div className="mb-10 flex items-center justify-between lg:hidden">
            <Brand />
            <Link
              className="flex items-center gap-2 text-xs font-semibold text-[#60736b]"
              href="/"
            >
              <ArrowLeft className="size-4" />
              Voltar
            </Link>
          </div>

          <Card className="min-w-0 p-7 sm:p-9">
            <div className="grid size-11 place-items-center rounded-2xl bg-[#edf5e5] text-[#315d4f]">
              <LockKeyhole className="size-5" />
            </div>
            <h2 className="mt-6 text-3xl font-semibold tracking-[-.05em] text-[#173f35]">
              Entre na sua Rayo
            </h2>
            <p className="mt-3 text-sm leading-6 text-[#687a72]">
              Use sua conta Google. Solicitamos somente nome, email e foto para
              identificar você.
            </p>

            {error ? (
              <div
                className="mt-6 rounded-xl border border-[#efd4cf] bg-[#fff4f1] p-3 text-sm text-[#94483d]"
                role="alert"
              >
                {errorMessage}
              </div>
            ) : null}

            {authStatus.google_configured ? (
              <Link
                className={cn(buttonVariants({ size: "lg" }), "mt-7 w-full")}
                href="/api/v1/auth/google/start"
              >
                <svg aria-hidden="true" className="size-5" viewBox="0 0 24 24">
                  <path
                    fill="#fff"
                    d="M21.35 12.2c0-.7-.06-1.21-.2-1.75H12v3.3h5.37a4.6 4.6 0 0 1-2 3.02v2.14h3.24c1.9-1.75 2.74-4.32 2.74-6.71Z"
                  />
                  <path
                    fill="#fff"
                    fillOpacity=".85"
                    d="M12 21.7c2.7 0 4.97-.9 6.62-2.43l-3.24-2.5c-.9.6-2.05.96-3.38.96-2.6 0-4.8-1.76-5.6-4.13H3.05v2.59A10 10 0 0 0 12 21.7Z"
                  />
                  <path
                    fill="#fff"
                    fillOpacity=".7"
                    d="M6.4 13.6a6 6 0 0 1 0-3.2V7.81H3.05a10 10 0 0 0 0 8.38L6.4 13.6Z"
                  />
                  <path
                    fill="#fff"
                    d="M12 6.27c1.47 0 2.79.5 3.83 1.5l2.87-2.88A9.62 9.62 0 0 0 12 2.3a10 10 0 0 0-8.95 5.51L6.4 10.4A6 6 0 0 1 12 6.27Z"
                  />
                </svg>
                Continuar com Google
              </Link>
            ) : (
              <div className="mt-7">
                <button
                  className={cn(buttonVariants({ size: "lg" }), "w-full")}
                  disabled
                >
                  Continuar com Google
                </button>
                <div className="mt-4 rounded-xl bg-[#f5f7f2] p-4 text-xs leading-5 text-[#66776f]">
                  O acesso com Google está temporariamente indisponível.
                </div>
              </div>
            )}

            <div className="my-5 flex items-center gap-3 text-[11px] uppercase tracking-[.14em] text-[#96a29c]">
              <span className="h-px flex-1 bg-[#dfe5dd]" />
              ou
              <span className="h-px flex-1 bg-[#dfe5dd]" />
            </div>

            <form action="/api/v1/auth/demo" method="post">
              <button
                className={cn(
                  buttonVariants({ size: "lg", variant: "outline" }),
                  "w-full",
                )}
                type="submit"
              >
                <Eye className="size-4" />
                Explorar demonstração
              </button>
            </form>
            <p className="mt-3 text-center text-xs leading-5 text-[#7a8982]">
              Veja a Rayo com informações totalmente fictícias, sem conectar contas.
            </p>

            <p className="mt-7 text-center text-[11px] leading-5 text-[#819088]">
              Ao continuar, você confirma que leu os Termos e a Política de
              Privacidade. Consentimentos bancários são solicitados separadamente.
            </p>
          </Card>
        </div>
      </section>
    </main>
  );
}
