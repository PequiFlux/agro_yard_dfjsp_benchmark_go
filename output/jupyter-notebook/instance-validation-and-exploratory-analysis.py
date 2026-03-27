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
# - cobertura do espaço de instâncias e checagem de redundância
# - smoke test orientado a solver para verificar utilidade algorítmica do benchmark
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
import exact_solver_smoke as solver_smoke

repl = importlib.reload(repl)
solver_smoke = importlib.reload(solver_smoke)

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
# 4. Confirmar que o release cobre regiões distintas do espaço de instâncias e não colapsa em casos quase redundantes.
# 5. Executar um smoke test exato com orçamento fixo para mostrar que o benchmark é informativo do ponto de vista algorítmico.
# 6. Fazer drilldown visual em uma instância para checagem manual do baseline FIFO.

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
fifo_schema_report = repl.FIFO_SCHEMA_REPORT.copy()
release_consistency_report = repl.RELEASE_CONSISTENCY_REPORT.copy()
utilization = repl.UTILIZATION.copy()
instance_space_features = repl.INSTANCE_SPACE_FEATURES.copy()
instance_space_pairs = repl.INSTANCE_SPACE_PAIRS.copy()
instance_space_summary = repl.INSTANCE_SPACE_SUMMARY.copy()
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
- `repl.plot_instance_space_coverage()`
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
            "parent_dataset_version": manifest.get("parent_dataset_version"),
            "generator_model": observed_noise_manifest.get(
                "generator_model", "ChatGPT 5.4 PRO"
            ),
        }
    ]
)

display(params.head())
display(noise_manifest_summary)
display(release_consistency_report)
display(pd.DataFrame([g2milp_contract]).iloc[:, :8])

release_consistency_report.to_csv(
    ARTIFACT_DIR / "release_consistency_report.csv", index=False
)

# %% [markdown]
# **Como ler as tabelas acima**
#
# - `noise_manifest_summary` resume a versão oficial, a linhagem e o modelo gerador da camada observacional
# - `release_consistency_report` formaliza a governança do release: `manifest.json` raiz, `params.json` das instâncias e `observed_noise_manifest.json`
# - para publicação, o desejável é que todos os checks dessa tabela estejam em `pass = True`
# - no release oficial atual, isso de fato ocorre; em particular, não há divergência entre a `dataset_version` do `manifest.json` raiz e a `dataset_version` declarada nos `params.json`

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
# - executabilidade formal do baseline FIFO contra o schema
# - consistência de eventos
# - margem do prazo sobre o lower bound nominal
# - reconciliação auditável entre arquivos centrais e CSVs de audit

# %%
# The shared REPL backend already ships these reports with scale/regime context.

display(structural_report.sort_values(["scale_code", "regime_code", "instance_id"]))
display(fifo_schema_report.sort_values(["scale_code", "regime_code", "instance_id"]))
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
fifo_schema_report.to_csv(ARTIFACT_DIR / "fifo_schema_report.csv", index=False)
event_report.to_csv(ARTIFACT_DIR / "event_report.csv", index=False)
audit_reconciliation.to_csv(ARTIFACT_DIR / "audit_reconciliation.csv", index=False)
due_margin_summary.to_csv(ARTIFACT_DIR / "due_margin_summary.csv", index=False)

# %% [markdown]
# **Como ler a figura acima**
#
# - painel esquerdo: cada célula deve ficar em `PASS`; se aparecer número de issues, aquela família tem falhas estruturais
# - a tabela `fifo_schema_report` formaliza a executabilidade do baseline FIFO: elegibilidade, `release_time`, precedência, overlap e downtime
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
# - `balanced < peak < disrupted` permanece verdadeiro para `mean_flow` e `p95_flow`
# - a fila média também preserva monotonicidade
# - o proxy médio de congestionamento não precisa ser monotônico em todas as famílias
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
# - os heatmaps do topo validam a monotonicidade esperada apenas para `flow`: `balanced < peak < disrupted`
# - a tabela `regime_checks` separa formalmente os checks de `flow`, `queue` e `congestion`
# - o boxplot inferior esquerdo mostra a distribuição de `flow_time` no nível de job
# - o gráfico inferior direito ajuda a ver quais famílias de máquina absorvem mais pressão em cada regime

# %% [markdown]
# ## Instance-space coverage and redundancy screening
#
# Além de ser íntegro e executável, o release precisa cobrir regiões distintas do problema.
# Esta seção responde:
#
# - se há duplicatas exatas no nível de instância
# - se há casos "duplicate-like" em um espaço multivariado de features estruturais e operacionais
# - quão dispersas as instâncias estão quando projetadas em 2D
# - quais pares são os mais próximos dentro do release

