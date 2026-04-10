"""
generator.py — Generate Plotly Python code from BCAI metadata + parsed block
"""
import re


# ── SAS → Plotly mappings ──────────────────────────────────────────────────────

SAS_COLOR_MAP = {
    "red": "red", "blue": "blue", "green": "green", "black": "black",
    "white": "white", "gray": "gray", "grey": "gray", "orange": "orange",
    "yellow": "yellow", "purple": "purple", "pink": "pink", "brown": "brown",
    "cx000000": "black", "cxffffff": "white", "cxff0000": "red",
    "cx0000ff": "blue", "cx00ff00": "green", "cx808080": "gray",
    "navy": "navy", "teal": "teal", "maroon": "maroon", "olive": "olive",
    "lime": "lime", "aqua": "aqua", "fuchsia": "fuchsia",
    "biw": "steelblue", "vigb": "steelblue", "vlig": "lightgreen",
}

SAS_SYMBOL_MAP = {
    "circle": "circle", "circlefilled": "circle", "square": "square",
    "squarefilled": "square", "diamond": "diamond", "diamondfilled": "diamond",
    "triangle": "triangle-up", "trianglefilled": "triangle-up",
    "triangledown": "triangle-down", "triangledownfilled": "triangle-down",
    "star": "star", "starfilled": "star", "plus": "cross", "x": "x",
    "asterisk": "asterisk", "hash": "hash",
}

SAS_LINE_MAP = {
    "solid": "solid", "1": "solid", "dash": "dash", "2": "dash",
    "dot": "dot", "3": "dot", "dashdot": "dashdot", "4": "dashdot",
    "shortdash": "dash", "longdash": "longdashdot", "blank": None,
}

SAS_LEGEND_POS = {
    "bottom": {"yanchor": "bottom", "y": -0.2, "xanchor": "center", "x": 0.5},
    "top":    {"yanchor": "top",    "y": 1.0,  "xanchor": "center", "x": 0.5},
    "left":   {"yanchor": "middle", "y": 0.5,  "xanchor": "left",   "x": -0.15},
    "right":  {"yanchor": "middle", "y": 0.5,  "xanchor": "right",  "x": 1.15},
    "topleft": {"yanchor": "top",   "y": 1.0,  "xanchor": "left",   "x": 0.0},
    "topright":{"yanchor": "top",   "y": 1.0,  "xanchor": "right",  "x": 1.0},
    "bottomleft":{"yanchor":"bottom","y":-0.2, "xanchor": "left",   "x": 0.0},
    "bottomright":{"yanchor":"bottom","y":-0.2,"xanchor": "right",  "x": 1.0},
}


def _color(c):
    if not c: return None
    c = c.strip().lower()
    if c.startswith("cx"):
        return "#" + c[2:]
    return SAS_COLOR_MAP.get(c, c)


def _symbol(s):
    if not s: return None
    return SAS_SYMBOL_MAP.get(s.lower().replace(" ", ""), s.lower())


def _line_dash(p):
    if not p: return None
    return SAS_LINE_MAP.get(p.lower(), "solid")


def _size_to_px(s):
    if not s: return None
    s = str(s)
    m = re.match(r'([\d.]+)\s*(px|pt|pct|%|in|cm)?', s, re.IGNORECASE)
    if m:
        val = float(m.group(1))
        unit = (m.group(2) or "").lower()
        if unit == "pt":  return int(val * 1.333)
        if unit == "in":  return int(val * 96)
        if unit == "cm":  return int(val * 37.8)
        return int(val)
    return None


def _repr(v):
    if v is None: return "None"
    if isinstance(v, str): return repr(v)
    if isinstance(v, dict): return str(v)
    return str(v)


