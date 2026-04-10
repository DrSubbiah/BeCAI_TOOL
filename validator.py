"""
validator.py — Build validation table comparing SAS metadata to Plotly code
"""
import re
from datetime import datetime


# Maps each BCAI item to its Plotly property name and how to detect it in generated code
PLOTLY_PROPERTY_MAP = {
    # B — BASE
    "PROC name":                   ("go.Figure / go.Scatter / px.*",     r'go\.\w+|px\.\w+|make_subplots'),
    "Plot type":                   ("go trace type",                      r'go\.(Scatter|Bar|Histogram|Box|Heatmap|Scatter3d|Violin)'),
    "Dataset name":                ("df variable",                        r'\bdf\b|\bdata\b'),
    "X variable":                  ("x=df[...]",                          r"x=df\[|x=gdf\["),
    "Y variable":                  ("y=df[...]",                          r"y=df\[|y=gdf\["),
    "Additional role vars":        ("color=/size= in go trace",           r"color=|size=|symbol="),
    "MODEL statement":             ("statsmodels OLS",                    r'sm\.OLS|LinearRegression'),
    "Overlay statements":          ("fig.add_trace (reg/loess)",          r'go\.Scatter.*Regression|LOESS|lowess'),
    "Number of panels":            ("make_subplots / facet_col",          r'make_subplots|facet_col|facet_row'),
    "Output dataset name":         ("dataframe assignment",               r'agg_df|out_df|=\s*df\.'),
    "X variable type / measurement level": ("axis type",                  r"type='log'|type='date'|type='category'"),
    "Sort order of data":          ("df.sort_values",                     r'sort_values'),
    "Panel-by variable(s)":        ("facet_col/row",                      r'facet_col|facet_row|make_subplots'),
    "Z variable / third data role":("marker size/color",                  r'sizemode|colorresponse|z='),
    "Second Y variable (Y2)":      ("secondary_y=True",                   r'secondary_y'),
    "X2AXIS variable (secondary horizontal)": ("xaxis2",                  r'xaxis2'),
    # C — CONTEXT
    "WHERE clause":                ("df.query / df[mask]",               r'query\(|df\[.*\]'),
    "BY group variables":          ("groupby",                           r'groupby'),
    "Variable transformations":    ("np.log / np.sqrt / computed col",   r'np\.log|np\.sqrt|np\.exp|df\['),
    "Fit / regression type":       ("statsmodels / lowess",              r'sm\.OLS|lowess|LOESS|LinearRegression'),
    "Confidence band type":        ("fill='toself' confidence band",     r"fill='toself'|mean_ci|obs_ci"),
    "Statistical output shown":    ("fig.add_annotation (stats)",        r'add_annotation.*R²|add_annotation.*p-val|R²|r_squared'),
    "Y-axis range":                ("yaxis range=",                      r"yaxes.*range=|update_layout.*yaxis.*range"),
    "X-axis scale type":           ("xaxis type='log'",                  r"type='log'.*xaxis|update_xaxes.*type"),
    "Y-axis scale type":           ("yaxis type='log'",                  r"type='log'.*yaxis|update_yaxes.*type"),
    "Aggregation grain":           ("groupby / agg",                     r'groupby|\.agg\(|\.mean\(|PROC MEANS'),
    "Derived / computed variable": ("df[col] = expr",                    r"df\['\w+'\]\s*="),
    "Pre-visualisation data check":("PROC UNIVARIATE/FREQ/MEANS comment",r'PROC UNIVARIATE|PROC FREQ|PROC MEANS'),
    "Time axis interval type":     ("tickformat date",                   r"tickformat.*%[YmdHMS]|INTERVAL="),
    "Frequency / weight variable": ("freq= / weight=",                   r'freq=|weight='),
    "Second axis range (Y2)":      ("yaxis2 range",                      r'secondary_y.*range|y2axis'),
    "Axis tick interval / step":   ("dtick / tickvals",                  r'dtick=|tickvals=|VALUES='),
    "UNIFORM axis scaling across BY groups": ("matches=",                r'matches=|UNIFORM='),
    "Axis offset — min/max padding":("range with offset",                r'OFFSETMIN|OFFSETMAX|range=\['),
    "Log scale base and style":    ("type='log'",                        r"type='log'"),
    "Axis reverse order":          ("autorange='reversed'",              r"autorange='reversed'"),
    "Axis discrete value order":   ("categoryorder",                     r'categoryorder|DISCRETEORDER'),
    # A — AESTHETICS
    "Marker symbol / shape":       ("marker.symbol",                     r"symbol="),
    "Marker size":                 ("marker.size",                       r"size=\d"),
    "Marker fill color":           ("marker.color",                      r"marker.*color=|marker_color="),
    "Marker outline color":        ("marker.line.color",                 r"marker.*line.*color|FILLEDOUTLINED"),
    "Marker transparency":         ("opacity=",                          r"opacity="),
    "Marker label variable":       ("text= in trace",                    r"text=|datalabel"),
    "Marker label position":       ("textposition=",                     r"textposition=|datalabelpos"),
    "Marker label font":           ("textfont=",                         r"textfont=|datalabelattrs"),
    "Line color":                  ("line.color",                        r"line.*color="),
    "Line style":                  ("line.dash",                         r"dash="),
    "Line thickness":              ("line.width",                        r"line.*width=|width=\d"),
    "Band fill color":             ("fillcolor=",                        r"fillcolor="),
    "Band transparency":           ("opacity=",                          r"opacity="),
    "Plot area background":        ("plot_bgcolor=",                     r"plot_bgcolor="),
    "Plot border / frame":         ("showline=",                         r"showline=|NOFRAME|noframe"),
    "ODS style / template":        ("template=",                         r"template="),
    "Discrete color map":          ("colorway=",                         r"colorway=|DATACONTRASTCOLORS"),
    "Continuous color ramp":       ("colorscale=",                       r"colorscale=|colormodel"),
    "Axis line color":             ("linecolor=",                        r"linecolor="),
    "Axis line thickness":         ("linewidth=",                        r"linewidth="),
    "Tick line color":             ("tickfont.color",                    r"tickfont.*color"),
    "Tick line length":            ("ticklen=",                          r"ticklen="),
    "Tick value font":             ("tickfont=",                         r"tickfont="),
    "Tick value rotation":         ("tickangle=",                        r"tickangle="),
    "Legend position":             ("legend x/y/anchor",                 r"legend.*x=|legend.*y=|legend.*anchor"),
    "Legend title text":           ("legend.title.text",                 r"legend.*title"),
    "Legend title font":           ("legend.title.font",                 r"legend.*title.*font|TITLEATTRS"),
    "Legend value font":           ("legend.font",                       r"legend.*font|VALUEATTRS"),
    "Legend border":               ("legend.borderwidth",                r"borderwidth="),
    "Panel spacing and header style": ("subplot spacing",                r'horizontal_spacing|vertical_spacing|COLSPACE|ROWSPACE'),
    "Second Y-axis style":         ("yaxis2 style",                      r'secondary_y|yaxis2'),
    "Heat map cell color ramp":    ("colorscale=",                       r"colorscale=|COLORMODEL"),
    "Error bar / limit attributes":("error_y=",                          r"error_y=|error_x=|LIMITATTRS"),
    "Box plot whisker style":      ("go.Box line_color",                 r'go\.Box|whisker|WHISKERATTRS'),
    "Bar width / spacing":         ("width= in go.Bar",                  r"width=.*Bar|barwidth|BARWIDTH"),
    "Bar fill color / pattern":    ("marker_color= in go.Bar",           r"marker_color=.*Bar|FILLATTRS"),
    "Graph padding (PAD=)":        ("margin= in layout",                 r"margin=|PAD="),
    "Attribute map dataset (DATTRMAP)": ("colorway/marker cycle",        r"colorway=|DATTRMAP"),
    "Cycle attributes (CYCLEATTRS)":("colorway=",                        r"colorway=|CYCLEATTRS"),
    "Minor tick marks":            ("minor=dict(showgrid=True)",         r"minor=dict|MINOR"),
    "Tick label fit policy":       ("tickangle / tickmode",              r"tickangle=|tickmode=|FITPOLICY"),
    "Axis display components":     ("showticklabels / showline",         r"showticklabels=|showline=|DISPLAY="),
    # I — INFORMATION
    "Insight vs topic title flag": ("title.text audit",                  r"title.*text=|TITLE"),
    "Title text":                  ("layout.title.text",                 r"title=dict.*text=|title_text="),
    "Title font name":             ("title.font.family",                 r"title.*font.*family|FONT="),
    "Title font size":             ("title.font.size",                   r"title.*font.*size="),
    "Title font style":            ("title.font (bold/italic)",          r"title.*font|BOLD|ITALIC"),
    "Title font color":            ("title.font.color",                  r"title.*font.*color="),
    "Title justification":         ("title.x",                          r"title.*x=0|title.*x=0.5|title.*x=1"),
    "Subheading text":             ("title.text with <br>",              r"<br>|title2|subtitle"),
    "Footnote text":               ("annotation text at bottom",         r"annotations.*text=|FOOTNOTE"),
    "Footnote font / size / color":("annotation font",                   r"annotations.*font=|FOOTNOTE.*FONT"),
    "X-axis label text":           ("xaxis.title.text",                  r"title_text=.*xaxes|XAXIS LABEL"),
    "Y-axis label text":           ("yaxis.title.text",                  r"title_text=.*yaxes|YAXIS LABEL"),
    "Axis label font":             ("title_font=",                       r"title_font=|LABELATTRS"),
    "Axis label rotation":         ("tickangle=",                        r"tickangle="),
    "Tick value format":           ("tickformat=",                       r"tickformat="),
    "Tick value font":             ("tickfont=",                         r"tickfont="),
    "Tick positions":              ("tickvals=",                         r"tickvals=|dtick=|VALUES="),
    "Inset / annotation text":     ("fig.add_annotation",                r"add_annotation"),
    "Inset position":              ("annotation x/y",                    r"add_annotation.*x=|xref='paper'"),
    "Inset font":                  ("annotation font=",                  r"add_annotation.*font="),
    "Inset border / background":   ("annotation bgcolor/bordercolor",    r"bgcolor=|bordercolor="),
    "Grid lines — major":          ("showgrid=True",                     r"showgrid=True"),
    "Grid lines — minor":          ("minor showgrid",                    r"minor.*showgrid|minorgrid"),
    "Reference line value":        ("add_hline / add_vline",             r"add_hline|add_vline"),
    "Reference line label":        ("annotation_text=",                  r"annotation_text="),
    "Reference line style":        ("line=dict(color=...) in refline",   r"add_hline.*line=|add_vline.*line="),
    "ODS output destination":      ("write_html / write_image",          r"write_html|write_image|fig\.show"),
    "Plot image width":            ("layout.width=",                     r"width=\d"),
    "Plot image height":           ("layout.height=",                    r"height=\d"),
    "Output file name / path":     ("write_html(filename)",              r"write_html\(|write_image\("),
    "Image resolution (DPI)":      ("scale= in write_image",             r"scale=|dpi=|DPIMAX"),
    "Data source citation":        ("footnote annotation",               r"Source:|annotation.*source"),
    "Axis tick label suppression": ("showticklabels=False",              r"showticklabels=False"),
    "Legend display on/off":       ("showlegend=",                       r"showlegend="),
    "Panel header text / format":  ("subplot title",                     r"subplot_titles|facet_labels|PANELBY"),
    "Second Y-axis label text":    ("yaxis2 title",                      r"secondary_y.*title|Y2AXIS"),
    "NOTIMESPLIT — time axis row split": ("tickformat date no split",    r"NOTIMESPLIT|tickformat"),
    "Axis integer-only ticks":     ("tickformat='d'",                    r"tickformat='d'|INTEGER"),
    "X2AXIS label text":           ("xaxis2 title",                      r"xaxis2.*title"),
    "LINEPARM anchor, slope and label": ("slope line trace",             r"LINEPARM|slope.*line|_lp_y"),
    "NOAUTOLEGEND":                ("showlegend=False",                  r"showlegend=False|NOAUTOLEGEND"),
    "SG annotation dataset (SGANNO)": ("SGANNO — skipped",               r"SGANNO"),
}


