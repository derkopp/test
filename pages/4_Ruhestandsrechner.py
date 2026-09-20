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
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Ruhestandsrechner", page_icon="🧓")


def fmt_eur(value: float) -> str:
    return f"{value:,.0f} €".replace(",", ".")


def fmt_pct(value: float) -> str:
    return f"{value * 100:,.1f} %".replace(",", ".")


def annual_to_monthly_rate(annual_rate):
    """Convert one or many annual rates to the equivalent monthly rate.

    Clipped at -99.9% so a very bad random draw doesn't take the base of
    the fractional power to zero or negative.
    """
    base = np.clip(1 + annual_rate, 0.001, None)
    return base ** (1 / 12) - 1


def simulate_deterministic(
    current_age: int,
    retirement_age: int,
    current_capital: float,
    monthly_savings: float,
    savings_growth: float,
    annual_return_savings: float,
    annual_return_withdrawal: float,
    annual_inflation: float,
    monthly_withdrawal_today: float,
    withdrawal_years: int,
    keep_saving_in_retirement: bool,
    extra_monthly_saving: float,
):
    """Single expected-value path with fixed, non-random assumptions."""
    months_accum = max(0, round((retirement_age - current_age) * 12))
    months_decum = max(0, round(withdrawal_years * 12))

    r1 = (1 + annual_return_savings) ** (1 / 12) - 1
    r2 = (1 + annual_return_withdrawal) ** (1 / 12) - 1

    capital = current_capital
    history = [(0, capital)]

    for m in range(months_accum):
        year_index = m // 12
        savings_this_month = monthly_savings * (1 + savings_growth) ** year_index
        capital = capital * (1 + r1) + savings_this_month
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


def simulate_monte_carlo(
    n_sims: int,
    seed: int,
    current_age: int,
    retirement_age: int,
    current_capital: float,
    monthly_savings: float,
    savings_growth: float,
    mean_return_savings: float,
    vol_return_savings: float,
    mean_return_withdrawal: float,
    vol_return_withdrawal: float,
    mean_inflation: float,
    vol_inflation: float,
    monthly_withdrawal_today: float,
    withdrawal_years: int,
    keep_saving_in_retirement: bool,
    extra_monthly_saving: float,
    target_leftover_today: float,
):
    """Vectorised Monte-Carlo simulation across `n_sims` random paths.

    A new annual return and a new annual inflation rate are drawn per
    simulated year (not per month) so a single bad/good year affects all
    twelve months the same way, in line with how sequence-of-returns risk
    is usually modelled.
    """
    rng = np.random.default_rng(seed if seed else None)

    months_accum = max(0, round((retirement_age - current_age) * 12))
    months_decum = max(0, round(withdrawal_years * 12))
    total_months = months_accum + months_decum

    capital = np.full(n_sims, current_capital, dtype=float)
    inflation_index = np.ones(n_sims, dtype=float)

    real_history = np.zeros((n_sims, total_months + 1))
    real_history[:, 0] = capital / inflation_index

    monthly_r = monthly_infl = None
    year_index = 0
    for m in range(months_accum):
        if m % 12 == 0:
            annual_r = rng.normal(mean_return_savings, vol_return_savings, n_sims)
            monthly_r = annual_to_monthly_rate(annual_r)
            annual_infl = np.clip(
                rng.normal(mean_inflation, vol_inflation, n_sims), -0.5, None
            )
            monthly_infl = annual_to_monthly_rate(annual_infl)
            savings_this_year = monthly_savings * (1 + savings_growth) ** year_index
            year_index += 1
        capital = capital * (1 + monthly_r) + savings_this_year
        inflation_index = inflation_index * (1 + monthly_infl)
        real_history[:, m + 1] = capital / inflation_index

    depleted = np.zeros(n_sims, dtype=bool)
    monthly_r2 = monthly_infl2 = None
    for m in range(months_decum):
        if m % 12 == 0:
            annual_r2 = rng.normal(mean_return_withdrawal, vol_return_withdrawal, n_sims)
            monthly_r2 = annual_to_monthly_rate(annual_r2)
            annual_infl2 = np.clip(
                rng.normal(mean_inflation, vol_inflation, n_sims), -0.5, None
            )
            monthly_infl2 = annual_to_monthly_rate(annual_infl2)

        if keep_saving_in_retirement:
            cashflow = np.full(n_sims, extra_monthly_saving)
        else:
            cashflow = -(monthly_withdrawal_today * inflation_index)

        capital = capital * (1 + monthly_r2) + cashflow
        inflation_index = inflation_index * (1 + monthly_infl2)
        depleted = depleted | (capital < 0)
        real_history[:, months_accum + m + 1] = capital / inflation_index

    final_capital_real = capital / inflation_index
    success = (~depleted) & (final_capital_real >= target_leftover_today)

    return {
        "real_history": real_history,
        "final_capital_real": final_capital_real,
        "success_prob": float(success.mean()),
        "depleted_prob": float(depleted.mean()),
        "months_accum": months_accum,
        "total_months": total_months,
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
        "Monatliche Sparrate im Sparplan, heute (€)",
        min_value=0.0,
        value=400.0,
        step=50.0,
    )
    savings_growth_pct = st.number_input(
        "Jährliche Steigerung der Sparrate (%)",
        min_value=-10.0,
        max_value=20.0,
        value=0.0,
        step=0.5,
        help="Z. B. durch Gehaltssteigerungen: Die Sparrate wird jedes Jahr "
        "um diesen Prozentsatz erhöht.",
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

st.header("4. Unsicherheit (Monte-Carlo-Simulation)")
run_monte_carlo = st.checkbox(
    "Schwankende Rendite & Inflation simulieren, um eine "
    "Erfolgswahrscheinlichkeit zu berechnen",
    value=False,
)

if run_monte_carlo:
    col1, col2, col3 = st.columns(3)
    with col1:
        vol_savings_pct = st.number_input(
            "Volatilität der Verzinsung – Ansparphase "
            "(Std.-Abw., % p.a.)",
            min_value=0.0,
            max_value=40.0,
            value=15.0,
            step=1.0,
        )
    with col2:
        vol_withdrawal_pct = st.number_input(
            "Volatilität der Verzinsung – Entnahmephase "
            "(Std.-Abw., % p.a.)",
            min_value=0.0,
            max_value=40.0,
            value=8.0,
            step=1.0,
        )
    with col3:
        vol_inflation_pct = st.number_input(
            "Volatilität der Inflation (Std.-Abw., % p.a.)",
            min_value=0.0,
            max_value=10.0,
            value=1.0,
            step=0.5,
        )

    col1, col2 = st.columns(2)
    with col1:
        n_sims = st.slider(
            "Anzahl Simulationen", min_value=200, max_value=5000, value=1000, step=200
        )
    with col2:
        seed = st.number_input(
            "Zufalls-Seed (0 = jedes Mal neu zufällig)",
            min_value=0,
            max_value=1_000_000,
            value=0,
            step=1,
        )

result = simulate_deterministic(
    current_age=int(current_age),
    retirement_age=int(retirement_age),
    current_capital=current_capital,
    monthly_savings=monthly_savings,
    savings_growth=savings_growth_pct / 100,
    annual_return_savings=annual_return_savings_pct / 100,
    annual_return_withdrawal=annual_return_withdrawal_pct / 100,
    annual_inflation=annual_inflation_pct / 100,
    monthly_withdrawal_today=monthly_withdrawal_today,
    withdrawal_years=int(withdrawal_years),
    keep_saving_in_retirement=keep_saving_in_retirement,
    extra_monthly_saving=extra_monthly_saving,
)

st.header("5. Ergebnis")
st.subheader("Erwartungswert-Szenario")

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
        f"✅ Im Erwartungswert-Szenario reicht dein Geld aus. Am Ende bleiben "
        f"{fmt_eur(surplus)} mehr übrig als dein gewünschtes Restvermögen "
        f"von {fmt_eur(target_leftover_today)}."
    )
