#!/usr/bin/env python3
"""
Sprint 3: Pre-Training Privacy Gate Adversarial Testing Suite
Author: Abhisakh Sharma

This script is strictly for testing the pipeline's rejection parameters.
It passes adversarial edge cases to prove the gate catches threats by
measuring them against Guy's benchmark targets.
"""

import sys
import pandas as pd
from pathlib import Path
from sprint3_k_anonymity_gate import run_pre_train_firewall, compute_k_distribution

WORKSPACE_ROOT = Path(__file__).parent.resolve()

# =====================================================================
# TEMPORARY TEST PLOT CONTROLS (EASY TO REMOVE LATER)
# =====================================================================
ENABLE_TEST_PLOTS = True  # Set to False to instantly disable all test plotting

def _generate_temporary_test_plot(case_name: str, raw_df: pd.DataFrame, generalized_df: pd.DataFrame, sanitized_df: pd.DataFrame, k_target: int, output_dir: Path):
    """Generates a diagnostic plot for test datasets to visualize why they get rejected."""
    if not ENABLE_TEST_PLOTS:
        return
    try:
        import matplotlib.pyplot as plt

        total_input_count = len(raw_df)
        final_row_count = len(sanitized_df)
        records_suppressed = int(total_input_count - final_row_count)
        sacrifice_pct = (100.0 * records_suppressed / total_input_count) if total_input_count else 0.0

        fig, axes = plt.subplots(1, 3, figsize=(18, 5), sharey=False)
        fig.suptitle(
            f"Adversarial Test Diagnostic Snapshot: [{case_name.upper()}]\n"
            f"Test Input Size: {total_input_count} rows | Suppressed: {records_suppressed} rows | Sacrifice: {sacrifice_pct:.2f}%",
            fontsize=14, fontweight='bold', y=0.98
        )

        # 1. Native Test Raw State
        raw_df_copy = raw_df.copy()
        raw_df_copy["k_raw"] = compute_k_distribution(raw_df_copy)
        axes[0].hist(raw_df_copy["k_raw"], bins=10, color='orange', alpha=0.6, edgecolor='black')
        axes[0].set_title("1. Raw Test Payload\n(Unbinned Threat Vector)")
        axes[0].set_xlabel("Raw Group Sizes (k)")
        axes[0].set_ylabel("Record Count")
        axes[0].grid(axis='y', alpha=0.3)

        # 2. Test Generalized State
        counts, bins, patches = axes[1].hist(generalized_df["k"], bins=10, color='royalblue', alpha=0.75, edgecolor='black')
        axes[1].axvline(x=k_target, color='crimson', linestyle='--', linewidth=2, label=f"Guy's Target K ({k_target})")
        for patch, left_edge in zip(patches, bins[:-1]):
            if left_edge < k_target:
                patch.set_facecolor('crimson')
        axes[1].set_title("2. Post-Binning Assessment\n(Red Highlights Policy Violations)")
        axes[1].set_xlabel("Binned Group Sizes (k)")
        axes[1].legend(loc="upper right")
        axes[1].grid(axis='y', alpha=0.3)

        # 3. Test Sanitized Output State
        if not sanitized_df.empty:
            axes[2].hist(sanitized_df["k"], bins=10, color='forestgreen', alpha=0.75, edgecolor='black')
        else:
            axes[2].text(0.5, 0.5, "DATASET REJECTED\nZero Compliant Rows Retained", ha='center', va='center', color='crimson', fontweight='bold', fontsize=12)
        axes[2].set_title("3. Output Workspace State\n(Post Threshold Removal)")
        axes[2].set_xlabel("Compliant Group Sizes (k)")
        axes[2].grid(axis='y', alpha=0.3)

        plt.tight_layout(rect=[0, 0, 1, 0.90])
        plot_path = output_dir / f"test_diagnostic_{case_name}.png"
        plt.savefig(plot_path, dpi=150, bbox_inches='tight')

        print(f"[DEBUG][TEST-PLOT] Displaying visual rejection mapping for {case_name.upper()}...")
        plt.show()
        plt.close()
    except Exception as e:
        print(f"[DEBUG][TEST-PLOT] Test plotter skipped: {e}")

# ─────────────────────────────────────────────────────────────────────
# CORE ADVERSARIAL TESTING LOGIC
# ─────────────────────────────────────────────────────────────────────

