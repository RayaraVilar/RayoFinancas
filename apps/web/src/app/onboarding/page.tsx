import { Building2, Check, Circle, Landmark, ShieldCheck, UserRound } from "lucide-react";
import { redirect } from "next/navigation";

import { Brand } from "@/components/brand";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, serverApi } from "@/lib/server-api";
import {
  acceptPrivacyAction,
  completeOnboardingAction,
  createAccountAction,
  createProfileAction,
} from "./actions";

type User = {
  id: string;
  display_name: string;
  email: string;
  onboarding_completed_at: string | null;
};

type Profile = {
  id: string;
  type: "PERSONAL" | "BUSINESS";
  name: string;
};

type OnboardingState = {
  profile_count: number;
  account_count: number;
  privacy_consent_granted: boolean;
  completed: boolean;
};

function Step({
  done,
  children,
}: {
  done: boolean;
  children: React.ReactNode;
}) {
  return (
    <li className="flex items-center gap-3 text-sm">
      <span
        className={`grid size-6 place-items-center rounded-full ${
          done ? "bg-[#d9ff65] text-[#244b40]" : "bg-white/10 text-white/45"
        }`}
      >
        {done ? <Check className="size-3.5" /> : <Circle className="size-2.5" />}
      </span>
      <span className={done ? "text-white" : "text-white/55"}>{children}</span>
    </li>
  );
}

export const dynamic = "force-dynamic";

