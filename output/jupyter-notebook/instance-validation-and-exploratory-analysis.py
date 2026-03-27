# Generated from output/jupyter-notebook/instance-validation-and-exploratory-analysis.ipynb
# Run as a percent script in editors that support `# %%` cells, or as plain Python.

# %% [markdown]
# # Experiment: Instance Validation and Exploratory Analysis
#
# **Objetivo**
#
# Usar o próprio notebook como workspace interativo principal para validar e explorar o release oficial `v1.1.0-observed`, reaproveitando o backend consolidado em `tools/instance_analysis_repl.py`.
#
# **O que este notebook cobre**
#
# - inventário do release oficial e contexto estrutural
# - validação estrutural e reconciliação dos audits
# - comportamento da camada observacional
# - sanidade operacional por regime
# - drilldown visual de uma instância concreta
#
# **Modo de uso**
#
# Este notebook é a interface interativa principal. O módulo `tools/instance_analysis_repl.py` funciona como backend compartilhado da análise, para evitar duas implementações diferentes do mesmo pipeline analítico.

# %%
# Setup: notebook runtime, paths and shared backend
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import matplotlib

NON_INTERACTIVE_CLI = __name__ == "__main__" and "ipykernel" not in sys.modules
if NON_INTERACTIVE_CLI:
    matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from IPython.display import Markdown, display

if NON_INTERACTIVE_CLI:
    plt.show = lambda *args, **kwargs: None


def find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (
            (candidate / "instances").exists()
            and (candidate / "catalog").exists()
            and (candidate / "tools").exists()
        ):
            return candidate
    raise RuntimeError(
        "Could not locate repository root from current working directory."
    )


REPO_ROOT = find_repo_root(Path.cwd().resolve())
ARTIFACT_DIR = (
    REPO_ROOT / "output" / "jupyter-notebook" / "instance_validation_analysis_artifacts"
)
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

TOOLS_DIR = REPO_ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import instance_analysis_repl as repl

repl = importlib.reload(repl)

SEED = repl.SEED
np.random.seed(SEED)
sns.set_theme(style="whitegrid", context="talk")
pd.set_option("display.max_columns", 120)
pd.set_option("display.width", 180)

STAGE_ORDER = repl.STAGE_ORDER
REGIME_ORDER = repl.REGIME_ORDER
SCALE_ORDER = repl.SCALE_ORDER

# %% [markdown]
# ## Plan
#
# 1. Carregar o backend analítico compartilhado e expor os objetos principais no notebook.
# 2. Validar integridade estrutural, reconciliar audits e inspecionar métricas agregadas do release.
# 3. Verificar se a camada observacional reduz sobre-determinismo sem quebrar a semântica operacional.
# 4. Fazer drilldown visual em uma instância para checagem manual do baseline FIFO.

# %%
# Bootstrap the notebook workspace from the shared REPL backend
CTX = repl.CTX
SUMMARY = repl.SUMMARY

params = repl.PARAMS.copy()
catalog = repl.CATALOG.copy()
family_summary = repl.FAMILY_SUMMARY.copy()
observed_noise_manifest = repl.OBSERVED_NOISE_MANIFEST
manifest = repl.MANIFEST

jobs = repl.JOBS.copy()
jobs_enriched = repl.JOBS_ENRICHED.copy()
operations = repl.OPERATIONS.copy()
eligible = repl.ELIGIBLE.copy()
machines = repl.MACHINES.copy()
precedences = repl.PRECEDENCES.copy()
downtimes = repl.DOWNTIMES.copy()
events = repl.EVENTS.copy()
schedule = repl.SCHEDULE.copy()
job_metrics = repl.JOB_METRICS.copy()
due_audit = repl.DUE_AUDIT.copy()
proc_audit = repl.PROC_AUDIT.copy()
proc_audit_enriched = repl.PROC_AUDIT_ENRICHED.copy()
congestion = repl.CONGESTION.copy()

structural_report = repl.STRUCTURAL_REPORT.copy()
event_report = repl.EVENT_REPORT.copy()
audit_reconciliation = repl.AUDIT_RECONCILIATION.copy()
regime_checks = repl.REGIME_CHECKS.copy()
utilization = repl.UTILIZATION.copy()
diagnostics = repl.DIAGNOSTICS.copy()
unload = repl.UNLOAD.copy()

