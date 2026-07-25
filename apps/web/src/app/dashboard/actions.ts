"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { serverApi } from "@/lib/server-api";

function dashboardUrl(profileId: string, key: "error" | "success", message: string) {
  const params = new URLSearchParams({ profile: profileId, [key]: message });
  return `/dashboard?${params.toString()}`;
}

function decimalValue(value: FormDataEntryValue | null) {
  const rawValue = String(value ?? "").trim();
  return rawValue.includes(",")
    ? rawValue.replace(/\./g, "").replace(",", ".")
    : rawValue;
}

export type AssistantActionState = {
  answer: string | null;
  error: string | null;
};

export async function askAssistantAction(
  _previousState: AssistantActionState,
  formData: FormData,
): Promise<AssistantActionState> {
  const profileId = String(formData.get("profile_id") ?? "");
  const message = String(formData.get("message") ?? "").trim();
  try {
    const response = await serverApi<{ answer: string }>(
      `/financial-profiles/${profileId}/assistant/messages`,
      {
        method: "POST",
        body: JSON.stringify({ message }),
      },
    );
    return { answer: response.answer, error: null };
  } catch (error) {
    return {
      answer: null,
      error:
        error instanceof Error
          ? error.message
          : "Não foi possível consultar o assistente agora.",
    };
  }
}