export default async function OnboardingPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const { error } = await searchParams;
  let user: User;
  let profiles: Profile[];
  let state: OnboardingState;
  try {
    [user, profiles, state] = await Promise.all([
      serverApi<User>("/auth/me"),
      serverApi<Profile[]>("/financial-profiles"),
      serverApi<OnboardingState>("/onboarding/state"),
    ]);
  } catch (requestError) {
    if (requestError instanceof ApiError && requestError.status === 401) {
      redirect("/entrar");
    }
    throw requestError;
  }
  if (state.completed) redirect("/dashboard");

  const activeProfile = profiles[0];
  const currentStep =
    state.profile_count === 0
      ? 1
      : state.account_count === 0
        ? 2
        : !state.privacy_consent_granted
          ? 3
          : 4;

  return (
    <main className="min-h-screen bg-[#f3f5ef]">
      <header className="mx-auto flex max-w-[1120px] items-center justify-between px-5 py-6 sm:px-8">
        <Brand />
        <div className="text-right">
          <p className="text-sm font-semibold text-[#294a41]">{user.display_name}</p>
          <p className="text-xs text-[#829189]">{user.email}</p>
        </div>
      </header>

      <div className="mx-auto grid max-w-[1120px] gap-6 px-5 pb-16 pt-5 sm:px-8 lg:grid-cols-[.7fr_1.3fr]">
        <aside className="rounded-[28px] bg-[#173f35] p-7 text-white lg:sticky lg:top-6 lg:h-fit">
          <p className="text-xs font-bold uppercase tracking-[.18em] text-[#d9ff65]">
            Primeiros passos
          </p>
          <h1 className="mt-4 text-3xl font-semibold tracking-[-.05em]">
            Sua Rayo começa pelo contexto certo.
          </h1>
          <p className="mt-4 text-sm leading-6 text-white/60">
            Separe vida pessoal e empresa desde o início. Você poderá adicionar
            outros perfis e bancos depois.
          </p>
          <ol className="mt-9 space-y-5">
            <Step done={state.profile_count > 0}>Criar perfil financeiro</Step>
            <Step done={state.account_count > 0}>Adicionar primeira conta</Step>
            <Step done={state.privacy_consent_granted}>
              Confirmar privacidade
            </Step>
            <Step done={false}>Concluir configuração</Step>
          </ol>
        </aside>

        <Card className="p-6 sm:p-9">
          <div className="mb-8 flex items-center justify-between">
            <div>
              <p className="text-xs font-bold uppercase tracking-[.16em] text-[#7d945e]">
                Etapa {currentStep} de 4
              </p>
              <p className="mt-2 text-sm text-[#71817a]">
                Seus dados ficam associados ao perfil escolhido.
              </p>
            </div>
            <span className="rounded-full bg-[#f0f5ed] px-3 py-1.5 text-xs font-semibold text-[#557068]">
              {Math.round(((currentStep - 1) / 4) * 100)}%
            </span>
          </div>

          {error ? (
            <div
              className="mb-6 rounded-xl border border-[#efd4cf] bg-[#fff4f1] p-3 text-sm text-[#94483d]"
              role="alert"
            >
              Não foi possível salvar. Revise os dados e tente novamente.
            </div>
          ) : null}

          {currentStep === 1 ? (
            <form action={createProfileAction}>
              <div className="grid size-12 place-items-center rounded-2xl bg-[#edf5e5] text-[#315d4f]">
                <UserRound className="size-5" />
              </div>
              <h2 className="mt-5 text-2xl font-semibold tracking-[-.04em] text-[#173f35]">
                Qual vida financeira vamos organizar?
              </h2>
              <p className="mt-2 text-sm leading-6 text-[#71817a]">
                A visão “Tudo” consolida depois, sem misturar a origem dos dados.
              </p>
              <fieldset className="mt-7 grid gap-3 sm:grid-cols-2">
                <label className="cursor-pointer rounded-2xl border border-[#dce5de] p-4 has-[:checked]:border-[#587f6d] has-[:checked]:bg-[#f2f7ef]">
                  <input
                    className="sr-only"
                    defaultChecked
                    name="type"
                    type="radio"
                    value="PERSONAL"
                  />
                  <UserRound className="size-5 text-[#426457]" />
                  <span className="mt-3 block text-sm font-semibold">Pessoal</span>
                  <span className="mt-1 block text-xs text-[#78877f]">Sua vida PF</span>
                </label>
                <label className="cursor-pointer rounded-2xl border border-[#dce5de] p-4 has-[:checked]:border-[#587f6d] has-[:checked]:bg-[#f2f7ef]">
                  <input className="sr-only" name="type" type="radio" value="BUSINESS" />
                  <Building2 className="size-5 text-[#426457]" />
                  <span className="mt-3 block text-sm font-semibold">Empresa</span>
                  <span className="mt-1 block text-xs text-[#78877f]">Caixa PJ</span>
                </label>
              </fieldset>
              <div className="mt-6 space-y-2">
                <Label htmlFor="profile-name">Nome do perfil</Label>
                <Input
                  id="profile-name"
                  name="name"
                  placeholder="Ex.: Pessoal ou Empresa Aurora"
                  required
                />
              </div>
              <div className="mt-5 space-y-2">
                <Label htmlFor="document-last4">Últimos 4 dígitos do CPF/CNPJ</Label>
                <Input
                  id="document-last4"
                  inputMode="numeric"
                  maxLength={4}
                  name="document_last4"
                  pattern="\d{4}"
                  placeholder="Opcional"
                />
                <p className="text-xs text-[#8a9791]">
                  Não solicitamos o documento completo nesta etapa.
                </p>
              </div>
              <Button className="mt-8 w-full sm:w-auto" size="lg" type="submit">
                Criar perfil
              </Button>
            </form>
          ) : null}

          {currentStep === 2 && activeProfile ? (
            <form action={createAccountAction}>
              <input name="profile_id" type="hidden" value={activeProfile.id} />
              <div className="grid size-12 place-items-center rounded-2xl bg-[#edf5e5] text-[#315d4f]">
                <Landmark className="size-5" />
              </div>
              <h2 className="mt-5 text-2xl font-semibold tracking-[-.04em] text-[#173f35]">
                Adicione sua primeira conta
              </h2>
              <p className="mt-2 text-sm leading-6 text-[#71817a]">
                Cadastro manual em <strong>{activeProfile.name}</strong>. Nenhuma
                conexão bancária será feita agora.
              </p>
              <div className="mt-7 grid gap-5 sm:grid-cols-2">
                <div className="space-y-2 sm:col-span-2">
                  <Label htmlFor="account-name">Nome da conta</Label>
                  <Input
                    id="account-name"
                    name="name"
                    placeholder="Ex.: Conta principal"
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="institution-name">Instituição</Label>
                  <Input
                    id="institution-name"
                    name="institution_name"
                    placeholder="Ex.: Nubank"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="account-type">Tipo</Label>
                  <select
                    className="h-11 w-full rounded-xl border border-[#d9e2db] bg-white px-3.5 text-sm outline-none focus:border-[#7f9c8d] focus:ring-2 focus:ring-[#dce9df]"
                    id="account-type"
                    name="account_type"
                    defaultValue="CHECKING"
                  >
                    <option value="CHECKING">Conta corrente</option>
                    <option value="SAVINGS">Poupança</option>
                    <option value="PAYMENT">Conta de pagamento</option>
                    <option value="CASH">Dinheiro</option>
                    <option value="OTHER">Outra</option>
                  </select>
                </div>
                <div className="space-y-2 sm:col-span-2">
                  <Label htmlFor="current-balance">Saldo atual</Label>
                  <Input
                    id="current-balance"
                    inputMode="decimal"
                    name="current_balance"
                    placeholder="0,00"
                    required
                  />
                </div>
              </div>
              <Button className="mt-8 w-full sm:w-auto" size="lg" type="submit">
                Salvar conta manual
              </Button>
            </form>
          ) : null}

          {currentStep === 3 ? (
            <form action={acceptPrivacyAction}>
              <div className="grid size-12 place-items-center rounded-2xl bg-[#edf5e5] text-[#315d4f]">
                <ShieldCheck className="size-5" />
              </div>
              <h2 className="mt-5 text-2xl font-semibold tracking-[-.04em] text-[#173f35]">
                Você controla seus dados
              </h2>
              <div className="mt-5 space-y-3 text-sm leading-6 text-[#66776f]">
                <p>A Rayo usará os dados inseridos para organizar e calcular sua visão financeira.</p>
                <p>Conexões bancárias, Gmail, IA e pagamentos terão consentimentos separados.</p>
                <p>Você poderá solicitar exportação, revogação e exclusão conforme a política aplicável.</p>
              </div>
              <label className="mt-7 flex items-start gap-3 rounded-2xl border border-[#dce5de] bg-[#f8faf6] p-4">
                <input className="mt-1 size-4 accent-[#173f35]" required type="checkbox" />
                <span className="text-sm leading-6 text-[#496158]">
                  Li e concordo com a Política de Privacidade, versão 24/07/2026.
                </span>
              </label>
              <Button className="mt-8 w-full sm:w-auto" size="lg" type="submit">
                Confirmar e continuar
              </Button>
            </form>
          ) : null}

          {currentStep === 4 ? (
            <form action={completeOnboardingAction}>
              <div className="grid size-12 place-items-center rounded-2xl bg-[#e9ffd0] text-[#315d30]">
                <Check className="size-5" />
              </div>
              <h2 className="mt-5 text-2xl font-semibold tracking-[-.04em] text-[#173f35]">
                Tudo pronto para começar
              </h2>
              <p className="mt-3 max-w-lg text-sm leading-6 text-[#71817a]">
                Seu perfil e sua conta manual foram criados. Não importamos
                transações nem conectamos bancos.
              </p>
              <Button className="mt-8 w-full sm:w-auto" size="lg" type="submit">
                Ir para minha visão
              </Button>
            </form>
          ) : null}
        </Card>
      </div>
    </main>
  );
}
