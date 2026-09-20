# Copyright (c) Streamlit Inc. (2018-2022) Snowflake Inc. (2022)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import altair as alt
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Ruhestandsrechner", page_icon="🧓")


def fmt_eur(value: float) -> str:
    return f"{value:,.0f} €".replace(",", ".")


def simulate(
    current_age: int,
    retirement_age: int,
    current_capital: float,
    monthly_savings: float,
    annual_return_savings: float,
    annual_return_withdrawal: float,
    annual_inflation: float,
    monthly_withdrawal_today: float,
    withdrawal_years: int,
    keep_saving_in_retirement: bool,
    extra_monthly_saving: float,
):
    months_accum = max(0, round((retirement_age - current_age) * 12))
    months_decum = max(0, round(withdrawal_years * 12))

    r1 = (1 + annual_return_savings) ** (1 / 12) - 1
    r2 = (1 + annual_return_withdrawal) ** (1 / 12) - 1

    capital = current_capital
    history = [(0, capital)]

    for _ in range(months_accum):
        capital = capital * (1 + r1) + monthly_savings
        history.append((history[-1][0] + 1, capital))

    capital_at_retirement = capital
    depletion_month = None

    for m in range(months_decum):
        month_index = months_accum + m
        if keep_saving_in_retirement:
            cashflow = extra_monthly_saving
        else:
            withdrawal_nominal = monthly_withdrawal_today * (1 + annual_inflation) ** (
                month_index / 12
            )
            cashflow = -withdrawal_nominal
            if capital >= 0 and (capital * (1 + r2) + cashflow) < 0 and depletion_month is None:
                depletion_month = month_index + 1

        capital = capital * (1 + r2) + cashflow
        history.append((history[-1][0] + 1, capital))

    final_capital_nominal = capital
    total_months = months_accum + months_decum
    total_years = total_months / 12
    deflator_end = (1 + annual_inflation) ** total_years
    deflator_retirement = (1 + annual_inflation) ** (months_accum / 12)

    return {
        "history": history,
        "months_accum": months_accum,
        "capital_at_retirement_nominal": capital_at_retirement,
        "capital_at_retirement_real": capital_at_retirement / deflator_retirement,
        "final_capital_nominal": final_capital_nominal,
        "final_capital_real": final_capital_nominal / deflator_end if deflator_end else final_capital_nominal,
        "annual_inflation": annual_inflation,
        "depletion_age": current_age + depletion_month / 12 if depletion_month else None,
    }


st.markdown("# 🧓 Ruhestandsrechner")
st.write(
    "Finde heraus, ob dein aktuelles Vermögen und dein Sparplan ausreichen, um "
    "deinen gewünschten Lebensstandard im Ruhestand zu finanzieren. Alle "
    "Endergebnisse werden **inflationsbereinigt in heutiger Kaufkraft** "
    "ausgewiesen, damit sie sich intuitiv einordnen lassen."
)

st.header("1. Alter")
col1, col2 = st.columns(2)
with col1:
    current_age = st.number_input(
        "Aktuelles Alter", min_value=0, max_value=100, value=35, step=1
    )
with col2:
    retirement_age = st.number_input(
        "Alter bei Renteneintritt (Beginn der Entnahmephase)",
        min_value=int(current_age) + 1,
        max_value=100,
        value=max(int(current_age) + 1, 67),
        step=1,
    )

st.header("2. Ansparphase")
col1, col2 = st.columns(2)
with col1:
    current_capital = st.number_input(
        "Aktuell vorhandenes Vermögen (€)", min_value=0.0, value=20000.0, step=1000.0
    )
    monthly_savings = st.number_input(
        "Monatliche Sparrate im Sparplan (€)", min_value=0.0, value=400.0, step=50.0
    )
with col2:
    annual_return_savings_pct = st.number_input(
        "Erwartete jährliche Verzinsung in der Ansparphase (%)",
        min_value=-10.0,
        max_value=20.0,
        value=6.0,
        step=0.5,
    )
    annual_inflation_pct = st.number_input(
        "Erwartete jährliche Inflation (%)",
        min_value=0.0,
        max_value=15.0,
        value=2.0,
        step=0.1,
    )

st.header("3. Entnahmephase")
phase_mode = st.radio(
    "Was möchtest du während der Ruhestandsphase tun?",
    ["Geld entnehmen (Entsparphase)", "Weiter ansparen (noch nicht entnehmen)"],
    index=0,
)
keep_saving_in_retirement = phase_mode == "Weiter ansparen (noch nicht entnehmen)"

