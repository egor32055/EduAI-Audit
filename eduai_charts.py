"""Plots of existing capacity results; no model fitting or audit calculations."""

from html import escape

import altair as alt
import numpy as np
import pandas as pd

from eduai_i18n import tr


SERIES = {
    "counts": [("selected_records", "Selected records"), ("found_positives", "Found cases"),
               ("missed_positives", "Missed cases"), ("false_alarms", "False alarms")],
    "rates": [("recall_pct", "Recall"), ("precision_pct", "Precision"),
              ("false_positive_rate_pct", "False-positive rate")],
}
COLORS = ["#2251A4", "#8C56A2", "#CC7A28", "#367B80"]


def group_chart_data(audit, feature, language="en"):
    """Keep original estimates and suppress unavailable intervals, never replace them by zero."""
    data = audit["group_uncertainty"].loc[lambda frame: frame.group_column.eq(feature)].copy()
    reference = audit["uncertainty_configuration"]["group_references"].get(feature)
    data["point_kind"] = [tr("Group" if reference is None else "Reference group" if str(value) == str(reference) else "Other group", language)
                          for value in data.group_value]
    data["interval_status"] = data.ci_status.map(lambda value: tr(value, language))
    data["support"] = data.support_note.map(lambda value: tr(value, language) if value else tr("No support flag", language))
    available = data.ci_status.eq("Available") & np.isfinite(data.ci_lower_pct) & np.isfinite(data.ci_upper_pct)
    data.loc[~available, ["ci_lower_pct", "ci_upper_pct"]] = np.nan
    return data


def group_chart(audit, feature, metric, language="en"):
    data = group_chart_data(audit, feature, language).loc[lambda frame: frame.metric.eq(metric)]
    label = "Recall" if metric == "recall_pct" else tr("False-positive rate", language)
    groups = data.group_value.astype(str).tolist()
    tooltip = [alt.Tooltip("group_value:N", title=tr("Group", language)),
               alt.Tooltip("estimate_pct:Q", title=label + " (%)", format=".1f"),
               alt.Tooltip("ci_lower_pct:Q", title=tr("Interval lower bound (%)", language), format=".1f"),
               alt.Tooltip("ci_upper_pct:Q", title=tr("Interval upper bound (%)", language), format=".1f"),
               alt.Tooltip("interval_status:N", title=tr("Interval status", language)),
               alt.Tooltip("denominator_records:Q", title=tr("Relevant outcomes", language)),
               alt.Tooltip("denominator_units:Q", title=tr("Contributing students", language)),
               alt.Tooltip("support:N", title=tr("Support note", language))]
    base = alt.Chart(data).encode(y=alt.Y("group_value:N", title=None, scale=alt.Scale(domain=groups)), tooltip=tooltip)
    intervals = base.mark_rule(color="#8899AF", strokeWidth=2).encode(
        x=alt.X("ci_lower_pct:Q", title=label + " (%)", scale=alt.Scale(domain=[0, 100])), x2="ci_upper_pct:Q")
    points = base.mark_point(color=COLORS[0], filled=True, size=85).encode(
        x=alt.X("estimate_pct:Q", title=label + " (%)", scale=alt.Scale(domain=[0, 100])),
        shape=alt.Shape("point_kind:N", title=None, legend=alt.Legend(orient="bottom")
                        if feature in audit["uncertainty_configuration"]["group_references"] else None))
    confidence = 100 * audit["uncertainty_configuration"]["confidence_level"]
    missing = base.transform_filter("!isValid(datum.estimate_pct)").mark_text(align="left", color="#68778C").encode(
        x=alt.value(5), text=alt.value(tr("Metric unavailable", language)))
    return (intervals + points + missing).properties(title=f"{label} · {confidence:g}% CI", height=max(280, 130 + 30 * len(groups)))


def group_charts_html(audit, language="en"):
    """Script-free interval plots for every group feature at the report focus share."""
    parts = []
    for feature in audit["configuration"]["group_columns"]:
        data = group_chart_data(audit, feature, language)
        for metric, name in [("recall_pct", "Recall"), ("false_positive_rate_pct", tr("False-positive rate", language))]:
            rows = data.loc[data.metric.eq(metric)]
            height = 110 + 30 * len(rows)
            confidence = 100 * audit["uncertainty_configuration"]["confidence_level"]
            title = f"{feature} · {name} · {confidence:g}% CI"
            parts += [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 {height}" role="img" aria-label="{escape(title, quote=True)}">',
                      f'<title>{escape(title)}</title><rect width="900" height="{height}" fill="white"/>',
                      f'<text x="15" y="25" font-size="16">{escape(title)}</text>']
            for tick in (0, 25, 50, 75, 100):
                x = 240 + 6 * tick
                parts += [f'<line x1="{x}" x2="{x}" y1="45" y2="{height - 35}" stroke="#dce2ec"/>',
                          f'<text x="{x}" y="{height - 12}" text-anchor="middle" font-size="12">{tick}%</text>']
            for index, (_, row) in enumerate(rows.iterrows()):
                y = 60 + index * 30
                estimate = f"{row.estimate_pct:g}%" if pd.notna(row.estimate_pct) else tr("Metric unavailable", language)
                tip = f"{row.group_value}: {estimate}; {row.interval_status}; {row.support}; {row.point_kind}"
                parts.append(f'<text x="225" y="{y + 4}" text-anchor="end" font-size="12">{escape(str(row.group_value))}<title>{escape(str(row.group_value))}</title></text>')
                if pd.notna(row.ci_lower_pct) and pd.notna(row.ci_upper_pct):
                    parts.append(f'<line x1="{240 + 6 * row.ci_lower_pct:.2f}" x2="{240 + 6 * row.ci_upper_pct:.2f}" y1="{y}" y2="{y}" stroke="#8899AF" stroke-width="2"><title>{escape(tip)}</title></line>')
                if pd.notna(row.estimate_pct):
                    parts.append(f'<circle cx="{240 + 6 * row.estimate_pct:.2f}" cy="{y}" r="5" fill="#2251A4"><title>{escape(tip)}</title></circle>')
                else:
                    parts.append(f'<text x="245" y="{y + 4}" font-size="12" fill="#68778C">{escape(tr("Metric unavailable", language))}<title>{escape(row.interval_status)}</title></text>')
            parts.append('</svg>')
    if not parts:
        return ""
    return '<section><h2>' + escape(tr("Group metrics at the focus share", language)) + '</h2>' + ''.join(parts) + '<p>' + escape(tr("Points show group estimates; lines show available confidence intervals. Unavailable intervals are not drawn. Inspect support notes in the tooltips and tables.", language)) + '</p></section>'


