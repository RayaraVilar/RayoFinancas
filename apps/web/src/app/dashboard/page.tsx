import { randomUUID } from "node:crypto";

import {
  ArrowLeftRight,
  ArrowDownLeft,
  ArrowUpRight,
  Building2,
  ChartNoAxesColumnIncreasing,
  CalendarClock,
  ChevronRight,
  CircleUserRound,
  CreditCard as CreditCardIcon,
  Filter,
  Landmark,
  Plus,
  ReceiptText,
  RotateCcw,
  Scissors,
  Search,
  Sparkles,
  Trash2,
  WalletCards,
} from "lucide-react";
import { redirect } from "next/navigation";

import { Brand } from "@/components/brand";
import { BankConnect } from "@/components/bank-connect";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, serverApi } from "@/lib/server-api";
import {
  archiveCategoryRuleAction,
  createBillAction,
  createCategoryRuleAction,
  createCreditCardAction,
  createDebtAction,
  createGoalAction,
  createReceivableAction,
  createSubscriptionAction,
  createTransferAction,
  createTransactionAction,
  logoutAction,
  payCardInvoiceAction,
  refundTransactionAction,
  revokeBankConnectionAction,
  saveMonthlyPlanAction,
  simulatePaymentAction,
  syncBankConnectionAction,
  splitTransactionAction,
  transitionBillAction,
} from "./actions";

type User = {
  display_name: string;
  email: string;
  onboarding_completed_at: string | null;
};

type Profile = {
  id: string;
  type: "PERSONAL" | "BUSINESS";
  name: string;
};

type Context = {
  mode: "all" | "profile";
  profile_id: string | null;
  profile_name: string | null;
};

type Account = {
  id: string;
  name: string;
  institution_name: string | null;
};

type Category = {
  id: string;
  name: string;
  kind: "INCOME" | "EXPENSE" | "BOTH";
  color: string;
};

type CategoryRule = {
  id: string;
  category_id: string;
  match_text: string;
  priority: number;
};

type BankingStatus = {
  provider: "PLUGGY";
  configured: boolean;
  mode: "SANDBOX" | "PENDING_CREDENTIALS";
};

type BankConnection = {
  id: string;
  connector_name: string | null;
  status:
    | "PENDING"
    | "SYNCING"
    | "HEALTHY"
    | "ERROR"
    | "RECONNECT_REQUIRED"
    | "REVOKED";
  error_code: string | null;
  last_synced_at: string | null;
  sync_started_at: string | null;
  sync_accounts_total: number;
  sync_transactions_total: number;
  consecutive_failures: number;
};

type CreditCard = {
  id: string;
  name: string;
  institution_name: string | null;
  last_four: string | null;
  closing_day: number;
  due_day: number;
  credit_limit: string;
  open_balance: string;
};

type CardInvoice = {
  id: string;
  credit_card_id: string;
  card_name: string;
  competence_month: string;
  due_on: string;
  status: "OPEN" | "CLOSED" | "PAID";
  total_amount: string;
  paid_on: string | null;
};

type Transaction = {
  id: string;
  kind: "INCOME" | "EXPENSE" | "TRANSFER";
  status: "PENDING" | "POSTED" | "VOIDED";
  description: string;
  amount: string;
  currency: string;
  occurred_on: string;
  category_id: string | null;
  account_id: string | null;
  credit_card_id: string | null;
  card_invoice_id: string | null;
  transfer_group_id: string | null;
  transfer_direction: "OUTFLOW" | "INFLOW" | null;
  reversal_of_transaction_id: string | null;
  version: number;
};

type TransactionPage = {
  items: Transaction[];
  next_cursor: string | null;
  income_total: string;
  expense_total: string;
  net_total: string;
};

type AnalyticsMetric = {
  value: string;
  previous_equivalent: string | null;
  change_percent: string | null;
};

type DashboardAnalytics = {
  period_start: string;
  period_end: string;
  income: AnalyticsMetric;
  expense: AnalyticsMetric;
  monthly_balance: AnalyticsMetric;
  savings_rate_percent: string | null;
  net_worth: string;
  projected_month_expense: string;
  projected_month_balance: string;
  categories: {
    category: string;
    color: string;
    amount: string;
    share_percent: string;
  }[];
  recurring_expenses: {
    description: string;
    average_amount: string;
    occurrences: number;
  }[];
  coverage: {
    transaction_count: number;
    categorized_percent: string;
    latest_sync_at: string | null;
    freshness: string;
    confidence: string;
  };
  calculation_notes: string[];
};

type PlanningSummary = {
  as_of: string;
  horizon_end: string;
  account_balance: string;
  confirmed_bills: string;
  planned_commitments: string;
  free_balance: string;
  projected_deficit: boolean;
  bills: {
    id: string;
    description: string;
    amount: string;
    due_on: string;
    status: "DRAFT" | "REVIEW_REQUIRED" | "CONFIRMED" | "PAID" | "DISMISSED";
    version: number;
  }[];
  plan: {
    competence_month: string;
    expected_income: string;
    essential_commitment: string;
    debt_commitment: string;
    goal_contribution: string;
  } | null;
  calculation_notes: string[];
};

type Goal = {
  id: string;
  name: string;
  target_amount: string;
  current_amount: string;
  progress_percent: string;
  pace_status: string;
};

type Debt = {
  id: string;
  name: string;
  outstanding_balance: string;
  annual_cet_rate: string | null;
  data_quality: string;
};

type Future = {
  net_worth: string;
  assumed_monthly_savings: string;
  health_score: {
    score: string | null;
    confidence_percent: string;
    sufficient_data: boolean;
    disclaimer: string;
  };
  projections: {
    months: number;
    net_worth: string;
  }[];
};

type Insight = {
  id: string;
  priority: number;
  severity: string;
  title: string;
  message: string;
};

type BusinessCalendar = {
  opening_balance: string;
  working_capital_at_horizon: string;
  days: {
    date: string;
    payable: string;
    receivable: string;
    projected_balance: string;
  }[];
};

function money(value: string) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(Number(value));
}

function shortDate(value: string) {
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "short",
  }).format(new Date(`${value}T12:00:00`));
}

function monthLabel(value: string) {
  return new Intl.DateTimeFormat("pt-BR", {
    month: "long",
    year: "numeric",
  }).format(new Date(`${value}T12:00:00`));
}

function dateTimeLabel(value: string) {
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "America/Sao_Paulo",
  }).format(new Date(value));
}

export const dynamic = "force-dynamic";

