"""Plots of existing capacity results; no model fitting or audit calculations."""

from html import escape

import altair as alt
import pandas as pd

from eduai_i18n import tr


SERIES = {
    "counts": [("selected_records", "Selected records"), ("found_positives", "Found cases"),
               ("missed_positives", "Missed cases"), ("false_alarms", "False alarms")],
    "rates": [("recall_pct", "Recall"), ("precision_pct", "Precision"),
              ("false_positive_rate_pct", "False-positive rate")],
}
COLORS = ["#2251A4", "#8C56A2", "#CC7A28", "#367B80"]


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
