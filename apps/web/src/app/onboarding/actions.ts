"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { ApiError, serverApi } from "@/lib/server-api";

function onboardingError(error: unknown) {
  if (error instanceof ApiError) {
    if (error.status === 409) return "incomplete";
    if (error.status === 403) return "security";
  }
  return "unexpected";
}

function normalizeMoney(value: string) {
  const normalized = value.trim().replace(/\./g, "").replace(",", ".");
  return normalized || "0";
}

export async function createProfileAction(formData: FormData) {
  try {
    await serverApi("/financial-profiles", {
      method: "POST",
      body: JSON.stringify({
        type: formData.get("type"),
        name: formData.get("name"),
        document_last4: formData.get("document_last4") || null,
      }),
    });
  } catch (error) {
    redirect(`/onboarding?error=${onboardingError(error)}`);
  }
  revalidatePath("/onboarding");
}

export async function createAccountAction(formData: FormData) {
  const profileId = String(formData.get("profile_id"));
  try {
    await serverApi(`/financial-profiles/${profileId}/accounts`, {
      method: "POST",
      body: JSON.stringify({
        name: formData.get("name"),
        institution_name: formData.get("institution_name") || null,
        type: formData.get("account_type"),
        current_balance: normalizeMoney(String(formData.get("current_balance"))),
      }),
    });
  } catch (error) {
    redirect(`/onboarding?error=${onboardingError(error)}`);
  }
  revalidatePath("/onboarding");
}

export async function acceptPrivacyAction() {
  try {
    await serverApi("/onboarding/privacy-consent", { method: "POST" });
  } catch (error) {
    redirect(`/onboarding?error=${onboardingError(error)}`);
  }
  revalidatePath("/onboarding");
}

export async function completeOnboardingAction() {
  try {
    await serverApi("/onboarding/complete", { method: "POST" });
  } catch (error) {
    redirect(`/onboarding?error=${onboardingError(error)}`);
  }
  redirect("/dashboard");
}