validation_observed = pd.read_csv(
    REPO_ROOT / "catalog" / "validation_report_observed.csv"
)
validation_nominal_style = pd.read_csv(REPO_ROOT / "catalog" / "validation_report.csv")
g2milp_contract = json.loads(
    (REPO_ROOT / "catalog" / "g2milp_generation_contract.json").read_text(
        encoding="utf-8"
    )
)

inventory_summary = pd.DataFrame([SUMMARY])
display(inventory_summary)
display(
    Markdown(
        """
**Quick start interativo**

- `SUMMARY`
- `params.head()`
- `structural_report.head()`
- `repl.plot_inventory_overview()`
- `repl.plot_validation_overview()`
- `repl.plot_observational_layer()`
- `repl.plot_operational_sanity()`
- `repl.plot_instance_drilldown("GO_XS_DISRUPTED_01")`
"""
    )
)

# %%
# Release metadata and provenance checks
noise_manifest_summary = pd.DataFrame(
    [
        {
            "dataset_version": manifest["dataset_version"],
            "official_dataset_role": manifest["official_dataset_role"],
            "noise_model_id": observed_noise_manifest.get("model_id"),
            "noise_global_seed": observed_noise_manifest.get("global_seed"),
            "parent_dataset_version": observed_noise_manifest.get(
                "parent_dataset_version"
            ),
            "generator_model": observed_noise_manifest.get(
                "generator_model", "ChatGPT 5.4 PRO"
            ),
        }
    ]
)

display(params.head())
display(noise_manifest_summary)
display(pd.DataFrame([g2milp_contract]).iloc[:, :8])

# %% [markdown]
# ## Inventory and structural context
#
# Esta seção responde:
#
# - quantas instâncias, jobs, operações, máquinas e linhas elegíveis existem
# - como as famílias `XS/S/M/L` e os regimes `balanced/peak/disrupted` estão distribuídos
# - se os artefatos de auditoria e catálogo estão completos

# %%
display(catalog.sort_values(["scale_code", "regime_code", "replicate"]).head(12))
display(family_summary.sort_values(["scale_code", "regime_code"]))

fig, axes = plt.subplots(1, 2, figsize=(16, 6))

jobs_heatmap = family_summary.pivot(
    index="scale_code", columns="regime_code", values="avg_n_jobs"
).reindex(index=SCALE_ORDER, columns=REGIME_ORDER)
sns.heatmap(jobs_heatmap, annot=True, fmt=".1f", cmap="YlGnBu", ax=axes[0])
axes[0].set_title("Jobs médios por escala e regime")
axes[0].set_xlabel("Regime")
axes[0].set_ylabel("Escala")

machine_family = (
    machines.groupby(["machine_family"], as_index=False)["machine_id"]
    .count()
    .rename(columns={"machine_id": "machine_rows"})
    .sort_values("machine_rows", ascending=False)
)
sns.barplot(
    data=machine_family,
    x="machine_family",
    y="machine_rows",
    hue="machine_family",
    dodge=False,
    legend=False,
    ax=axes[1],
    palette="crest",
)
axes[1].set_title("Linhas de máquinas por família no release")
axes[1].set_xlabel("Família")
axes[1].set_ylabel("Contagem de linhas")
axes[1].tick_params(axis="x", rotation=20)

fig.tight_layout()
fig.savefig(ARTIFACT_DIR / "inventory_overview.png", dpi=160, bbox_inches="tight")
plt.show()

# %% [markdown]
# ## Structural validation and auditability
#
# Aqui reaplicamos o verificador estrutural do release e complementamos com:
#
# - consistência de eventos
# - margem do prazo sobre o lower bound nominal
# - reconciliação auditável entre arquivos centrais e CSVs de audit

# %%
# The shared REPL backend already ships these reports with scale/regime context.

display(structural_report.sort_values(["scale_code", "regime_code", "instance_id"]))
display(event_report.sort_values(["scale_code", "regime_code", "instance_id"]))
display(audit_reconciliation.sort_values(["scale_code", "regime_code", "instance_id"]))

due_margin_summary = (
    jobs_enriched.groupby(["scale_code", "regime_code"], as_index=False)[
        "due_margin_over_lb_min"
    ]
    .agg(["mean", "min", "median", "max"])
    .round(2)
    .reset_index()
)
display(due_margin_summary)

fig, axes = plt.subplots(1, 3, figsize=(18, 5))

