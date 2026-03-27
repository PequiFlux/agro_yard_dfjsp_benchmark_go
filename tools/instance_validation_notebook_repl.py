#!/usr/bin/env python3
"""REPL companion for the notebook `instance-validation-and-exploratory-analysis.ipynb`.

Usage:
    python -i tools/instance_validation_notebook_repl.py

This module exposes the same consolidated analysis context used by the notebook
`output/jupyter-notebook/instance-validation-and-exploratory-analysis.ipynb`,
but in a script-first REPL workflow.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import instance_analysis_repl as base


REPO_ROOT = base.REPO_ROOT
NOTEBOOK_PATH = REPO_ROOT / "output" / "jupyter-notebook" / "instance-validation-and-exploratory-analysis.ipynb"
NOTEBOOK_ARTIFACT_DIR = REPO_ROOT / "output" / "jupyter-notebook" / "instance_validation_analysis_artifacts"
NOTEBOOK_TITLE = "Instance Validation and Exploratory Analysis"

STAGE_ORDER = base.STAGE_ORDER
REGIME_ORDER = base.REGIME_ORDER
SCALE_ORDER = base.SCALE_ORDER
SEED = base.SEED


def notebook_sections() -> list[str]:
    return [
        "Inventory and structural context",
        "Structural validation and auditability",
        "Observational layer behavior",
        "Operational performance and regime sanity",
        "Instance drilldown",
        "Results and notes",
    ]


def _make_ctx() -> dict[str, Any]:
    ctx = dict(base.CTX)
    ctx["artifact_dir"] = NOTEBOOK_ARTIFACT_DIR
    return ctx


CTX = _make_ctx()

SUMMARY = CTX["summary"]
PARAMS = CTX["params"]
CATALOG = CTX["catalog"]
FAMILY_SUMMARY = CTX["family_summary"]
VALIDATION_REPORT_OBSERVED = CTX["validation_report_observed"]
OBSERVED_NOISE_MANIFEST = CTX["observed_noise_manifest"]
MANIFEST = CTX["manifest"]
JOBS = CTX["jobs"]
JOBS_ENRICHED = CTX["jobs_enriched"]
OPERATIONS = CTX["operations"]
ELIGIBLE = CTX["eligible"]
MACHINES = CTX["machines"]
PRECEDENCES = CTX["precedences"]
DOWNTIMES = CTX["downtimes"]
EVENTS = CTX["events"]
SCHEDULE = CTX["schedule"]
JOB_METRICS = CTX["job_metrics"]
DUE_AUDIT = CTX["due_audit"]
PROC_AUDIT = CTX["proc_audit"]
PROC_AUDIT_ENRICHED = CTX["proc_audit_enriched"]
CONGESTION = CTX["congestion"]
STRUCTURAL_REPORT = CTX["structural_report"]
EVENT_REPORT = CTX["event_report"]
AUDIT_RECONCILIATION = CTX["audit_reconciliation"]
REGIME_CHECKS = CTX["regime_checks"]
UTILIZATION = CTX["utilization"]
DIAGNOSTICS = CTX["diagnostics"]
UNLOAD = CTX["unload"]


def inventory_tables(ctx: dict[str, Any] | None = None) -> dict[str, pd.DataFrame]:
    return base.inventory_tables(ctx or CTX)


def validation_tables(ctx: dict[str, Any] | None = None) -> dict[str, pd.DataFrame]:
    return base.validation_tables(ctx or CTX)


def plot_inventory_overview(ctx: dict[str, Any] | None = None, save: bool = False):
    return base.plot_inventory_overview(ctx or CTX, save=save)


def plot_validation_overview(ctx: dict[str, Any] | None = None, save: bool = False):
    return base.plot_validation_overview(ctx or CTX, save=save)


def plot_observational_layer(ctx: dict[str, Any] | None = None, save: bool = False):
    return base.plot_observational_layer(ctx or CTX, save=save)


def plot_operational_sanity(ctx: dict[str, Any] | None = None, save: bool = False):
    return base.plot_operational_sanity(ctx or CTX, save=save)


def plot_fifo_schedule(instance_id: str = "GO_XS_DISRUPTED_01", ctx: dict[str, Any] | None = None, save: bool = False):
    ctx = ctx or CTX
    fig = base.schedule_plot(instance_id, ctx["schedule"], ctx["downtimes"])
    if save:
        NOTEBOOK_ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
        fig.savefig(ctx["artifact_dir"] / f"{instance_id.lower()}_fifo_schedule.png", dpi=160, bbox_inches="tight")
    return fig


def plot_congestion_diagnostics(ctx: dict[str, Any] | None = None, save: bool = False):
    ctx = ctx or CTX
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    sns.scatterplot(
        data=ctx["proc_audit_enriched"].sample(min(len(ctx["proc_audit_enriched"]), 3000), random_state=SEED),
        x="arrival_congestion_score",
        y="proc_multiplier",
        hue="stage_name",
        alpha=0.35,
        ax=axes[0],
    )
    axes[0].set_title("Congestion vs processing multiplier")
    axes[0].set_xlabel("Arrival congestion score")
    axes[0].set_ylabel("Observed / nominal")

    sns.boxplot(
        data=ctx["jobs_enriched"],
        x="regime_code",
        y="arrival_congestion_score",
        order=REGIME_ORDER,
        hue="regime_code",
        dodge=False,
        legend=False,
        ax=axes[1],
        palette="mako",
    )
    axes[1].set_title("Arrival congestion by regime")
    axes[1].set_xlabel("Regime")
    axes[1].set_ylabel("Arrival congestion score")

    fig.tight_layout()
    if save:
        NOTEBOOK_ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
        fig.savefig(ctx["artifact_dir"] / "congestion_diagnostics.png", dpi=160, bbox_inches="tight")
    return fig


def plot_job_level_views(instance_id: str = "GO_XS_DISRUPTED_01", ctx: dict[str, Any] | None = None, save: bool = False):
    ctx = ctx or CTX
    sample_jobs = ctx["jobs_enriched"][ctx["jobs_enriched"]["instance_id"] == instance_id].copy()
    sample_metrics = ctx["job_metrics"][ctx["job_metrics"]["instance_id"] == instance_id].copy()

    fig, axes = plt.subplots(1, 2, figsize=(16, 5))
    sns.scatterplot(data=sample_jobs, x="arrival_time_min", y="completion_due_min", hue="priority_class", ax=axes[0], s=80)
    axes[0].set_title(f"{instance_id}: arrival vs due")
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
    axes[1].set_title(f"{instance_id}: top flow times")
    axes[1].set_xlabel("Job")
    axes[1].set_ylabel("Flow time (min)")
    axes[1].tick_params(axis="x", rotation=75)

    fig.tight_layout()
    if save:
        NOTEBOOK_ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
        fig.savefig(ctx["artifact_dir"] / f"{instance_id.lower()}_job_level_views.png", dpi=160, bbox_inches="tight")
    return fig


def notebook_summary_table(ctx: dict[str, Any] | None = None) -> pd.DataFrame:
    ctx = ctx or CTX
    return pd.DataFrame([ctx["summary"]])


def export_notebook_artifacts(ctx: dict[str, Any] | None = None, instance_id: str = "GO_XS_DISRUPTED_01") -> Path:
    ctx = ctx or CTX
    ctx["artifact_dir"].mkdir(parents=True, exist_ok=True)
    notebook_summary_table(ctx).to_csv(ctx["artifact_dir"] / "notebook_repl_summary.csv", index=False)
    validation = validation_tables(ctx)
    validation["structural_report"].to_csv(ctx["artifact_dir"] / "structural_report.csv", index=False)
    validation["event_report"].to_csv(ctx["artifact_dir"] / "event_report.csv", index=False)
    validation["audit_reconciliation"].to_csv(ctx["artifact_dir"] / "audit_reconciliation.csv", index=False)
    validation["due_margin_summary"].to_csv(ctx["artifact_dir"] / "due_margin_summary.csv", index=False)
    plot_inventory_overview(ctx, save=True)
    plot_validation_overview(ctx, save=True)
    plot_observational_layer(ctx, save=True)
    plot_congestion_diagnostics(ctx, save=True)
    plot_operational_sanity(ctx, save=True)
    plot_fifo_schedule(instance_id=instance_id, ctx=ctx, save=True)
    plot_job_level_views(instance_id=instance_id, ctx=ctx, save=True)
    return ctx["artifact_dir"]


def repl_help() -> None:
    print(f"Notebook companion REPL loaded for: {NOTEBOOK_PATH}")
    print("")
    print("Sections:")
    for section in notebook_sections():
        print(f"  - {section}")
    print("")
    print("Quick start:")
    print("  SUMMARY")
    print("  NOTEBOOK_PATH")
    print("  notebook_sections()")
    print("  inventory_tables()['inventory']")
    print("  validation_tables()['structural_report'].head()")
    print("  plot_inventory_overview()")
    print("  plot_validation_overview()")
    print("  plot_observational_layer()")
    print("  plot_congestion_diagnostics()")
    print("  plot_operational_sanity()")
    print("  plot_fifo_schedule('GO_XS_DISRUPTED_01')")
    print("  plot_job_level_views('GO_XS_DISRUPTED_01')")
    print("  export_notebook_artifacts()")


if __name__ == "__main__":
    print("Instance validation notebook REPL loaded.")
    print(json.dumps(SUMMARY, indent=2, ensure_ascii=False))
    print("")
    repl_help()
