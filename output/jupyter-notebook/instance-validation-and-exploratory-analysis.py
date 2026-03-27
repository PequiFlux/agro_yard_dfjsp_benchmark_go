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
NOTEBOOK_CTX = dict(repl.CTX)
NOTEBOOK_CTX["artifact_dir"] = ARTIFACT_DIR

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
- `repl.plot_congestion_diagnostics()`
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

fig = repl.plot_inventory_overview(ctx=NOTEBOOK_CTX, save=True)
plt.show()

# %% [markdown]
# **Como ler a figura acima**
#
# - o heatmap da esquerda mostra cobertura do release por família `escala x regime`
# - as barras da direita mostram quantas linhas de recurso existem por família de máquina no release consolidado
# - a figura serve como checagem de inventário, não de desempenho

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

fig = repl.plot_validation_overview(ctx=NOTEBOOK_CTX, save=True)
plt.show()

structural_report.to_csv(ARTIFACT_DIR / "structural_report.csv", index=False)
event_report.to_csv(ARTIFACT_DIR / "event_report.csv", index=False)
audit_reconciliation.to_csv(ARTIFACT_DIR / "audit_reconciliation.csv", index=False)
due_margin_summary.to_csv(ARTIFACT_DIR / "due_margin_summary.csv", index=False)

# %% [markdown]
# **Como ler a figura acima**
#
# - painel esquerdo: cada célula deve ficar em `PASS`; se aparecer número de issues, aquela família tem falhas estruturais
# - painel central: os dois bars precisam ficar em `100%`; qualquer queda indica quebra entre CSV central e CSV de audit
# - painel direito: mostra quanta folga de prazo sobra acima do lower bound físico plausível

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

fig = repl.plot_observational_layer(ctx=NOTEBOOK_CTX, save=True)
plt.show()

# %% [markdown]
# **Como ler a figura acima**
#
# - prioridade ainda ordena a folga de prazo, mas o `R²` abaixo de `0.5` mostra que ela não explica tudo sozinha
# - `appointment` afeta visibilidade antes da chegada, o que ajuda a aproximar o benchmark de uma operação real
# - em `UNLOAD`, a carga e o regime empurram o tempo mediano para cima
# - os multiplicadores por estágio mostram onde a camada observacional realmente introduziu variação

# %%
fig = repl.plot_congestion_diagnostics(ctx=NOTEBOOK_CTX, save=True)
plt.show()

# %% [markdown]
# **Como ler a figura acima**
#
# - no painel esquerdo, cada linha resume um estágio por decil de congestionamento; inclinação positiva significa que o proxy está influenciando `proc_time`
# - no painel direito, `balanced`, `peak` e `disrupted` deveriam deslocar a distribuição para cima nessa ordem

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

fig = repl.plot_operational_sanity(ctx=NOTEBOOK_CTX, save=True)
plt.show()

# %% [markdown]
# **Como ler a figura acima**
#
# - os heatmaps do topo validam a monotonicidade esperada: `balanced < peak < disrupted`
# - o boxplot inferior esquerdo mostra a distribuição de `flow_time` no nível de job
# - o gráfico inferior direito ajuda a ver quais famílias de máquina absorvem mais pressão em cada regime

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

fig = repl.plot_instance_drilldown(sample_instance, ctx=NOTEBOOK_CTX, save=True)
plt.show()

fig = repl.plot_job_level_views(sample_instance, ctx=NOTEBOOK_CTX, save=True)
plt.show()

# %% [markdown]
# **Como ler as figuras acima**
#
# - o Gantt mostra ocupação por máquina, faixas de downtime e ausência de overlap no baseline FIFO
# - o scatter de jobs ajuda a ver como os prazos se distribuem em função da chegada
# - o ranking horizontal destaca os jobs mais críticos em `flow_time`

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