def generate_plotly_code(meta: list, block: dict, parsed: dict) -> str:
    # Build lookup from meta
    m = {item["item"]: item["value"] for item in meta}

    proc = block.get("proc_name", "SGPLOT")
    stmts = block.get("plot_statements", [])
    dataset = block.get("dataset", "df")
    xax = block.get("xaxis", {})
    yax = block.get("yaxis", {})
    y2ax = block.get("y2axis", {})
    x2ax = block.get("x2axis", {})
    leg = block.get("keylegend", {})
    insets = block.get("insets", [])
    reflines = block.get("reflines", [])
    lineparms = block.get("lineparms", [])
    panelby = block.get("panelby", {})
    ods = parsed.get("ods", {})
    titles = parsed.get("titles", {})
    fns = parsed.get("footnotes", {})
    title1 = titles.get("title", titles.get("title1", {}))
    fn1 = fns.get("footnote", fns.get("footnote1", {}))

    lines = []
    a = lines.append

    # ── Imports ─────────────────────────────────────────────────────────────────
    a("import pandas as pd")
    a("import numpy as np")
    a("import plotly.graph_objects as go")
    a("import plotly.express as px")
    a("from plotly.subplots import make_subplots")
    a("")

    # ── Data loading placeholder ────────────────────────────────────────────────
    a(f"# ── Data ──────────────────────────────────────────────────────────────────")
    a(f"# Replace with your actual data loading")
    a(f"# df = pd.read_csv('your_data.csv')  # or pd.read_sas('{dataset}.sas7bdat')")
    a(f"df = {dataset}  # SAS dataset: {dataset}")
    a("")

    # ── Pre-processing from C-layer ──────────────────────────────────────────────
    data_steps = parsed.get("data_steps", [])
    proc_sort = parsed.get("proc_sort", [])
    proc_means = parsed.get("proc_means", [])

    if m.get("WHERE clause"):
        a(f"# ── C-layer: WHERE filter ─────────────────────────────────────────────────")
        a(f"# SAS: WHERE {m['WHERE clause']}")
        a(f"# df = df.query('...')  # Translate SAS WHERE to pandas query")
        a("")

    if proc_sort:
        ps = proc_sort[0]
        by_vars = [v.strip() for v in ps.get("by", "").split() if v.strip()]
        if by_vars:
            asc = not ps.get("descending", False)
            a(f"# ── C-layer: Sort order ─────────────────────────────────────────────────")
            a(f"df = df.sort_values({_repr(by_vars)}, ascending={_repr([asc]*len(by_vars))})")
            a("")

    if m.get("Variable transformations"):
        a(f"# ── C-layer: Variable transformations ───────────────────────────────────")
        for t in m["Variable transformations"].split(";"):
            t = t.strip()
            if t:
                a(f"# SAS: {t}")
                # Attempt Python translation
                py = t.replace("log(", "np.log(").replace("sqrt(", "np.sqrt(").replace("exp(", "np.exp(")
                a(f"# df['{t.split('=')[0].strip()}'] = {py.split('=',1)[-1].strip()}")
        a("")

    if proc_means:
        pm = proc_means[0]
        a(f"# ── C-layer: Aggregation (PROC MEANS → groupby) ─────────────────────────")
        a(f"# SAS: PROC MEANS data={pm.get('data','')} out={pm.get('out','')}")
        if pm.get("class") and pm.get("var"):
            class_vars = pm["class"].split()
            var_vars = pm["var"].split()
            a(f"agg_df = df.groupby({_repr(class_vars)})[{_repr(var_vars)}].mean().reset_index()")
        a("")

    # ── Figure setup ────────────────────────────────────────────────────────────
    has_y2 = bool(y2ax) and any(s.get("y2") for s in stmts)
    has_facets = bool(panelby.get("variable"))

    a(f"# ── Figure ───────────────────────────────────────────────────────────────")
    if has_y2:
        a(f"fig = make_subplots(specs=[[{{\"secondary_y\": True}}]])")
    elif has_facets:
        facet_var = panelby["variable"]
        a(f"# SGPANEL → faceted figure via px")
    else:
        a(f"fig = go.Figure()")
    a("")

    # ── Traces ──────────────────────────────────────────────────────────────────
    a(f"# ── Traces ───────────────────────────────────────────────────────────────")
    for i, stmt in enumerate(stmts):
        stype = stmt.get("type", "scatter")
        x_var = stmt.get("x") or m.get("X variable", "x")
        y_var = stmt.get("y") or m.get("Y variable", "y")
        y2_var = stmt.get("y2", "")
        group = stmt.get("group", "")

        mc = _color(stmt.get("marker_color"))
        ms = _symbol(stmt.get("marker_symbol"))
        msize = _size_to_px(stmt.get("marker_size")) or 8
        transp = stmt.get("transparency", "")
        opacity = round(1.0 - float(transp), 2) if transp else None

        lc = _color(stmt.get("line_color"))
        ld = _line_dash(stmt.get("line_pattern"))
        lt = _size_to_px(stmt.get("line_thickness")) or 2

        if stype == "scatter":
            a(f"# B-layer: Scatter plot")
            if group:
                a(f"for grp, gdf in df.groupby('{group}'):")
                a(f"    fig.add_trace(go.Scatter(")
                a(f"        x=gdf['{x_var}'], y=gdf['{y_var}'],")
                a(f"        mode='markers',")
                a(f"        name=str(grp),")
                a(f"        marker=dict(")
                a(f"            symbol={_repr(ms)},")
                a(f"            size={msize},")
                a(f"            {'color='+_repr(mc)+',' if mc else ''}")
                if opacity: a(f"            opacity={opacity},")
                a(f"        ),")
                a(f"    ))")
            else:
                a(f"fig.add_trace(go.Scatter(")
                a(f"    x=df['{x_var}'], y=df['{y_var}'],")
                a(f"    mode='markers',")
                a(f"    name='{y_var}',")
                a(f"    marker=dict(")
                a(f"        symbol={_repr(ms)},")
                a(f"        size={msize},")
                a(f"        {'color='+_repr(mc)+',' if mc else ''}")
                if opacity: a(f"        opacity={opacity},")
                a(f"    ),")
                a(f"))")

        elif stype == "series":
            a(f"# B-layer: Line series")
            if group:
                a(f"for grp, gdf in df.groupby('{group}'):")
                a(f"    fig.add_trace(go.Scatter(")
                a(f"        x=gdf['{x_var}'], y=gdf['{y_var}'],")
                a(f"        mode='lines+markers',")
                a(f"        name=str(grp),")
                a(f"        line=dict(color={_repr(lc)}, dash={_repr(ld)}, width={lt}),")
                a(f"        marker=dict(symbol={_repr(ms)}, size={msize}),")
                a(f"    ))")
            else:
                a(f"fig.add_trace(go.Scatter(")
                a(f"    x=df['{x_var}'], y=df['{y_var}'],")
                a(f"    mode='lines+markers',")
                a(f"    name='{y_var}',")
                a(f"    line=dict(color={_repr(lc)}, dash={_repr(ld)}, width={lt}),")
                a(f"    marker=dict(symbol={_repr(ms)}, size={msize}),")
                a(f"))")

        elif stype == "reg":
            a(f"# C-layer: OLS regression line overlay")
            a(f"import statsmodels.api as sm")
            a(f"_X = sm.add_constant(df['{x_var}'].dropna())")
            a(f"_y = df.loc[_X.index, '{y_var}']")
            a(f"_model = sm.OLS(_y, _X).fit()")
            a(f"_x_range = np.linspace(df['{x_var}'].min(), df['{x_var}'].max(), 200)")
            a(f"_y_pred = _model.params.iloc[0] + _model.params.iloc[1] * _x_range")
            a(f"fig.add_trace(go.Scatter(")
            a(f"    x=_x_range, y=_y_pred,")
            a(f"    mode='lines',")
            a(f"    name='Regression line',")
            a(f"    line=dict(color={_repr(lc or 'blue')}, dash={_repr(ld or 'solid')}, width={lt}),")
            a(f"))")
            if stmt.get("clm") or block.get("clm"):
                a(f"# C-layer: Confidence band (CLM — mean CI)")
                a(f"_pred = _model.get_prediction(sm.add_constant(_x_range))")
                a(f"_ci = _pred.summary_frame(alpha={stmt.get('alpha') or '0.05'})")
                a(f"fig.add_trace(go.Scatter(")
                a(f"    x=np.concatenate([_x_range, _x_range[::-1]]),")
                a(f"    y=np.concatenate([_ci['mean_ci_upper'], _ci['mean_ci_lower'][::-1]]),")
                a(f"    fill='toself', fillcolor='rgba(0,100,255,0.15)',")
                a(f"    line=dict(color='rgba(255,255,255,0)'),")
                a(f"    name='95% Confidence Band (Mean)',")
                a(f"))")
            if stmt.get("cli") or block.get("cli"):
                a(f"# C-layer: Prediction interval (CLI — individual PI)")
                a(f"fig.add_trace(go.Scatter(")
                a(f"    x=np.concatenate([_x_range, _x_range[::-1]]),")
                a(f"    y=np.concatenate([_ci['obs_ci_upper'], _ci['obs_ci_lower'][::-1]]),")
                a(f"    fill='toself', fillcolor='rgba(255,100,0,0.08)',")
                a(f"    line=dict(color='rgba(255,255,255,0)'),")
                a(f"    name='95% Prediction Interval',")
                a(f"))")

        elif stype == "loess":
            a(f"# C-layer: LOESS smoothing")
            a(f"from statsmodels.nonparametric.smoothers_lowess import lowess")
            a(f"_loess = lowess(df['{y_var}'], df['{x_var}'], frac=0.3)")
            a(f"fig.add_trace(go.Scatter(")
            a(f"    x=_loess[:, 0], y=_loess[:, 1],")
            a(f"    mode='lines',")
            a(f"    name='LOESS',")
            a(f"    line=dict(color={_repr(lc or 'red')}, dash={_repr(ld or 'solid')}, width={lt}),")
            a(f"))")

        elif stype == "histogram":
            a(f"# B-layer: Histogram")
            a(f"fig.add_trace(go.Histogram(")
            a(f"    x=df['{x_var}'],")
            a(f"    name='{x_var}',")
            a(f"    marker_color={_repr(mc or 'steelblue')},")
            if opacity: a(f"    opacity={opacity},")
            a(f"))")

        elif stype in ("vbar", "hbar"):
            a(f"# B-layer: {'Vertical' if stype=='vbar' else 'Horizontal'} bar chart")
            orientation = "'v'" if stype == "vbar" else "'h'"
            bw = stmt.get("barwidth")
            a(f"fig.add_trace(go.Bar(")
            a(f"    {'x' if stype=='vbar' else 'y'}=df['{x_var}'],")
            a(f"    {'y' if stype=='vbar' else 'x'}=df['{y_var}'],")
            a(f"    name='{y_var}',")
            a(f"    orientation={orientation},")
            if mc: a(f"    marker_color={_repr(mc)},")
            if bw: a(f"    width={float(bw) if bw else 0.7},")
            if stmt.get("groupdisplay", "").upper() == "CLUSTER":
                a(f"    barmode='group',  # GROUPDISPLAY=CLUSTER")
            a(f"))")

        elif stype in ("vbox", "hbox"):
            a(f"# B-layer: Box plot")
            orientation = "'v'" if stype == "vbox" else "'h'"
            a(f"fig.add_trace(go.Box(")
            a(f"    {'y' if stype=='vbox' else 'x'}=df['{y_var}'],")
            if x_var: a(f"    x=df['{x_var}'],")
            a(f"    name='{y_var}',")
            a(f"    orientation={orientation},")
            if mc: a(f"    marker_color={_repr(mc)},")
            wc = _color(stmt.get("whiskerattrs_color"))
            if wc: a(f"    line_color={_repr(wc)},")
            a(f"    boxpoints='outliers',")
            a(f"))")

        elif stype == "band":
            a(f"# B-layer: Band (confidence / tolerance)")
            upper = stmt.get("y") or "upper"
            lower = stmt.get("x") or "lower"
            fc = _color(stmt.get("fill_color")) or "rgba(100,150,255,0.2)"
            a(f"fig.add_trace(go.Scatter(")
            a(f"    x=pd.concat([df.index, df.index[::-1]]),")
            a(f"    y=pd.concat([df['{upper}'], df['{lower}'][::-1]]),")
            a(f"    fill='toself',")
            a(f"    fillcolor={_repr(fc)},")
            a(f"    line=dict(color='rgba(255,255,255,0)'),")
            a(f"    name='Band',")
            a(f"))")

        elif stype == "bubble":
            a(f"# B-layer: Bubble chart")
            size_var = stmt.get("size", "")
            a(f"fig.add_trace(go.Scatter(")
            a(f"    x=df['{x_var}'], y=df['{y_var}'],")
            a(f"    mode='markers',")
            a(f"    name='{y_var}',")
            a(f"    marker=dict(")
            a(f"        size=df['{size_var}'] if '{size_var}' else 10,")
            a(f"        sizemode='area', sizeref=2.*df['{size_var}'].max()/(40.**2) if '{size_var}' else 1,")
            if mc: a(f"        color={_repr(mc)},")
            a(f"    ),")
            a(f"))")

        elif stype == "ellipse":
            a(f"# B-layer: Prediction ellipse (confidence ellipse)")
            a(f"# Generate 95% confidence ellipse via eigenvalues of covariance matrix")
            a(f"_cov = np.cov(df['{x_var}'].dropna(), df['{y_var}'].dropna())")
            a(f"_eigvals, _eigvecs = np.linalg.eigh(_cov)")
            a(f"_order = _eigvals.argsort()[::-1]; _eigvals, _eigvecs = _eigvals[_order], _eigvecs[:, _order]")
            a(f"_theta = np.degrees(np.arctan2(*_eigvecs[:, 0][::-1]))")
            a(f"_w, _h = 2 * np.sqrt(_eigvals * 5.991)  # chi2 95%")
            a(f"_t = np.linspace(0, 2*np.pi, 100)")
            a(f"_cos, _sin = np.cos(np.radians(_theta)), np.sin(np.radians(_theta))")
            a(f"_ex = df['{x_var}'].mean() + _w/2*np.cos(_t)*_cos - _h/2*np.sin(_t)*_sin")
            a(f"_ey = df['{y_var}'].mean() + _w/2*np.cos(_t)*_sin + _h/2*np.sin(_t)*_cos")
            a(f"fig.add_trace(go.Scatter(x=_ex, y=_ey, mode='lines', name='95% Ellipse',")
            a(f"    line=dict(color={_repr(lc or 'gray')}, dash={_repr(ld or 'dash')})))")

        elif stype == "needle":
            a(f"# B-layer: Needle plot")
            a(f"for _, row in df.iterrows():")
            a(f"    fig.add_shape(type='line',")
            a(f"        x0=row['{x_var}'], x1=row['{x_var}'], y0=0, y1=row['{y_var}'],")
            a(f"        line=dict(color={_repr(lc or 'blue')}, width={lt}))")

        elif stype == "highlow":
            a(f"# B-layer: High-low plot")
            a(f"fig.add_trace(go.Scatter(")
            a(f"    x=df['{x_var}'], y=df['{y_var}'],")
            a(f"    error_y=dict(type='data', symmetric=False,")
            a(f"        array=df.get('high', df['{y_var}']),")
            a(f"        arrayminus=df.get('low', df['{y_var}'])),")
            a(f"    mode='markers',")
            a(f"    name='{y_var}',")
            a(f"))")

        elif stype == "density":
            a(f"# B-layer: Density plot (KDE)")
            a(f"from scipy.stats import gaussian_kde")
            a(f"_kde = gaussian_kde(df['{x_var}'].dropna())")
            a(f"_xr = np.linspace(df['{x_var}'].min(), df['{x_var}'].max(), 300)")
            a(f"fig.add_trace(go.Scatter(x=_xr, y=_kde(_xr), mode='lines', name='KDE',")
            a(f"    fill='tozeroy', line=dict(color={_repr(lc or 'steelblue')})))")

        # Datalabel annotation
        if stmt.get("datalabel"):
            dl_var = stmt["datalabel"]
            dlc = _color(stmt.get("datalabelattrs_color"))
            dls = _size_to_px(stmt.get("datalabelattrs_size")) or 12
            a(f"# A-layer: Data labels (DATALABEL={dl_var})")
            a(f"for _, row in df.iterrows():")
            a(f"    fig.add_annotation(x=row['{x_var}'], y=row['{y_var}'],")
            a(f"        text=str(row['{dl_var}']), showarrow=False,")
            a(f"        font=dict(size={dls}{', color='+_repr(dlc) if dlc else ''}),)")
        a("")

    # ── Reference lines ──────────────────────────────────────────────────────────
    if reflines:
        a(f"# I-layer: Reference lines")
        for rl in reflines:
            rc = _color(rl.get("color")) or "gray"
            rd = _line_dash(rl.get("pattern")) or "dash"
            rt = float(rl.get("thickness") or 1)
            axis = (rl.get("axis") or "y").lower()
            val = rl.get("value", "0")
            if axis == "x":
                a(f"fig.add_vline(x={val}, line=dict(color={_repr(rc)}, dash={_repr(rd)}, width={rt}),")
                a(f"    annotation_text={_repr(rl.get('label',''))}, annotation_position='top right')")
            else:
                a(f"fig.add_hline(y={val}, line=dict(color={_repr(rc)}, dash={_repr(rd)}, width={rt}),")
                a(f"    annotation_text={_repr(rl.get('label',''))}, annotation_position='right')")
        a("")

    # ── LINEPARM ─────────────────────────────────────────────────────────────────
    if lineparms:
        a(f"# I-layer: LINEPARM — anchor+slope lines")
        for lp in lineparms:
            lpc = _color(lp.get("color")) or "black"
            lpd = _line_dash(lp.get("pattern")) or "solid"
            a(f"_lp_x = np.array([df.index.min(), df.index.max()]) if hasattr(df.index, 'min') else np.array([0, 1])")
            a(f"_lp_y = {lp.get('y', 0)} + {lp.get('slope', 1)} * _lp_x")
            a(f"fig.add_trace(go.Scatter(x=_lp_x, y=_lp_y, mode='lines',")
            a(f"    name={_repr(lp.get('label','LINEPARM'))},")
            a(f"    line=dict(color={_repr(lpc)}, dash={_repr(lpd)}, width={float(lp.get('thickness') or 1)})))")
        a("")

    # ── Layout ───────────────────────────────────────────────────────────────────
    a(f"# ── Layout ───────────────────────────────────────────────────────────────")
    layout_args = []

    # Title
    if title1 and title1.get("text"):
        title_font = {}
        if title1.get("size"):  title_font["size"] = _size_to_px(title1["size"]) or 16
        if title1.get("color"): title_font["color"] = _color(title1["color"])
        if title1.get("bold"):  title_font["family"] = "Arial Bold"
        just_map = {"left": "left", "center": "center", "right": "right"}
        title_x = {"left": 0.0, "center": 0.5, "right": 1.0}.get((title1.get("justify") or "center").lower(), 0.5)
        layout_args.append(f"    title=dict(\n        text={_repr(title1['text'])},\n        x={title_x},\n        font={title_font or {}},\n    ),")

    # Plot size
    width = _size_to_px(ods.get("width")) or 800
    height = _size_to_px(ods.get("height")) or 600
    layout_args.append(f"    width={width},")
    layout_args.append(f"    height={height},")

    # Plot background
    raw = block.get("raw", "")
    wm = re.search(r'\bwallcolor\s*=\s*(\w+)', raw, re.IGNORECASE)
    if wm:
        wc = _color(wm.group(1))
        layout_args.append(f"    plot_bgcolor={_repr(wc)},")

    # Frame / no frame
    fm = re.search(r'\b(noframe)\b', raw, re.IGNORECASE)
    if fm:
        layout_args.append(f"    # NOFRAME → hide all axis lines below")

    # Legend
    if not leg.get("show", True) or block.get("noautolegend"):
        layout_args.append(f"    showlegend=False,  # NOLEGEND / NOAUTOLEGEND")
    else:
        legend_dict = {"borderwidth": 0 if leg.get("noborder") else 1}
        pos = leg.get("position", "")
        if pos and pos.lower() in SAS_LEGEND_POS:
            legend_dict.update(SAS_LEGEND_POS[pos.lower()])
        if leg.get("title"):
            legend_dict["title"] = {"text": leg["title"]}
        layout_args.append(f"    showlegend=True,")
        layout_args.append(f"    legend={legend_dict},")

    # Footnote as annotation
    if fn1 and fn1.get("text"):
        fn_color = _color(fn1.get("color")) or "gray"
        fn_size = _size_to_px(fn1.get("size")) or 10
        layout_args.append(f"    annotations=[dict(")
        layout_args.append(f"        text={_repr(fn1['text'])},")
        layout_args.append(f"        xref='paper', yref='paper', x=0, y=-0.12,")
        layout_args.append(f"        showarrow=False, font=dict(size={fn_size}, color={_repr(fn_color)}),")
        layout_args.append(f"    )],")

    a("fig.update_layout(")
    for la in layout_args:
        a(f"    {la.strip()}")
    a(")")
    a("")

    # ── X-axis ───────────────────────────────────────────────────────────────────
    def axis_update_args(ax, axis_name):
        if not ax:
            return
        args = []
        if ax.get("label"):    args.append(f"title_text={_repr(ax['label'])}")
        if ax.get("type", "").upper() == "LOG":
            args.append("type='log'")
        if ax.get("logbase"):
            base = ax["logbase"]
            if base != "10": args.append(f"# logbase={base} — Plotly log is always base 10; pre-transform data if needed")
        if ax.get("min"):      args.append(f"range=[{ax['min']}, {ax.get('max','None')}]")
        if ax.get("reverse"):  args.append("autorange='reversed'")
        if ax.get("grid"):
            gc = _color(ax.get("gridattrs_color")) or "lightgray"
            args.append(f"showgrid=True, gridcolor={_repr(gc)}")
        else:
            args.append("showgrid=False")
        if ax.get("minorgrid"): args.append("minor=dict(showgrid=True)")
        if ax.get("color"):    args.append(f"linecolor={_repr(_color(ax['color']))}")
        if ax.get("novalues"): args.append("showticklabels=False")
        if ax.get("noticks"):  args.append("ticks=''")
        if ax.get("integer"):  args.append("tickformat='d'")
        if ax.get("tickvaluerotate"): args.append(f"tickangle={ax['tickvaluerotate']}")
        if ax.get("format"):   args.append(f"tickformat={_repr(ax['format'])}")
        ta_fam = ax.get("tickvalueattrs_family")
        ta_sz  = ax.get("tickvalueattrs_size")
        ta_col = ax.get("tickvalueattrs_color")
        if ta_fam or ta_sz or ta_col:
            tf = {}
            if ta_fam: tf["family"] = ta_fam
            if ta_sz:  tf["size"] = _size_to_px(ta_sz)
            if ta_col: tf["color"] = _color(ta_col)
            args.append(f"tickfont={tf}")
        la_fam = ax.get("labelattrs_family")
        la_sz  = ax.get("labelattrs_size")
        la_col = ax.get("labelattrs_color")
        if la_fam or la_sz or la_col:
            lf = {}
            if la_fam: lf["family"] = la_fam
            if la_sz:  lf["size"] = _size_to_px(la_sz)
            if la_col: lf["color"] = _color(la_col)
            args.append(f"title_font={lf}")
        if ax.get("minor"):    args.append("minor=dict(ticks='outside', showgrid=False)")
        if ax.get("offsetmin") or ax.get("offsetmax"):
            args.append(f"# OFFSETMIN={ax.get('offsetmin','')} OFFSETMAX={ax.get('offsetmax','')} → not directly in Plotly; adjust range manually")
        if args:
            a(f"fig.update_{axis_name}(")
            for arg in args:
                a(f"    {arg},")
            a(")")
            a("")

    a(f"# ── Axes ─────────────────────────────────────────────────────────────────")
    axis_update_args(xax, "xaxes")
    axis_update_args(yax, "yaxes")
    if y2ax:
        a("# A-layer: Second Y-axis (Y2AXIS)")
        axis_update_args(y2ax, "yaxes(secondary_y=True)")
    if x2ax:
        a("# B-layer: Secondary X-axis (X2AXIS)")
        a(f"fig.update_layout(xaxis2=dict(")
        if x2ax.get("label"): a(f"    title_text={_repr(x2ax['label'])},")
        a(f"    overlaying='x', side='top',")
        a(f"))")
        a("")

    # ── Insets (annotations) ─────────────────────────────────────────────────────
    if insets:
        a(f"# I-layer: Inset annotations")
        pos_map = {
            "topleft": (0.02, 0.98, "left", "top"),
            "topright": (0.98, 0.98, "right", "top"),
            "bottomleft": (0.02, 0.02, "left", "bottom"),
            "bottomright": (0.98, 0.02, "right", "bottom"),
        }
        for ins in insets:
            px_coord, py_coord, xanchor, yanchor = pos_map.get((ins.get("position") or "topright").lower(), (0.98, 0.98, "right", "top"))
            if ins.get("x"): px_coord = float(ins["x"])
            if ins.get("y"): py_coord = float(ins["y"])
            ifc = _color(ins.get("font_color")) or "black"
            ifs = _size_to_px(ins.get("font_size")) or 12
            bgcolor = _color(ins.get("background")) or "rgba(255,255,255,0.8)"
            a(f"fig.add_annotation(")
            a(f"    xref='paper', yref='paper',")
            a(f"    x={px_coord}, y={py_coord},")
            a(f"    text={_repr(ins.get('text', ''))},")
            a(f"    showarrow=False,")
            a(f"    xanchor={_repr(xanchor)}, yanchor={_repr(yanchor)},")
            a(f"    font=dict(size={ifs}, color={_repr(ifc)}),")
            a(f"    bgcolor={_repr(bgcolor)},")
            a(f"    bordercolor={'black' if ins.get('border') else repr('rgba(0,0,0,0)')},")
            a(f"    borderwidth={'1' if ins.get('border') else '0'},")
            a(f")")
        a("")

    # ── Output ───────────────────────────────────────────────────────────────────
    a(f"# ── Output ───────────────────────────────────────────────────────────────")
    dest = ods.get("destination", "HTML").upper()
    fname = ods.get("file") or ods.get("imagename") or "bcai_chart"
    if not fname.endswith((".html", ".pdf", ".png", ".svg")):
        fname += ".html"

    if dest in ("HTML", ""):
        a(f"fig.write_html({_repr(fname)})")
        a(f"# fig.show()  # uncomment to display in browser")
    elif dest == "PDF":
        a(f"fig.write_image({_repr(fname.replace('.html','.pdf'))})  # requires kaleido: pip install kaleido")
    elif dest in ("PNG", "JPEG", "SVG"):
        ext = dest.lower()
        a(f"fig.write_image({_repr(fname.replace('.html', '.'+ext))})  # requires kaleido")
    else:
        a(f"fig.write_html({_repr(fname)})")
        a(f"fig.show()")

    return "\n".join(lines)