export default async function DashboardPage({
  searchParams,
}: {
  searchParams: Promise<{
    profile?: string;
    query?: string;
    kind?: string;
    cursor?: string;
    error?: string;
    success?: string;
    split?: string;
    simulation?: string;
    payment_total?: string;
    payment_expires?: string;
    payment_operations?: string;
    payment_account?: string;
    payment_balance_after?: string;
    payment_free_after?: string;
    payment_risk?: string;
  }>;
}) {
  const {
    profile = "all",
    query = "",
    kind = "",
    cursor = "",
    error: actionError,
    success,
    split = "",
    simulation = "",
    payment_total: paymentTotal = "",
    payment_expires: paymentExpires = "",
    payment_operations: paymentOperations = "",
    payment_account: paymentAccount = "",
    payment_balance_after: paymentBalanceAfter = "",
    payment_free_after: paymentFreeAfter = "",
    payment_risk: paymentRisk = "",
  } = await searchParams;
  let user: User;
  let profiles: Profile[];
  let context: Context;
  let transactions: TransactionPage;
  let analytics: DashboardAnalytics;
  let accounts: Account[] = [];
  let categories: Category[] = [];
  let creditCards: CreditCard[] = [];
  let cardInvoices: CardInvoice[] = [];
  let categoryRules: CategoryRule[] = [];
  let bankingStatus: BankingStatus = {
    provider: "PLUGGY",
    configured: false,
    mode: "PENDING_CREDENTIALS",
  };
  let bankConnections: BankConnection[] = [];
  let planning: PlanningSummary | null = null;
  let goals: Goal[] = [];
  let debts: Debt[] = [];
  let future: Future | null = null;
  let insights: Insight[] = [];
  let businessCalendar: BusinessCalendar | null = null;
  try {
    [user, profiles, context] = await Promise.all([
      serverApi<User>("/auth/me"),
      serverApi<Profile[]>("/financial-profiles"),
      serverApi<Context>("/financial-context", {
        headers: { "X-Financial-Profile-Id": profile },
      }),
    ]);
    const transactionParams = new URLSearchParams();
    if (query) transactionParams.set("query", query);
    if (kind) transactionParams.set("kind", kind);
    if (cursor) transactionParams.set("cursor", cursor);
    transactionParams.set("limit", "12");
    transactions = await serverApi<TransactionPage>(
      `/transactions?${transactionParams.toString()}`,
      { headers: { "X-Financial-Profile-Id": profile } },
    );
    analytics = await serverApi<DashboardAnalytics>("/analytics/dashboard", {
      headers: { "X-Financial-Profile-Id": profile },
    });
    if (profile !== "all") {
      [
        accounts,
        categories,
        creditCards,
        cardInvoices,
        categoryRules,
        bankingStatus,
        bankConnections,
        planning,
        goals,
        debts,
        future,
        insights,
        businessCalendar,
      ] = await Promise.all([
        serverApi<Account[]>(`/financial-profiles/${profile}/accounts`),
        serverApi<Category[]>(`/financial-profiles/${profile}/categories`),
        serverApi<CreditCard[]>(`/financial-profiles/${profile}/credit-cards`),
        serverApi<CardInvoice[]>(`/financial-profiles/${profile}/card-invoices`),
        serverApi<CategoryRule[]>(`/financial-profiles/${profile}/category-rules`),
        serverApi<BankingStatus>("/banking/status"),
        serverApi<BankConnection[]>(
          `/financial-profiles/${profile}/bank-connections`,
        ),
        serverApi<PlanningSummary>(
          `/financial-profiles/${profile}/planning/summary`,
        ),
        serverApi<Goal[]>(`/financial-profiles/${profile}/goals`),
        serverApi<Debt[]>(`/financial-profiles/${profile}/debts`),
        serverApi<Future>(`/financial-profiles/${profile}/future`),
        serverApi<Insight[]>(`/financial-profiles/${profile}/insights`),
        profiles.find((item) => item.id === profile)?.type === "BUSINESS"
          ? serverApi<BusinessCalendar>(
              `/financial-profiles/${profile}/business-calendar`,
            )
          : Promise.resolve(null),
      ]);
    }
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) redirect("/entrar");
    if (error instanceof ApiError && error.status === 404) redirect("/dashboard");
    throw error;
  }
  if (!user.onboarding_completed_at) redirect("/onboarding");
  const transferOperationKey = randomUUID();
  const splitTransaction = transactions.items.find((item) => item.id === split);

  return (
    <main className="min-h-screen bg-[#f3f5ef] text-[#173f35]">
      <header className="border-b border-[#dde5de] bg-white/80 backdrop-blur">
        <div className="mx-auto flex max-w-[1180px] items-center justify-between px-5 py-4 sm:px-8">
          <Brand />
          <div className="flex items-center gap-4">
            <div className="hidden text-right sm:block">
              <p className="text-sm font-semibold">{user.display_name}</p>
              <p className="text-xs text-[#7f8e87]">{user.email}</p>
            </div>
            <form action={logoutAction}>
              <Button size="sm" type="submit" variant="ghost">
                Sair
              </Button>
            </form>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-[1180px] px-5 py-8 sm:px-8">
        <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
          <div>
            <p className="text-xs font-bold uppercase tracking-[.16em] text-[#7d945e]">
              Contexto financeiro
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-[-.05em] sm:text-4xl">
              {context.mode === "all" ? "Tudo" : context.profile_name}
            </h1>
            <p className="mt-2 text-sm text-[#71817a]">
              Lançamentos manuais com origem, competência e contexto explícitos.
            </p>
          </div>
          <form className="flex items-center gap-2" method="get">
            <label className="sr-only" htmlFor="profile">
              Perfil financeiro
            </label>
            <select
              className="h-11 rounded-full border border-[#cdd9d0] bg-white px-4 text-sm font-semibold outline-none focus:ring-2 focus:ring-[#dce9df]"
              defaultValue={profile}
              id="profile"
              name="profile"
            >
              <option value="all">Tudo</option>
              {profiles.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
            <Button size="sm" type="submit" variant="outline">
              Aplicar
            </Button>
          </form>
        </div>

        {actionError ? (
          <div className="mt-6 rounded-2xl border border-[#efcfc8] bg-[#fff3f0] px-4 py-3 text-sm text-[#9a4639]">
            {actionError}
          </div>
        ) : null}
        {success ? (
          <div className="mt-6 rounded-2xl border border-[#d5e5cd] bg-[#f2faeb] px-4 py-3 text-sm text-[#42643a]">
            {success}
          </div>
        ) : null}
        {simulation ? (
          <Card className="mt-6 border-[#cfe0c7] bg-[#f6fbf1] p-5">
            <div className="flex flex-col justify-between gap-4 sm:flex-row">
              <div>
                <p className="text-xs font-bold uppercase tracking-[.14em] text-[#6f8657]">
                  Simulação de pagamento
                </p>
                <p className="mt-2 text-xl font-semibold">
                  {money(paymentTotal)} em {paymentOperations} operação(ões)
                </p>
                <p className="mt-1 text-xs text-[#65756d]">
                  Melhor opção: {paymentAccount}. Saldo após: {money(paymentBalanceAfter)} ·
                  Saldo Livre: {money(paymentFreeAfter)} · risco {paymentRisk.toLowerCase()}.
                </p>
              </div>
              <p className="text-[10px] leading-4 text-[#75837c] sm:max-w-64 sm:text-right">
                Expira em {dateTimeLabel(paymentExpires)}. Nenhum pagamento foi iniciado.
                Alterações nas contas invalidam os hashes desta proposta.
              </p>
            </div>
          </Card>
        ) : null}

        <div className="mt-8 grid gap-4 sm:grid-cols-3">
          <Card className="p-5">
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold text-[#71817a]">Receitas</p>
              <ArrowDownLeft className="size-4 text-[#4e9a6d]" />
            </div>
            <p className="mt-3 text-2xl font-semibold tracking-[-.04em] text-[#24523f]">
              {money(analytics.income.value)}
            </p>
            <p className="mt-1 text-[10px] text-[#87958e]">
              {analytics.income.change_percent === null
                ? "Sem base equivalente"
                : `${Number(analytics.income.change_percent) >= 0 ? "+" : ""}${analytics.income.change_percent}% vs. período equivalente`}
            </p>
          </Card>
          <Card className="p-5">
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold text-[#71817a]">Despesas</p>
              <ArrowUpRight className="size-4 text-[#b55b55]" />
            </div>
            <p className="mt-3 text-2xl font-semibold tracking-[-.04em] text-[#8d4a45]">
              {money(analytics.expense.value)}
            </p>
            <p className="mt-1 text-[10px] text-[#87958e]">
              Projeção do mês: {money(analytics.projected_month_expense)}
            </p>
          </Card>
          <Card className="bg-[#173f35] p-5 text-white">
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold text-white/65">Resultado</p>
              <WalletCards className="size-4 text-[#d9ff65]" />
            </div>
            <p className="mt-3 text-2xl font-semibold tracking-[-.04em]">
              {money(analytics.monthly_balance.value)}
            </p>
            <p className="mt-1 text-[10px] text-white/60">
              Economia:{" "}
              {analytics.savings_rate_percent === null
                ? "renda insuficiente"
                : `${analytics.savings_rate_percent}%`}
            </p>
          </Card>
        </div>

        <div className="mt-5 grid gap-5 lg:grid-cols-[1.15fr_.85fr]">
          <Card className="p-5 sm:p-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-bold uppercase tracking-[.14em] text-[#79905d]">
                  Diagnóstico
                </p>
                <h2 className="mt-2 text-xl font-semibold tracking-[-.03em]">
                  Despesas por categoria
                </h2>
              </div>
              <ChartNoAxesColumnIncreasing className="size-5 text-[#557268]" />
            </div>
            {analytics.categories.length ? (
              <div className="mt-5 space-y-3">
                {analytics.categories.map((category) => (
                  <div key={category.category}>
                    <div className="mb-1.5 flex items-center justify-between gap-3 text-xs">
                      <span className="truncate font-semibold">{category.category}</span>
                      <span className="shrink-0 text-[#71817a]">
                        {money(category.amount)} · {category.share_percent}%
                      </span>
                    </div>
                    <div
                      aria-label={`${category.category}: ${category.share_percent}%`}
                      className="h-2 overflow-hidden rounded-full bg-[#edf1ed]"
                      role="img"
                    >
                      <div
                        className="h-full rounded-full"
                        style={{
                          backgroundColor: category.color,
                          width: `${Math.min(100, Math.max(0, Number(category.share_percent)))}%`,
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-5 text-sm text-[#7c8b84]">
                Categorize despesas para visualizar a distribuição.
              </p>
            )}
          </Card>

          <Card className="p-5 sm:p-6">
            <p className="text-xs font-bold uppercase tracking-[.14em] text-[#79905d]">
              Fechamento estimado
            </p>
            <p className="mt-3 text-3xl font-semibold tracking-[-.05em]">
              {money(analytics.projected_month_balance)}
            </p>
            <p className="mt-2 text-xs leading-5 text-[#71817a]">
              Patrimônio reconhecido: {money(analytics.net_worth)}. Confiança{" "}
              {analytics.coverage.confidence.toLocaleLowerCase()} com{" "}
              {analytics.coverage.categorized_percent}% das despesas categorizadas.
            </p>
            <details className="mt-5 rounded-2xl bg-[#f4f7f2] p-4 text-xs text-[#617169]">
              <summary className="cursor-pointer font-semibold text-[#315d4f]">
                Como calculamos
              </summary>
              <ul className="mt-3 space-y-2">
                {analytics.calculation_notes.map((note) => (
                  <li key={note}>• {note}</li>
                ))}
              </ul>
            </details>
          </Card>
        </div>

        {profile !== "all" && future ? (
          <section className="mt-5 grid gap-5 lg:grid-cols-3">
            <Card className="p-5 sm:p-6">
              <p className="text-xs font-bold uppercase tracking-[.14em] text-[#79905d]">
                Futuro financeiro
              </p>
              <div className="mt-3 flex items-end justify-between gap-4">
                <div>
                  <p className="text-3xl font-semibold tracking-[-.05em]">
                    {future.health_score.score ?? "—"}
                  </p>
                  <p className="text-[10px] text-[#7c8b84]">
                    Saúde financeira · confiança {future.health_score.confidence_percent}%
                  </p>
                </div>
                <Sparkles className="size-5 text-[#79905d]" />
              </div>
              <p className="mt-4 text-xs leading-5 text-[#71817a]">
                Patrimônio atual {money(future.net_worth)}. Em 12 meses,{" "}
                {money(
                  future.projections.find((point) => point.months === 12)?.net_worth ??
                    future.net_worth,
                )}
                , considerando economia mensal de {money(future.assumed_monthly_savings)}.
              </p>
              <p className="mt-3 text-[10px] leading-4 text-[#8b9791]">
                {future.health_score.disclaimer}
              </p>
            </Card>

            <Card className="p-5 sm:p-6">
              <p className="text-xs font-bold uppercase tracking-[.14em] text-[#79905d]">
                Metas e dívidas
              </p>
              <div className="mt-4 space-y-3">
                {goals.slice(0, 2).map((goal) => (
                  <div className="rounded-2xl bg-[#f4f7f2] p-3" key={goal.id}>
                    <div className="flex justify-between gap-3 text-xs">
                      <span className="font-semibold">{goal.name}</span>
                      <span>{goal.progress_percent}%</span>
                    </div>
                    <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-[#dfe7df]">
                      <div
                        className="h-full rounded-full bg-[#6f8f59]"
                        style={{ width: `${Math.min(100, Number(goal.progress_percent))}%` }}
                      />
                    </div>
                  </div>
                ))}
                {debts.slice(0, 2).map((debt) => (
                  <div className="flex justify-between gap-3 text-xs" key={debt.id}>
                    <span className="truncate text-[#66766f]">{debt.name}</span>
                    <span className="shrink-0 font-semibold">
                      {money(debt.outstanding_balance)}
                    </span>
                  </div>
                ))}
                {!goals.length && !debts.length ? (
                  <p className="text-xs leading-5 text-[#7c8b84]">
                    Cadastre metas e dívidas para comparar ritmo, custo e prioridade.
                  </p>
                ) : null}
              </div>
              <details className="mt-4 border-t border-[#e3e9e4] pt-3">
                <summary className="cursor-pointer text-xs font-semibold text-[#315d4f]">
                  Cadastrar meta
                </summary>
                <form action={createGoalAction} className="mt-3 grid gap-2">
                  <input name="profile_id" type="hidden" value={profile} />
                  <Input name="name" placeholder="Nome da meta" required />
                  <div className="grid grid-cols-2 gap-2">
                    <Input
                      inputMode="decimal"
                      name="target_amount"
                      placeholder="Valor alvo"
                      required
                    />
                    <Input
                      defaultValue="0"
                      inputMode="decimal"
                      name="current_amount"
                      placeholder="Valor atual"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <Input name="target_date" required type="date" />
                    <Input
                      defaultValue="0"
                      inputMode="decimal"
                      name="monthly_contribution"
                      placeholder="Aporte mensal"
                    />
                  </div>
                  <Button size="sm" type="submit" variant="outline">
                    Criar meta
                  </Button>
                </form>
              </details>
              <details className="mt-3 border-t border-[#e3e9e4] pt-3">
                <summary className="cursor-pointer text-xs font-semibold text-[#315d4f]">
                  Cadastrar dívida
                </summary>
                <form action={createDebtAction} className="mt-3 grid gap-2">
                  <input name="profile_id" type="hidden" value={profile} />
                  <Input name="name" placeholder="Nome da dívida" required />
                  <div className="grid grid-cols-2 gap-2">
                    <Input
                      inputMode="decimal"
                      name="original_principal"
                      placeholder="Valor original"
                      required
                    />
                    <Input
                      inputMode="decimal"
                      name="outstanding_balance"
                      placeholder="Saldo devedor"
                      required
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <Input
                      inputMode="decimal"
                      name="annual_interest_rate"
                      placeholder="Juros a.a. (%)"
                    />
                    <Input
                      inputMode="decimal"
                      name="annual_cet_rate"
                      placeholder="CET a.a. (%)"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <select
                      className="h-10 rounded-xl border border-[#cdd9d0] bg-white px-3 text-xs"
                      name="amortization_system"
                    >
                      <option value="UNKNOWN">Sistema desconhecido</option>
                      <option value="PRICE">Price</option>
                      <option value="SAC">SAC</option>
                    </select>
                    <Input
                      min={1}
                      name="installments_remaining"
                      placeholder="Parcelas restantes"
                      required
                      type="number"
                    />
                  </div>
                  <Input
                    inputMode="decimal"
                    name="monthly_payment"
                    placeholder="Parcela mensal (opcional)"
                  />
                  <Input name="next_due_on" type="date" />
                  <Button size="sm" type="submit" variant="outline">
                    Cadastrar dívida
                  </Button>
                </form>
              </details>
            </Card>

            <Card className="p-5 sm:p-6">
              <p className="text-xs font-bold uppercase tracking-[.14em] text-[#79905d]">
                Próximas decisões
              </p>
              <div className="mt-4 space-y-3">
                {insights.length ? (
                  insights.map((insight) => (
                    <div className="rounded-2xl border border-[#e0e7e1] p-3" key={insight.id}>
                      <p className="text-xs font-semibold">{insight.title}</p>
                      <p className="mt-1 text-[11px] leading-4 text-[#71817a]">
                        {insight.message}
                      </p>
                    </div>
                  ))
                ) : (
                  <p className="text-xs leading-5 text-[#7c8b84]">
                    Nenhum alerta relevante agora. As regras são versionadas e exibem no
                    máximo três prioridades.
                  </p>
                )}
              </div>
              <div className="mt-4 rounded-2xl bg-[#173f35] p-3 text-[10px] leading-4 text-white/70">
                Pagamentos permanecem em modo de simulação. Nenhuma movimentação externa é
                executada por esta tela ou pelo assistente.
              </div>
            </Card>

            {businessCalendar ? (
              <Card className="p-5 sm:p-6 lg:col-span-3">
                <p className="text-xs font-bold uppercase tracking-[.14em] text-[#79905d]">
                  Caixa do negócio
                </p>
                <div className="mt-3 grid gap-3 sm:grid-cols-3">
                  <div>
                    <p className="text-[10px] text-[#7c8b84]">Saldo inicial</p>
                    <p className="mt-1 font-semibold">
                      {money(businessCalendar.opening_balance)}
                    </p>
                  </div>
                  <div>
                    <p className="text-[10px] text-[#7c8b84]">Fechamento projetado</p>
                    <p className="mt-1 font-semibold">
                      {money(
                        businessCalendar.days.at(-1)?.projected_balance ??
                          businessCalendar.opening_balance,
                      )}
                    </p>
                  </div>
                  <div>
                    <p className="text-[10px] text-[#7c8b84]">Saldo no horizonte</p>
                    <p className="mt-1 font-semibold">
                      {money(businessCalendar.working_capital_at_horizon)}
                    </p>
                  </div>
                </div>
                <div className="mt-5 grid gap-4 border-t border-[#e3e9e4] pt-4 md:grid-cols-2">
                  <form action={createReceivableAction} className="grid gap-2">
                    <input name="profile_id" type="hidden" value={profile} />
                    <p className="text-xs font-semibold">Novo recebível confirmado</p>
                    <Input name="description" placeholder="Descrição" required />
                    <div className="grid grid-cols-2 gap-2">
                      <Input name="counterparty" placeholder="Cliente" />
                      <Input inputMode="decimal" name="amount" placeholder="Valor" required />
                    </div>
                    <Input name="due_on" required type="date" />
                    <Button size="sm" type="submit" variant="outline">
                      Adicionar recebível
                    </Button>
                  </form>
                  <form action={createSubscriptionAction} className="grid gap-2">
                    <input name="profile_id" type="hidden" value={profile} />
                    <p className="text-xs font-semibold">Candidata a assinatura</p>
                    <Input name="name" placeholder="Serviço ou fornecedor" required />
                    <div className="grid grid-cols-2 gap-2">
                      <Input inputMode="decimal" name="amount" placeholder="Valor" required />
                      <Input
                        defaultValue={1}
                        max={12}
                        min={1}
                        name="cadence_months"
                        type="number"
                      />
                    </div>
                    <Input name="next_charge_on" required type="date" />
                    <Button size="sm" type="submit" variant="outline">
                      Criar para revisão
                    </Button>
                  </form>
                </div>
              </Card>
            ) : null}
          </section>
        ) : null}

        {profile !== "all" && planning ? (
          <section className="mt-5 grid gap-5 lg:grid-cols-[1.1fr_.9fr]">
            <Card className="p-5 sm:p-6">
              <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
                <div>
                  <p className="text-xs font-bold uppercase tracking-[.14em] text-[#79905d]">
                    Saldo Livre
                  </p>
                  <h2 className="mt-2 text-3xl font-semibold tracking-[-.05em]">
                    {money(planning.free_balance)}
                  </h2>
                  <p
                    className={`mt-2 text-xs ${
                      planning.projected_deficit ? "text-[#a5514b]" : "text-[#71817a]"
                    }`}
                  >
                    {planning.projected_deficit
                      ? "Déficit projetado: revise compromissos antes de assumir novos gastos."
                      : `Depois de ${money(planning.planned_commitments)} em compromissos até ${shortDate(planning.horizon_end)}.`}
                  </p>
                </div>
                <div className="rounded-2xl bg-[#f4f7f2] px-4 py-3 text-right">
                  <p className="text-[10px] uppercase tracking-[.12em] text-[#7c8b84]">
                    Saldo em contas
                  </p>
                  <p className="mt-1 text-sm font-semibold">
                    {money(planning.account_balance)}
                  </p>
                </div>
              </div>

              <div className="mt-6 border-t border-[#e5ebe6] pt-5">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold">Central de Contas</h3>
                  <span className="text-[11px] text-[#7c8b84]">
                    {money(planning.confirmed_bills)} confirmados
                  </span>
                </div>
                {planning.bills.length ? (
                  <div className="mt-3 space-y-2">
                    {planning.bills.slice(0, 5).map((bill) => (
                      <div
                        className="flex items-center gap-3 rounded-2xl bg-[#f7f9f5] px-4 py-3"
                        key={bill.id}
                      >
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-xs font-semibold">{bill.description}</p>
                          <p className="mt-0.5 text-[10px] text-[#7c8b84]">
                            {money(bill.amount)} · vence {shortDate(bill.due_on)}
                            {bill.status === "REVIEW_REQUIRED"
                              ? " · possível duplicidade"
                              : ""}
                          </p>
                        </div>
                        {bill.status === "DRAFT" || bill.status === "REVIEW_REQUIRED" ? (
                          <form action={transitionBillAction}>
                            <input name="profile_id" type="hidden" value={profile} />
                            <input name="bill_id" type="hidden" value={bill.id} />
                            <input name="version" type="hidden" value={bill.version} />
                            <input name="target_status" type="hidden" value="CONFIRMED" />
                            <button
                              className="text-[11px] font-semibold text-[#315d4f]"
                              type="submit"
                            >
                              Confirmar
                            </button>
                          </form>
                        ) : bill.status === "CONFIRMED" ? (
                          <form action={transitionBillAction}>
                            <input name="profile_id" type="hidden" value={profile} />
                            <input name="bill_id" type="hidden" value={bill.id} />
                            <input name="version" type="hidden" value={bill.version} />
                            <input name="target_status" type="hidden" value="PAID" />
                            <input
                              name="paid_on"
                              type="hidden"
                              value={new Date().toISOString().slice(0, 10)}
                            />
                            <button
                              className="text-[11px] font-semibold text-[#315d4f]"
                              type="submit"
                            >
                              Marcar paga
                            </button>
                          </form>
                        ) : null}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="mt-3 text-xs text-[#7c8b84]">
                    Nenhuma conta futura confirmada neste perfil.
                  </p>
                )}
                <form action={createBillAction} className="mt-4 grid gap-3 sm:grid-cols-4">
                  <input name="profile_id" type="hidden" value={profile} />
                  <Input name="description" placeholder="Descrição" required />
                  <Input inputMode="decimal" name="amount" placeholder="Valor" required />
                  <Input name="due_on" required type="date" />
                  <Button type="submit">Adicionar conta</Button>
                </form>
                {planning.bills.some((bill) => bill.status === "CONFIRMED") ? (
                  <form
                    action={simulatePaymentAction}
                    className="mt-4 rounded-2xl border border-[#dce5dc] p-4"
                  >
                    <input name="profile_id" type="hidden" value={profile} />
                    <p className="text-xs font-semibold">Simular pagamentos</p>
                    <p className="mt-1 text-[10px] text-[#7c8b84]">
                      Selecione contas confirmadas. A simulação não movimenta dinheiro.
                    </p>
                    <div className="mt-3 grid gap-2 sm:grid-cols-2">
                      {planning.bills
                        .filter((bill) => bill.status === "CONFIRMED")
                        .map((bill) => (
                          <label
                            className="flex items-center gap-2 text-xs"
                            key={bill.id}
                          >
                            <input name="bill_ids" type="checkbox" value={bill.id} />
                            <span className="truncate">
                              {bill.description} · {money(bill.amount)}
                            </span>
                          </label>
                        ))}
                    </div>
                    <Button className="mt-3" size="sm" type="submit" variant="outline">
                      Gerar proposta segura
                    </Button>
                  </form>
                ) : null}
              </div>
            </Card>

            <Card className="p-5 sm:p-6">
              <p className="text-xs font-bold uppercase tracking-[.14em] text-[#79905d]">
                Planejamento mensal
              </p>
              <h2 className="mt-2 text-xl font-semibold tracking-[-.03em]">
                Premissas de {monthLabel(analytics.period_start)}
              </h2>
              <form action={saveMonthlyPlanAction} className="mt-5 grid gap-3 sm:grid-cols-2">
                <input name="profile_id" type="hidden" value={profile} />
                <input
                  name="competence_month"
                  type="hidden"
                  value={analytics.period_start}
                />
                <label className="text-xs font-semibold">
                  Renda prevista
                  <Input
                    className="mt-1.5"
                    defaultValue={planning.plan?.expected_income ?? "0.00"}
                    inputMode="decimal"
                    name="expected_income"
                  />
                </label>
                <label className="text-xs font-semibold">
                  Essenciais
                  <Input
                    className="mt-1.5"
                    defaultValue={planning.plan?.essential_commitment ?? "0.00"}
                    inputMode="decimal"
                    name="essential_commitment"
                  />
                </label>
                <label className="text-xs font-semibold">
                  Dívidas
                  <Input
                    className="mt-1.5"
                    defaultValue={planning.plan?.debt_commitment ?? "0.00"}
                    inputMode="decimal"
                    name="debt_commitment"
                  />
                </label>
                <label className="text-xs font-semibold">
                  Metas
                  <Input
                    className="mt-1.5"
                    defaultValue={planning.plan?.goal_contribution ?? "0.00"}
                    inputMode="decimal"
                    name="goal_contribution"
                  />
                </label>
                <Button className="sm:col-span-2" type="submit">
                  Salvar planejamento
                </Button>
              </form>
              <details className="mt-4 text-xs text-[#617169]">
                <summary className="cursor-pointer font-semibold text-[#315d4f]">
                  Como calculamos o Saldo Livre
                </summary>
                <ul className="mt-2 space-y-1.5">
                  {planning.calculation_notes.map((note) => (
                    <li key={note}>• {note}</li>
                  ))}
                </ul>
              </details>
            </Card>
          </section>
        ) : null}

        <div className="mt-5 grid gap-5 lg:grid-cols-[1.25fr_.75fr]">
          <Card className="overflow-hidden p-0">
            <div className="border-b border-[#e1e8e2] p-5 sm:p-6">
              <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
                <div>
                  <h2 className="text-xl font-semibold tracking-[-.03em]">
                    Movimentações
                  </h2>
                  <p className="mt-1 text-xs text-[#7c8b84]">
                    Valores realizados; transferências não entram nos totais.
                  </p>
                </div>
                <form className="flex gap-2" method="get">
                  <input name="profile" type="hidden" value={profile} />
                  <label className="relative">
                    <span className="sr-only">Buscar movimentação</span>
                    <Search className="absolute left-3 top-3 size-4 text-[#87958e]" />
                    <input
                      className="h-10 w-full rounded-full border border-[#d6e0d8] bg-[#f8faf6] pl-9 pr-3 text-xs outline-none focus:ring-2 focus:ring-[#dce9df] sm:w-44"
                      defaultValue={query}
                      name="query"
                      placeholder="Buscar"
                    />
                  </label>
                  <select
                    aria-label="Filtrar por tipo"
                    className="h-10 rounded-full border border-[#d6e0d8] bg-white px-3 text-xs font-semibold"
                    defaultValue={kind}
                    name="kind"
                  >
                    <option value="">Todos</option>
                    <option value="INCOME">Receitas</option>
                    <option value="EXPENSE">Despesas</option>
                    <option value="TRANSFER">Transferências</option>
                  </select>
                  <Button aria-label="Aplicar filtros" size="sm" type="submit" variant="outline">
                    <Filter className="size-4" />
                  </Button>
                </form>
              </div>
            </div>

            {transactions.items.length ? (
              <div className="divide-y divide-[#edf1ed]">
                {transactions.items.map((transaction) => (
                  <div className="flex items-center gap-3 px-5 py-4 sm:px-6" key={transaction.id}>
                    <span
                      className={`grid size-10 shrink-0 place-items-center rounded-xl ${
                        transaction.kind === "INCOME"
                          ? "bg-[#eaf6e7] text-[#43805d]"
                          : transaction.kind === "EXPENSE"
                            ? "bg-[#fff0ec] text-[#a5514b]"
                            : "bg-[#eef1f4] text-[#657681]"
                      }`}
                    >
                      {transaction.reversal_of_transaction_id ? (
                        <RotateCcw className="size-4" />
                      ) : transaction.kind === "TRANSFER" ? (
                        <ArrowLeftRight className="size-4" />
                      ) : transaction.kind === "INCOME" ? (
                        <ArrowDownLeft className="size-4" />
                      ) : (
                        <ArrowUpRight className="size-4" />
                      )}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold">
                        {transaction.description}
                      </p>
                      <p className="mt-1 text-[11px] text-[#819088]">
                        {shortDate(transaction.occurred_on)}
                        {transaction.status === "PENDING" ? " · Pendente" : ""}
                        {transaction.reversal_of_transaction_id ? " · Estorno" : ""}
                        {transaction.transfer_direction === "OUTFLOW" ? " · Saída" : ""}
                        {transaction.transfer_direction === "INFLOW" ? " · Entrada" : ""}
                        {transaction.credit_card_id
                          ? ` · ${
                              creditCards.find(
                                (card) => card.id === transaction.credit_card_id,
                              )?.name ?? "Cartão"
                            }`
                          : ""}
                      </p>
                    </div>
                    <p
                      className={`text-sm font-semibold ${
                        transaction.kind === "INCOME"
                          ? "text-[#397052]"
                          : transaction.kind === "EXPENSE"
                            ? "text-[#9d4d48]"
                            : "text-[#60716a]"
                      }`}
                    >
                      {transaction.kind === "INCOME" ? "+" : transaction.kind === "EXPENSE" ? "−" : ""}
                      {money(transaction.amount)}
                    </p>
                    {profile !== "all" &&
                    transaction.status === "POSTED" &&
                    transaction.kind !== "TRANSFER" &&
                    !transaction.reversal_of_transaction_id ? (
                      <div className="flex flex-col items-end gap-1">
                        <a
                          className="rounded-full px-2 py-1 text-[10px] font-semibold text-[#315d4f] hover:bg-[#f0f4ef]"
                          href={`/dashboard?profile=${profile}&split=${transaction.id}`}
                        >
                          Dividir
                        </a>
                        <form action={refundTransactionAction}>
                          <input name="profile_id" type="hidden" value={profile} />
                          <input
                            name="transaction_id"
                            type="hidden"
                            value={transaction.id}
                          />
                          <input
                            name="occurred_on"
                            type="hidden"
                            value={new Date().toISOString().slice(0, 10)}
                          />
                          <button
                            className="rounded-full px-2 py-1 text-[10px] font-semibold text-[#71817a] hover:bg-[#f0f4ef]"
                            type="submit"
                          >
                            Estornar
                          </button>
                        </form>
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>
            ) : (
              <div className="grid min-h-64 place-items-center p-8 text-center">
                <div>
                  <span className="mx-auto grid size-12 place-items-center rounded-2xl bg-[#eef4e9] text-[#547164]">
                    <ReceiptText className="size-5" />
                  </span>
                  <h3 className="mt-4 text-base font-semibold">Nenhuma movimentação</h3>
                  <p className="mt-2 max-w-xs text-xs leading-5 text-[#7c8b84]">
                    Selecione um perfil e registre a primeira receita ou despesa.
                  </p>
                </div>
              </div>
            )}

            {transactions.next_cursor ? (
              <div className="border-t border-[#e7ede8] p-4 text-center">
                <a
                  className="text-xs font-semibold text-[#315d4f]"
                  href={`/dashboard?${new URLSearchParams({
                    profile,
                    ...(query ? { query } : {}),
                    ...(kind ? { kind } : {}),
                    cursor: transactions.next_cursor,
                  }).toString()}`}
                >
                  Próxima página
                </a>
              </div>
            ) : null}
          </Card>

          <Card className="h-fit p-6">
            {profile !== "all" && (accounts.length || creditCards.length) ? (
              <>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs font-bold uppercase tracking-[.14em] text-[#79905d]">
                      Novo lançamento
                    </p>
                    <h2 className="mt-2 text-xl font-semibold tracking-[-.03em]">
                      Registre sem planilha
                    </h2>
                  </div>
                  <Plus className="size-5 text-[#557268]" />
                </div>
                <form action={createTransactionAction} className="mt-6 space-y-4">
                  <input name="profile_id" type="hidden" value={profile} />
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <Label htmlFor="kind">Tipo</Label>
                      <select
                        className="mt-1.5 h-11 w-full rounded-xl border border-[#d6e0d8] bg-white px-3 text-sm"
                        id="kind"
                        name="kind"
                      >
                        <option value="EXPENSE">Despesa</option>
                        <option value="INCOME">Receita</option>
                        <option value="TRANSFER">Transferência</option>
                      </select>
                    </div>
                    <div>
                      <Label htmlFor="amount">Valor</Label>
                      <Input
                        className="mt-1.5"
                        id="amount"
                        inputMode="decimal"
                        name="amount"
                        placeholder="0,00"
                        required
                      />
                    </div>
                  </div>
                  <div>
                    <Label htmlFor="description">Descrição</Label>
                    <Input
                      className="mt-1.5"
                      id="description"
                      maxLength={160}
                      name="description"
                      placeholder="Ex.: Supermercado"
                      required
                    />
                  </div>
                  <div>
                    <Label htmlFor="instrument">Origem</Label>
                    <select
                      className="mt-1.5 h-11 w-full rounded-xl border border-[#d6e0d8] bg-white px-3 text-sm"
                      id="instrument"
                      name="instrument"
                    >
                      {accounts.length ? (
                        <optgroup label="Contas">
                          {accounts.map((account) => (
                            <option key={account.id} value={`account:${account.id}`}>
                              {account.name}
                              {account.institution_name ? ` · ${account.institution_name}` : ""}
                            </option>
                          ))}
                        </optgroup>
                      ) : null}
                      {creditCards.length ? (
                        <optgroup label="Cartões">
                          {creditCards.map((card) => (
                            <option key={card.id} value={`card:${card.id}`}>
                              {card.name}
                              {card.last_four ? ` · final ${card.last_four}` : ""}
                            </option>
                          ))}
                        </optgroup>
                      ) : null}
                    </select>
                    <p className="mt-1.5 text-[11px] leading-4 text-[#809088]">
                      Compras no cartão entram na fatura; o pagamento não duplica a despesa.
                    </p>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <Label htmlFor="category_id">Categoria</Label>
                      <select
                        className="mt-1.5 h-11 w-full rounded-xl border border-[#d6e0d8] bg-white px-3 text-sm"
                        id="category_id"
                        name="category_id"
                      >
                        <option value="">Sem categoria</option>
                        {categories.map((category) => (
                          <option key={category.id} value={category.id}>
                            {category.name}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <Label htmlFor="occurred_on">Data</Label>
                      <Input
                        className="mt-1.5"
                        defaultValue={new Date().toISOString().slice(0, 10)}
                        id="occurred_on"
                        name="occurred_on"
                        required
                        type="date"
                      />
                    </div>
                  </div>
                  <Button className="w-full" type="submit">
                    Salvar lançamento
                  </Button>
                </form>
                {accounts.length >= 2 ? (
                  <details className="mt-5 border-t border-[#e5ebe6] pt-5">
                    <summary className="cursor-pointer list-none text-sm font-semibold text-[#315d4f]">
                      <span className="flex items-center justify-between">
                        Transferir entre contas
                        <ArrowLeftRight className="size-4" />
                      </span>
                    </summary>
                    <form action={createTransferAction} className="mt-4 space-y-4">
                      <input name="profile_id" type="hidden" value={profile} />
                      <input
                        name="idempotency_key"
                        type="hidden"
                        value={transferOperationKey}
                      />
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <Label htmlFor="source_account_id">Sai de</Label>
                          <select
                            className="mt-1.5 h-11 w-full rounded-xl border border-[#d6e0d8] bg-white px-3 text-sm"
                            id="source_account_id"
                            name="source_account_id"
                          >
                            {accounts.map((account) => (
                              <option key={account.id} value={account.id}>
                                {account.name}
                              </option>
                            ))}
                          </select>
                        </div>
                        <div>
                          <Label htmlFor="destination_account_id">Entra em</Label>
                          <select
                            className="mt-1.5 h-11 w-full rounded-xl border border-[#d6e0d8] bg-white px-3 text-sm"
                            defaultValue={accounts[1]?.id}
                            id="destination_account_id"
                            name="destination_account_id"
                          >
                            {accounts.map((account) => (
                              <option key={account.id} value={account.id}>
                                {account.name}
                              </option>
                            ))}
                          </select>
                        </div>
                      </div>
                      <div>
                        <Label htmlFor="transfer_description">Descrição</Label>
                        <Input
                          className="mt-1.5"
                          defaultValue="Transferência entre contas"
                          id="transfer_description"
                          name="description"
                          required
                        />
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <Label htmlFor="transfer_amount">Valor</Label>
                          <Input
                            className="mt-1.5"
                            id="transfer_amount"
                            inputMode="decimal"
                            name="amount"
                            placeholder="0,00"
                            required
                          />
                        </div>
                        <div>
                          <Label htmlFor="transfer_date">Data</Label>
                          <Input
                            className="mt-1.5"
                            defaultValue={new Date().toISOString().slice(0, 10)}
                            id="transfer_date"
                            name="occurred_on"
                            required
                            type="date"
                          />
                        </div>
                      </div>
                      <p className="text-[11px] leading-4 text-[#809088]">
                        A saída e a entrada são conciliadas juntas e não alteram receitas ou
                        despesas.
                      </p>
                      <Button className="w-full" type="submit" variant="outline">
                        Registrar transferência
                      </Button>
                    </form>
                  </details>
                ) : null}
                <details className="mt-5 border-t border-[#e5ebe6] pt-5">
                  <summary className="cursor-pointer list-none text-sm font-semibold text-[#315d4f]">
                    <span className="flex items-center justify-between">
                      Automatizar categoria
                      <Sparkles className="size-4" />
                    </span>
                  </summary>
                  <form action={createCategoryRuleAction} className="mt-4 space-y-3">
                    <input name="profile_id" type="hidden" value={profile} />
                    <div>
                      <Label htmlFor="rule_match_text">Descrição contém</Label>
                      <Input
                        className="mt-1.5"
                        id="rule_match_text"
                        name="match_text"
                        placeholder="Ex.: Uber"
                        required
                      />
                    </div>
                    <div>
                      <Label htmlFor="rule_category_id">Aplicar categoria</Label>
                      <select
                        className="mt-1.5 h-11 w-full rounded-xl border border-[#d6e0d8] bg-white px-3 text-sm"
                        id="rule_category_id"
                        name="category_id"
                      >
                        {categories.map((category) => (
                          <option key={category.id} value={category.id}>
                            {category.name}
                          </option>
                        ))}
                      </select>
                    </div>
                    <Button className="w-full" type="submit" variant="outline">
                      Criar regra
                    </Button>
                  </form>
                  {categoryRules.length ? (
                    <div className="mt-4 space-y-2">
                      {categoryRules.map((rule) => (
                        <div
                          className="flex items-center gap-2 rounded-xl bg-[#f4f7f2] px-3 py-2"
                          key={rule.id}
                        >
                          <p className="min-w-0 flex-1 truncate text-xs text-[#62736b]">
                            “{rule.match_text}” →{" "}
                            {categories.find((item) => item.id === rule.category_id)?.name ??
                              "Categoria"}
                          </p>
                          <form action={archiveCategoryRuleAction}>
                            <input name="profile_id" type="hidden" value={profile} />
                            <input name="rule_id" type="hidden" value={rule.id} />
                            <button
                              aria-label={`Remover regra ${rule.match_text}`}
                              className="grid size-7 place-items-center rounded-full text-[#829088] hover:bg-white"
                              type="submit"
                            >
                              <Trash2 className="size-3.5" />
                            </button>
                          </form>
                        </div>
                      ))}
                    </div>
                  ) : null}
                </details>
              </>
            ) : (
              <div className="py-6 text-center">
                <CircleUserRound className="mx-auto size-7 text-[#678078]" />
                <h2 className="mt-4 text-lg font-semibold">Escolha um perfil</h2>
                <p className="mt-2 text-xs leading-5 text-[#7c8b84]">
                  A visão Tudo consolida leituras. Para lançar, selecione o perfil de origem.
                </p>
                <div className="mt-5 space-y-2">
                  {profiles.map((item) => (
                    <a
                      className="flex items-center justify-between rounded-xl border border-[#e0e8e1] px-4 py-3 text-sm font-semibold"
                      href={`/dashboard?profile=${item.id}`}
                      key={item.id}
                    >
                      <span className="flex items-center gap-2">
                        {item.type === "PERSONAL" ? (
                          <CircleUserRound className="size-4" />
                        ) : (
                          <Building2 className="size-4" />
                        )}
                        {item.name}
                      </span>
                      <ChevronRight className="size-4" />
                    </a>
                  ))}
                </div>
              </div>
            )}
          </Card>
        </div>

        {profile !== "all" && splitTransaction ? (
          <Card className="mt-5 p-5 sm:p-6">
            <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
              <div className="flex items-start gap-3">
                <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-[#eef4e9] text-[#547164]">
                  <Scissors className="size-4" />
                </span>
                <div>
                  <p className="text-xs font-bold uppercase tracking-[.14em] text-[#79905d]">
                    Dividir lançamento
                  </p>
                  <h2 className="mt-1 text-lg font-semibold">
                    {splitTransaction.description} · {money(splitTransaction.amount)}
                  </h2>
                  <p className="mt-1 text-xs text-[#7c8b84]">
                    As duas partes devem somar exatamente o valor original.
                  </p>
                </div>
              </div>
              <a
                className="text-xs font-semibold text-[#62736b]"
                href={`/dashboard?profile=${profile}`}
              >
                Cancelar
              </a>
            </div>
            <form
              action={splitTransactionAction}
              className="mt-5 grid gap-4 lg:grid-cols-2"
            >
              <input name="profile_id" type="hidden" value={profile} />
              <input name="transaction_id" type="hidden" value={splitTransaction.id} />
              <input name="version" type="hidden" value={splitTransaction.version} />
              {[1, 2].map((position) => (
                <div
                  className="rounded-2xl border border-[#e0e8e1] bg-[#fafbf8] p-4"
                  key={position}
                >
                  <p className="text-xs font-semibold text-[#62736b]">
                    Parte {position}
                  </p>
                  <div className="mt-3 grid grid-cols-2 gap-3">
                    <div>
                      <Label htmlFor={`split_category_${position}`}>Categoria</Label>
                      <select
                        className="mt-1.5 h-11 w-full rounded-xl border border-[#d6e0d8] bg-white px-3 text-sm"
                        id={`split_category_${position}`}
                        name={`category_id_${position}`}
                      >
                        {categories
                          .filter(
                            (category) =>
                              category.kind === splitTransaction.kind ||
                              category.kind === "BOTH",
                          )
                          .map((category) => (
                            <option key={category.id} value={category.id}>
                              {category.name}
                            </option>
                          ))}
                      </select>
                    </div>
                    <div>
                      <Label htmlFor={`split_amount_${position}`}>Valor</Label>
                      <Input
                        className="mt-1.5"
                        id={`split_amount_${position}`}
                        inputMode="decimal"
                        name={`amount_${position}`}
                        placeholder="0,00"
                        required
                      />
                    </div>
                  </div>
                  <div className="mt-3">
                    <Label htmlFor={`split_description_${position}`}>
                      Detalhe opcional
                    </Label>
                    <Input
                      className="mt-1.5"
                      id={`split_description_${position}`}
                      name={`description_${position}`}
                      placeholder="Ex.: parte pessoal"
                    />
                  </div>
                </div>
              ))}
              <div className="lg:col-span-2">
                <Button className="w-full sm:w-auto" type="submit">
                  Salvar divisão
                </Button>
              </div>
            </form>
          </Card>
        ) : null}

        {profile !== "all" ? (
          <Card className="mt-5 p-5 sm:p-6">
            <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-center">
              <div className="flex items-start gap-3">
                <span className="grid size-11 shrink-0 place-items-center rounded-2xl bg-[#eef4e9] text-[#547164]">
                  <Landmark className="size-5" />
                </span>
                <div>
                  <p className="text-xs font-bold uppercase tracking-[.14em] text-[#79905d]">
                    Integração bancária
                  </p>
                  <h2 className="mt-1 text-lg font-semibold">Conecte com consentimento</h2>
                  <p className="mt-1 max-w-xl text-xs leading-5 text-[#7c8b84]">
                    O token de conexão é temporário. Senhas bancárias não passam pela Rayo e
                    você pode revogar o acesso quando quiser.
                  </p>
                </div>
              </div>
              <BankConnect
                configured={bankingStatus.configured}
                profileId={profile}
              />
            </div>
            {bankConnections.length ? (
              <div className="mt-5 grid gap-3 border-t border-[#e5ebe6] pt-5 sm:grid-cols-2">
                {bankConnections.map((connection) => (
                  <div
                    className="flex items-center gap-3 rounded-2xl bg-[#f6f8f4] px-4 py-3"
                    key={connection.id}
                  >
                    <span
                      className={`size-2 rounded-full ${
                        connection.status === "HEALTHY"
                          ? "bg-[#5b9c70]"
                          : connection.status === "REVOKED"
                            ? "bg-[#9aa59f]"
                            : connection.status === "ERROR" ||
                                connection.status === "RECONNECT_REQUIRED"
                              ? "bg-[#c36b5e]"
                              : "bg-[#d0a64d]"
                      }`}
                    />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold">
                        {connection.connector_name ?? "Conexão em andamento"}
                      </p>
                      <p className="mt-0.5 text-[11px] text-[#7c8b84]">
                        {connection.status === "HEALTHY"
                          ? "Conectada"
                          : connection.status === "SYNCING"
                            ? "Sincronizando"
                            : connection.status === "REVOKED"
                              ? "Revogada"
                              : connection.status === "RECONNECT_REQUIRED"
                                ? "Reconexão necessária"
                                : "Aguardando conclusão"}
                      </p>
                      {connection.last_synced_at ? (
                        <p className="mt-0.5 text-[10px] text-[#8b9892]">
                          Atualizado em {dateTimeLabel(connection.last_synced_at)} ·{" "}
                          {connection.sync_accounts_total} contas ·{" "}
                          {connection.sync_transactions_total} movimentações
                        </p>
                      ) : null}
                      {connection.error_code ? (
                        <p className="mt-0.5 text-[10px] text-[#a5514b]">
                          Falha segura: {connection.error_code}. Tentativas consecutivas:{" "}
                          {connection.consecutive_failures}.
                        </p>
                      ) : null}
                    </div>
                    {connection.status !== "REVOKED" ? (
                      <div className="flex flex-col items-end gap-1.5">
                        {connection.status !== "PENDING" ? (
                          <form action={syncBankConnectionAction}>
                            <input name="profile_id" type="hidden" value={profile} />
                            <input
                              name="connection_id"
                              type="hidden"
                              value={connection.id}
                            />
                            <button
                              className="text-[11px] font-semibold text-[#315d4f] disabled:opacity-50"
                              disabled={connection.status === "SYNCING"}
                              type="submit"
                            >
                              {connection.status === "SYNCING" ? "Em fila" : "Sincronizar"}
                            </button>
                          </form>
                        ) : null}
                        <form action={revokeBankConnectionAction}>
                          <input name="profile_id" type="hidden" value={profile} />
                          <input
                            name="connection_id"
                            type="hidden"
                            value={connection.id}
                          />
                          <button
                            className="text-[11px] font-semibold text-[#8b5a52]"
                            type="submit"
                          >
                            Revogar
                          </button>
                        </form>
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>
            ) : null}
          </Card>
        ) : null}

        {profile !== "all" ? (
          <section className="mt-5 grid gap-5 lg:grid-cols-[1.25fr_.75fr]">
            <Card className="overflow-hidden p-0">
              <div className="flex items-center justify-between border-b border-[#e1e8e2] p-5 sm:p-6">
                <div>
                  <p className="text-xs font-bold uppercase tracking-[.14em] text-[#79905d]">
                    Cartões e faturas
                  </p>
                  <h2 className="mt-2 text-xl font-semibold tracking-[-.03em]">
                    Compromissos sem dupla contagem
                  </h2>
                </div>
                <CreditCardIcon className="size-5 text-[#557268]" />
              </div>

              {creditCards.length ? (
                <div className="grid gap-3 border-b border-[#e8eee9] p-5 sm:grid-cols-2 sm:p-6">
                  {creditCards.map((card) => (
                    <div
                      className="rounded-2xl bg-[#173f35] p-5 text-white"
                      key={card.id}
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <p className="text-sm font-semibold">{card.name}</p>
                          <p className="mt-1 text-[11px] text-white/60">
                            {card.institution_name ?? "Cartão manual"}
                            {card.last_four ? ` · final ${card.last_four}` : ""}
                          </p>
                        </div>
                        <CreditCardIcon className="size-5 text-[#d9ff65]" />
                      </div>
                      <p className="mt-6 text-[11px] text-white/60">Faturas em aberto</p>
                      <p className="mt-1 text-xl font-semibold">{money(card.open_balance)}</p>
                      <div className="mt-4 flex justify-between text-[10px] text-white/55">
                        <span>Fecha dia {card.closing_day}</span>
                        <span>Vence dia {card.due_day}</span>
                        <span>Limite {money(card.credit_limit)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : null}

              {cardInvoices.length ? (
                <div className="divide-y divide-[#edf1ed]">
                  {cardInvoices.map((invoice) => (
                    <div className="p-5 sm:px-6" key={invoice.id}>
                      <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
                        <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-[#eef4e9] text-[#547164]">
                          <CalendarClock className="size-4" />
                        </span>
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-semibold">
                            {invoice.card_name} · {monthLabel(invoice.competence_month)}
                          </p>
                          <p className="mt-1 text-[11px] text-[#819088]">
                            Vence em {shortDate(invoice.due_on)}
                            {invoice.status === "PAID" ? " · Paga" : " · Em aberto"}
                          </p>
                        </div>
                        <p className="text-base font-semibold text-[#8d4a45]">
                          {money(invoice.total_amount)}
                        </p>
                        {invoice.status !== "PAID" && accounts.length ? (
                          <form
                            action={payCardInvoiceAction}
                            className="flex flex-col gap-2 sm:flex-row"
                          >
                            <input name="profile_id" type="hidden" value={profile} />
                            <input name="invoice_id" type="hidden" value={invoice.id} />
                            <input
                              name="paid_on"
                              type="hidden"
                              value={new Date().toISOString().slice(0, 10)}
                            />
                            <select
                              aria-label="Conta pagadora"
                              className="h-9 rounded-full border border-[#d6e0d8] bg-white px-3 text-xs"
                              name="account_id"
                            >
                              {accounts.map((account) => (
                                <option key={account.id} value={account.id}>
                                  {account.name}
                                </option>
                              ))}
                            </select>
                            <Button size="sm" type="submit" variant="outline">
                              Marcar paga
                            </Button>
                          </form>
                        ) : null}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-6 text-center text-xs leading-5 text-[#7c8b84]">
                  Cadastre um cartão e lance uma compra para criar a primeira fatura.
                </div>
              )}
            </Card>

            <Card className="h-fit p-6">
              <details open={!creditCards.length}>
                <summary className="cursor-pointer list-none">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs font-bold uppercase tracking-[.14em] text-[#79905d]">
                        Novo cartão
                      </p>
                      <h2 className="mt-2 text-xl font-semibold tracking-[-.03em]">
                        Adicione os dados da fatura
                      </h2>
                    </div>
                    <Plus className="size-5 text-[#557268]" />
                  </div>
                </summary>
                <form action={createCreditCardAction} className="mt-6 space-y-4">
                  <input name="profile_id" type="hidden" value={profile} />
                  <div>
                    <Label htmlFor="card_name">Nome do cartão</Label>
                    <Input
                      className="mt-1.5"
                      id="card_name"
                      name="name"
                      placeholder="Ex.: Nubank"
                      required
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <Label htmlFor="institution_name">Instituição</Label>
                      <Input
                        className="mt-1.5"
                        id="institution_name"
                        name="institution_name"
                        placeholder="Banco"
                      />
                    </div>
                    <div>
                      <Label htmlFor="last_four">Final</Label>
                      <Input
                        className="mt-1.5"
                        id="last_four"
                        inputMode="numeric"
                        maxLength={4}
                        name="last_four"
                        pattern="[0-9]{4}"
                        placeholder="1234"
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <Label htmlFor="closing_day">Fechamento</Label>
                      <Input
                        className="mt-1.5"
                        id="closing_day"
                        max={28}
                        min={1}
                        name="closing_day"
                        required
                        type="number"
                      />
                    </div>
                    <div>
                      <Label htmlFor="due_day">Vencimento</Label>
                      <Input
                        className="mt-1.5"
                        id="due_day"
                        max={28}
                        min={1}
                        name="due_day"
                        required
                        type="number"
                      />
                    </div>
                  </div>
                  <div>
                    <Label htmlFor="credit_limit">Limite</Label>
                    <Input
                      className="mt-1.5"
                      id="credit_limit"
                      inputMode="decimal"
                      name="credit_limit"
                      placeholder="0,00"
                      required
                    />
                  </div>
                  <Button className="w-full" type="submit" variant="outline">
                    Cadastrar cartão
                  </Button>
                </form>
              </details>
            </Card>
          </section>
        ) : null}
      </div>
    </main>
  );
}
