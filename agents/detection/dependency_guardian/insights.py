"""
Dependency Guardian — AI Risk Insights Formatter and Exporter.
Renders structured executive summaries, consumer impact analysis,
and remediation guidance into text and JSON formats.
"""
from typing import Any, Dict, List, Optional


def format_insights_text(insights: Dict[str, Any], result_summary: Optional[Dict[str, Any]] = None) -> str:
    """Format AI risk insights into a human-readable executive report."""
    lines = [
        "=" * 76,
        " DEPENDENCY GUARDIAN — AI RISK & COMPATIBILITY INSIGHTS REPORT",
        "=" * 76,
        f" Provider: {insights.get('provider', 'ollama').upper()} | Model: {insights.get('model', 'default')}",
        "-" * 76,
        " [1] EXECUTIVE SUMMARY",
        f" {insights.get('executive_summary', 'No executive summary available.')}",
        "",
    ]

    if result_summary:
        lines.extend([
            "-" * 76,
            " [2] QUANTITATIVE BREAKDOWN",
            f" Total Contract Findings: {result_summary.get('total_findings', 0)}",
            f"   - Breaking:             {result_summary.get('breaking_count', 0)}",
            f"   - Potentially Breaking: {result_summary.get('potentially_breaking_count', 0)}",
            f"   - Non-Breaking:         {result_summary.get('non_breaking_count', 0)}",
            f"   - Unknown:              {result_summary.get('unknown_count', 0)}",
            f" Severity: {result_summary.get('by_severity', {})}",
            "",
        ])

    lines.extend([
        "-" * 76,
        " [3] CONSUMER IMPACT ANALYSIS",
        f" {insights.get('consumer_impact_analysis', 'No consumer impact analysis.')}",
        "",
        "-" * 76,
        " [4] TOP BREAKING CONTRACT CHANGES",
    ])

    top_breaking = insights.get("top_breaking_changes", [])
    if top_breaking:
        for item in top_breaking:
            lines.append(f"   * {item}")
    else:
        lines.append("   (None identified)")
    lines.append("")

    lines.extend([
        "-" * 76,
        " [5] RECOMMENDED REMEDIATION & MIGRATION STEPS",
    ])
    fixes = insights.get("recommended_fixes", [])
    if fixes:
        for idx, fix in enumerate(fixes, 1):
            lines.append(f"   {idx}. {fix}")
    else:
        lines.append("   * Update client libraries to align with new contract specification.")
    lines.append("")

    lines.extend([
        "-" * 76,
        " [6] RECOMMENDED REGRESSION TEST SCENARIOS",
    ])
    tests = insights.get("recommended_regression_tests", [])
    if tests:
        for idx, t in enumerate(tests, 1):
            lines.append(f"   {idx}. {t}")
    else:
        lines.append("   * Execute tests with legacy payloads to verify graceful 4xx failure handling.")
    lines.append("")

    lines.extend([
        "-" * 76,
        " [7] SUGGESTED ORDER OF RESOLUTION",
    ])
    order = insights.get("recommended_order_of_resolution", [])
    if order:
        for idx, o in enumerate(order, 1):
            lines.append(f"   Step {idx}: {o}")
    else:
        lines.append("   1. Deprecated/removed endpoints. 2. Required fields. 3. Type modifications.")
    lines.append("")

    lines.extend([
        "-" * 76,
        " [8] GROUNDING: FACTS (FROM CONTRACTS) VS. HYPOTHESES (AI-GENERATED)",
        " Facts Extracted from OpenAPI:",
    ])
    facts = insights.get("facts_extracted_from_openapi", [])
    for f in facts[:8]:
        lines.append(f"   + [FACT] {f}")
    if len(facts) > 8:
        lines.append(f"   ... ({len(facts) - 8} more factual changes)")

    lines.append(" AI-Generated Hypotheses & Interpretations:")
    hypotheses = insights.get("ai_generated_hypotheses", [])
    if hypotheses:
        for h in hypotheses:
            lines.append(f"   ? [HYPOTHESIS] {h}")
    else:
        lines.append("   ? [HYPOTHESIS] Downstream callers lack retry/fallback handling for removed routes.")
    lines.append("")

    lines.extend([
        "-" * 76,
        " [9] ASSUMPTIONS, UNCERTAINTY & LIMITATIONS",
        f" {insights.get('assumptions_and_limitations', 'Analysis bounded by OpenAPI specifications.')}",
        "=" * 76,
    ])

    return "\n".join(lines)
