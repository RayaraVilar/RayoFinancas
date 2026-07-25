"use client";

import { useActionState } from "react";
import { KeyRound, Send, Sparkles, Trash2 } from "lucide-react";

import {
  askAssistantAction,
  deleteGeminiCredentialAction,
  saveGeminiCredentialAction,
  type AssistantActionState,
} from "@/app/dashboard/actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const initialState: AssistantActionState = { answer: null, error: null };

export function AssistantPanel({
  configured,
  isDemo,
  keyHint,
  model,
  profileId,
}: {
  configured: boolean;
  isDemo: boolean;
  keyHint: string | null;
  model: string;
  profileId: string;
}) {
  const [state, action, pending] = useActionState(askAssistantAction, initialState);

  return (
    <section className="rounded-[26px] border border-[#dfe6df] bg-white p-5 sm:p-6 lg:col-span-3">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[.14em] text-[#79905d]">
            <Sparkles className="size-4" />
            Assistente Rayo
          </p>
          <h2 className="mt-2 text-xl font-semibold tracking-[-.03em]">
            Pergunte sobre seus próprios números
          </h2>
          <p className="mt-2 max-w-2xl text-xs leading-5 text-[#71817a]">
            A resposta usa os cálculos da sua conta. Sua chave fica criptografada e pode
            ser removida a qualquer momento.
          </p>
        </div>
        <span className="rounded-full bg-[#eef4e8] px-3 py-1 text-[10px] font-semibold text-[#557044]">
          {model}
        </span>
      </div>

      {isDemo ? (
        <div className="mt-5 rounded-2xl bg-[#f5f7f2] p-4 text-xs leading-5 text-[#66776f]">
          O assistente fica desligado na demonstração. Entre com sua conta para usar sua
          própria chave Gemini.
        </div>
      ) : configured ? (
        <>
          <form action={action} className="mt-5 grid gap-3 sm:grid-cols-[1fr_auto]">
            <input name="profile_id" type="hidden" value={profileId} />
            <Input
              maxLength={1200}
              name="message"
              placeholder="Ex.: quanto ainda posso gastar neste mês?"
              required
            />
            <Button disabled={pending} type="submit">
              <Send className="size-4" />
              {pending ? "Analisando..." : "Perguntar"}
            </Button>
          </form>
          {state.answer ? (
            <div className="mt-4 rounded-2xl bg-[#f1f6ec] p-4 text-sm leading-6 text-[#365248]">
              {state.answer}
            </div>
          ) : null}
          {state.error ? (
            <div className="mt-4 rounded-2xl bg-[#fff4f1] p-4 text-sm text-[#94483d]">
              {state.error}
            </div>
          ) : null}
          <form action={deleteGeminiCredentialAction} className="mt-4">
            <input name="profile_id" type="hidden" value={profileId} />
            <Button size="sm" type="submit" variant="ghost">
              <Trash2 className="size-4" />
              Remover chave {keyHint}
            </Button>
          </form>
        </>
      ) : (
        <form action={saveGeminiCredentialAction} className="mt-5 max-w-2xl">
          <input name="profile_id" type="hidden" value={profileId} />
          <label className="text-xs font-semibold" htmlFor="gemini-api-key">
            Sua chave da API Gemini
          </label>
          <div className="mt-2 grid gap-3 sm:grid-cols-[1fr_auto]">
            <div className="relative">
              <KeyRound className="pointer-events-none absolute left-3 top-3 size-4 text-[#84928b]" />
              <Input
                autoComplete="off"
                className="pl-9"
                id="gemini-api-key"
                minLength={20}
                name="api_key"
                placeholder="Cole a chave aqui"
                required
                type="password"
              />
            </div>
            <Button type="submit">Salvar com segurança</Button>
          </div>
          <p className="mt-2 text-[10px] leading-4 text-[#84928b]">
            A Rayo nunca mostra a chave novamente. O consumo e os limites pertencem à sua
            conta do Google AI Studio.{" "}
            <a
              className="font-semibold text-[#557044] underline underline-offset-2"
              href="https://aistudio.google.com/app/apikey"
              rel="noreferrer"
              target="_blank"
            >
              Criar minha chave
            </a>
            .
          </p>
          <p className="mt-2 text-[10px] leading-4 text-[#84928b]">
            Quando você fizer uma pergunta, somente resumos financeiros necessários serão
            enviados ao Gemini para gerar a resposta. O histórico não é armazenado pela
            Rayo.
          </p>
        </form>
      )}
    </section>
  );
}