else:
    st.error(
        f"❌ Im Erwartungswert-Szenario reicht dein Geld nicht aus. Es fehlen "
        f"{fmt_eur(-surplus)}, um dein gewünschtes Restvermögen von "
        f"{fmt_eur(target_leftover_today)} zu erreichen."
    )

if result["depletion_age"] is not None:
    st.warning(
        f"⚠️ Bei diesen Annahmen wäre dein Vermögen bereits mit rund "
        f"{result['depletion_age']:.1f} Jahren aufgebraucht."
    )

mc_result = None
if run_monte_carlo:
    mc_result = simulate_monte_carlo(
        n_sims=int(n_sims),
        seed=int(seed),
        current_age=int(current_age),
        retirement_age=int(retirement_age),
        current_capital=current_capital,
        monthly_savings=monthly_savings,
        savings_growth=savings_growth_pct / 100,
        mean_return_savings=annual_return_savings_pct / 100,
        vol_return_savings=vol_savings_pct / 100,
        mean_return_withdrawal=annual_return_withdrawal_pct / 100,
        vol_return_withdrawal=vol_withdrawal_pct / 100,
        mean_inflation=annual_inflation_pct / 100,
        vol_inflation=vol_inflation_pct / 100,
        monthly_withdrawal_today=monthly_withdrawal_today,
        withdrawal_years=int(withdrawal_years),
        keep_saving_in_retirement=keep_saving_in_retirement,
        extra_monthly_saving=extra_monthly_saving,
        target_leftover_today=target_leftover_today,
    )

    st.subheader("Monte-Carlo-Simulation")
    st.caption(
        f"Basiert auf {n_sims:,}".replace(",", ".")
        + " zufälligen Verläufen mit schwankender Rendite und Inflation "
        "um die oben angegebenen Erwartungswerte."
    )

    success_pct = mc_result["success_prob"]
    col1, col2 = st.columns(2)
    col1.metric("Erfolgswahrscheinlichkeit", fmt_pct(success_pct))
    col2.metric(
        "Wahrscheinlichkeit, dass das Geld vorzeitig ausgeht",
        fmt_pct(mc_result["depleted_prob"]),
    )

    if success_pct >= 0.8:
        st.success(
            f"✅ In {fmt_pct(success_pct)} der simulierten Verläufe reicht "
            "dein Geld für dein gewünschtes Restvermögen aus."
        )
    elif success_pct >= 0.5:
        st.warning(
            f"⚠️ Nur in {fmt_pct(success_pct)} der simulierten Verläufe "
            "reicht dein Geld aus – ein spürbares Risiko bleibt."
        )
    else:
        st.error(
            f"❌ Nur in {fmt_pct(success_pct)} der simulierten Verläufe "
            "reicht dein Geld aus."
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
    "(Renteneintritt). Werte in heutiger Kaufkraft."
)