# %%
display(instance_space_summary)
display(
    instance_space_features[
        [
            "instance_id",
            "scale_code",
            "regime_code",
            "nearest_neighbor_instance_id",
            "nearest_neighbor_distance",
            "duplicate_like_candidate",
        ]
    ].sort_values("nearest_neighbor_distance")
)
display(instance_space_pairs.head(12))

fig = repl.plot_instance_space_coverage(ctx=NOTEBOOK_CTX, save=True)
plt.show()

instance_space_features.to_csv(ARTIFACT_DIR / "instance_space_features.csv", index=False)
instance_space_pairs.to_csv(ARTIFACT_DIR / "instance_space_pairs.csv", index=False)
instance_space_summary.to_csv(ARTIFACT_DIR / "instance_space_summary.csv", index=False)

# %% [markdown]
# **Como ler a figura acima**
#
# - painel esquerdo: a PCA resume o release em 2 dimensões; espalhamento visível indica que as instâncias não colapsam em um bloco quase idêntico
# - painel central: cada barra é a distância ao vizinho mais próximo; quanto mais longe da linha tracejada, menor a suspeita de redundância
# - painel direito: mostra os pares mais próximos do release; se algum caísse abaixo do limiar, ele apareceria como candidato `duplicate-like`
# - o screening aqui é deliberadamente conservador: ele combina `core_instance_digest`, features padronizadas e distância ao vizinho mais próximo

# %% [markdown]
# ## Solver-oriented smoke test
#
# As seções anteriores mostram que o release é válido e diverso. Esta seção
# adiciona uma evidência complementar: o dataset também é informativo para
# benchmark algorítmico.
#
# O teste abaixo não é o protocolo final do TCC. Ele é um **smoke test exato
# budgetado**, usando `scipy.optimize.milp` neste ambiente porque `gurobipy`
# não está disponível localmente. Para manter o tempo de execução sob controle,
# usamos subinstâncias induzidas pelos primeiros jobs em ordem de chegada,
# com orçamento fixo de `5` segundos por caso.
#
# A leitura desejada é:
#
# - casos pequenos fecham com solver exato
# - casos intermediários continuam viáveis, mas passam a exibir gap
# - casos maiores seguem carregando e produzindo incumbentes, mas já apontam para trilhas `hybrid` ou `metaheuristic`

# %%
solver_smoke_df = solver_smoke.run_smoke_suite(root=REPO_ROOT)
solver_smoke_df["case_label"] = (
    solver_smoke_df["scale_code"].astype(str)
    + "-"
    + solver_smoke_df["max_jobs"].astype(int).astype(str)
    + " jobs"
)
solver_smoke_df["gap_pct"] = solver_smoke_df["mip_gap"].fillna(1.0) * 100.0
solver_smoke_df["objective_vs_dual_gap_min"] = (
    solver_smoke_df["objective_makespan_min"] - solver_smoke_df["dual_bound_makespan_min"]
)

display(solver_smoke_df)

fig, axes = plt.subplots(1, 3, figsize=(20, 6.5))

sns.barplot(
    data=solver_smoke_df,
    x="case_label",
    y="objective_makespan_min",
    hue="status_label",
    dodge=False,
    palette={"optimal": "#2a9d8f", "time_limit": "#e9c46a", "feasible": "#8ecae6", "other": "#94a3b8", "infeasible": "#d62828"},
    ax=axes[0],
)
axes[0].scatter(
    range(len(solver_smoke_df)),
    solver_smoke_df["dual_bound_makespan_min"],
    color="#1d3557",
    s=70,
    marker="D",
    zorder=3,
    label="Dual bound",
)
for idx, row in solver_smoke_df.reset_index(drop=True).iterrows():
    if pd.notna(row["mip_gap"]):
        axes[0].text(idx, row["objective_makespan_min"] + 8, f"gap {row['mip_gap']:.1%}", ha="center", va="bottom", fontsize=9, color="#334155")
axes[0].set_title("Incumbente e dual bound por caso\nFechar o gap fica mais difícil à medida que o tamanho cresce", fontsize=13)
axes[0].set_xlabel("")
axes[0].set_ylabel("Makespan (min)")
axes[0].tick_params(axis="x", rotation=15)
handles, labels = axes[0].get_legend_handles_labels()
axes[0].legend(handles, labels, loc="upper left", frameon=True)

