"use client";

import { useActionState } from "react";

import {
  confirmGoalSimulationAction,
  type GoalSimulationState,
  simulateGoalAction,
  updateGoalAction,
} from "@/app/dashboard/actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type Goal = {
  id: string;
  name: string;
  target_amount: string;
  current_amount: string;
  target_date: string;
  monthly_contribution: string;
  priority: number;
  version: number;
};

const initialState: GoalSimulationState = {
  scenarios: [],
  pendingActionId: null,
  error: null,
};

const money = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
});

export function GoalManager({
  goal,
  profileId,
}: {
  goal: Goal;
  profileId: string;
}) {
  const [simulation, simulateAction, isSimulating] = useActionState(
    simulateGoalAction,
    initialState,
  );

  return (
    <details className="mt-3 border-t border-[#dfe7df] pt-2">
      <summary className="cursor-pointer text-[11px] font-semibold text-[#315d4f]">
        Editar e simular
      </summary>

      <div className="mt-3 grid gap-4">
        <form action={updateGoalAction} className="grid gap-2">
          <p className="text-[10px] font-bold uppercase tracking-[.12em] text-[#79905d]">
            Editar meta
          </p>
          <input name="profile_id" type="hidden" value={profileId} />
          <input name="goal_id" type="hidden" value={goal.id} />
          <input name="version" type="hidden" value={goal.version} />
          <Input defaultValue={goal.name} name="name" required />
          <div className="grid grid-cols-2 gap-2">
            <Input
              defaultValue={goal.target_amount}
              inputMode="decimal"
              name="target_amount"
              placeholder="Valor da meta"
              required
            />
            <Input
              defaultValue={goal.current_amount}
              inputMode="decimal"
              name="current_amount"
              placeholder="Valor acumulado"
              required
            />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <Input defaultValue={goal.target_date} name="target_date" required type="date" />
            <Input
              defaultValue={goal.monthly_contribution}
              inputMode="decimal"
              name="monthly_contribution"
              placeholder="Aporte mensal"
              required
            />
          </div>
          <label className="text-[11px] font-semibold text-[#617169]">
            Prioridade
            <Input
              className="mt-1"
              defaultValue={goal.priority}
              max={1000}
              min={1}
              name="priority"
              type="number"
            />
          </label>
          <Button size="sm" type="submit" variant="outline">
            Salvar alterações
          </Button>
        </form>

        <form action={simulateAction} className="grid gap-2 border-t border-[#dfe7df] pt-3">
          <p className="text-[10px] font-bold uppercase tracking-[.12em] text-[#79905d]">
            Simular planejamento
          </p>
          <input name="goal_id" type="hidden" value={goal.id} />
          <p className="text-[11px] leading-4 text-[#71817a]">
            Informe um aporte e uma data. A simulação não altera a meta até você confirmar.
          </p>
          <div className="grid grid-cols-2 gap-2">
            <Input
              defaultValue={goal.monthly_contribution}
              inputMode="decimal"
              name="monthly_contribution"
              placeholder="Novo aporte"
              required
            />
            <Input defaultValue={goal.target_date} name="target_date" required type="date" />
          </div>
          <Button disabled={isSimulating} size="sm" type="submit">
            {isSimulating ? "Calculando…" : "Comparar cenários"}
          </Button>
        </form>

        {simulation.error ? (
          <p className="rounded-xl bg-[#fff3f0] p-3 text-xs text-[#a33f31]">
            {simulation.error}
          </p>
        ) : null}

        {simulation.scenarios.length ? (
          <div className="grid gap-2">
            {simulation.scenarios.map((scenario) => (
              <div className="rounded-xl border border-[#dfe7df] bg-white p-3" key={scenario.name}>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-semibold">{scenario.name}</span>
                  <span
                    className={`text-[10px] font-bold ${
                      scenario.reaches_target ? "text-[#397255]" : "text-[#a06a33]"
                    }`}
                  >
                    {scenario.reaches_target ? "Alcança a meta" : "Abaixo da meta"}
                  </span>
                </div>
                <p className="mt-1 text-[11px] leading-4 text-[#71817a]">
                  {money.format(Number(scenario.monthly_contribution))}/mês · projeção{" "}
                  {money.format(Number(scenario.projected_amount_at_target))}
                  {scenario.months_to_target === null
                    ? " · sem prazo estimado"
                    : ` · ${scenario.months_to_target} meses`}
                </p>
              </div>
            ))}
            {simulation.pendingActionId ? (
              <form action={confirmGoalSimulationAction}>
                <input name="profile_id" type="hidden" value={profileId} />
                <input name="action_id" type="hidden" value={simulation.pendingActionId} />
                <Button className="w-full" size="sm" type="submit">
                  Aplicar cenário equilibrado
                </Button>
              </form>
            ) : null}
          </div>
        ) : null}
      </div>
    </details>
  );
}
