"""SQLite database layer for persisting baselines, observations, scans, changes, repairs, and audit events."""

import sqlite3
import json
import os
from typing import List, Optional, Dict, Any


class Database:
    def __init__(self, db_path: str = "dependency_guardian.db"):
        self.db_path = db_path
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS baselines (
                    id TEXT PRIMARY KEY,
                    dependency_id TEXT,
                    probe_id TEXT,
                    version INTEGER,
                    fingerprint TEXT,
                    raw_response TEXT,
                    created_at TEXT,
                    created_by_action TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS observations (
                    id TEXT PRIMARY KEY,
                    dependency_id TEXT,
                    probe_id TEXT,
                    scan_id TEXT,
                    status_code INTEGER,
                    normalized_fingerprint TEXT,
                    safe_response_snapshot TEXT,
                    latency_ms REAL,
                    observed_at TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scans (
                    id TEXT PRIMARY KEY,
                    status TEXT,
                    services_checked INTEGER,
                    changes_detected INTEGER,
                    started_at TEXT,
                    duration_ms REAL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS changes (
                    id TEXT PRIMARY KEY,
                    scan_id TEXT,
                    dependency_id TEXT,
                    probe_id TEXT,
                    change_type TEXT,
                    severity TEXT,
                    evidence TEXT,
                    status TEXT,
                    created_at TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS impacts (
                    id TEXT PRIMARY KEY,
                    change_id TEXT,
                    workflow_id TEXT,
                    workflow_name TEXT,
                    source_files TEXT,
                    tests TEXT,
                    affected_fields TEXT,
                    reason TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS repairs (
                    id TEXT PRIMARY KEY,
                    change_id TEXT,
                    repair_type TEXT,
                    target_file TEXT,
                    original_code_snippet TEXT,
                    proposed_code_snippet TEXT,
                    diff TEXT,
                    evidence TEXT,
                    assumptions TEXT,
                    confidence REAL,
                    status TEXT,
                    created_at TEXT,
                    error_message TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS validations (
                    id TEXT PRIMARY KEY,
                    repair_id TEXT,
                    command TEXT,
                    exit_code INTEGER,
                    output_summary TEXT,
                    duration_ms REAL,
                    status TEXT,
                    started_at TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_events (
                    id TEXT PRIMARY KEY,
                    actor_action TEXT,
                    target_type TEXT,
                    target_id TEXT,
                    details TEXT,
                    created_at TEXT
                )
            """)
            conn.commit()

    # Baseline methods
    def save_baseline(self, baseline: Dict[str, Any]):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO baselines (
                    id, dependency_id, probe_id, version, fingerprint, raw_response, created_at, created_by_action
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    baseline["id"],
                    baseline["dependency_id"],
                    baseline["probe_id"],
                    baseline["version"],
                    baseline["fingerprint"],
                    json.dumps(baseline["raw_response"]),
                    baseline["created_at"],
                    baseline.get("created_by_action", "manual_baseline"),
                ),
            )
            conn.commit()

    def get_latest_baseline(self, dependency_id: str, probe_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM baselines 
                WHERE dependency_id = ? AND probe_id = ? 
                ORDER BY version DESC LIMIT 1
                """,
                (dependency_id, probe_id),
            )
            row = cursor.fetchone()
            if not row:
                return None
            data = dict(row)
            data["raw_response"] = json.loads(data["raw_response"])
            return data

    def list_baselines(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM baselines ORDER BY created_at DESC")
            rows = cursor.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                item["raw_response"] = json.loads(item["raw_response"])
                results.append(item)
            return results

    # Observation methods
    def save_observation(self, obs: Dict[str, Any]):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO observations (
                    id, dependency_id, probe_id, scan_id, status_code, normalized_fingerprint, safe_response_snapshot, latency_ms, observed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    obs["id"],
                    obs["dependency_id"],
                    obs["probe_id"],
                    obs["scan_id"],
                    obs["status_code"],
                    obs["normalized_fingerprint"],
                    json.dumps(obs.get("safe_response_snapshot")),
                    obs["latency_ms"],
                    obs["observed_at"],
                ),
            )
            conn.commit()

    # Scan methods
    def save_scan(self, scan: Dict[str, Any]):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO scans (
                    id, status, services_checked, changes_detected, started_at, duration_ms
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    scan["scan_id"],
                    scan["status"],
                    scan["services_checked"],
                    scan["changes_detected"],
                    scan["started_at"],
                    scan["duration_ms"],
                ),
            )
            conn.commit()

    def get_scan(self, scan_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scans WHERE id = ?", (scan_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    # Change methods
    def save_change(self, change: Dict[str, Any]):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO changes (
                    id, scan_id, dependency_id, probe_id, change_type, severity, evidence, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    change["id"],
                    change["scan_id"],
                    change["dependency_id"],
                    change["probe_id"],
                    change["change_type"],
                    change["severity"],
                    json.dumps(change["evidence"]),
                    change["status"],
                    change["created_at"],
                ),
            )
            conn.commit()

    def get_change(self, change_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM changes WHERE id = ?", (change_id,))
            row = cursor.fetchone()
            if not row:
                return None
            data = dict(row)
            data["evidence"] = json.loads(data["evidence"])
            return data

    def list_changes(self, scan_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if scan_id:
                cursor.execute("SELECT * FROM changes WHERE scan_id = ? ORDER BY created_at DESC", (scan_id,))
            else:
                cursor.execute("SELECT * FROM changes ORDER BY created_at DESC")
            rows = cursor.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                item["evidence"] = json.loads(item["evidence"])
                results.append(item)
            return results

    # Impact methods
    def save_impact(self, impact: Dict[str, Any]):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO impacts (
                    id, change_id, workflow_id, workflow_name, source_files, tests, affected_fields, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    impact["id"],
                    impact["change_id"],
                    impact["workflow_id"],
                    impact["workflow_name"],
                    json.dumps(impact["source_files"]),
                    json.dumps(impact["tests"]),
                    json.dumps(impact["affected_fields"]),
                    impact["reason"],
                ),
            )
            conn.commit()

    def get_impacts_for_change(self, change_id: str) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM impacts WHERE change_id = ?", (change_id,))
            rows = cursor.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                item["source_files"] = json.loads(item["source_files"])
                item["tests"] = json.loads(item["tests"])
                item["affected_fields"] = json.loads(item["affected_fields"])
                results.append(item)
            return results

    # Repair methods
    def save_repair(self, repair: Dict[str, Any]):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO repairs (
                    id, change_id, repair_type, target_file, original_code_snippet, proposed_code_snippet, diff, evidence, assumptions, confidence, status, created_at, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    repair["id"],
                    repair["change_id"],
                    repair["repair_type"],
                    repair["target_file"],
                    repair["original_code_snippet"],
                    repair["proposed_code_snippet"],
                    repair["diff"],
                    json.dumps(repair["evidence"]),
                    json.dumps(repair["assumptions"]),
                    repair["confidence"],
                    repair["status"],
                    repair["created_at"],
                    repair.get("error_message"),
                ),
            )
            conn.commit()

    def get_repair(self, repair_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM repairs WHERE id = ?", (repair_id,))
            row = cursor.fetchone()
            if not row:
                return None
            data = dict(row)
            data["evidence"] = json.loads(data["evidence"])
            data["assumptions"] = json.loads(data["assumptions"])
            return data

    def list_repairs(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM repairs ORDER BY created_at DESC")
            rows = cursor.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                item["evidence"] = json.loads(item["evidence"])
                item["assumptions"] = json.loads(item["assumptions"])
                results.append(item)
            return results

    def update_repair_status(self, repair_id: str, status: str, error_message: Optional[str] = None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE repairs SET status = ?, error_message = ? WHERE id = ?",
                (status, error_message, repair_id),
            )
            conn.commit()

    # Validation methods
    def save_validation(self, val: Dict[str, Any]):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO validations (
                    id, repair_id, command, exit_code, output_summary, duration_ms, status, started_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    val["id"],
                    val["repair_id"],
                    val["command"],
                    val["exit_code"],
                    val["output_summary"],
                    val["duration_ms"],
                    val["status"],
                    val["started_at"],
                ),
            )
            conn.commit()

    def get_validations_for_repair(self, repair_id: str) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM validations WHERE repair_id = ? ORDER BY started_at DESC", (repair_id,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    # Audit events
    def save_audit_event(self, event: Dict[str, Any]):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO audit_events (
                    id, actor_action, target_type, target_id, details, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event["id"],
                    event["actor_action"],
                    event["target_type"],
                    event["target_id"],
                    json.dumps(event.get("details", {})),
                    event["created_at"],
                ),
            )
            conn.commit()

    def list_audit_events(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM audit_events ORDER BY created_at DESC LIMIT 100")
            rows = cursor.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                item["details"] = json.loads(item["details"])
                results.append(item)
            return results