issue_heatmap = structural_report.pivot_table(
    index="scale_code",
    columns="regime_code",
    values="issue_count",
    aggfunc="sum",
    fill_value=0,
).reindex(index=SCALE_ORDER, columns=REGIME_ORDER)
sns.heatmap(
    issue_heatmap, annot=True, fmt=".0f", cmap="Greens_r", ax=axes[0], cbar=False
)
axes[0].set_title("Issue count por escala/regime")

audit_long = audit_reconciliation.melt(
    id_vars=["instance_id", "scale_code", "regime_code"],
    value_vars=["due_match_share", "proc_match_share"],
    var_name="check",
    value_name="match_share",
)
sns.boxplot(
    data=audit_long,
    x="check",
    y="match_share",
    hue="check",
    dodge=False,
    legend=False,
    ax=axes[1],
    palette="Set2",
)
axes[1].set_title("Reconciliação com audits")
axes[1].set_xlabel("")
axes[1].set_ylabel("Share de linhas reconciliadas")
axes[1].set_ylim(0.95, 1.01)

sns.boxplot(
    data=jobs_enriched,
    x="regime_code",
    y="due_margin_over_lb_min",
    order=REGIME_ORDER,
    hue="regime_code",
    dodge=False,
    legend=False,
    ax=axes[2],
    palette="flare",
)
axes[2].set_title("Margem do prazo sobre lower bound")
axes[2].set_xlabel("Regime")
axes[2].set_ylabel("Margem (min)")

fig.tight_layout()
fig.savefig(
    ARTIFACT_DIR / "structural_validation_and_auditability.png",
    dpi=160,
    bbox_inches="tight",
)
plt.show()

structural_report.to_csv(ARTIFACT_DIR / "structural_report.csv", index=False)
event_report.to_csv(ARTIFACT_DIR / "event_report.csv", index=False)
audit_reconciliation.to_csv(ARTIFACT_DIR / "audit_reconciliation.csv", index=False)
due_margin_summary.to_csv(ARTIFACT_DIR / "due_margin_summary.csv", index=False)

# %% [markdown]
# ## Observational layer behavior
#
# Esta seção testa se a camada observacional cumpriu seu papel:
#
# - a prioridade continua importante, mas não perfeitamente determinística
# - tempos de `UNLOAD` continuam interpretáveis por carga, máquina, umidade e congestionamento
# - o ruído aparece de forma estruturada, e não como barulho arbitrário

# %%
diagnostics_df = pd.DataFrame([diagnostics])
display(diagnostics_df)

fig, axes = plt.subplots(2, 2, figsize=(18, 12))

sns.boxplot(
    data=jobs_enriched,
    x="priority_class",
    y="due_slack_min",
    order=["URGENT", "CONTRACTED", "REGULAR"],
    hue="priority_class",
    dodge=False,
    legend=False,
    ax=axes[0, 0],
    palette="viridis",
)
axes[0, 0].set_title("Folga observada por classe de prioridade")
axes[0, 0].set_xlabel("Priority class")
axes[0, 0].set_ylabel("Due slack (min)")

sns.boxplot(
    data=jobs_enriched,
    x="appointment_flag",
    y="reveal_lead_min",
    hue="appointment_flag",
    dodge=False,
    legend=False,
    ax=axes[0, 1],
    palette="coolwarm",
)
axes[0, 1].set_title("Lead de revelação por appointment")
axes[0, 1].set_xlabel("Appointment flag")
axes[0, 1].set_ylabel("Arrival - reveal (min)")

sns.scatterplot(
    data=unload.sample(min(len(unload), 2500), random_state=SEED),
    x="load_tons",
    y="proc_time_min",
    hue="moisture_class",
    style="regime_code",
    alpha=0.45,
    ax=axes[1, 0],
)
axes[1, 0].set_title("UNLOAD: carga vs proc_time observado")
axes[1, 0].set_xlabel("Load tons")
axes[1, 0].set_ylabel("Proc time (min)")

sns.boxplot(
    data=proc_audit_enriched,
    x="stage_name",
    y="proc_multiplier",
    order=STAGE_ORDER,
    hue="stage_name",
    dodge=False,
    legend=False,
    ax=axes[1, 1],
    palette="Set3",
)
axes[1, 1].set_title("Multiplicador observado/nominal por estágio")
axes[1, 1].set_xlabel("Stage")
axes[1, 1].set_ylabel("Observed / nominal")
axes[1, 1].tick_params(axis="x", rotation=15)