col1, col2 = st.columns(2)
with col1:
    if keep_saving_in_retirement:
        extra_monthly_saving = st.number_input(
            "Zusätzliche monatliche Sparrate während dieser Phase (€)",
            min_value=0.0,
            value=200.0,
            step=50.0,
        )
        monthly_withdrawal_today = 0.0
    else:
        monthly_withdrawal_today = st.number_input(
            "Gewünschte monatliche Entnahme in heutiger Kaufkraft (€)",
            min_value=0.0,
            value=2000.0,
            step=100.0,
        )
        extra_monthly_saving = 0.0
    withdrawal_years = st.number_input(
        "Geplante Dauer dieser Phase (Jahre)", min_value=1, max_value=60, value=25, step=1
    )
with col2:
    annual_return_withdrawal_pct = st.number_input(
        "Erwartete jährliche Verzinsung in dieser Phase (%)",
        min_value=-10.0,
        max_value=20.0,
        value=annual_return_savings_pct,
        step=0.5,
    )
    target_leftover_today = st.number_input(
        "Gewünschtes Restvermögen am Ende, in heutiger Kaufkraft "
        "(z. B. zum Vererben) (€)",
        min_value=0.0,
        value=0.0,
        step=1000.0,
    )

result = simulate(
    current_age=int(current_age),
    retirement_age=int(retirement_age),
    current_capital=current_capital,
    monthly_savings=monthly_savings,
    annual_return_savings=annual_return_savings_pct / 100,
    annual_return_withdrawal=annual_return_withdrawal_pct / 100,
    annual_inflation=annual_inflation_pct / 100,
    monthly_withdrawal_today=monthly_withdrawal_today,
    withdrawal_years=int(withdrawal_years),
    keep_saving_in_retirement=keep_saving_in_retirement,
    extra_monthly_saving=extra_monthly_saving,
)

st.header("4. Ergebnis")

col1, col2 = st.columns(2)
col1.metric(
    "Vermögen bei Renteneintritt (heutige Kaufkraft)",
    fmt_eur(result["capital_at_retirement_real"]),
)
col2.metric(
    "Vermögen am Ende der Entnahmephase (heutige Kaufkraft)",
    fmt_eur(result["final_capital_real"]),
)

surplus = result["final_capital_real"] - target_leftover_today
if surplus >= 0:
    st.success(
        f"✅ Dein Geld reicht voraussichtlich aus. Am Ende bleiben "
        f"{fmt_eur(surplus)} mehr übrig als dein gewünschtes Restvermögen "
        f"von {fmt_eur(target_leftover_today)}."
    )
else:
    st.error(
        f"❌ Dein Geld reicht voraussichtlich nicht aus. Es fehlen "
        f"{fmt_eur(-surplus)}, um dein gewünschtes Restvermögen von "
        f"{fmt_eur(target_leftover_today)} zu erreichen."
    )

if result["depletion_age"] is not None:
    st.warning(
        f"⚠️ Bei diesen Annahmen wäre dein Vermögen bereits mit rund "
        f"{result['depletion_age']:.1f} Jahren aufgebraucht."
    )

st.subheader("Vermögensverlauf")

ages = [current_age + m / 12 for m, _ in result["history"]]
nominal = [c for _, c in result["history"]]
real = [
    c / (1 + result["annual_inflation"]) ** (m / 12)
    for m, c in result["history"]
]

df = pd.DataFrame(
    {
        "Alter": ages,
        "Vermögen (nominal)": nominal,
        "Vermögen (heutige Kaufkraft)": real,
    }
)
df_long = df.melt(id_vars="Alter", var_name="Serie", value_name="Vermögen (€)")

line = (
    alt.Chart(df_long)
    .mark_line()
    .encode(
        x=alt.X("Alter", title="Alter"),
        y=alt.Y("Vermögen (€)", title="Vermögen (€)"),
        color="Serie",
    )
)
rule = (
    alt.Chart(pd.DataFrame({"Alter": [retirement_age]}))
    .mark_rule(strokeDash=[4, 4], color="gray")
    .encode(x="Alter")
)

st.altair_chart((line + rule).interactive(), use_container_width=True)
st.caption(
    "Die gestrichelte Linie markiert den Beginn der Entnahmephase "
    "(Renteneintritt)."
)

with st.expander("Annahmen & Berechnungsweise"):
    st.markdown(
        """
        - Zinsen werden monatlich verzinst (aus der jährlichen Verzinsung
          abgeleitet).
        - Während der Ansparphase wächst dein Vermögen durch die monatliche
          Sparrate und die angegebene Verzinsung.
        - Die monatliche Entnahme wird über die Entnahmephase hinweg mit der
          Inflation erhöht, damit die **reale Kaufkraft** der Entnahme
          konstant bleibt.
        - Alle Endergebnisse werden mit der Inflation auf heutige Kaufkraft
          abgezinst, damit sie direkt mit deinen heutigen Wunschbeträgen
          vergleichbar sind.
        - Dies ist eine vereinfachte Modellrechnung ohne Steuern, Gebühren
          oder Marktschwankungen und ersetzt keine individuelle
          Finanzberatung.
        """
    )
