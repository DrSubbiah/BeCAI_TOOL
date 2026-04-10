"""
metadata.py — Map parsed SAS structure to all 121 BCAI metadata items
Returns list of dicts: {pillar, item, value, sas_keyword}
"""


def _v(val):
    """Normalize empty/None to empty string."""
    if val is None:
        return ""
    v = str(val).strip()
    return "" if v in ("", "nan", "None", "False") else v


def _bool_v(val, true_str="yes", false_str=""):
    return true_str if val else false_str


def extract_bcai_metadata(parsed: dict) -> list:
    meta = []

    def add(pillar, item, value, sas_keyword=""):
        meta.append({
            "pillar": pillar,
            "item": item,
            "value": _v(value),
            "sas_keyword": sas_keyword,
        })

    blocks = parsed.get("proc_blocks", [])
    block = blocks[0] if blocks else {}
    stmts = block.get("plot_statements", [])
    first_stmt = stmts[0] if stmts else {}
    xax = block.get("xaxis", {})
    yax = block.get("yaxis", {})
    y2ax = block.get("y2axis", {})
    x2ax = block.get("x2axis", {})
    leg = block.get("keylegend", {})
    ods = parsed.get("ods", {})
    titles = parsed.get("titles", {})
    fns = parsed.get("footnotes", {})
    title1 = titles.get("title", titles.get("title1", {}))
    fn1 = fns.get("footnote", fns.get("footnote1", {}))
    insets = block.get("insets", [])
    reflines = block.get("reflines", [])
    lineparms = block.get("lineparms", [])
    panelby = block.get("panelby", {})
    proc_sort = parsed.get("proc_sort", [{}])
    data_steps = parsed.get("data_steps", [])
    sort0 = proc_sort[0] if proc_sort else {}

    # Collect overlay types
    overlay_types = [s["type"] for s in stmts if s["type"] in ("reg", "loess", "ellipse", "band", "refline")]
    all_stmt_types = [s["type"] for s in stmts]

    # ── B — BASE ───────────────────────────────────────────────────────────────
    add("B", "PROC name", block.get("proc_name", ""), "PROC <name>")
    add("B", "Plot type", ", ".join(set(all_stmt_types)) if all_stmt_types else "", "SCATTER / REG / HISTOGRAM etc.")
    add("B", "Dataset name", block.get("dataset", ""), "DATA=")
    add("B", "X variable", first_stmt.get("x", ""), "X=")
    add("B", "Y variable", first_stmt.get("y", ""), "Y=")

    # Additional role vars
    role_parts = []
    for s in stmts:
        if s.get("group"): role_parts.append(f"GROUP={s['group']}")
        if s.get("size"):  role_parts.append(f"SIZE={s['size']}")
        if s.get("colorresponse"): role_parts.append(f"COLORRESPONSE={s['colorresponse']}")
        if s.get("markerchar"):    role_parts.append(f"MARKERCHAR={s['markerchar']}")
    add("B", "Additional role vars", ", ".join(role_parts) if role_parts else "", "GROUP= / SIZE= / COLORRESPONSE= / MARKERCHAR=")

    add("B", "MODEL statement", block.get("model", ""), "MODEL Y = X1 X2 …")
    add("B", "Overlay statements", ", ".join(overlay_types) if overlay_types else "", "REG / LOESS / ELLIPSE / BAND / REFLINE")

    # Number of panels
    panel_count = ""
    if panelby.get("variable"):
        panel_count = f"PANELBY {panelby['variable']}"
    add("B", "Number of panels", panel_count, "PANELBY / SGSCATTER matrix")

    add("B", "Output dataset name", block.get("out", ""), "OUT=")

    # X variable type — infer from proc_freq / proc_univariate usage
    x_var = first_stmt.get("x", "")
    x_type = ""
    if x_var:
        for pf in parsed.get("proc_freq", []):
            if x_var.lower() in pf.get("tables", "").lower():
                x_type = "Categorical"
                break
        if not x_type:
            for pu in parsed.get("proc_univariate", []):
                if x_var.lower() in pu.get("var", "").lower():
                    x_type = "Continuous"
                    break
    add("B", "X variable type / measurement level", x_type, "Inferred from PROC FREQ / PROC UNIVARIATE")

    sort_by = sort0.get("by", "")
    add("B", "Sort order of data", sort_by, "PROC SORT BY=")
    add("B", "Panel-by variable(s)", panelby.get("variable", ""), "PANELBY variable")

    # Z variable
    z_var = ""
    for s in stmts:
        if s.get("colorresponse"): z_var = s["colorresponse"]; break
        if s.get("size"):          z_var = s["size"]; break
    add("B", "Z variable / third data role", z_var, "BUBBLE SIZE= / HEATMAPPARM COLORRESPONSE=")

    # Y2 variable
    y2_var = ""
    for s in stmts:
        if s.get("y2"): y2_var = s["y2"]; break
    add("B", "Second Y variable (Y2)", y2_var, "SERIES Y2= / SCATTER Y2=")

    # X2 variable
    x2_var = ""
    for s in stmts:
        if s.get("x2"): x2_var = s["x2"]; break
    add("B", "X2AXIS variable (secondary horizontal)", x2_var, "SCATTER X2AXIS / SERIES X2AXIS")

    # ── C — CONTEXT ────────────────────────────────────────────────────────────
    add("C", "WHERE clause", block.get("where", "") or parsed.get("global_where", ""), "WHERE")
    add("C", "BY group variables", block.get("by", "") or parsed.get("global_by", ""), "BY")

    # Variable transformations — from DATA steps
    transforms = []
    for ds in data_steps:
        transforms.extend(ds.get("transforms", []))
    add("C", "Variable transformations", "; ".join(transforms) if transforms else "", "DATA step / FORMAT")

    # Fit/regression type
    fit_types = []
    for s in stmts:
        if s["type"] == "reg":   fit_types.append(f"Linear regression{(' degree='+s['degree']) if s.get('degree') else ''}")
        if s["type"] == "loess": fit_types.append(f"LOESS{(' degree='+s['degree']) if s.get('degree') else ''}")
        if s["type"] == "pbspline": fit_types.append("Penalized B-spline")
    add("C", "Fit / regression type", ", ".join(fit_types) if fit_types else "", "REG / LOESS / PBSPLINE / DEGREE=")

    # Confidence band
    band_type = ""
    alpha_val = ""
    for s in stmts:
        if s.get("clm"): band_type = "CLM (mean CI)"
        if s.get("cli"): band_type = "CLI (individual PI)"
        if s.get("alpha"): alpha_val = s["alpha"]
    if block.get("clm"): band_type = "CLM (mean CI)"
    if block.get("cli"): band_type = "CLI (individual PI)"
    add("C", "Confidence band type", f"{band_type} alpha={alpha_val}" if band_type else "", "CLM / CLI / ALPHA=")

    # Statistical output shown
    stat_out = ", ".join([ins["text"] for ins in insets if ins.get("text")]) if insets else ""
    add("C", "Statistical output shown", stat_out, "INSET / STAT=")

    add("C", "Y-axis range", f"min={yax.get('min','')} max={yax.get('max','')}" if (yax.get("min") or yax.get("max")) else "", "YMIN= / YMAX= on YAXIS")
    add("C", "X-axis scale type", xax.get("type", ""), "TYPE=LOG on XAXIS")
    add("C", "Y-axis scale type", yax.get("type", ""), "TYPE=LOG on YAXIS")

    # Aggregation grain
    agg = ""
    if parsed.get("proc_means"):
        pm = parsed["proc_means"][0]
        agg = f"PROC MEANS: data={pm.get('data','')}, out={pm.get('out','')}, var={pm.get('var','')}"
    add("C", "Aggregation grain", agg, "PROC MEANS / PROC SUMMARY OUT=")

    # Derived computed variables
    derived = "; ".join(transforms) if transforms else ""
    add("C", "Derived / computed variable", derived, "DATA step computed columns")

    # Pre-visualisation data check
    pre_checks = []
    if parsed.get("proc_univariate"): pre_checks.append("PROC UNIVARIATE")
    if parsed.get("proc_freq"):       pre_checks.append("PROC FREQ")
    if parsed.get("proc_means"):      pre_checks.append("PROC MEANS")
    add("C", "Pre-visualisation data check", ", ".join(pre_checks) if pre_checks else "", "PROC UNIVARIATE / PROC FREQ / PROC MEANS")

    add("C", "Time axis interval type", xax.get("interval", "") or yax.get("interval", ""), "XAXIS INTERVAL=")

    freq_var = block.get("freq", "") or first_stmt.get("freq", "") or first_stmt.get("weight", "")
    add("C", "Frequency / weight variable", freq_var, "FREQ= / WEIGHT=")

    y2_range = f"min={y2ax.get('min','')} max={y2ax.get('max','')}" if (y2ax.get("min") or y2ax.get("max")) else ""
    add("C", "Second axis range (Y2)", y2_range, "Y2AXIS MIN= MAX=")

    add("C", "Axis tick interval / step", xax.get("values", "") or yax.get("values", ""), "XAXIS VALUES=(start TO end BY step)")
    add("C", "UNIFORM axis scaling across BY groups", block.get("uniform", ""), "PROC SGPLOT UNIFORM=")
    add("C", "Axis offset — min/max padding", f"offsetmin={xax.get('offsetmin','')} offsetmax={xax.get('offsetmax','')}" if (xax.get("offsetmin") or xax.get("offsetmax")) else "", "XAXIS OFFSETMIN= OFFSETMAX=")
    add("C", "Log scale base and style", f"logbase={xax.get('logbase','')} logstyle={xax.get('logstyle','')}" if xax.get("logbase") else "", "XAXIS LOGBASE= LOGSTYLE=")
    add("C", "Axis reverse order", _bool_v(xax.get("reverse") or yax.get("reverse"), "yes"), "XAXIS / YAXIS REVERSE")
    add("C", "Axis discrete value order", xax.get("discreteorder", "") or yax.get("discreteorder", ""), "XAXIS / YAXIS DISCRETEORDER=")

    # ── A — AESTHETICS ─────────────────────────────────────────────────────────
    # Collect from first scatter/series stmt
    scatter_stmt = next((s for s in stmts if s["type"] in ("scatter", "series", "bubble")), first_stmt)

    add("A", "Marker symbol / shape", scatter_stmt.get("marker_symbol", ""), "MARKERATTRS=(SYMBOL=)")
    add("A", "Marker size", scatter_stmt.get("marker_size", ""), "MARKERATTRS=(SIZE=)")
    add("A", "Marker fill color", scatter_stmt.get("marker_color", ""), "MARKERATTRS=(COLOR=)")
    add("A", "Marker outline color", scatter_stmt.get("marker_color", ""), "FILLEDOUTLINEDCIRCLE / MARKERATTRS")
    add("A", "Marker transparency", scatter_stmt.get("transparency", ""), "TRANSPARENCY=")
    add("A", "Marker label variable", scatter_stmt.get("datalabel", ""), "DATALABEL=")
    add("A", "Marker label position", scatter_stmt.get("datalabelpos", ""), "DATALABELPOS=")
    add("A", "Marker label font", f"family={scatter_stmt.get('datalabelattrs_family','')} size={scatter_stmt.get('datalabelattrs_size','')}" if scatter_stmt.get("datalabelattrs_family") or scatter_stmt.get("datalabelattrs_size") else "", "DATALABELATTRS=")

    # Line attrs — from series/reg stmt
    line_stmt = next((s for s in stmts if s["type"] in ("series", "reg", "loess", "step", "band")), first_stmt)
    add("A", "Line color", line_stmt.get("line_color", ""), "LINEATTRS=(COLOR=)")
    add("A", "Line style", line_stmt.get("line_pattern", ""), "LINEATTRS=(PATTERN=)")
    add("A", "Line thickness", line_stmt.get("line_thickness", ""), "LINEATTRS=(THICKNESS=)")

    # Band fill
    band_stmt = next((s for s in stmts if s["type"] == "band"), {})
    add("A", "Band fill color", band_stmt.get("fill_color", ""), "FILLATTRS=(COLOR=)")
    add("A", "Band transparency", band_stmt.get("transparency", ""), "TRANSPARENCY=")

    # Plot area / ODS style
    # Wallcolor from raw block
    import re
    wallcolor = re.search(r'\bwallcolor\s*=\s*(\w+)', block.get("raw", ""), re.IGNORECASE)
    add("A", "Plot area background", wallcolor.group(1) if wallcolor else "", "STYLEATTRS WALLCOLOR=")

    frame = re.search(r'\b(frame|noframe)\b', block.get("raw", ""), re.IGNORECASE)
    add("A", "Plot border / frame", frame.group(1).upper() if frame else "", "FRAME / NOFRAME")
    add("A", "ODS style / template", ods.get("style", ""), "ODS STYLE=")

    # Discrete color map
    dcc = re.search(r'datacontrastcolors\s*=\s*\(([^)]+)\)', block.get("raw", ""), re.IGNORECASE)
    add("A", "Discrete color map", dcc.group(1) if dcc else "", "STYLEATTRS DATACONTRASTCOLORS=")

    # Continuous color ramp — from any stmt
    cm = next((s.get("colormodel") for s in stmts if s.get("colormodel")), "")
    add("A", "Continuous color ramp", cm, "COLORMODEL=")

    add("A", "Axis line color", xax.get("color", "") or yax.get("color", ""), "XAXIS / YAXIS COLOR=")
    add("A", "Axis line thickness", "", "LINEATTRS=(THICKNESS=) on AXIS")
    add("A", "Tick line color", xax.get("tickvalueattrs_color", "") or yax.get("tickvalueattrs_color", ""), "TICKVALUEATTRS=(COLOR=)")
    add("A", "Tick line length", "", "TICKDISPLAY / ODS style")
    add("A", "Tick value font", f"family={xax.get('tickvalueattrs_family','')} size={xax.get('tickvalueattrs_size','')}" if xax.get("tickvalueattrs_family") or xax.get("tickvalueattrs_size") else "", "TICKVALUEATTRS=")
    add("A", "Tick value rotation", xax.get("tickvaluerotate", "") or yax.get("tickvaluerotate", ""), "TICKVALUEROTATE=")

    add("A", "Legend position", leg.get("position", ""), "KEYLEGEND POSITION=")
    add("A", "Legend title text", leg.get("title", ""), "KEYLEGEND TITLE=")
    add("A", "Legend title font", f"family={leg.get('titleattrs_family','')} size={leg.get('titleattrs_size','')}" if leg.get("titleattrs_family") or leg.get("titleattrs_size") else "", "KEYLEGEND TITLEATTRS=")
    add("A", "Legend value font", f"family={leg.get('valueattrs_family','')} size={leg.get('valueattrs_size','')}" if leg.get("valueattrs_family") or leg.get("valueattrs_size") else "", "KEYLEGEND VALUEATTRS=")
    add("A", "Legend border", "NOBORDER" if leg.get("noborder") else "", "NOBORDER / BORDER on KEYLEGEND")

    add("A", "Panel spacing and header style", f"colspace={panelby.get('colspace','')} rowspace={panelby.get('rowspace','')}" if panelby.get("colspace") or panelby.get("rowspace") else "", "PANELBY COLSPACE= ROWSPACE=")
    add("A", "Second Y-axis style", f"color={y2ax.get('color','')} label={y2ax.get('label','')}" if y2ax else "", "Y2AXIS COLOR= / TICKVALUEATTRS=")

    # Heat map cell color ramp
    hm_stmt = next((s for s in stmts if s["type"] == "heatmapparm"), {})
    add("A", "Heat map cell color ramp", hm_stmt.get("colormodel", ""), "HEATMAPPARM COLORRESPONSE= COLORMODEL=")

    # Error bar
    hl_stmt = next((s for s in stmts if s["type"] in ("highlow", "scatter")), {})
    limit_attrs = f"color={hl_stmt.get('limitattrs_color','')} thickness={hl_stmt.get('limitattrs_thickness','')}" if hl_stmt.get("limitattrs_color") or hl_stmt.get("limitattrs_thickness") else ""
    add("A", "Error bar / limit attributes", limit_attrs, "LIMITATTRS=(COLOR= THICKNESS=)")

    # Box plot
    box_stmt = next((s for s in stmts if s["type"] in ("vbox", "hbox")), {})
    whisker = f"color={box_stmt.get('whiskerattrs_color','')}" if box_stmt.get("whiskerattrs_color") else ""
    add("A", "Box plot whisker style", whisker, "VBOX / HBOX WHISKERATTRS=")

    # Bar options
    bar_stmt = next((s for s in stmts if s["type"] in ("vbar", "hbar")), {})
    add("A", "Bar width / spacing", bar_stmt.get("barwidth", ""), "VBAR / HBAR BARWIDTH=")
    add("A", "Bar fill color / pattern", bar_stmt.get("fill_color", ""), "VBAR / HBAR FILLATTRS=(COLOR=)")

    add("A", "Graph padding (PAD=)", block.get("pad", ""), "PROC SGPLOT PAD=")
    add("A", "Attribute map dataset (DATTRMAP)", block.get("dattrmap", ""), "PROC SGPLOT DATTRMAP=")
    add("A", "Cycle attributes (CYCLEATTRS)", _bool_v(block.get("cycleattrs"), "yes"), "PROC SGPLOT CYCLEATTRS")
    add("A", "Minor tick marks", _bool_v(xax.get("minor") or yax.get("minor"), "yes"), "XAXIS / YAXIS MINOR")
    add("A", "Tick label fit policy", xax.get("fitpolicy", "") or yax.get("fitpolicy", ""), "XAXIS FITPOLICY=")
    display_val = xax.get("display", "") or yax.get("display", "")
    add("A", "Axis display components", display_val, "XAXIS / YAXIS DISPLAY=")

    # ── I — INFORMATION ────────────────────────────────────────────────────────
    # Insight vs topic title flag
    t1_text = title1.get("text", "") if title1 else ""
    insight_flag = "Insight title" if (t1_text and any(c in t1_text for c in [":", "shows", "reveals", "indicates", "higher", "lower", "increases", "decreases"])) else ("Topic title" if t1_text else "")
    add("I", "Insight vs topic title flag", insight_flag, "TITLE= text audit")

    add("I", "Title text", t1_text, "TITLE")
    add("I", "Title font name", title1.get("font", "") if title1 else "", "TITLE FONT=")
    add("I", "Title font size", title1.get("size", "") if title1 else "", "TITLE HEIGHT=")
    add("I", "Title font style", ("BOLD " if (title1 or {}).get("bold") else "") + ("ITALIC" if (title1 or {}).get("italic") else ""), "TITLE BOLD / ITALIC")
    add("I", "Title font color", title1.get("color", "") if title1 else "", "TITLE COLOR=")
    add("I", "Title justification", title1.get("justify", "") if title1 else "", "TITLE JUSTIFY=")

    # Subheadings
    subheads = [v.get("text", "") for k, v in titles.items() if k not in ("title", "title1") and v.get("text")]
    add("I", "Subheading text", " | ".join(subheads) if subheads else "", "TITLE2 / TITLE3 …")

    add("I", "Footnote text", fn1.get("text", "") if fn1 else "", "FOOTNOTE")
    add("I", "Footnote font / size / color", f"font={fn1.get('font','')} size={fn1.get('size','')} color={fn1.get('color','')}" if fn1 and any([fn1.get("font"), fn1.get("size"), fn1.get("color")]) else "", "FOOTNOTE FONT= HEIGHT= COLOR=")

    add("I", "X-axis label text", xax.get("label", ""), "XAXIS LABEL=")
    add("I", "Y-axis label text", yax.get("label", ""), "YAXIS LABEL=")
    add("I", "Axis label font", f"family={xax.get('labelattrs_family','')} size={xax.get('labelattrs_size','')} color={xax.get('labelattrs_color','')}" if xax.get("labelattrs_family") or xax.get("labelattrs_size") else "", "XAXIS / YAXIS LABELATTRS=")
    add("I", "Axis label rotation", "", "LABELPOS= / ODS style")
    add("I", "Tick value format", xax.get("format", "") or yax.get("format", ""), "XAXIS / YAXIS VALUES FORMAT=")
    add("I", "Tick value font", f"family={xax.get('tickvalueattrs_family','')} size={xax.get('tickvalueattrs_size','')}" if xax.get("tickvalueattrs_family") or xax.get("tickvalueattrs_size") else "", "TICKVALUEATTRS=")
    add("I", "Tick positions", xax.get("values", "") or yax.get("values", ""), "XAXIS VALUES=(list)")

    ins0 = insets[0] if insets else {}
    add("I", "Inset / annotation text", ins0.get("text", ""), "INSET / ANNOTATE dataset")
    add("I", "Inset position", ins0.get("position", "") or f"x={ins0.get('x','')} y={ins0.get('y','')}" if ins0 else "", "INSET POSITION= / X= Y=")
    add("I", "Inset font", f"family={ins0.get('font_family','')} size={ins0.get('font_size','')} color={ins0.get('font_color','')}" if ins0.get("font_family") or ins0.get("font_size") else "", "INSET TEXTATTRS=")
    add("I", "Inset border / background", f"border={ins0.get('border','')} background={ins0.get('background','')}" if ins0 else "", "INSET BORDER / NOBORDER / BACKGROUND=")

    add("I", "Grid lines — major", _bool_v(xax.get("grid") or yax.get("grid"), f"yes color={xax.get('gridattrs_color','')}"), "XAXIS / YAXIS GRID")
    add("I", "Grid lines — minor", _bool_v(xax.get("minorgrid") or yax.get("minorgrid"), "yes"), "XAXIS / YAXIS MINORGRID")

    rl0 = reflines[0] if reflines else {}
    add("I", "Reference line value", rl0.get("value", ""), "REFLINE value / XREF= / YREF=")
    add("I", "Reference line label", rl0.get("label", ""), "REFLINE LABEL=")
    add("I", "Reference line style", f"color={rl0.get('color','')} pattern={rl0.get('pattern','')} thickness={rl0.get('thickness','')}" if rl0.get("color") or rl0.get("pattern") else "", "REFLINE LINEATTRS=")

    add("I", "ODS output destination", ods.get("destination", ""), "ODS HTML / PDF / RTF")
    add("I", "Plot image width", ods.get("width", ""), "ODS GRAPHICS WIDTH=")
    add("I", "Plot image height", ods.get("height", ""), "ODS GRAPHICS HEIGHT=")
    add("I", "Output file name / path", ods.get("file", "") or ods.get("imagename", ""), "ODS GRAPHICS IMAGENAME= / FILE=")
    add("I", "Image resolution (DPI)", ods.get("dpi", ""), "ODS GRAPHICS IMAGEFMT= DPIMAX=")

    # Data source citation — look in footnotes
    citation = ""
    for k, v in fns.items():
        if "source" in v.get("text", "").lower():
            citation = v["text"]
            break
    add("I", "Data source citation", citation, "FOOTNOTE 'Source: …'")

    add("I", "Axis tick label suppression", _bool_v(xax.get("novalues") or yax.get("novalues"), "yes"), "XAXIS NOVALUES; / YAXIS NOTICKS;")
    add("I", "Legend display on/off", "ON" if leg.get("show", True) else "OFF", "KEYLEGEND / NOLEGEND statement")
    add("I", "Panel header text / format", panelby.get("label", "") or panelby.get("format", ""), "PANELBY LABEL= / HEADERATTRS= / FORMAT=")
    add("I", "Second Y-axis label text", y2ax.get("label", ""), "Y2AXIS LABEL=")
    add("I", "NOTIMESPLIT — time axis row split", _bool_v(xax.get("notimesplit") or yax.get("notimesplit"), "yes"), "XAXIS / YAXIS NOTIMESPLIT")
    add("I", "Axis integer-only ticks", _bool_v(xax.get("integer") or yax.get("integer"), "yes"), "XAXIS / YAXIS INTEGER")
    add("I", "X2AXIS label text", x2ax.get("label", ""), "X2AXIS LABEL=")

    lp0 = lineparms[0] if lineparms else {}
    add("I", "LINEPARM anchor, slope and label", f"x={lp0.get('x','')} y={lp0.get('y','')} slope={lp0.get('slope','')}" if lp0.get("x") else "", "LINEPARM X= Y= SLOPE=")
    add("I", "NOAUTOLEGEND", _bool_v(block.get("noautolegend"), "yes"), "PROC SGPLOT NOAUTOLEGEND")
    add("I", "SG annotation dataset (SGANNO)", block.get("sganno", ""), "PROC SGPLOT SGANNO=")

    return meta