fig.tight_layout()
fig.savefig(
    ARTIFACT_DIR / "observational_layer_behavior.png", dpi=160, bbox_inches="tight"
)
plt.show()

# %%
congestion_vs_proc = proc_audit_enriched.copy()

fig, axes = plt.subplots(1, 2, figsize=(16, 6))

sns.scatterplot(
    data=congestion_vs_proc.sample(
        min(len(congestion_vs_proc), 3000), random_state=SEED
    ),
    x="arrival_congestion_score",
    y="proc_multiplier",
    hue="stage_name",
    alpha=0.35,
    ax=axes[0],
)
axes[0].set_title("Congestionamento vs multiplicador de proc_time")
axes[0].set_xlabel("Arrival congestion score")
axes[0].set_ylabel("Observed / nominal")

sns.boxplot(
    data=jobs_enriched,
    x="regime_code",
    y="arrival_congestion_score",
    order=REGIME_ORDER,
    hue="regime_code",
    dodge=False,
    legend=False,
    ax=axes[1],
    palette="mako",
)
axes[1].set_title("Congestionamento por regime")
axes[1].set_xlabel("Regime")
axes[1].set_ylabel("Arrival congestion score")

fig.tight_layout()
fig.savefig(ARTIFACT_DIR / "congestion_diagnostics.png", dpi=160, bbox_inches="tight")
plt.show()

# %% [markdown]
# ## Operational performance and regime sanity
#
# A validação não depende só de integridade estrutural. Também interessa saber se:
#
# - `balanced < peak < disrupted` permanece verdadeiro
# - os tempos de fluxo e fila continuam coerentes com a escala do problema
# - a utilização de recurso faz sentido por família de máquina

# %%
display(regime_checks)
display(family_summary.sort_values(["scale_code", "regime_code"]))

fig, axes = plt.subplots(2, 2, figsize=(18, 12))

mean_heatmap = family_summary.pivot(
    index="scale_code", columns="regime_code", values="avg_fifo_mean_flow_min"
).reindex(index=SCALE_ORDER, columns=REGIME_ORDER)
sns.heatmap(mean_heatmap, annot=True, fmt=".1f", cmap="YlOrBr", ax=axes[0, 0])
axes[0, 0].set_title("FIFO mean flow por escala/regime")

p95_heatmap = family_summary.pivot(
    index="scale_code", columns="regime_code", values="avg_fifo_p95_flow_min"
).reindex(index=SCALE_ORDER, columns=REGIME_ORDER)
sns.heatmap(p95_heatmap, annot=True, fmt=".1f", cmap="YlGnBu", ax=axes[0, 1])
axes[0, 1].set_title("FIFO p95 flow por escala/regime")

sns.boxplot(
    data=job_metrics,
    x="regime_code",
    y="flow_time_min",
    order=REGIME_ORDER,
    hue="regime_code",
    dodge=False,
    legend=False,
    ax=axes[1, 0],
    palette="Spectral",
)
axes[1, 0].set_title("Distribuição de flow time por regime")
axes[1, 0].set_xlabel("Regime")
axes[1, 0].set_ylabel("Flow time (min)")

util_plot = utilization.groupby(["machine_family", "regime_code"], as_index=False)[
    "utilization_share"
].mean()
sns.barplot(
    data=util_plot,
    x="machine_family",
    y="utilization_share",
    hue="regime_code",
    hue_order=REGIME_ORDER,
    ax=axes[1, 1],
    palette="deep",
)
axes[1, 1].set_title("Utilização média por família de máquina")
axes[1, 1].set_xlabel("Machine family")
axes[1, 1].set_ylabel("Utilization share")
axes[1, 1].tick_params(axis="x", rotation=20)

fig.tight_layout()
fig.savefig(
    ARTIFACT_DIR / "operational_performance_and_regime_sanity.png",
    dpi=160,
    bbox_inches="tight",
)
plt.show()

# %% [markdown]
# ## Instance drilldown
#
# Um drilldown ajuda a validar visualmente se o baseline FIFO de uma instância concreta:
#
# - respeita o fluxo por máquina
# - evita overlap
# - incorpora downtimes
# - produz métricas coerentes com o regime escolhido

# %%
sample_instance = "GO_XS_DISRUPTED_01"

sample_params = params[params["instance_id"] == sample_instance]
sample_summary = catalog[catalog["instance_id"] == sample_instance]
sample_jobs = jobs_enriched[jobs_enriched["instance_id"] == sample_instance]
sample_metrics = job_metrics[job_metrics["instance_id"] == sample_instance]