sns.barplot(
    data=solver_smoke_df,
    x="case_label",
    y="gap_pct",
    hue="recommended_solver_track",
    dodge=False,
    palette="deep",
    ax=axes[1],
)
axes[1].set_title("Gap relativo sob orçamento fixo de 5 s\nA escada de dificuldade já aparece no smoke test", fontsize=13)
axes[1].set_xlabel("")
axes[1].set_ylabel("MIP gap (%)")
axes[1].tick_params(axis="x", rotation=15)
for patch in axes[1].patches:
    height = patch.get_height()
    if np.isfinite(height) and height > 0:
        axes[1].text(patch.get_x() + patch.get_width() / 2, height + 1.0, f"{height:.1f}%", ha="center", va="bottom", fontsize=9, color="#334155")

size_plot = solver_smoke_df.melt(
    id_vars=["case_label"],
    value_vars=["eligible_var_count", "machine_pair_binary_count", "constraint_count"],
    var_name="size_metric",
    value_name="count",
)
size_labels = {
    "eligible_var_count": "x vars",
    "machine_pair_binary_count": "sequencing binaries",
    "constraint_count": "constraints",
}
size_plot["size_metric"] = size_plot["size_metric"].map(size_labels)
sns.barplot(
    data=size_plot,
    x="case_label",
    y="count",
    hue="size_metric",
    ax=axes[2],
    palette="Set2",
)
axes[2].set_title("Crescimento do modelo exato\nO custo combinatório sobe rapidamente com o tamanho", fontsize=13)
axes[2].set_xlabel("")
axes[2].set_ylabel("Contagem")
axes[2].tick_params(axis="x", rotation=15)

fig.suptitle("Smoke test orientado a solver", x=0.02, y=1.03, ha="left", fontsize=18, fontweight="bold")
fig.text(
    0.02,
    0.95,
    "Leitura rápida: o pipeline exato carrega, fecha nos menores e passa a exibir gaps não triviais quando a escala do caso cresce.",
    fontsize=11,
)
fig.tight_layout(rect=(0, 0, 1, 0.92))
fig.savefig(ARTIFACT_DIR / "solver_oriented_smoke_test.png", dpi=160, bbox_inches="tight")
plt.show()

solver_smoke_df.to_csv(ARTIFACT_DIR / "solver_smoke_results.csv", index=False)

solver_smoke_summary = pd.DataFrame(
    [
        {
            "solver_backend": "scipy.optimize.milp (HiGHS)",
            "time_limit_sec": float(solver_smoke_df["time_limit_sec"].iloc[0]),
            "small_cases_optimal": bool(
                solver_smoke_df.loc[solver_smoke_df["max_jobs"].isin([8, 12]), "status_label"].eq("optimal").all()
            ),
            "all_cases_have_solution": bool(solver_smoke_df["has_solution"].all()),
            "large_cases_nontrivial_gap": bool(
                solver_smoke_df.loc[solver_smoke_df["max_jobs"].isin([18, 24]), "mip_gap"].fillna(0.0).ge(0.10).all()
            ),
            "gap_non_decreasing_with_case_size": bool(
                solver_smoke_df.sort_values("max_jobs")["mip_gap"].fillna(0.0).is_monotonic_increasing
            ),
        }
    ]
)
display(solver_smoke_summary)
solver_smoke_summary.to_csv(ARTIFACT_DIR / "solver_smoke_summary.csv", index=False)

# %% [markdown]
# **Como ler a figura acima**
#
# - painel esquerdo: as barras são os incumbentes e os diamantes são os dual bounds; distância grande entre eles significa dificuldade residual
# - painel central: sob o mesmo orçamento de tempo, `XS-8` e `S-12` fecham, enquanto `M-18` e `L-24` já preservam gaps não triviais
# - painel direito: o crescimento de binárias disjuntivas e restrições explica por que a trilha recomendada migra de `exact` para `hybrid/metaheuristic`
# - esta seção é um **smoke test de utilidade algorítmica**, não o protocolo final de competição entre solvers

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
# - o baseline FIFO é executável contra o schema nas `36` instâncias
# - os audits reconciliam os valores centrais
# - os checks de regime são positivos para `mean_flow`, `p95_flow` e fila média
# - o proxy médio de congestionamento é útil, mas não monotônico em todas as famílias
# - o espaço de instâncias não contém duplicatas exatas nem candidatos `duplicate-like` sob o screening adotado
# - o smoke test exato fecha nos casos menores e exibe gaps não triviais quando o tamanho da subinstância cresce
# - a camada observacional reduz determinismo excessivo sem destruir semântica
# - a base é forte o suficiente para servir como dataset pai de análises e futuras derivações com G2MILP

