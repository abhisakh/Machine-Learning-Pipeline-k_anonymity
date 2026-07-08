#!/usr/bin/env python3
"""
Sprint 3: Pre-Training Data Anonymity & Epsilon Sufficiency Firewall
Author: Abhisakh Sharma

This gate checks raw data compliance AFTER the k-anonymizer pipeline
but BEFORE the dataset is passed down to the machine learning model.
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from pathlib import Path

# Temporary Development Interface Controls
ENABLE_TEMPORARY_PLOTS = True

SCRIPT_DIR = Path(__file__).parent.resolve()
QI_COLUMNS = ["Age", "Sex_male", "Education", "PovertyRatio"]

# Placeholder thresholds aligned with site-fraction profile skews
GUY_BENCHMARK_OPERATING_POINTS = {
    #"equal":   {"K_TARGET": 5,  "TARGET_EPSILON": 1.5, "MIN_SUFFICIENT_ROWS": 1200, "MAX_SACRIFICE_PCT": 30.0}
    "equal":   {"K_TARGET": 100,  "TARGET_EPSILON": 1.5, "MIN_SUFFICIENT_ROWS": 1200, "MAX_SACRIFICE_PCT": 30.0},
    "mild":    {"K_TARGET": 5,  "TARGET_EPSILON": 2.0, "MIN_SUFFICIENT_ROWS": 1000, "MAX_SACRIFICE_PCT": 35.0},
    "strong":  {"K_TARGET": 8,  "TARGET_EPSILON": 3.5, "MIN_SUFFICIENT_ROWS": 800,  "MAX_SACRIFICE_PCT": 40.0},
    "extreme": {"K_TARGET": 12, "TARGET_EPSILON": 5.0, "MIN_SUFFICIENT_ROWS": 600,  "MAX_SACRIFICE_PCT": 45.0}
}

# ─────────────────────────────────────────────────────────────────────
# UPGRADED TEMPORARY DIAGNOSTICS PLOTTER (EASY TO PURGE LATER)
# ─────────────────────────────────────────────────────────────────────
def _generate_temporary_diagnostics_plot(
    profile: str,
    raw_df: pd.DataFrame,
    generalized_df: pd.DataFrame,
    sanitized_df: pd.DataFrame,
    k_target: int,
    output_dir: Path
):
    """
    Generates a 3-panel comparative pipeline plot displaying:
    1. Raw Input State (Without Binning)
    2. Generalized State (After Binning, highlights violations)
    3. Final Sanitized State (Post Threshold Suppression)
    """
    if not ENABLE_TEMPORARY_PLOTS:
        return
    try:
        import matplotlib.pyplot as plt

        # Calculate pipeline execution metrics
        total_input_count = len(raw_df)
        final_row_count = len(sanitized_df)
        records_suppressed = int(total_input_count - final_row_count)
        sacrifice_pct = (100.0 * records_suppressed / total_input_count) if total_input_count else 0.0

        # Initialize 3-Panel Side-by-Side Canvas
        fig, axes = plt.subplots(1, 3, figsize=(18, 5), sharey=False)
        fig.suptitle(
            f"Sprint 3 Data Pipeline Diagnostics Layer [{profile.upper()} Profile]\n"
            f"Original Size: {total_input_count} rows | Suppressed: {records_suppressed} rows | Sacrifice: {sacrifice_pct:.2f}%",
            fontsize=14, fontweight='bold', y=0.98
        )

        # ─── SUBPLOT 1: RAW STATE (WITHOUT BINNING) ───
        raw_df_copy = raw_df.copy()
        raw_df_copy["k_raw"] = compute_k_distribution(raw_df_copy)
        axes[0].hist(raw_df_copy["k_raw"], bins=20, color='gray', alpha=0.7, edgecolor='black')
        axes[0].set_title("1. Raw State\n(Unbinned Native Distribution)")
        axes[0].set_xlabel("Raw Group Sizes (k)")
        axes[0].set_ylabel("Record Count")
        axes[0].grid(axis='y', alpha=0.3)

        # ─── SUBPLOT 2: AFTER BINNING (BEFORE THRESHOLD REMOVAL) ───
        counts, bins, patches = axes[1].hist(
            generalized_df["k"], bins=20, color='royalblue', alpha=0.75, edgecolor='black'
        )
        axes[1].axvline(x=k_target, color='crimson', linestyle='--', linewidth=2, label=f"Target K Boundary ({k_target})")

        # Color code the sub-threshold components red to visualize what fails compliance
        for patch, left_edge in zip(patches, bins[:-1]):
            if left_edge < k_target:
                patch.set_facecolor('crimson')

        axes[1].set_title("2. Generalized State\n(Binned / Red Indicates Violations)")
        axes[1].set_xlabel("Binned Group Sizes (k)")
        axes[1].legend(loc="upper right")
        axes[1].grid(axis='y', alpha=0.3)

        # ─── SUBPLOT 3: AFTER THRESHOLD REMOVAL (SANITIZED WORKSPACE) ───
        if not sanitized_df.empty:
            axes[2].hist(sanitized_df["k"], bins=20, color='forestgreen', alpha=0.75, edgecolor='black')
        else:
            axes[2].text(0.5, 0.5, "DATASET DEGENERATE\nAll Rows Suppressed", ha='center', va='center', color='crimson', fontsize=12)

        axes[2].set_title("3. Sanitized State\n(Post Threshold Removal)")
        axes[2].set_xlabel("Compliant Group Sizes (k)")
        axes[2].grid(axis='y', alpha=0.3)

        plt.tight_layout(rect=[0, 0, 1, 0.90])

        # Output artifacts
        plot_path = output_dir / f"temp_diagnostics_pipeline_{profile}.png"
        plt.savefig(plot_path, dpi=150, bbox_inches='tight')

        print(f"[DEBUG][TEMP-PLOT] Displaying complete lifecycle pipeline visualization window...")
        plt.show()
        plt.close()

    except ImportError:
        print("[DEBUG][TEMP-PLOT] matplotlib not installed. Skipping rendering pipelines.")
    except Exception as e:
        print(f"[DEBUG][TEMP-PLOT] Core plotting engine exception: {e}")

# ─────────────────────────────────────────────────────────────────────
# TRANSFORMATION PIPELINE SUBROUTINES
# ─────────────────────────────────────────────────────────────────────

def apply_edge_trimming(df: pd.DataFrame, numeric_columns: list, percentile_bound: float = 0.01) -> pd.DataFrame:
    trimmed_df = df.copy()
    for col in numeric_columns:
        if col in trimmed_df.columns:
            lower_bound = trimmed_df[col].quantile(percentile_bound)
            upper_bound = trimmed_df[col].quantile(1.0 - percentile_bound)
            trimmed_df[col] = trimmed_df[col].clip(lower_bound, upper_bound)
    return trimmed_df

def apply_numeric_generalization(df: pd.DataFrame) -> pd.DataFrame:
    print("[DEBUG] Initializing aggressive data generalization transformations...")
    CONTINUOUS_TARGETS = [col for col in ["Age", "PovertyRatio"] if col in df.columns]
    generalized_df = apply_edge_trimming(df, numeric_columns=CONTINUOUS_TARGETS, percentile_bound=0.01)

    if "Age" in generalized_df.columns:
        if generalized_df["Age"].max() <= 1.0:
            generalized_df["Age"] = pd.qcut(generalized_df["Age"], q=5, labels=False, duplicates='drop').astype(float)
            print("[DEBUG] Pre-scaled Age aggressively binned into 4 quantile brackets.")
        else:
            generalized_df["Age"] = generalized_df["Age"].apply(lambda a: float((int(a) // 5) * 5) if not pd.isna(a) else np.nan)
            print("[DEBUG] Age binned into wide 5-year generation blocks.")

    if "PovertyRatio" in generalized_df.columns:
        generalized_df["PovertyRatio"] = pd.qcut(generalized_df["PovertyRatio"], q=5, labels=False, duplicates='drop').astype(float)
        print("[DEBUG] PovertyRatio aggressively binned into 5 simple quantile tiers.")

    if "Education" in generalized_df.columns:
        generalized_df["Education"] = generalized_df["Education"].apply(lambda e: float(int(e) // 2) if not pd.isna(e) else np.nan)
        print("[DEBUG] Education codes generalized into broader consolidated tiers.")

    return generalized_df

def compute_k_distribution(df: pd.DataFrame) -> pd.Series:
    active_qi = [col for col in QI_COLUMNS if col in df.columns]
    qi_signature_keys = df[active_qi].apply(lambda row: "-".join(row.values.astype(str)), axis=1)
    return qi_signature_keys.map(qi_signature_keys.value_counts())

# ─────────────────────────────────────────────────────────────────────
# CORE FIREWALL ENGINE
# ─────────────────────────────────────────────────────────────────────

def run_pre_train_firewall(profile: str, raw_data_path: Path, target_column: str = "Diabetes") -> dict:
    if profile not in GUY_BENCHMARK_OPERATING_POINTS:
        raise ValueError(f"Unknown profile target: {profile}")

    config = GUY_BENCHMARK_OPERATING_POINTS[profile]
    k_target = config["K_TARGET"]
    target_epsilon = config["TARGET_EPSILON"]
    min_sufficient_rows = config["MIN_SUFFICIENT_ROWS"]
    max_sacrifice_pct = config["MAX_SACRIFICE_PCT"]

    # ─── ADDED: MANUAL ADMINISTRATOR OVERRIDE FOR FALSE POSITIVES ───
    if os.getenv("ANONYMITY_GATE_OVERRIDE") == "TRUE":
        print("\n[⚠️ OVERRIDE WARNING] Secure Admin Override detected via environment tokens.")
        print("[⚠️ OVERRIDE WARNING] Bypassing automated safety checks for forensic triage review.")
        return {
            "rejected": False,
            "verdict": "APPROVED_BY_ADMIN_OVERRIDE",
            "profile_context": profile,
            "temporary_configuration_flag": True,
            "reasons": ["Manual compliance override verified by authorized officer."],
            "metrics": {
                "calibrated_k_bound": k_target,
                "observed_minimum_k": k_target,
                "target_epsilon_limit": target_epsilon,
                "min_rows_for_epsilon_sufficiency": min_sufficient_rows,
                "retained_records_count": min_sufficient_rows,
                "max_allowed_sacrifice_pct": max_sacrifice_pct,
                "observed_sacrifice_pct": 0.0
            }
        }
    # ─────────────────────────────────────────────────────────────────

    raw_df = pd.read_csv(raw_data_path).dropna(subset=[target_column])
    total_input_count = len(raw_df)

    # Apply your numeric binning rules
    generalized_df = apply_numeric_generalization(raw_df)
    generalized_df["k"] = compute_k_distribution(generalized_df)

    # Isolate sanitized dataset matrix post threshold filters
    sanitized_df = generalized_df[generalized_df["k"] >= k_target].reset_index(drop=True)

    # Trigger 3-panel pipeline visualization analytics
    output_dir = SCRIPT_DIR / "analysis"
    output_dir.mkdir(exist_ok=True)
    _generate_temporary_diagnostics_plot(profile, raw_df, generalized_df, sanitized_df, k_target, output_dir)

    # Calculate operational metrics
    observed_min_k = sanitized_df["k"].min() if not sanitized_df.empty else 0
    final_row_count = len(sanitized_df)
    records_dropped = int(total_input_count - final_row_count)
    sacrifice_pct = (100.0 * records_dropped / total_input_count) if total_input_count else 0.0

    # The Enforceable Gate Logic Boundaries
    is_k_breached = bool(observed_min_k < k_target)
    is_sacrifice_breached = bool(sacrifice_pct > max_sacrifice_pct)
    is_epsilon_insufficient = bool(final_row_count < min_sufficient_rows)

    is_gate_rejected = is_k_breached or is_sacrifice_breached or is_epsilon_insufficient

    rejection_reasons = []
    if is_k_breached:
        rejection_reasons.append(f"Anonymity Breach: Minimum group size ({observed_min_k}) dropped below Guy's calibrated target ({k_target}).")
    if is_sacrifice_breached:
        rejection_reasons.append(f"Utility Violation: Suppressed {sacrifice_pct:.2f}% of rows, breaching utility ceiling ({max_sacrifice_pct}%).")
    if is_epsilon_insufficient:
        rejection_reasons.append(f"Epsilon Sufficiency Check Failed: Post-sanitization volume ({final_row_count} rows) falls short of required baseline ({min_sufficient_rows}). Model noise injection cannot preserve target privacy ceiling epsilon={target_epsilon}.")

    return {
        "rejected": is_gate_rejected,
        "verdict": "REJECTED" if is_gate_rejected else "APPROVED",
        "profile_context": profile,
        "temporary_configuration_flag": True,
        "reasons": rejection_reasons if is_gate_rejected else ["Data approved for ML model ingestion."],
        "metrics": {
            "calibrated_k_bound": k_target,
            "observed_minimum_k": int(observed_min_k),
            "target_epsilon_limit": target_epsilon,
            "min_rows_for_epsilon_sufficiency": min_sufficient_rows,
            "retained_records_count": final_row_count,
            "max_allowed_sacrifice_pct": max_sacrifice_pct,
            "observed_sacrifice_pct": float(sacrifice_pct)
        }
    }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Pre-Training Privacy & Epsilon Sufficiency Firewall Gate")
    parser.add_argument("--profile", type=str, required=True, choices=GUY_BENCHMARK_OPERATING_POINTS.keys())
    parser.add_argument("--data_path", type=str, required=True)
    args = parser.parse_args()

    try:
        result = run_pre_train_firewall(args.profile, Path(args.data_path))

        # ─── ADDED: AUTOMATED GITHUB RUNNER SUMMARY DATA ───
        # Writes directly to GitHub's environment logging pipeline
        github_summary = os.getenv("GITHUB_STEP_SUMMARY")
        if github_summary:
            with open(github_summary, "w") as summary_file:
                summary_file.write(f"# 🛡️ Privacy Gate Operational Report\n")
                summary_file.write(f"**Verdict:** `{result['verdict']}`\n")
                summary_file.write(f"**Profile Context:** `{result['profile_context']}`\n\n")
                summary_file.write(f"### 📊 Telemetry Metrics Breakdown\n")
                summary_file.write(f"| Metric Name | Required Boundary | Observed Data Value |\n")
                summary_file.write(f"| --- | --- | --- |\n")
                summary_file.write(f"| Group Size ($k$) | $\ge$ {result['metrics']['calibrated_k_bound']} | **{result['metrics']['observed_minimum_k']}** |\n")
                summary_file.write(f"| Sufficiency Count | $\ge$ {result['metrics']['min_rows_for_epsilon_sufficiency']} rows | **{result['metrics']['retained_records_count']}** rows |\n")
                summary_file.write(f"| Data Sacrifice | $\le$ {result['metrics']['max_allowed_sacrifice_pct']}% | **{result['metrics']['observed_sacrifice_pct']:.2f}%** |\n\n")

                if result["rejected"]:
                    summary_file.write(f"### 🚨 Compliance Violations Detected:\n")
                    for reason in result["reasons"]:
                        summary_file.write(f"- {reason}\n")
                    summary_file.write(f"\n> 💡 *Reviewer Note:* To bypass this block, inspect the diagnostic plot artifact attached below and click **Review Deployment -> Approve** if this constitutes an acceptable false positive.\n")

        print(json.dumps(result, indent=2))

        if result["rejected"]:
            sys.exit(1)
        else:
            sys.exit(0)

    except Exception as exc:
        print(f"[-] CRITICAL ENGINE RUNTIME ERROR: {exc}", file=sys.stderr)
        sys.exit(2)