display(sample_params)
display(sample_summary)
display(sample_jobs.head())
display(sample_metrics.describe().round(2))

fig = repl.schedule_plot(sample_instance, schedule, downtimes)
fig.savefig(
    ARTIFACT_DIR / f"{sample_instance.lower()}_fifo_schedule.png",
    dpi=160,
    bbox_inches="tight",
)
plt.show()

fig, axes = plt.subplots(1, 2, figsize=(16, 5))
sns.scatterplot(
    data=sample_jobs,
    x="arrival_time_min",
    y="completion_due_min",
    hue="priority_class",
    ax=axes[0],
    s=80,
)
axes[0].set_title(f"{sample_instance}: chegada vs prazo")
axes[0].set_xlabel("Arrival time (min)")
axes[0].set_ylabel("Completion due (min)")

sns.barplot(
    data=sample_metrics.sort_values("flow_time_min", ascending=False).head(12),
    x="job_id",
    y="flow_time_min",
    hue="job_id",
    dodge=False,
    legend=False,
    ax=axes[1],
    palette="rocket",
)
axes[1].set_title(f"{sample_instance}: top flow times")
axes[1].set_xlabel("Job")
axes[1].set_ylabel("Flow time (min)")
axes[1].tick_params(axis="x", rotation=75)

fig.tight_layout()
fig.savefig(
    ARTIFACT_DIR / f"{sample_instance.lower()}_job_level_views.png",
    dpi=160,
    bbox_inches="tight",
)
plt.show()

# %% [markdown]
# ## Results and notes
#
# O notebook consolida uma leitura de qualidade do release oficial:
#
# - o release está estruturalmente íntegro
# - os audits reconciliam os valores centrais
# - os regimes preservam a hierarquia operacional esperada
# - a camada observacional reduz determinismo excessivo sem destruir semântica
# - a base é forte o suficiente para servir como dataset pai de análises e futuras derivações com G2MILP

# %%
summary = {
    "dataset_version": manifest["dataset_version"],
    "instance_count": int(params["instance_id"].nunique()),
    "structural_pass_rate": float((structural_report["status"] == "PASS").mean()),
    "due_audit_match_share": float(audit_reconciliation["due_match_share"].mean()),
    "proc_audit_match_share": float(audit_reconciliation["proc_match_share"].mean()),
    "r2_due_slack_vs_priority": float(diagnostics["r2_due_slack_vs_priority"]),
    "r2_unload_proc_vs_load_machine_moisture": float(
        diagnostics["r2_unload_proc_vs_load_machine_moisture"]
    ),
    "all_regime_order_checks_pass": bool(
        regime_checks["mean_flow_order_ok"].all()
        and regime_checks["p95_flow_order_ok"].all()
    ),
    "g2milp_role": manifest["official_dataset_role"],
}
summary_df = pd.DataFrame([summary])
display(summary_df)

summary_lines = [
    "# Notebook Summary",
    "",
    f"- Dataset version: `{summary['dataset_version']}`",
    f"- Instances: `{summary['instance_count']}`",
    f"- Structural pass rate: `{summary['structural_pass_rate']:.4f}`",
    f"- Due audit match share: `{summary['due_audit_match_share']:.4f}`",
    f"- Proc audit match share: `{summary['proc_audit_match_share']:.4f}`",
    f"- R2 due slack vs priority: `{summary['r2_due_slack_vs_priority']:.4f}`",
    f"- R2 unload proc vs load+machine+moisture: `{summary['r2_unload_proc_vs_load_machine_moisture']:.4f}`",
    f"- Regime ordering checks all pass: `{summary['all_regime_order_checks_pass']}`",
    f"- Official role: `{summary['g2milp_role']}`",
]
summary_text = "\n".join(summary_lines)
(ARTIFACT_DIR / "notebook_summary.md").write_text(summary_text, encoding="utf-8")
summary_df.to_csv(ARTIFACT_DIR / "notebook_summary.csv", index=False)
display(Markdown(summary_text))

# %% [markdown]
# ## Next steps
#
# - usar este notebook como baseline de validação antes de gerar filhos com G2MILP
# - ampliar com comparações entre esta release oficial e futuros datasets derivados
# - adicionar testes de sensibilidade por família de máquina ou por política de geração