# %%
summary = {
    "dataset_version": manifest["dataset_version"],
    "instance_count": int(params["instance_id"].nunique()),
    "structural_pass_rate": float((structural_report["status"] == "PASS").mean()),
    "release_consistency_checks_pass": bool(release_consistency_report["pass"].all()),
    "fifo_schema_checks_pass": bool(
        fifo_schema_report[
            [
                "eligible_assignment_ok",
                "release_time_ok",
                "precedence_ok",
                "machine_overlap_ok",
                "downtime_ok",
            ]
        ].all(axis=None)
    ),
    "due_audit_match_share": float(audit_reconciliation["due_match_share"].mean()),
    "proc_audit_match_share": float(audit_reconciliation["proc_match_share"].mean()),
    "r2_due_slack_vs_priority": float(diagnostics["r2_due_slack_vs_priority"]),
    "r2_unload_proc_vs_load_machine_moisture": float(
        diagnostics["r2_unload_proc_vs_load_machine_moisture"]
    ),
    "flow_regime_order_checks_pass": bool(
        regime_checks["mean_flow_order_ok"].all()
        and regime_checks["p95_flow_order_ok"].all()
    ),
    "queue_regime_order_checks_pass": bool(regime_checks["mean_queue_order_ok"].all()),
    "congestion_mean_regime_order_checks_pass": bool(
        regime_checks["mean_congestion_order_ok"].all()
    ),
    "instance_space_exact_duplicate_checks_pass": bool(
        instance_space_summary.loc[0, "exact_core_duplicate_count"] == 0
        and instance_space_summary.loc[0, "exact_feature_duplicate_count"] == 0
    ),
    "instance_space_duplicate_like_checks_pass": bool(
        instance_space_summary.loc[0, "duplicate_like_candidate_count"] == 0
    ),
    "instance_space_nearest_neighbor_distance_min": float(
        instance_space_summary.loc[0, "nearest_neighbor_distance_min"]
    ),
    "solver_smoke_small_cases_optimal": bool(
        solver_smoke_summary.loc[0, "small_cases_optimal"]
    ),
    "solver_smoke_all_cases_have_solution": bool(
        solver_smoke_summary.loc[0, "all_cases_have_solution"]
    ),
    "solver_smoke_large_cases_nontrivial_gap": bool(
        solver_smoke_summary.loc[0, "large_cases_nontrivial_gap"]
    ),
    "solver_smoke_gap_ladder_pass": bool(
        solver_smoke_summary.loc[0, "gap_non_decreasing_with_case_size"]
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
    f"- Release consistency checks pass: `{summary['release_consistency_checks_pass']}`",
    f"- FIFO schema checks pass: `{summary['fifo_schema_checks_pass']}`",
    f"- Due audit match share: `{summary['due_audit_match_share']:.4f}`",
    f"- Proc audit match share: `{summary['proc_audit_match_share']:.4f}`",
    f"- R2 due slack vs priority: `{summary['r2_due_slack_vs_priority']:.4f}`",
    f"- R2 unload proc vs load+machine+moisture: `{summary['r2_unload_proc_vs_load_machine_moisture']:.4f}`",
    f"- Flow regime checks pass: `{summary['flow_regime_order_checks_pass']}`",
    f"- Mean queue regime checks pass: `{summary['queue_regime_order_checks_pass']}`",
    f"- Mean congestion regime checks pass: `{summary['congestion_mean_regime_order_checks_pass']}`",
    f"- Instance-space exact duplicate checks pass: `{summary['instance_space_exact_duplicate_checks_pass']}`",
    f"- Instance-space duplicate-like checks pass: `{summary['instance_space_duplicate_like_checks_pass']}`",
    f"- Instance-space nearest-neighbor distance min: `{summary['instance_space_nearest_neighbor_distance_min']:.4f}`",
    f"- Solver smoke small cases optimal: `{summary['solver_smoke_small_cases_optimal']}`",
    f"- Solver smoke all cases have solution: `{summary['solver_smoke_all_cases_have_solution']}`",
    f"- Solver smoke large cases show non-trivial gap: `{summary['solver_smoke_large_cases_nontrivial_gap']}`",
    f"- Solver smoke gap ladder pass: `{summary['solver_smoke_gap_ladder_pass']}`",
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