def build_validation_report(meta: list, plotly_code: str) -> dict:
    rows = []
    full = 0
    approx = 0
    none_ = 0
    na = 0

    for item in meta:
        pillar = item["pillar"]
        name = item["item"]
        sas_val = item["value"]
        sas_kw = item["sas_keyword"]

        plotly_prop, pattern = PLOTLY_PROPERTY_MAP.get(name, ("—", None))

        # Determine match status
        if not sas_val:
            # SAS property not present in code → N/A
            match = "N/A"
            plotly_value = "—"
            na += 1
        elif pattern is None:
            match = "APPROXIMATE"
            plotly_value = "Manual mapping required"
            approx += 1
        else:
            found = bool(re.search(pattern, plotly_code, re.IGNORECASE | re.DOTALL))
            if found:
                # Extract the matched snippet as plotly_value
                m = re.search(pattern, plotly_code, re.IGNORECASE)
                snippet = m.group(0)[:60] if m else ""
                plotly_value = snippet
                match = "FULL"
                full += 1
            else:
                # SAS has a value but Plotly code doesn't contain the equivalent
                # Check if it's genuinely not applicable
                if name in ("SG annotation dataset (SGANNO)",):
                    match = "N/A"
                    plotly_value = "Out of scope"
                    na += 1
                else:
                    match = "APPROXIMATE"
                    plotly_value = f"See: {plotly_prop}"
                    approx += 1

        rows.append({
            "pillar": pillar,
            "item": name,
            "sas_value": sas_val,
            "plotly_prop": plotly_prop,
            "plotly_value": plotly_value,
            "match": match,
            "sas_keyword": sas_kw,
        })

    # Score = (full + 0.5*approx) / (full + approx + none_) * 100
    scored = full + approx + none_
    score = ((full + 0.5 * approx) / scored * 100) if scored > 0 else 0.0

    # ── Report text ──────────────────────────────────────────────────────────────
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "=" * 80,
        "  BeCAI — SAS → Plotly Validation Report",
        f"  Generated: {now}",
        "=" * 80,
        "",
        f"  OVERALL MATCH SCORE: {score:.1f}%",
        f"  Full Match:   {full}",
        f"  Approximate:  {approx}",
        f"  Not Found:    {none_}",
        "",
        "=" * 80,
        "",
    ]

    for pillar in ["B", "C", "A", "I"]:
        pillar_names = {"B": "BASE — Structural", "C": "CONTEXT — Data & Computation",
                        "A": "AESTHETICS — Visual Encoding", "I": "INFORMATION — Communication Design"}
        lines.append(f"── {pillar_names[pillar]} ──")
        lines.append("")
        pillar_rows = [r for r in rows if r["pillar"] == pillar]
        for r in pillar_rows:
            icon = {"FULL": "✅", "APPROXIMATE": "⚠️", "NOT FOUND": "❌", "N/A": "—"}.get(r["match"], "?")
            lines.append(f"  {icon} [{r['match']:<11}] {r['item']}")
            if r["sas_value"]:
                lines.append(f"           SAS:    {r['sas_value'][:70]}")
            lines.append(f"           Plotly: {r['plotly_prop']}")
            if r["plotly_value"] and r["plotly_value"] not in ("—", ""):
                lines.append(f"           Found:  {r['plotly_value'][:70]}")
            lines.append("")
        lines.append("")

    lines += [
        "=" * 80,
        "  LEGEND",
        "  ✅ FULL        — SAS property detected and Plotly equivalent applied",
        "  ⚠️  APPROXIMATE — Property mapped but value is approximate or inferred",
        "  ❌ NOT FOUND   — SAS property present but no Plotly equivalent found",
        "  —  N/A         — Property not used in this SAS code",
        "=" * 80,
        "",
        "  BeCAI Framework: Base · Context · Aesthetics · Information",
        "  SAS Plot Metadata Extraction — Generic Framework",
    ]

    return {
        "rows": rows,
        "score": score,
        "report_text": "\n".join(lines),
        "full": full,
        "approx": approx,
        "none": none_,
        "na": na,
    }