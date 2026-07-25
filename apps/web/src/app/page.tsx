import { Brand } from "@/components/brand";

type ApiState = {
  online: boolean;
  label: string;
};

async function getApiState(): Promise<ApiState> {
  const baseUrl = process.env.INTERNAL_API_URL ?? "http://localhost:8000";

  try {
    const response = await fetch(`${baseUrl}/api/v1/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(1500),
    });

    if (!response.ok) {
      throw new Error("API unavailable");
    }

    return { online: true, label: "Tudo pronto para começar" };
  } catch {
    return { online: false, label: "Estamos voltando em instantes" };
  }
}

function ArrowIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 20 20" className="size-5 fill-none">
      <path
        d="M4 10h12m-5-5 5 5-5 5"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function DashboardPreview() {
  return (
    <div className="dashboard-shell relative mx-auto min-w-0 w-full max-w-[560px] overflow-hidden rounded-[26px] border border-white/70 bg-[#fbfcf7] p-4 shadow-[0_28px_90px_rgba(29,65,55,.18)] sm:p-5">
      <div className="mb-7 flex items-center justify-between">
        <div>
          <span className="text-[11px] font-semibold uppercase tracking-[.16em] text-[#84918a]">
            Visão de julho
          </span>
          <p className="mt-1 text-lg font-bold tracking-[-.04em] text-[#183d34]">
            Boa tarde, Marina
          </p>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-[#dfe8e1] bg-white px-3 py-2 text-[11px] font-semibold text-[#557068]">
          <span className="size-2 rounded-full bg-[#60b887]" />
          Atualizado agora
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-[1.35fr_.8fr]">
        <div className="rounded-[20px] bg-[#173f35] p-5 text-white">
          <p className="text-xs text-white/65">Saldo do mês</p>
          <p className="mt-2 text-[1.8rem] font-semibold tracking-[-.05em]">
            + R$ 2.840
          </p>
          <div className="mt-6 flex items-end justify-between gap-3">
            <div>
              <p className="text-[10px] uppercase tracking-[.12em] text-white/50">
                Economia
              </p>
              <p className="mt-1 text-sm font-semibold text-[#d9ff65]">18,4%</p>
            </div>
            <svg
              aria-label="Tendência de saldo positiva"
              className="h-12 w-28"
              viewBox="0 0 112 48"
              fill="none"
            >
              <path
                d="M2 39c12-3 15-17 28-16 13 1 15 11 27 7 14-5 17-21 30-18 9 2 12 10 23 3"
                stroke="#D9FF65"
                strokeWidth="2.5"
                strokeLinecap="round"
              />
            </svg>
          </div>
        </div>

        <div className="rounded-[20px] border border-[#e4ebe5] bg-white p-5">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs text-[#76857e]">Saúde financeira</p>
              <p className="mt-2 text-3xl font-semibold tracking-[-.05em] text-[#173f35]">
                78
                <span className="text-sm text-[#91a099]">/100</span>
              </p>
            </div>
            <div className="grid size-9 place-items-center rounded-full bg-[#edffd0] text-[#315d30]">
              ↑
            </div>
          </div>
          <div className="mt-6 h-2 overflow-hidden rounded-full bg-[#edf1ed]">
            <div className="h-full w-[78%] rounded-full bg-[#80b83c]" />
          </div>
          <p className="mt-3 text-[11px] leading-relaxed text-[#75847d]">
            Seu ritmo de economia melhorou.
          </p>
        </div>
      </div>

      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <div className="rounded-[20px] border border-[#e4ebe5] bg-white p-5">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-[#294a41]">Onde você gasta</p>
            <span className="text-[10px] text-[#8b9992]">este mês</span>
          </div>
          <div className="mt-5 space-y-4">
            {[
              ["Moradia", "42%", "bg-[#2d6657]"],
              ["Alimentação", "28%", "bg-[#83aa4d]"],
              ["Transporte", "17%", "bg-[#c9d48b]"],
            ].map(([name, value, color]) => (
              <div key={name}>
                <div className="mb-1.5 flex justify-between text-[10px]">
                  <span className="text-[#66776f]">{name}</span>
                  <span className="font-semibold text-[#2c4941]">{value}</span>
                </div>
                <div className="h-1.5 rounded-full bg-[#edf1ed]">
                  <div
                    className={`h-full rounded-full ${color}`}
                    style={{ width: value }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-[20px] border border-[#dce8ce] bg-[#f5ffe7] p-5">
          <span className="inline-flex rounded-full bg-[#e3f6bf] px-2.5 py-1 text-[9px] font-bold uppercase tracking-[.12em] text-[#4d6b2b]">
            Insight
          </span>
          <p className="mt-4 text-sm font-semibold leading-snug text-[#25483e]">
            Você gastou 23% menos com delivery nas últimas três semanas.
          </p>
          <p className="mt-3 text-[11px] leading-relaxed text-[#66776f]">
            Mantendo o ritmo, seu mês fecha R$ 310 abaixo do orçamento.
          </p>
        </div>
      </div>
    </div>
  );
}

function FinancialHeroVisual() {
  return (
    <div className="relative px-3 pb-9 pt-7 sm:px-7 sm:pb-11 sm:pt-9">
      <div
        aria-label="Ilustração de um cartão, moedas e um extrato financeiro"
        className="pointer-events-none absolute inset-0 z-20"
        role="img"
      >
        <div className="finance-float-card absolute right-0 top-0 w-[174px] rotate-[7deg] rounded-[20px] bg-[#173f35] p-4 text-white shadow-[0_20px_45px_rgba(23,63,53,.25)] sm:-right-1 sm:w-[194px]">
          <div className="flex items-start justify-between">
            <span className="grid size-9 place-items-center rounded-full bg-[#d9ff65] text-[11px] font-black text-[#173f35]">
              R$
            </span>
            <svg aria-hidden="true" className="h-7 w-9" viewBox="0 0 36 28" fill="none">
              <rect width="21" height="28" rx="10.5" fill="white" fillOpacity=".78" />
              <rect x="15" width="21" height="28" rx="10.5" fill="#D9FF65" fillOpacity=".8" />
            </svg>
          </div>
          <p className="mt-5 text-[10px] uppercase tracking-[.16em] text-white/55">
            Saldo disponível
          </p>
          <p className="mt-1 text-xl font-semibold tracking-[-.04em]">R$ 4.280,60</p>
          <div className="mt-4 flex items-center justify-between text-[9px] text-white/55">
            <span>•••• 2840</span>
            <span>RAYO</span>
          </div>
        </div>

        <div className="finance-float-receipt absolute -bottom-1 left-0 w-[156px] -rotate-[6deg] rounded-[18px] border border-[#dce5dd] bg-white p-4 shadow-[0_18px_45px_rgba(35,67,58,.14)] sm:-left-1 sm:w-[176px]">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold uppercase tracking-[.14em] text-[#49665c]">
              Extrato
            </span>
            <span className="rounded-full bg-[#eef8df] px-2 py-1 text-[8px] font-bold text-[#527331]">
              HOJE
            </span>
          </div>
          <div className="mt-4 space-y-3">
            {[
              ["Mercado", "− R$ 86"],
              ["Salário", "+ R$ 3.800"],
              ["Transporte", "− R$ 24"],
            ].map(([label, amount], index) => (
              <div className="flex items-center gap-2" key={label}>
                <span
                  className={`size-2 rounded-full ${
                    index === 1 ? "bg-[#85b64d]" : "bg-[#cbd8cf]"
                  }`}
                />
                <span className="flex-1 text-[9px] text-[#65766f]">{label}</span>
                <span className="text-[9px] font-semibold text-[#2f5046]">{amount}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="finance-float-coin absolute bottom-5 right-2 grid size-14 place-items-center rounded-full border-[6px] border-[#f4ffcb] bg-[#d9ff65] text-base font-black text-[#315331] shadow-[0_14px_30px_rgba(91,120,45,.22)] sm:-right-1 sm:size-16">
          R$
        </div>
      </div>

      <div className="relative z-10">
        <DashboardPreview />
      </div>
    </div>
  );
}

export const dynamic = "force-dynamic";

export default async function Home() {
  const apiState = await getApiState();

  return (
    <main className="min-h-screen overflow-hidden bg-[#f6f7f1] text-[#173f35]">
      <div className="hero-glow">
        <nav
          aria-label="Navegação principal"
          className="hero-nav mx-auto flex w-full max-w-[1180px] items-center justify-between px-5 py-4 sm:px-8 lg:px-10"
        >
          <Brand />
          <div className="hidden items-center gap-8 text-sm font-medium text-[#536a62] md:flex">
            <a className="transition hover:text-[#173f35]" href="#produto">
              Produto
            </a>
            <a className="transition hover:text-[#173f35]" href="#como-funciona">
              Como funciona
            </a>
            <a className="transition hover:text-[#173f35]" href="#seguranca">
              Segurança
            </a>
          </div>
          <a
            className="rounded-full border border-[#cbd8cf] bg-white/70 px-4 py-2.5 text-xs font-semibold text-[#244b40] backdrop-blur transition hover:border-[#9eb4a6] hover:bg-white sm:text-sm"
            href="/entrar"
          >
            Entrar
          </a>
        </nav>

        <section className="hero-layout mx-auto grid min-w-0 w-full max-w-[1180px] items-center gap-10 px-5 pb-16 pt-12 sm:px-8 sm:pt-16 lg:min-h-[calc(100svh-82px)] lg:grid-cols-[.94fr_1.06fr] lg:px-10 lg:pb-10 lg:pt-5">
          <div className="relative z-10 min-w-0 w-full max-w-[600px]">
            <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-[#dbe7d5] bg-white/65 px-3 py-2 text-[11px] font-semibold text-[#557064] backdrop-blur">
              <span
                className={`size-2 rounded-full ${
                  apiState.online ? "bg-[#56ad7c]" : "bg-[#e6a54a]"
                }`}
              />
              {apiState.label}
            </div>
            <h1 className="max-w-[540px] text-[clamp(2.8rem,13vw,4.2rem)] font-semibold leading-[.94] tracking-[-.065em] text-[#153d33] lg:text-[clamp(3.4rem,5vw,4.7rem)]">
              Seu dinheiro entra.
              <span className="mt-2 block font-serif font-normal italic text-[#5e7a6e]">
                Mas para onde ele vai?
              </span>
            </h1>
            <p className="mt-5 max-w-[500px] text-base leading-7 text-[#60736b] sm:text-lg sm:leading-8">
              Conecte suas contas, entenda seu dinheiro e veja o impacto das
              suas decisões antes de tomá-las.
            </p>
            <div className="mt-6 flex flex-col gap-3 sm:flex-row">
              <a
                className="inline-flex items-center justify-center gap-2 rounded-full bg-[#173f35] px-6 py-3.5 text-sm font-semibold text-white shadow-[0_14px_35px_rgba(23,63,53,.18)] transition hover:-translate-y-0.5 hover:bg-[#205448]"
                href="/entrar"
              >
                Começar gratuitamente
                <ArrowIcon />
              </a>
              <a
                className="inline-flex items-center justify-center rounded-full px-6 py-3.5 text-sm font-semibold text-[#476158] transition hover:bg-white/70"
                href="#produto"
              >
                Ver demonstração
              </a>
            </div>
            <div className="mt-6 flex flex-wrap gap-x-6 gap-y-2 text-xs text-[#75877f]">
              <span>✓ Sem planilhas</span>
              <span>✓ Clareza sem julgamentos</span>
              <span>✓ Você decide cada mudança</span>
            </div>
          </div>

          <div
            id="produto"
            className="relative min-w-0 max-w-full overflow-hidden lg:-my-8 lg:translate-x-4 lg:scale-[.9] lg:overflow-visible"
          >
            <div className="preview-orbit" />
            <FinancialHeroVisual />
          </div>
        </section>
      </div>

      <section
        id="como-funciona"
        className="border-y border-[#dfe5dc] bg-[#eef1e9] px-5 py-20 sm:px-8 lg:py-28"
      >
        <div className="mx-auto max-w-[1100px]">
          <div className="max-w-xl">
            <p className="text-xs font-bold uppercase tracking-[.18em] text-[#779058]">
              Do extrato à ação
            </p>
            <h2 className="mt-4 text-3xl font-semibold tracking-[-.05em] text-[#173f35] sm:text-5xl">
              Menos números soltos. Mais respostas.
            </h2>
          </div>
          <div className="mt-14 grid gap-5 md:grid-cols-3">
            {[
              [
                "01",
                "Reúna",
                "Contas e registros em uma visão organizada, sem guardar sua senha bancária.",
              ],
              [
                "02",
                "Entenda",
                "Veja mudanças, padrões e projeções com a origem de cada cálculo.",
              ],
              [
                "03",
                "Decida",
                "Simule metas e ajustes antes de confirmar qualquer mudança no seu plano.",
              ],
            ].map(([number, title, description]) => (
              <article
                className="rounded-[24px] border border-white/80 bg-white/60 p-7"
                key={number}
              >
                <span className="text-xs font-semibold text-[#8a9c94]">{number}</span>
                <h3 className="mt-8 text-xl font-semibold tracking-[-.03em]">
                  {title}
                </h3>
                <p className="mt-3 text-sm leading-6 text-[#66776f]">
                  {description}
                </p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section
        id="seguranca"
        className="bg-[#173f35] px-5 py-20 text-white sm:px-8 lg:py-28"
      >
        <div className="mx-auto grid max-w-[1100px] gap-12 lg:grid-cols-2 lg:items-center">
          <div>
            <p className="text-xs font-bold uppercase tracking-[.18em] text-[#d9ff65]">
              Privacidade por princípio
            </p>
            <h2 className="mt-4 text-3xl font-semibold tracking-[-.05em] sm:text-5xl">
              Seus dados existem para ajudar você.
            </h2>
          </div>
          <div className="grid gap-4 text-sm leading-6 text-white/70 sm:grid-cols-2">
            <p className="rounded-2xl border border-white/10 p-5">
              A Rayo nunca armazena sua senha bancária.
            </p>
            <p className="rounded-2xl border border-white/10 p-5">
              Toda simulação fica separada até sua confirmação.
            </p>
            <p className="rounded-2xl border border-white/10 p-5">
              Cálculos financeiros são determinísticos e explicáveis.
            </p>
            <p className="rounded-2xl border border-white/10 p-5">
              Conexões podem ser revogadas por você.
            </p>
          </div>
        </div>
      </section>

      <section id="acesso" className="bg-[#d9ff65] px-5 py-16 sm:px-8">
        <div className="mx-auto flex max-w-[1100px] flex-col justify-between gap-8 sm:flex-row sm:items-center">
          <div>
            <p className="text-sm font-semibold text-[#3c5d30]">Estamos construindo com cuidado.</p>
            <h2 className="mt-2 text-3xl font-semibold tracking-[-.05em] text-[#173f35]">
              Acesso antecipado em breve.
            </h2>
          </div>
          <span className="inline-flex w-fit rounded-full border border-[#91b83f] px-5 py-3 text-sm font-semibold text-[#244b40]">
            Beta privada
          </span>
        </div>
      </section>

      <footer className="bg-[#f6f7f1] px-5 py-8 sm:px-8">
        <div className="mx-auto flex max-w-[1100px] flex-col gap-4 text-xs text-[#71837b] sm:flex-row sm:items-center sm:justify-between">
          <Brand />
          <p>© 2026 Rayo Finanças. Clareza para decidir melhor.</p>
        </div>
      </footer>
    </main>
  );
}
