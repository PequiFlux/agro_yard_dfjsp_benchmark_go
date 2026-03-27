#!/usr/bin/env python3
"""REPL-friendly analysis bootstrap for the official observed benchmark release.

Usage:
    python -i tools/instance_analysis_repl.py

After the session starts, the main loaded objects are available as globals:
    SUMMARY
    PARAMS
    CATALOG
    FAMILY_SUMMARY
    JOBS
    JOBS_ENRICHED
    OPERATIONS
    ELIGIBLE
    MACHINES
    EVENTS
    SCHEDULE
    JOB_METRICS
    DUE_AUDIT
    PROC_AUDIT
    STRUCTURAL_REPORT
    EVENT_REPORT
    AUDIT_RECONCILIATION
    REGIME_CHECKS
    UTILIZATION
    DIAGNOSTICS

Main helper functions:
    inventory_tables()
    plot_inventory_overview()
    validation_tables()
    plot_validation_overview()
    plot_observational_layer()
    plot_operational_sanity()
    plot_instance_drilldown("GO_XS_DISRUPTED_01")
    export_all_artifacts()
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from validate_observed_release import diagnostics as release_diagnostics
from validate_observed_release import validate_instance


SEED = 7
np.random.seed(SEED)
sns.set_theme(style="whitegrid", context="talk")

STAGE_ORDER = ["WEIGH_IN", "SAMPLE_CLASSIFY", "UNLOAD", "WEIGH_OUT"]
REGIME_ORDER = ["balanced", "peak", "disrupted"]
SCALE_ORDER = ["XS", "S", "M", "L"]


def find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "instances").exists() and (candidate / "catalog").exists() and (candidate / "tools").exists():
            return candidate
    raise RuntimeError("Could not locate repository root from current working directory.")


REPO_ROOT = find_repo_root(Path(__file__).resolve())
ARTIFACT_DIR = REPO_ROOT / "output" / "repl-analysis-artifacts"


def iter_instance_dirs(root: Path) -> list[Path]:
    return sorted(p for p in (root / "instances").iterdir() if p.is_dir())


def load_instance_csv(root: Path, file_name: str) -> pd.DataFrame:
    frames = []
    for inst_dir in iter_instance_dirs(root):
        frame = pd.read_csv(inst_dir / file_name)
        frame["instance_id"] = inst_dir.name
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def load_params_frame(root: Path) -> pd.DataFrame:
    rows = []
    for inst_dir in iter_instance_dirs(root):
        payload = json.loads((inst_dir / "params.json").read_text(encoding="utf-8"))
        rows.append(payload)
    return pd.DataFrame(rows)


def add_instance_context(frame: pd.DataFrame, params: pd.DataFrame) -> pd.DataFrame:
    keep = ["instance_id", "scale_code", "regime_code", "replicate", "dataset_version"]
    return frame.merge(params[keep], on="instance_id", how="left")


def compute_due_lower_bounds(jobs: pd.DataFrame, eligible: pd.DataFrame) -> pd.DataFrame:
    lower_bounds = (
        eligible.groupby(["instance_id", "job_id", "op_seq"], as_index=False)["proc_time_min"]
        .min()
        .groupby(["instance_id", "job_id"], as_index=False)["proc_time_min"]
        .sum()
        .rename(columns={"proc_time_min": "nominal_lb_min"})
    )
    merged = jobs.merge(lower_bounds, on=["instance_id", "job_id"], how="left")
    merged["due_slack_min"] = merged["completion_due_min"] - merged["arrival_time_min"]
    merged["due_margin_over_lb_min"] = merged["due_slack_min"] - merged["nominal_lb_min"]
    merged["reveal_lead_min"] = merged["arrival_time_min"] - merged["reveal_time_min"]
    return merged


def build_structural_report(root: Path) -> pd.DataFrame:
    rows = [validate_instance(inst_dir) for inst_dir in iter_instance_dirs(root)]
    return pd.DataFrame(rows)


def event_consistency_frame(jobs: pd.DataFrame, events: pd.DataFrame, downtimes: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for instance_id, jobs_g in jobs.groupby("instance_id"):
        events_g = events[events["instance_id"] == instance_id]
        downs_g = downtimes[downtimes["instance_id"] == instance_id]
        visible = events_g[events_g["event_type"] == "JOB_VISIBLE"].groupby("entity_id").size()
        arrival = events_g[events_g["event_type"] == "JOB_ARRIVAL"].groupby("entity_id").size()
        visible_mismatch = int((visible.reindex(jobs_g["job_id"]).fillna(0) != 1).sum())
        arrival_mismatch = int((arrival.reindex(jobs_g["job_id"]).fillna(0) != 1).sum())

        down_rows = events_g[events_g["event_type"] == "MACHINE_DOWN"][["entity_id", "event_time_min"]]
        up_rows = events_g[events_g["event_type"] == "MACHINE_UP"][["entity_id", "event_time_min"]]
        down_expected = downs_g[["machine_id", "start_min"]].rename(columns={"machine_id": "entity_id", "start_min": "event_time_min"})
        up_expected = downs_g[["machine_id", "end_min"]].rename(columns={"machine_id": "entity_id", "end_min": "event_time_min"})
        down_missing = int(len(pd.merge(down_expected, down_rows, on=["entity_id", "event_time_min"], how="left", indicator=True).query('_merge != "both"')))
        up_missing = int(len(pd.merge(up_expected, up_rows, on=["entity_id", "event_time_min"], how="left", indicator=True).query('_merge != "both"')))
        rows.append(
            {
                "instance_id": instance_id,
                "job_visible_mismatch": visible_mismatch,
                "job_arrival_mismatch": arrival_mismatch,
                "machine_down_missing": down_missing,
                "machine_up_missing": up_missing,
            }
        )
    return pd.DataFrame(rows)


def build_audit_reconciliation(jobs: pd.DataFrame, eligible: pd.DataFrame, due_audit: pd.DataFrame, proc_audit: pd.DataFrame) -> pd.DataFrame:
    due_check = jobs[["instance_id", "job_id", "completion_due_min"]].merge(
        due_audit[["instance_id", "job_id", "completion_due_observed_min"]],
        on=["instance_id", "job_id"],
        how="left",
    )
    due_check["due_matches_audit"] = due_check["completion_due_min"].eq(due_check["completion_due_observed_min"])

    proc_check = eligible[["instance_id", "job_id", "op_seq", "machine_id", "proc_time_min"]].merge(
        proc_audit[["instance_id", "job_id", "op_seq", "machine_id", "proc_time_observed_min"]],
        on=["instance_id", "job_id", "op_seq", "machine_id"],
        how="left",
    )
    proc_check["proc_matches_audit"] = proc_check["proc_time_min"].eq(proc_check["proc_time_observed_min"])

    due_summary = due_check.groupby("instance_id", as_index=False)["due_matches_audit"].mean().rename(columns={"due_matches_audit": "due_match_share"})
    proc_summary = proc_check.groupby("instance_id", as_index=False)["proc_matches_audit"].mean().rename(columns={"proc_matches_audit": "proc_match_share"})
    return due_summary.merge(proc_summary, on="instance_id", how="outer")


def build_regime_order_checks(family_summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for scale_code, group in family_summary.groupby("scale_code"):
        group = group.set_index("regime_code")
        mean_order = (
            group.loc["balanced", "avg_fifo_mean_flow_min"]
            < group.loc["peak", "avg_fifo_mean_flow_min"]
            < group.loc["disrupted", "avg_fifo_mean_flow_min"]
        )
        p95_order = (
            group.loc["balanced", "avg_fifo_p95_flow_min"]
            < group.loc["peak", "avg_fifo_p95_flow_min"]
            < group.loc["disrupted", "avg_fifo_p95_flow_min"]
        )
        rows.append(
            {
                "scale_code": scale_code,
                "mean_flow_order_ok": bool(mean_order),
                "p95_flow_order_ok": bool(p95_order),
            }
        )
    return pd.DataFrame(rows).sort_values("scale_code")


def machine_utilization_frame(schedule: pd.DataFrame, machines: pd.DataFrame, params: pd.DataFrame) -> pd.DataFrame:
    busy = (
        schedule.assign(busy_min=schedule["end_min"] - schedule["start_min"])
        .groupby(["instance_id", "machine_id"], as_index=False)["busy_min"]
        .sum()
    )
    frame = machines.merge(busy, on=["instance_id", "machine_id"], how="left").fillna({"busy_min": 0})
    frame = frame.merge(params[["instance_id", "planning_horizon_min"]], on="instance_id", how="left")
    frame["utilization_share"] = frame["busy_min"] / frame["planning_horizon_min"]
    return frame


def schedule_plot(instance_id: str, schedule: pd.DataFrame, downtimes: pd.DataFrame):
    plot_df = schedule[schedule["instance_id"] == instance_id].copy().sort_values(["machine_id", "start_min", "end_min"])
    downs = downtimes[downtimes["instance_id"] == instance_id].copy()
    machine_order = sorted(plot_df["machine_id"].unique())
    ypos = {machine: idx for idx, machine in enumerate(machine_order)}
    fig, ax = plt.subplots(figsize=(14, max(4, 0.6 * len(machine_order) + 1)))
    palette = dict(zip(STAGE_ORDER, sns.color_palette("Set2", n_colors=len(STAGE_ORDER))))
    for row in plot_df.itertuples(index=False):
        ax.barh(
            ypos[row.machine_id],
            row.end_min - row.start_min,
            left=row.start_min,
            height=0.6,
            color=palette.get(row.stage_name, "#4c78a8"),
            edgecolor="black",
            alpha=0.9,
        )
        ax.text(row.start_min + 0.5, ypos[row.machine_id], f"{row.job_id}:{row.op_seq}", va="center", ha="left", fontsize=8)
    for row in downs.itertuples(index=False):
        ax.barh(
            ypos[row.machine_id],
            row.end_min - row.start_min,
            left=row.start_min,
            height=0.8,
            color="#d62728",
            alpha=0.25,
            edgecolor="none",
        )
    ax.set_yticks(list(ypos.values()))
    ax.set_yticklabels(list(ypos.keys()))
    ax.set_xlabel("Time (min)")
    ax.set_ylabel("Machine")
    ax.set_title(f"FIFO schedule by machine: {instance_id}")
    legend_handles = [plt.Rectangle((0, 0), 1, 1, color=palette[s]) for s in STAGE_ORDER]
    ax.legend(legend_handles, STAGE_ORDER, title="Stage", bbox_to_anchor=(1.02, 1), loc="upper left")
    fig.tight_layout()
    return fig


def load_context(root: Path = REPO_ROOT) -> dict[str, Any]:
    params = load_params_frame(root).sort_values(["scale_code", "regime_code", "replicate"]).reset_index(drop=True)
    catalog = pd.read_csv(root / "catalog" / "benchmark_catalog.csv")
    family_summary = pd.read_csv(root / "catalog" / "instance_family_summary.csv")
    validation_report_observed = pd.read_csv(root / "catalog" / "validation_report_observed.csv")
    observed_noise_manifest = json.loads((root / "catalog" / "observed_noise_manifest.json").read_text(encoding="utf-8"))
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))

    jobs = add_instance_context(load_instance_csv(root, "jobs.csv"), params)
    operations = add_instance_context(load_instance_csv(root, "operations.csv"), params)
    eligible = add_instance_context(load_instance_csv(root, "eligible_machines.csv"), params)
    machines = add_instance_context(load_instance_csv(root, "machines.csv"), params)
    precedences = add_instance_context(load_instance_csv(root, "precedences.csv"), params)
    downtimes = add_instance_context(load_instance_csv(root, "machine_downtimes.csv"), params)
    events = add_instance_context(load_instance_csv(root, "events.csv"), params)
    schedule = add_instance_context(load_instance_csv(root, "fifo_schedule.csv"), params)
    job_metrics = add_instance_context(load_instance_csv(root, "fifo_job_metrics.csv"), params)
    due_audit = add_instance_context(load_instance_csv(root, "job_noise_audit.csv"), params)
    proc_audit = add_instance_context(load_instance_csv(root, "proc_noise_audit.csv"), params)
    congestion = add_instance_context(load_instance_csv(root, "job_congestion_proxy.csv"), params)

    jobs_enriched = compute_due_lower_bounds(jobs, eligible)
    structural_report = build_structural_report(root).merge(params[["instance_id", "scale_code", "regime_code"]], on="instance_id", how="left")
    event_report = event_consistency_frame(jobs, events, downtimes).merge(params[["instance_id", "scale_code", "regime_code"]], on="instance_id", how="left")
    audit_reconciliation = build_audit_reconciliation(jobs, eligible, due_audit, proc_audit).merge(
        params[["instance_id", "scale_code", "regime_code"]], on="instance_id", how="left"
    )
    regime_checks = build_regime_order_checks(family_summary)
    utilization = machine_utilization_frame(schedule, machines, params)
    diagnostics = release_diagnostics(root)

    unload = (
        eligible.merge(
            operations[["instance_id", "job_id", "op_seq", "stage_name"]],
            on=["instance_id", "job_id", "op_seq"],
            how="left",
        )
        .merge(
            jobs[["instance_id", "job_id", "load_tons", "moisture_class", "commodity", "arrival_congestion_score"]],
            on=["instance_id", "job_id"],
            how="left",
        )
    )
    unload = unload[unload["stage_name"] == "UNLOAD"].copy()

    proc_audit_enriched = proc_audit.copy()
    proc_audit_enriched["proc_multiplier"] = proc_audit_enriched["proc_time_observed_min"] / proc_audit_enriched["proc_time_nominal_min"]

    summary = {
        "dataset_version": manifest["dataset_version"],
        "instance_count": int(params["instance_id"].nunique()),
        "job_count": int(len(jobs)),
        "operation_count": int(len(operations)),
        "eligible_rows": int(len(eligible)),
        "machine_rows": int(len(machines)),
        "structural_pass_rate": float((structural_report["status"] == "PASS").mean()),
        "due_audit_match_share": float(audit_reconciliation["due_match_share"].mean()),
        "proc_audit_match_share": float(audit_reconciliation["proc_match_share"].mean()),
        "r2_due_slack_vs_priority": float(diagnostics["r2_due_slack_vs_priority"]),
        "r2_unload_proc_vs_load_machine_moisture": float(diagnostics["r2_unload_proc_vs_load_machine_moisture"]),
        "all_regime_order_checks_pass": bool(regime_checks["mean_flow_order_ok"].all() and regime_checks["p95_flow_order_ok"].all()),
        "g2milp_role": manifest.get("official_dataset_role", ""),
    }

    return {
        "root": root,
        "artifact_dir": ARTIFACT_DIR,
        "params": params,
        "catalog": catalog,
        "family_summary": family_summary,
        "validation_report_observed": validation_report_observed,
        "observed_noise_manifest": observed_noise_manifest,
        "manifest": manifest,
        "jobs": jobs,
        "jobs_enriched": jobs_enriched,
        "operations": operations,
        "eligible": eligible,
        "machines": machines,
        "precedences": precedences,
        "downtimes": downtimes,
        "events": events,
        "schedule": schedule,
        "job_metrics": job_metrics,
        "due_audit": due_audit,
        "proc_audit": proc_audit,
        "proc_audit_enriched": proc_audit_enriched,
        "congestion": congestion,
        "structural_report": structural_report,
        "event_report": event_report,
        "audit_reconciliation": audit_reconciliation,
        "regime_checks": regime_checks,
        "utilization": utilization,
        "diagnostics": diagnostics,
        "unload": unload,
        "summary": summary,
    }


CTX = load_context()

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
    ctx = ctx or CTX
    inventory = pd.DataFrame([ctx["summary"]])
    machine_family = (
        ctx["machines"].groupby(["machine_family"], as_index=False)["machine_id"]
        .count()
        .rename(columns={"machine_id": "machine_rows"})
        .sort_values("machine_rows", ascending=False)
    )
    return {
        "inventory": inventory,
        "catalog": ctx["catalog"].sort_values(["scale_code", "regime_code", "replicate"]),
        "family_summary": ctx["family_summary"].sort_values(["scale_code", "regime_code"]),
        "machine_family": machine_family,
    }


def validation_tables(ctx: dict[str, Any] | None = None) -> dict[str, pd.DataFrame]:
    ctx = ctx or CTX
    due_margin_summary = (
        ctx["jobs_enriched"].groupby(["scale_code", "regime_code"], as_index=False)["due_margin_over_lb_min"]
        .agg(["mean", "min", "median", "max"])
        .round(2)
        .reset_index()
    )
    return {
        "structural_report": ctx["structural_report"].sort_values(["scale_code", "regime_code", "instance_id"]),
        "event_report": ctx["event_report"].sort_values(["scale_code", "regime_code", "instance_id"]),
        "audit_reconciliation": ctx["audit_reconciliation"].sort_values(["scale_code", "regime_code", "instance_id"]),
        "due_margin_summary": due_margin_summary,
    }


def plot_inventory_overview(ctx: dict[str, Any] | None = None, save: bool = False):
    ctx = ctx or CTX
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    jobs_heatmap = ctx["family_summary"].pivot(index="scale_code", columns="regime_code", values="avg_n_jobs").reindex(index=SCALE_ORDER, columns=REGIME_ORDER)
    sns.heatmap(jobs_heatmap, annot=True, fmt=".1f", cmap="YlGnBu", ax=axes[0])
    axes[0].set_title("Jobs average by scale and regime")
    axes[0].set_xlabel("Regime")
    axes[0].set_ylabel("Scale")

    machine_family = inventory_tables(ctx)["machine_family"]
    sns.barplot(data=machine_family, x="machine_family", y="machine_rows", hue="machine_family", dodge=False, legend=False, ax=axes[1], palette="crest")
    axes[1].set_title("Machine rows by family")
    axes[1].tick_params(axis="x", rotation=20)
    fig.tight_layout()
    if save:
        _ensure_artifact_dir(ctx)
        fig.savefig(ctx["artifact_dir"] / "inventory_overview.png", dpi=160, bbox_inches="tight")
    return fig


def plot_validation_overview(ctx: dict[str, Any] | None = None, save: bool = False):
    ctx = ctx or CTX
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    issue_heatmap = ctx["structural_report"].pivot_table(
        index="scale_code",
        columns="regime_code",
        values="issue_count",
        aggfunc="sum",
        fill_value=0,
    ).reindex(index=SCALE_ORDER, columns=REGIME_ORDER)
    sns.heatmap(issue_heatmap, annot=True, fmt=".0f", cmap="Greens_r", ax=axes[0], cbar=False)
    axes[0].set_title("Issue count by scale/regime")

    audit_long = ctx["audit_reconciliation"].melt(
        id_vars=["instance_id", "scale_code", "regime_code"],
        value_vars=["due_match_share", "proc_match_share"],
        var_name="check",
        value_name="match_share",
    )
    sns.boxplot(data=audit_long, x="check", y="match_share", hue="check", dodge=False, legend=False, ax=axes[1], palette="Set2")
    axes[1].set_title("Audit reconciliation")
    axes[1].set_ylim(0.95, 1.01)

    sns.boxplot(data=ctx["jobs_enriched"], x="regime_code", y="due_margin_over_lb_min", order=REGIME_ORDER, hue="regime_code", dodge=False, legend=False, ax=axes[2], palette="flare")
    axes[2].set_title("Due margin over lower bound")
    axes[2].set_xlabel("Regime")
    axes[2].set_ylabel("Margin (min)")

    fig.tight_layout()
    if save:
        _ensure_artifact_dir(ctx)
        fig.savefig(ctx["artifact_dir"] / "structural_validation_and_auditability.png", dpi=160, bbox_inches="tight")
    return fig


def plot_observational_layer(ctx: dict[str, Any] | None = None, save: bool = False):
    ctx = ctx or CTX
    fig, axes = plt.subplots(2, 2, figsize=(18, 12))

    sns.boxplot(data=ctx["jobs_enriched"], x="priority_class", y="due_slack_min", order=["URGENT", "CONTRACTED", "REGULAR"], hue="priority_class", dodge=False, legend=False, ax=axes[0, 0], palette="viridis")
    axes[0, 0].set_title("Observed due slack by priority")

    sns.boxplot(data=ctx["jobs_enriched"], x="appointment_flag", y="reveal_lead_min", hue="appointment_flag", dodge=False, legend=False, ax=axes[0, 1], palette="coolwarm")
    axes[0, 1].set_title("Reveal lead by appointment")

    sns.scatterplot(
        data=ctx["unload"].sample(min(len(ctx["unload"]), 2500), random_state=SEED),
        x="load_tons",
        y="proc_time_min",
        hue="moisture_class",
        style="regime_code",
        alpha=0.45,
        ax=axes[1, 0],
    )
    axes[1, 0].set_title("UNLOAD observed proc time")

    sns.boxplot(data=ctx["proc_audit_enriched"], x="stage_name", y="proc_multiplier", order=STAGE_ORDER, hue="stage_name", dodge=False, legend=False, ax=axes[1, 1], palette="Set3")
    axes[1, 1].set_title("Observed/nominal multiplier by stage")
    axes[1, 1].tick_params(axis="x", rotation=15)

    fig.tight_layout()
    if save:
        _ensure_artifact_dir(ctx)
        fig.savefig(ctx["artifact_dir"] / "observational_layer_behavior.png", dpi=160, bbox_inches="tight")
    return fig


def plot_operational_sanity(ctx: dict[str, Any] | None = None, save: bool = False):
    ctx = ctx or CTX
    fig, axes = plt.subplots(2, 2, figsize=(18, 12))

    mean_heatmap = ctx["family_summary"].pivot(index="scale_code", columns="regime_code", values="avg_fifo_mean_flow_min").reindex(index=SCALE_ORDER, columns=REGIME_ORDER)
    sns.heatmap(mean_heatmap, annot=True, fmt=".1f", cmap="YlOrBr", ax=axes[0, 0])
    axes[0, 0].set_title("FIFO mean flow")

    p95_heatmap = ctx["family_summary"].pivot(index="scale_code", columns="regime_code", values="avg_fifo_p95_flow_min").reindex(index=SCALE_ORDER, columns=REGIME_ORDER)
    sns.heatmap(p95_heatmap, annot=True, fmt=".1f", cmap="YlGnBu", ax=axes[0, 1])
    axes[0, 1].set_title("FIFO p95 flow")

    sns.boxplot(data=ctx["job_metrics"], x="regime_code", y="flow_time_min", order=REGIME_ORDER, hue="regime_code", dodge=False, legend=False, ax=axes[1, 0], palette="Spectral")
    axes[1, 0].set_title("Flow time by regime")

    util_plot = ctx["utilization"].groupby(["machine_family", "regime_code"], as_index=False)["utilization_share"].mean()
    sns.barplot(data=util_plot, x="machine_family", y="utilization_share", hue="regime_code", hue_order=REGIME_ORDER, ax=axes[1, 1], palette="deep")
    axes[1, 1].set_title("Machine utilization by family")
    axes[1, 1].tick_params(axis="x", rotation=20)

    fig.tight_layout()
    if save:
        _ensure_artifact_dir(ctx)
        fig.savefig(ctx["artifact_dir"] / "operational_performance_and_regime_sanity.png", dpi=160, bbox_inches="tight")
    return fig


def plot_instance_drilldown(instance_id: str = "GO_XS_DISRUPTED_01", ctx: dict[str, Any] | None = None, save: bool = False):
    ctx = ctx or CTX
    fig = schedule_plot(instance_id, ctx["schedule"], ctx["downtimes"])
    if save:
        _ensure_artifact_dir(ctx)
        fig.savefig(ctx["artifact_dir"] / f"{instance_id.lower()}_fifo_schedule.png", dpi=160, bbox_inches="tight")
    return fig


def _ensure_artifact_dir(ctx: dict[str, Any]) -> None:
    ctx["artifact_dir"].mkdir(parents=True, exist_ok=True)


def export_all_artifacts(ctx: dict[str, Any] | None = None, instance_id: str = "GO_XS_DISRUPTED_01") -> Path:
    ctx = ctx or CTX
    _ensure_artifact_dir(ctx)
    inventory_tables(ctx)["inventory"].to_csv(ctx["artifact_dir"] / "inventory_summary.csv", index=False)
    validation_tables(ctx)["structural_report"].to_csv(ctx["artifact_dir"] / "structural_report.csv", index=False)
    validation_tables(ctx)["event_report"].to_csv(ctx["artifact_dir"] / "event_report.csv", index=False)
    validation_tables(ctx)["audit_reconciliation"].to_csv(ctx["artifact_dir"] / "audit_reconciliation.csv", index=False)
    validation_tables(ctx)["due_margin_summary"].to_csv(ctx["artifact_dir"] / "due_margin_summary.csv", index=False)
    pd.DataFrame([ctx["summary"]]).to_csv(ctx["artifact_dir"] / "repl_summary.csv", index=False)
    plot_inventory_overview(ctx, save=True)
    plot_validation_overview(ctx, save=True)
    plot_observational_layer(ctx, save=True)
    plot_operational_sanity(ctx, save=True)
    plot_instance_drilldown(instance_id=instance_id, ctx=ctx, save=True)
    return ctx["artifact_dir"]


def repl_help() -> None:
    print("Loaded the observed benchmark into REPL globals.")
    print("")
    print("Quick start:")
    print("  SUMMARY")
    print("  inventory_tables()['inventory']")
    print("  validation_tables()['structural_report'].head()")
    print("  plot_inventory_overview()")
    print("  plot_validation_overview()")
    print("  plot_observational_layer()")
    print("  plot_operational_sanity()")
    print("  plot_instance_drilldown('GO_XS_DISRUPTED_01')")
    print("  export_all_artifacts()")


if __name__ == "__main__":
    print("Observed benchmark REPL loaded.")
    print(json.dumps(SUMMARY, indent=2, ensure_ascii=False))
    print("")
    repl_help()