export async function saveGeminiCredentialAction(formData: FormData) {
  const profileId = String(formData.get("profile_id") ?? "");
  try {
    await serverApi("/assistant/settings", {
      method: "PUT",
      body: JSON.stringify({ api_key: String(formData.get("api_key") ?? "") }),
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Não foi possível salvar a chave.";
    redirect(dashboardUrl(profileId, "error", message));
  }
  redirect(
    dashboardUrl(
      profileId,
      "success",
      "Chave Gemini protegida e vinculada somente à sua conta.",
    ),
  );
}

export async function deleteGeminiCredentialAction(formData: FormData) {
  const profileId = String(formData.get("profile_id") ?? "");
  await serverApi("/assistant/settings", { method: "DELETE" });
  redirect(dashboardUrl(profileId, "success", "Chave Gemini removida."));
}

export async function createTransactionAction(formData: FormData) {
  const profileId = String(formData.get("profile_id") ?? "");
  const categoryId = String(formData.get("category_id") ?? "");
  const [instrumentType, instrumentId] = String(
    formData.get("instrument") ?? "",
  ).split(":", 2);
  try {
    await serverApi(`/financial-profiles/${profileId}/transactions`, {
      method: "POST",
      body: JSON.stringify({
        account_id: instrumentType === "account" ? instrumentId : null,
        credit_card_id: instrumentType === "card" ? instrumentId : null,
        category_id: categoryId || null,
        kind: String(formData.get("kind") ?? ""),
        description: String(formData.get("description") ?? ""),
        amount: decimalValue(formData.get("amount")),
        occurred_on: String(formData.get("occurred_on") ?? ""),
        status: "POSTED",
      }),
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Não foi possível salvar o lançamento.";
    redirect(dashboardUrl(profileId, "error", message));
  }
  redirect(dashboardUrl(profileId, "success", "Lançamento salvo."));
}

export async function createCreditCardAction(formData: FormData) {
  const profileId = String(formData.get("profile_id") ?? "");
  try {
    await serverApi(`/financial-profiles/${profileId}/credit-cards`, {
      method: "POST",
      body: JSON.stringify({
        name: String(formData.get("name") ?? ""),
        institution_name: String(formData.get("institution_name") ?? "") || null,
        last_four: String(formData.get("last_four") ?? "") || null,
        closing_day: Number(formData.get("closing_day")),
        due_day: Number(formData.get("due_day")),
        credit_limit: decimalValue(formData.get("credit_limit")),
      }),
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Não foi possível cadastrar o cartão.";
    redirect(dashboardUrl(profileId, "error", message));
  }
  redirect(dashboardUrl(profileId, "success", "Cartão cadastrado."));
}

export async function createCategoryRuleAction(formData: FormData) {
  const profileId = String(formData.get("profile_id") ?? "");
  try {
    await serverApi(`/financial-profiles/${profileId}/category-rules`, {
      method: "POST",
      body: JSON.stringify({
        match_text: String(formData.get("match_text") ?? ""),
        category_id: String(formData.get("category_id") ?? ""),
        priority: 100,
      }),
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Não foi possível criar a regra.";
    redirect(dashboardUrl(profileId, "error", message));
  }
  redirect(dashboardUrl(profileId, "success", "Regra de categorização criada."));
}

export async function archiveCategoryRuleAction(formData: FormData) {
  const profileId = String(formData.get("profile_id") ?? "");
  const ruleId = String(formData.get("rule_id") ?? "");
  try {
    await serverApi(`/category-rules/${ruleId}`, { method: "DELETE" });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Não foi possível remover a regra.";
    redirect(dashboardUrl(profileId, "error", message));
  }
  redirect(dashboardUrl(profileId, "success", "Regra removida."));
}

export async function revokeBankConnectionAction(formData: FormData) {
  const profileId = String(formData.get("profile_id") ?? "");
  const connectionId = String(formData.get("connection_id") ?? "");
  try {
    await serverApi(`/bank-connections/${connectionId}`, { method: "DELETE" });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Não foi possível revogar a conexão.";
    redirect(dashboardUrl(profileId, "error", message));
  }
  redirect(dashboardUrl(profileId, "success", "Consentimento bancário revogado."));
}

export async function syncBankConnectionAction(formData: FormData) {
  const profileId = String(formData.get("profile_id") ?? "");
  const connectionId = String(formData.get("connection_id") ?? "");
  try {
    await serverApi(`/bank-connections/${connectionId}/sync`, { method: "POST" });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Não foi possível iniciar a sincronização.";
    redirect(dashboardUrl(profileId, "error", message));
  }
  redirect(dashboardUrl(profileId, "success", "Sincronização enviada para processamento."));
}

export async function createBillAction(formData: FormData) {
  const profileId = String(formData.get("profile_id") ?? "");
  try {
    await serverApi(`/financial-profiles/${profileId}/bills`, {
      method: "POST",
      body: JSON.stringify({
        description: String(formData.get("description") ?? ""),
        amount: decimalValue(formData.get("amount")),
        due_on: String(formData.get("due_on") ?? ""),
      }),
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Não foi possível criar a conta a pagar.";
    redirect(dashboardUrl(profileId, "error", message));
  }
  redirect(dashboardUrl(profileId, "success", "Conta adicionada à Central de Contas."));
}

export async function transitionBillAction(formData: FormData) {
  const profileId = String(formData.get("profile_id") ?? "");
  const billId = String(formData.get("bill_id") ?? "");
  const targetStatus = String(formData.get("target_status") ?? "");
  try {
    await serverApi(`/bills/${billId}/transition`, {
      method: "POST",
      body: JSON.stringify({
        target_status: targetStatus,
        version: Number(formData.get("version")),
        ...(targetStatus === "PAID"
          ? { paid_on: String(formData.get("paid_on") ?? "") }
          : {}),
      }),
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Não foi possível atualizar a conta.";
    redirect(dashboardUrl(profileId, "error", message));
  }
  redirect(dashboardUrl(profileId, "success", "Estado da conta atualizado."));
}

export async function saveMonthlyPlanAction(formData: FormData) {
  const profileId = String(formData.get("profile_id") ?? "");
  try {
    await serverApi(`/financial-profiles/${profileId}/monthly-plan`, {
      method: "PUT",
      body: JSON.stringify({
        competence_month: String(formData.get("competence_month") ?? ""),
        expected_income: decimalValue(formData.get("expected_income")),
        essential_commitment: decimalValue(formData.get("essential_commitment")),
        debt_commitment: decimalValue(formData.get("debt_commitment")),
        goal_contribution: decimalValue(formData.get("goal_contribution")),
      }),
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Não foi possível salvar o planejamento.";
    redirect(dashboardUrl(profileId, "error", message));
  }
  redirect(dashboardUrl(profileId, "success", "Planejamento mensal atualizado."));
}

export async function createGoalAction(formData: FormData) {
  const profileId = String(formData.get("profile_id") ?? "");
  try {
    await serverApi(`/financial-profiles/${profileId}/goals`, {
      method: "POST",
      body: JSON.stringify({
        name: String(formData.get("name") ?? ""),
        target_amount: decimalValue(formData.get("target_amount")),
        current_amount: decimalValue(formData.get("current_amount")),
        target_date: String(formData.get("target_date") ?? ""),
        monthly_contribution: decimalValue(formData.get("monthly_contribution")),
      }),
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Não foi possível criar a meta.";
    redirect(dashboardUrl(profileId, "error", message));
  }
  redirect(dashboardUrl(profileId, "success", "Meta criada com premissas explícitas."));
}

export async function createDebtAction(formData: FormData) {
  const profileId = String(formData.get("profile_id") ?? "");
  const interest = decimalValue(formData.get("annual_interest_rate"));
  const cet = decimalValue(formData.get("annual_cet_rate"));
  const payment = decimalValue(formData.get("monthly_payment"));
  try {
    await serverApi(`/financial-profiles/${profileId}/debts`, {
      method: "POST",
      body: JSON.stringify({
        name: String(formData.get("name") ?? ""),
        original_principal: decimalValue(formData.get("original_principal")),
        outstanding_balance: decimalValue(formData.get("outstanding_balance")),
        annual_interest_rate: interest || null,
        annual_cet_rate: cet || null,
        amortization_system: String(formData.get("amortization_system") ?? "UNKNOWN"),
        installments_remaining: Number(formData.get("installments_remaining")),
        monthly_payment: payment || null,
        next_due_on: String(formData.get("next_due_on") ?? "") || null,
      }),
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Não foi possível cadastrar a dívida.";
    redirect(dashboardUrl(profileId, "error", message));
  }
  redirect(dashboardUrl(profileId, "success", "Dívida cadastrada com qualidade dos dados."));
}

export async function createReceivableAction(formData: FormData) {
  const profileId = String(formData.get("profile_id") ?? "");
  try {
    await serverApi(`/financial-profiles/${profileId}/receivables`, {
      method: "POST",
      body: JSON.stringify({
        description: String(formData.get("description") ?? ""),
        counterparty: String(formData.get("counterparty") ?? "") || null,
        amount: decimalValue(formData.get("amount")),
        due_on: String(formData.get("due_on") ?? ""),
        confirmed: true,
      }),
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Não foi possível cadastrar o recebível.";
    redirect(dashboardUrl(profileId, "error", message));
  }
  redirect(dashboardUrl(profileId, "success", "Recebível confirmado no calendário PJ."));
}

export async function createSubscriptionAction(formData: FormData) {
  const profileId = String(formData.get("profile_id") ?? "");
  try {
    await serverApi(`/financial-profiles/${profileId}/subscriptions`, {
      method: "POST",
      body: JSON.stringify({
        name: String(formData.get("name") ?? ""),
        amount: decimalValue(formData.get("amount")),
        cadence_months: Number(formData.get("cadence_months")),
        next_charge_on: String(formData.get("next_charge_on") ?? ""),
      }),
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Não foi possível criar a assinatura.";
    redirect(dashboardUrl(profileId, "error", message));
  }
  redirect(
    dashboardUrl(profileId, "success", "Assinatura criada como candidata para confirmação."),
  );
}

export async function simulatePaymentAction(formData: FormData) {
  const profileId = String(formData.get("profile_id") ?? "");
  const billIds = formData.getAll("bill_ids").map(String);
  try {
    const simulation = await serverApi<{
      id: string;
      total_amount: string;
      expires_at: string;
      external_operations_count: number;
      account_options: {
        account_name: string;
        balance_after: string;
        free_balance_after: string;
        risk: string;
      }[];
    }>(`/financial-profiles/${profileId}/payment-simulations`, {
      method: "POST",
      body: JSON.stringify({
        bill_ids: billIds,
        idempotency_key: crypto.randomUUID(),
      }),
    });
    const best = simulation.account_options[0];
    const params = new URLSearchParams({
      profile: profileId,
      simulation: simulation.id,
      payment_total: simulation.total_amount,
      payment_expires: simulation.expires_at,
      payment_operations: String(simulation.external_operations_count),
      payment_account: best?.account_name ?? "Sem conta elegível",
      payment_balance_after: best?.balance_after ?? "0",
      payment_free_after: best?.free_balance_after ?? "0",
      payment_risk: best?.risk ?? "UNAVAILABLE",
    });
    redirect(`/dashboard?${params.toString()}`);
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Não foi possível simular os pagamentos.";
    redirect(dashboardUrl(profileId, "error", message));
  }
}

export async function splitTransactionAction(formData: FormData) {
  const profileId = String(formData.get("profile_id") ?? "");
  const transactionId = String(formData.get("transaction_id") ?? "");
  try {
    await serverApi(`/transactions/${transactionId}/splits`, {
      method: "PUT",
      body: JSON.stringify({
        version: Number(formData.get("version")),
        items: [
          {
            category_id: String(formData.get("category_id_1") ?? ""),
            amount: decimalValue(formData.get("amount_1")),
            description: String(formData.get("description_1") ?? "") || null,
          },
          {
            category_id: String(formData.get("category_id_2") ?? ""),
            amount: decimalValue(formData.get("amount_2")),
            description: String(formData.get("description_2") ?? "") || null,
          },
        ],
      }),
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Não foi possível dividir o lançamento.";
    redirect(dashboardUrl(profileId, "error", message));
  }
  redirect(
    dashboardUrl(
      profileId,
      "success",
      "Divisão salva; o total do lançamento permanece inalterado.",
    ),
  );
}

export async function createTransferAction(formData: FormData) {
  const profileId = String(formData.get("profile_id") ?? "");
  try {
    await serverApi(`/financial-profiles/${profileId}/transfers`, {
      method: "POST",
      body: JSON.stringify({
        source_account_id: String(formData.get("source_account_id") ?? ""),
        destination_account_id: String(formData.get("destination_account_id") ?? ""),
        description: String(formData.get("description") ?? ""),
        amount: decimalValue(formData.get("amount")),
        occurred_on: String(formData.get("occurred_on") ?? ""),
        idempotency_key: String(formData.get("idempotency_key") ?? ""),
      }),
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Não foi possível registrar a transferência.";
    redirect(dashboardUrl(profileId, "error", message));
  }
  redirect(
    dashboardUrl(
      profileId,
      "success",
      "Transferência conciliada nas duas contas e excluída dos totais.",
    ),
  );
}

export async function refundTransactionAction(formData: FormData) {
  const profileId = String(formData.get("profile_id") ?? "");
  const transactionId = String(formData.get("transaction_id") ?? "");
  try {
    await serverApi(`/transactions/${transactionId}/refund`, {
      method: "POST",
      body: JSON.stringify({
        occurred_on: String(formData.get("occurred_on") ?? ""),
      }),
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Não foi possível registrar o estorno.";
    redirect(dashboardUrl(profileId, "error", message));
  }
  redirect(
    dashboardUrl(
      profileId,
      "success",
      "Estorno vinculado à movimentação original e compensado nos totais.",
    ),
  );
}

export async function payCardInvoiceAction(formData: FormData) {
  const profileId = String(formData.get("profile_id") ?? "");
  const invoiceId = String(formData.get("invoice_id") ?? "");
  try {
    await serverApi(`/card-invoices/${invoiceId}/pay`, {
      method: "POST",
      body: JSON.stringify({
        account_id: String(formData.get("account_id") ?? ""),
        paid_on: String(formData.get("paid_on") ?? ""),
      }),
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Não foi possível registrar o pagamento.";
    redirect(dashboardUrl(profileId, "error", message));
  }
  redirect(
    dashboardUrl(
      profileId,
      "success",
      "Fatura paga como transferência, sem duplicar a despesa.",
    ),
  );
}

export async function logoutAction() {
  try {
    await serverApi("/auth/logout", { method: "POST" });
  } finally {
    const cookieStore = await cookies();
    cookieStore.delete("rayo_session");
    cookieStore.delete("rayo_csrf");
  }
  redirect("/entrar");
}
