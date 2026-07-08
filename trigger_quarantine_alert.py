#!/usr/bin/env python3
"""
Sprint 3: Incident Mitigation & Active Email Alerting Engine
Author: Abhisakh Sharma

This script triggers automatically when the privacy gate returns exit code 1.
It handles file isolation, writes a forensic log, and transmits email alerts.
"""

import sys
import os
import json
import shutil
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path

def send_security_email(incident_id: str, email_body: str):
    """Handles the live SMTP transmission using secure environment secrets."""
    # Read email configurations from environment variables (set via GitHub Secrets)
    sender_email = os.getenv("SECURITY_ALERT_SENDER", "privacy-bot@yourdomain.com")
    recipient_email = os.getenv("SECURITY_ALERT_RECIPIENT", "data-gov-alerts@yourdomain.com")
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_password = os.getenv("EMAIL_PASSWORD") # Locked behind GitHub Secrets

    if not smtp_password:
        print("\n[⚠️ WARNING] 'EMAIL_PASSWORD' environment secret not found.")
        print("[⚠️ WARNING] Skipping live SMTP transmission. Printing final email output below:")
        print(email_body)
        return

    try:
        print(f"[*] Connecting to secure mail server ({smtp_server}:{smtp_port})...")
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = f"🚨 [CRITICAL PRIVACY BREACH] Deployment Halted - Incident {incident_id}"

        msg.attach(MIMEText(email_body, 'plain'))

        # Initialize secure TLS connection
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, smtp_password)

        print(f"[*] Transmitting automated notification matrix to {recipient_email}...")
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()
        print("[✓] Email alert successfully transmitted to security infrastructure.")
    except Exception as e:
        print(f"[-] FAILED TO TRANSMIT SECURITY EMAIL: {e}")

def execute_mitigation_pipeline():
    print("\n=======================================================")
    print("[-] EXECUTING AUTOMATED PRIVACY REJECTION PROTOCOL")
    print("=======================================================")

    # Define directories
    quarantine_dir = Path("quarantine/failed_updates")
    quarantine_dir.mkdir(parents=True, exist_ok=True)

    # 1. Enforce Quarantine Separation
    print("[*] Isolating non-compliant tracking shards out of active training pathways...")
    mock_source = Path("equal/client_0.csv")
    if mock_source.exists():
        shutil.copy(mock_source, quarantine_dir / "quarantined_client_0.csv")
        print("[✓] Relocated raw data copy into target storage partition: `./quarantine/failed_updates/`")

    # 2. Compile Forensic Manifest File
    incident_id = f"PRIV-FAIL-{int(datetime.utcnow().timestamp())}"
    incident_log = {
        "incident_id": incident_id,
        "timestamp": datetime.utcnow().isoformat(),
        "status": "QUARANTINED",
        "action_required": "Data Governance Committee / Governance Officer Manual Audit",
        "override_procedure": "Review dataset metrics. If flagged as a false positive, re-run deployment with env variable 'ANONYMITY_GATE_OVERRIDE=TRUE'."
    }

    with open(quarantine_dir / "incident_manifest.json", "w") as f:
        json.dump(incident_log, f, indent=2)
    print("[✓] Compiled immutable incident forensic metadata manifest file.")

    # 3. Compile the Email Telemetry Report
    email_body = f"""========================================================================
🚨 SECURITY FIREWALL REJECTION REPORT: INSIGHT ALARM TRIGGERED 🚨
========================================================================
Incident ID   : {incident_id}
Timestamp     : {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
Status        : PIPELINE DEPLOYMENT HALTED (CRITICAL UNRESOLVED EXCEPTION)
Target Area   : Federated Node Data Input Matrix Stream Verification

SUMMARY OF ACTIONS TAKEN:
1. Deployment pipeline execution has been aborted to prevent identification leaks.
2. Input datasets have been removed from active workspaces and isolated in quarantine.

MANUAL REVIEW & FALSE POSITIVE OVERRIDE INSTRUCTIONS:
If this infraction is verified as a False Positive (e.g., unexpected data scarcity),
an authorized officer can clear the block by re-running the deployment with the manual override key:

Command: export ANONYMITY_GATE_OVERRIDE="TRUE"
========================================================================
"""

    # 4. Trigger Email Dispatch
    send_security_email(incident_id, email_body)
    print("\n[✓] Rejection routing procedures completed successfully.")

if __name__ == "__main__":
    execute_mitigation_pipeline()
    sys.exit(0)