def test_adversarial_rejections():
    print("\n=======================================================")
    print("[TEST SUITE] Verifying Gate via Guy's Benchmarks")
    print("=======================================================")

    test_dir = WORKSPACE_ROOT / "tmp_test_scenarios"
    test_dir.mkdir(exist_ok=True)

    output_plot_dir = WORKSPACE_ROOT / "analysis"
    output_plot_dir.mkdir(exist_ok=True)

    # ─── THREAT VECTOR A: UNIQUE IDENTITY LEAK ───
    # We plant a highly identifiable outlier row (Age 99, Poverty 12.0)
    leak_dataset = {
        "Age": [35, 35, 35, 35, 99],
        "Sex_male": [1.0, 1.0, 1.0, 1.0, 0.0],
        "Education": [2.0, 2.0, 2.0, 2.0, 4.0],
        "PovertyRatio": [1.5, 1.5, 1.5, 1.5, 12.0],
        "Diabetes": [0, 1, 0, 0, 1]
    }
    leak_path = test_dir / "edge_case_leak.csv"
    df_leak = pd.DataFrame(leak_dataset)
    df_leak.to_csv(leak_path, index=False)

    # Run the gate execution
    res_a = run_pre_train_firewall(profile="equal", raw_data_path=leak_path)

    print(f"[*] Case A (Outlier Leak): Measured Min K={res_a['metrics']['observed_minimum_k']} vs Guy's Target K={res_a['metrics']['calibrated_k_bound']}")
    print(f"    └─ Verdict: {res_a['verdict']} (Reasons: {res_a['reasons']})")

    # Extract temporary mock states to visualize the threat rejection layout
    from sprint3_k_anonymity_gate import apply_numeric_generalization
    gen_df_a = apply_numeric_generalization(df_leak)
    gen_df_a["k"] = compute_k_distribution(gen_df_a)
    san_df_a = gen_df_a[gen_df_a["k"] >= res_a['metrics']['calibrated_k_bound']].reset_index(drop=True)

    # Trigger local pop-up image
    _generate_temporary_test_plot("case_a_leak_threat", df_leak, gen_df_a, san_df_a, res_a['metrics']['calibrated_k_bound'], output_plot_dir)

    # ─── THREAT VECTOR B: DATA STARVATION ───
    # Perfectly anonymous rows, but total volume is too small for DP noise stability
    starved_dataset = {
        "Age": [40, 40, 40],
        "Sex_male": [1.0, 1.0, 1.0],
        "Education": [3.0, 3.0, 3.0],
        "PovertyRatio": [2.0, 2.0, 2.0],
        "Diabetes": [0, 0, 1]
    }
    starved_path = test_dir / "edge_case_starved.csv"
    df_starved = pd.DataFrame(starved_dataset)
    df_starved.to_csv(starved_path, index=False)

    res_b = run_pre_train_firewall(profile="equal", raw_data_path=starved_path)

    print(f"\n[*] Case B (Data Starvation): Count={res_b['metrics']['retained_records_count']} vs Guy's Min Sufficiency={res_b['metrics']['min_rows_for_epsilon_sufficiency']}")
    print(f"    └─ Verdict: {res_b['verdict']} (Reasons: {res_b['reasons']})")

    # Extract temporary mock states to visualize data starvation
    gen_df_b = apply_numeric_generalization(df_starved)
    gen_df_b["k"] = compute_k_distribution(gen_df_b)
    san_df_b = gen_df_b[gen_df_b["k"] >= res_b['metrics']['calibrated_k_bound']].reset_index(drop=True)

    # Trigger local pop-up image
    _generate_temporary_test_plot("case_b_starvation_threat", df_starved, gen_df_b, san_df_b, res_b['metrics']['calibrated_k_bound'], output_plot_dir)

    # Cleanup files
    leak_path.unlink(missing_ok=True)
    starved_path.unlink(missing_ok=True)
    try: test_dir.rmdir()
    except OSError: pass

    if res_a["rejected"] and res_b["rejected"]:
        print("\n[✓] SUCCESS: Adversarial edge cases successfully blocked by Guy's benchmarks.")
        return True
    else:
        print("\n[-] FAILURE: Gate failed to enforce safety limits!")
        return False

if __name__ == "__main__":
    success = test_adversarial_rejections()
    sys.exit(0 if success else 1)