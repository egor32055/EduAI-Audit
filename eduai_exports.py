"""Export aggregate audit tables with numeric values and stable source column names."""

from io import BytesIO
import json
from zipfile import ZipFile, ZIP_DEFLATED

import pandas as pd


EXPORT_LABELS = {
    "capacity_results": "Review capacities", "marginal_changes": "Additional workload",
    "group_counts": "Group counts", "group_uncertainty": "Group metrics and uncertainty",
    "group_comparisons": "Group comparisons at all shares", "audit_scope": "Data and scope",
}


def export_tables(comparison, report):
    tables = {"capacity_results": comparison["summary"].copy(), "marginal_changes": comparison["marginal_changes"].copy()}
    for target, source in (("group_counts", "group_audit"), ("group_uncertainty", "group_uncertainty"), ("group_comparisons", "group_comparisons")):
        parts = []
        for share, audit in comparison["reports"].items():
            table = audit[source].copy()
            table.insert(0, "review_share_pct", 100 * share)
            parts.append(table)
        tables[target] = pd.concat(parts, ignore_index=True)
    tables["audit_scope"] = report["tables"]["scope"].copy()
    return tables


def table_csv(table):
    return table.to_csv(index=False, lineterminator="\n").encode("utf-8-sig")


def tables_zip(tables, report):
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        for name, table in tables.items():
            archive.writestr(name + ".csv", table_csv(table))
        archive.writestr("manifest.json", json.dumps({
            "application": "EduAI-Audit", "version": 1, "dataset_name": report["dataset_name"],
            "focus_share": report["focus_share"], "encoding": "UTF-8 with BOM", "delimiter": ",",
            "notes": "Aggregate tables across all declared review shares. Numeric values are not display-rounded. Empty numeric cells mean unavailable, not zero. Source codes, status codes and column names are preserved. Intervals are individual exploratory estimates for fixed scores and selections; consult the HTML report for scope, support notes and limitations.",
        }, ensure_ascii=False, indent=2))
    return buffer.getvalue()