def capacity_chart_data(summary, kind, language="en"):
    return pd.DataFrame([
        dict(share=float(row.review_share_pct), metric=tr(label, language), value=float(row[column]))
        for _, row in summary.iterrows() for column, label in SERIES[kind]
    ])


def capacity_chart(summary, kind, language="en"):
    data = capacity_chart_data(summary, kind, language)
    labels = [tr(label, language) for _, label in SERIES[kind]]
    return alt.Chart(data).mark_line(point=True).encode(
        x=alt.X("share:Q", title=tr("Requested review share (%)", language),
                scale=alt.Scale(zero=False), axis=alt.Axis(values=summary.review_share_pct.tolist())),
        y=alt.Y("value:Q", title=tr("Records" if kind == "counts" else "Rate (%)", language),
                scale=alt.Scale(domain=[0, 100]) if kind == "rates" else alt.Scale(zero=True)),
        color=alt.Color("metric:N", title=tr("Metric", language),
                        scale=alt.Scale(domain=labels, range=COLORS[:len(labels)]),
                        legend=alt.Legend(orient="top")),
        tooltip=[alt.Tooltip("share:Q", title=tr("Requested review share (%)", language)),
                 alt.Tooltip("metric:N", title=tr("Metric", language)),
                 alt.Tooltip("value:Q", title=tr("Records" if kind == "counts" else "Rate (%)", language), format=".1f")],
    ).properties(height=300)


def _svg_chart(summary, kind, language):
    """Standalone SVG counterpart for the downloadable, script-free report."""
    title = tr("Counts across review shares" if kind == "counts" else "Metrics across review shares", language)
    width, height = 900, 360
    left, top, plot_w, plot_h = 75, 45, 790, 220
    shares = summary.review_share_pct.to_list()
    low, high = min(shares), max(shares)
    series = SERIES[kind]
    ceiling = 100 if kind == "rates" else max(1, max(float(summary[c].max()) for c, _ in series))
    x = lambda value: left + plot_w * ((value - low) / (high - low) if high != low else 0.5)
    y = lambda value: top + plot_h * (1 - value / ceiling)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" style="width:100%;height:auto;display:block" role="img" aria-label="{escape(title, quote=True)}">',
             f'<title>{escape(title)}</title>',
             '<rect width="900" height="360" fill="white"/>',
             f'<text x="75" y="22" font-size="16" fill="#13233B">{escape(title)}</text>']
    for step in range(5):
        value = ceiling * step / 4
        parts += [f'<line x1="{left}" y1="{y(value):.2f}" x2="{left + plot_w}" y2="{y(value):.2f}" stroke="#dce2ec"/>',
                  f'<text x="65" y="{y(value) + 4:.2f}" text-anchor="end" font-size="12">{value:g}</text>']
    for share in shares:
        parts.append(f'<text x="{x(share):.2f}" y="285" text-anchor="middle" font-size="12">{share:g}%</text>')
    for index, (column, label) in enumerate(series):
        coordinates = " ".join(f'{x(row.review_share_pct):.2f},{y(row[column]):.2f}' for _, row in summary.iterrows())
        parts.append(f'<polyline points="{coordinates}" fill="none" stroke="{COLORS[index]}" stroke-width="2"/>')
        for _, row in summary.iterrows():
            parts.append(f'<circle cx="{x(row.review_share_pct):.2f}" cy="{y(row[column]):.2f}" r="4" fill="{COLORS[index]}"><title>{row.review_share_pct:g}%: {escape(tr(label, language))} {row[column]:g}</title></circle>')
        legend_x = 75 + (index % 2) * 410
        legend_y = 320 + (index // 2) * 23
        parts += [f'<line x1="{legend_x}" y1="{legend_y - 4}" x2="{legend_x + 22}" y2="{legend_y - 4}" stroke="{COLORS[index]}" stroke-width="3"/>',
                  f'<text x="{legend_x + 30}" y="{legend_y}" font-size="13">{escape(tr(label, language))}</text>']
    parts.append("</svg>")
    return "".join(parts)


def charts_html(summary, language="en"):
    return '<section class="capacity-charts">' + "".join(
        _svg_chart(summary, kind, language) for kind in ("counts", "rates")
    ) + '<p>' + escape(tr("Lines connect observed results at the declared shares. They do not select an optimal capacity. Intervals and support notes are in the tables.", language)) + '</p></section>'