if mc_result is not None:
    st.subheader("Bandbreite möglicher Verläufe (Monte-Carlo)")

    real_history = mc_result["real_history"]
    ages_mc = np.array([current_age + m / 12 for m in range(real_history.shape[1])])
    p10 = np.percentile(real_history, 10, axis=0)
    p50 = np.percentile(real_history, 50, axis=0)
    p90 = np.percentile(real_history, 90, axis=0)

    band_df = pd.DataFrame(
        {"Alter": ages_mc, "p10": p10, "p50": p50, "p90": p90}
    )

    band = (
        alt.Chart(band_df)
        .mark_area(opacity=0.25, color="#4c78a8")
        .encode(x="Alter", y=alt.Y("p10", title="Vermögen (heutige Kaufkraft, €)"), y2="p90")
    )
    median_line = (
        alt.Chart(band_df)
        .mark_line(color="#4c78a8")
        .encode(x="Alter", y="p50")
    )
    zero_line = (
        alt.Chart(pd.DataFrame({"y": [0]}))
        .mark_rule(strokeDash=[2, 2], color="crimson")
        .encode(y="y")
    )
    mc_rule = (
        alt.Chart(pd.DataFrame({"Alter": [retirement_age]}))
        .mark_rule(strokeDash=[4, 4], color="gray")
        .encode(x="Alter")
    )

    st.altair_chart(
        (band + median_line + zero_line + mc_rule).interactive(),
        use_container_width=True,
    )
    st.caption(
        "Blaues Band: 10.–90. Perzentil aller simulierten Verläufe, "
        "dunkle Linie: Median. Werte in heutiger Kaufkraft."
    )

    st.subheader("Verteilung des Endvermögens")
    hist_df = pd.DataFrame({"Endvermögen (€)": mc_result["final_capital_real"]})
    histogram = (
        alt.Chart(hist_df)
        .mark_bar()
        .encode(
            x=alt.X("Endvermögen (€)", bin=alt.Bin(maxbins=40)),
            y=alt.Y("count()", title="Anzahl Simulationen"),
        )
    )
    target_rule = (
        alt.Chart(pd.DataFrame({"x": [target_leftover_today]}))
        .mark_rule(strokeDash=[4, 4], color="crimson")
        .encode(x="x")
    )
    st.altair_chart((histogram + target_rule).interactive(), use_container_width=True)
    st.caption(
        "Verteilung des inflationsbereinigten Endvermögens über alle "
        "Simulationen. Die gestrichelte Linie zeigt dein gewünschtes "
        "Restvermögen."
    )

with st.expander("Annahmen & Berechnungsweise"):
    st.markdown(
        """
        - Zinsen werden monatlich verzinst (aus der jährlichen Verzinsung
          abgeleitet).
        - Während der Ansparphase wächst dein Vermögen durch die monatliche
          Sparrate (optional mit jährlicher Steigerung) und die angegebene
          Verzinsung.
        - Die monatliche Entnahme wird über die Entnahmephase hinweg mit der
          Inflation erhöht, damit die **reale Kaufkraft** der Entnahme
          konstant bleibt.
        - Alle Endergebnisse werden mit der Inflation auf heutige Kaufkraft
          abgezinst, damit sie direkt mit deinen heutigen Wunschbeträgen
          vergleichbar sind.
        - Die Monte-Carlo-Simulation zieht für jedes Jahr eine zufällige
          Verzinsung (normalverteilt um deine Erwartungswerte mit der
          angegebenen Volatilität) sowie eine zufällige Inflation und wendet
          sie auf alle zwölf Monate dieses Jahres an. Die
          Erfolgswahrscheinlichkeit ist der Anteil der Simulationen, in
          denen das Vermögen nie unter null fällt **und** am Ende
          mindestens dein gewünschtes Restvermögen erreicht wird.
        - Dies ist eine vereinfachte Modellrechnung ohne Steuern, Gebühren
          oder Marktschwankungen innerhalb eines Jahres und ersetzt keine
          individuelle Finanzberatung.
        """
    )
