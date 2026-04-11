"""
parser.py — Parse complete SAS program into structured blocks
Handles: DATA steps, PROC SORT/MEANS/FREQ/UNIVARIATE, PROC SGPLOT/SGPANEL/SGSCATTER/REG/GLM,
         ODS statements, TITLE/FOOTNOTE, WHERE/BY, variable transformations
"""
import re


def _clean(s):
    return s.strip().strip(";").strip("'\"").strip()


def _get(pattern, text, flags=re.IGNORECASE, group=1, default=""):
    m = re.search(pattern, text, flags)
    return _clean(m.group(group)) if m else default


def _getall(pattern, text, flags=re.IGNORECASE):
    return [_clean(m) for m in re.findall(pattern, text, flags)]


def _strip_comments(code):
    """Remove SAS block comments /* ... */"""
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    # Remove * inline comments (lines starting with *)
    code = re.sub(r'^\s*\*[^;]*;', '', code, flags=re.MULTILINE)
    return code


def parse_sas_code(code: str) -> dict:
    code = _strip_comments(code)

    result = {
        "raw": code,
        "ods": parse_ods(code),
        "titles": parse_titles(code),
        "footnotes": parse_footnotes(code),
        "data_steps": parse_data_steps(code),
        "proc_sort": parse_proc_sort(code),
        "proc_means": parse_proc_means(code),
        "proc_freq": parse_proc_freq(code),
        "proc_univariate": parse_proc_univariate(code),
        "proc_blocks": parse_plot_procs(code),
        "global_where": _get(r'\bwhere\s+([^;]+);', code),
        "global_by": _get(r'\bby\s+([^;]+);', code),
    }
    return result


# ── ODS ──────────────────────────────────────────────────────────────────────
def parse_ods(code):
    ods = {}
    # ODS GRAPHICS statement
    gfx = re.search(r'ods\s+graphics\s*/([^;]+);', code, re.IGNORECASE)
    if gfx:
        opts = gfx.group(1)
        ods["width"]     = _get(r'width\s*=\s*(\S+)', opts)
        ods["height"]    = _get(r'height\s*=\s*(\S+)', opts)
        ods["imagename"] = _get(r'imagename\s*=\s*["\']?([^"\';\s]+)', opts)
        ods["imagefmt"]  = _get(r'imagefmt\s*=\s*(\S+)', opts)
        ods["dpi"]       = _get(r'dpimax\s*=\s*(\d+)', opts)
    # ODS destination
    dest_m = re.search(r'ods\s+(html|pdf|rtf|listing|svg|png|jpeg)\s', code, re.IGNORECASE)
    ods["destination"] = dest_m.group(1).upper() if dest_m else ""
    file_m = re.search(r'ods\s+\w+\s+file\s*=\s*["\']?([^"\';\s]+)', code, re.IGNORECASE)
    ods["file"] = file_m.group(1) if file_m else ""
    # ODS style
    style_m = re.search(r'ods\s+\w+.*?style\s*=\s*(\w+)', code, re.IGNORECASE)
    ods["style"] = style_m.group(1) if style_m else ""
    return ods


# ── TITLE / FOOTNOTE ──────────────────────────────────────────────────────────
def parse_titles(code):
    titles = {}
    for m in re.finditer(r'(title\d?)\s*(?:(?:bold\s+)?(?:italic\s+)?(?:font\s*=\s*["\']?\S+["\']?\s+)?(?:height\s*=\s*\S+\s+)?(?:color\s*=\s*\S+\s+)?(?:justify\s*=\s*\S+\s+)?)?["\']([^"\']+)["\']', code, re.IGNORECASE):
        key = m.group(1).lower()
        titles[key] = {
            "text": _clean(m.group(2)),
            "font":  _get(r'font\s*=\s*["\']?(\S+)["\']?', m.group(0)),
            "size":  _get(r'height\s*=\s*(\S+)', m.group(0)),
            "color": _get(r'color\s*=\s*(\S+)', m.group(0)),
            "bold":  bool(re.search(r'\bbold\b', m.group(0), re.IGNORECASE)),
            "italic":bool(re.search(r'\bitalic\b', m.group(0), re.IGNORECASE)),
            "justify":_get(r'justify\s*=\s*(\w+)', m.group(0)),
        }
    return titles


def parse_footnotes(code):
    fns = {}
    for m in re.finditer(r'(footnote\d?)\s*["\']([^"\']+)["\']', code, re.IGNORECASE):
        key = m.group(1).lower()
        fns[key] = {
            "text":  _clean(m.group(2)),
            "font":  _get(r'font\s*=\s*["\']?(\S+)["\']?', m.group(0)),
            "size":  _get(r'height\s*=\s*(\S+)', m.group(0)),
            "color": _get(r'color\s*=\s*(\S+)', m.group(0)),
        }
    return fns


# ── DATA STEPS ────────────────────────────────────────────────────────────────
def parse_data_steps(code):
    steps = []
    for m in re.finditer(r'\bdata\s+((?:\w+\.)?\w+)\s*;(.*?)(?=\brun\b|\bdata\s+\w|\bproc\s+\w)', code, re.IGNORECASE | re.DOTALL):
        ds_name = m.group(1)
        body = m.group(2)
        transforms = []
        # log transforms
        for t in re.finditer(r'(\w+)\s*=\s*log\s*\(([^)]+)\)', body, re.IGNORECASE):
            transforms.append(f"{t.group(1)} = log({t.group(2).strip()})")
        # sqrt
        for t in re.finditer(r'(\w+)\s*=\s*sqrt\s*\(([^)]+)\)', body, re.IGNORECASE):
            transforms.append(f"{t.group(1)} = sqrt({t.group(2).strip()})")
        # general assignment
        for t in re.finditer(r'(\w+)\s*=\s*([^;]+);', body):
            val = t.group(2).strip()
            if any(op in val for op in ['*', '/', '+', '-', 'log', 'sqrt', 'exp']):
                expr = f"{t.group(1)} = {val}"
                if expr not in transforms:
                    transforms.append(expr)
        where = _get(r'\bwhere\s+([^;]+);', body)
        steps.append({"dataset": ds_name, "transforms": transforms, "where": where})
    return steps


# ── PROC SORT ─────────────────────────────────────────────────────────────────
def parse_proc_sort(code):
    results = []
    for m in re.finditer(r'proc\s+sort\s+[^;]*;(.*?)run\s*;', code, re.IGNORECASE | re.DOTALL):
        body = m.group(0)
        results.append({
            "data":    _get(r'data\s*=\s*(\S+)', body),
            "out":     _get(r'out\s*=\s*(\S+)', body),
            "by":      _get(r'\bby\s+([^;]+);', body),
            "descending": bool(re.search(r'\bdescending\b', body, re.IGNORECASE)),
        })
    return results


# ── PROC MEANS / SUMMARY ──────────────────────────────────────────────────────
def parse_proc_means(code):
    results = []
    for m in re.finditer(r'proc\s+(?:means|summary)\b[^;]*;(.*?)run\s*;', code, re.IGNORECASE | re.DOTALL):
        body = m.group(0)
        results.append({
            "data":  _get(r'data\s*=\s*(\S+)', body),
            "out":   _get(r'out\s*=\s*(\S+)', body),
            "by":    _get(r'\bby\s+([^;]+);', body),
            "var":   _get(r'\bvar\s+([^;]+);', body),
            "class": _get(r'\bclass\s+([^;]+);', body),
        })
    return results


# ── PROC FREQ ─────────────────────────────────────────────────────────────────
def parse_proc_freq(code):
    results = []
    for m in re.finditer(r'proc\s+freq\b[^;]*;(.*?)run\s*;', code, re.IGNORECASE | re.DOTALL):
        body = m.group(0)
        results.append({
            "data":   _get(r'data\s*=\s*(\S+)', body),
            "tables": _get(r'\btables\s+([^;]+);', body),
            "weight": _get(r'\bweight\s+([^;]+);', body),
        })
    return results


# ── PROC UNIVARIATE ────────────────────────────────────────────────────────────
def parse_proc_univariate(code):
    results = []
    for m in re.finditer(r'proc\s+univariate\b[^;]*;(.*?)run\s*;', code, re.IGNORECASE | re.DOTALL):
        body = m.group(0)
        results.append({
            "data": _get(r'data\s*=\s*(\S+)', body),
            "var":  _get(r'\bvar\s+([^;]+);', body),
            "histogram": bool(re.search(r'\bhistogram\b', body, re.IGNORECASE)),
            "qqplot":    bool(re.search(r'\bqqplot\b', body, re.IGNORECASE)),
            "normal":    bool(re.search(r'\bnormal\b', body, re.IGNORECASE)),
        })
    return results


# ── PLOT PROCs ────────────────────────────────────────────────────────────────
PLOT_PROCS = r'sgplot|sgpanel|sgscatter|reg|glm|mixed|univariate'

def _extract_scoped_titles(pre_block_text):
    """Extract TITLE statements from the text immediately before a PROC block."""
    titles = {}
    for m in re.finditer(
        r'(title\d?)\s*(?:(?:bold\s+)?(?:italic\s+)?(?:font\s*=\s*["\']?\S+["\']?\s+)?'
        r'(?:height\s*=\s*\S+\s+)?(?:color\s*=\s*\S+\s+)?(?:justify\s*=\s*\S+\s+)?)?'
        r'["\']([^"\']+)["\']',
        pre_block_text, re.IGNORECASE
    ):
        key = m.group(1).lower()
        titles[key] = {
            "text":   _clean(m.group(2)),
            "font":   _get(r'font\s*=\s*["\']?(\S+)["\']?', m.group(0)),
            "size":   _get(r'height\s*=\s*(\S+)', m.group(0)),
            "color":  _get(r'color\s*=\s*(\S+)', m.group(0)),
            "bold":   bool(re.search(r'\bbold\b', m.group(0), re.IGNORECASE)),
            "italic": bool(re.search(r'\bitalic\b', m.group(0), re.IGNORECASE)),
            "justify":_get(r'justify\s*=\s*(\w+)', m.group(0)),
        }
    return titles


def parse_plot_procs(code):
    blocks = []
    pattern = rf'(proc\s+(?:{PLOT_PROCS})\b[^;]*;)(.*?)(?:run\s*;|quit\s*;)'
    for m in re.finditer(pattern, code, re.IGNORECASE | re.DOTALL):
        header = m.group(1)
        body = m.group(2)
        full = header + body
        proc_name = _get(r'proc\s+(\w+)', header)

        # ── Scoped title: look in the 400 chars before this PROC, or inside body ──
        proc_start = m.start()
        pre_text = code[max(0, proc_start - 400): proc_start]
        scoped_titles = _extract_scoped_titles(pre_text)
        # Also check for title INSIDE the proc body (SAS allows title inside proc)
        body_titles = _extract_scoped_titles(body)
        scoped_titles.update(body_titles)  # body titles override pre-proc titles

        block = {
            "proc_name": proc_name.upper(),
            "raw": full,
            "scoped_titles": scoped_titles,
            "dataset":   _get(r'data\s*=\s*(\S+)', header),
            "out":       _get(r'out\s*=\s*(\S+)', header),
            "noautolegend": bool(re.search(r'\bnoautolegend\b', header, re.IGNORECASE)),
            "cycleattrs":   bool(re.search(r'\bcycleattrs\b', header, re.IGNORECASE)),
            "pad":          _get(r'\bpad\s*=\s*([^;]+)', header),
            "dattrmap":     _get(r'\bdattrmap\s*=\s*(\S+)', header),
            "sganno":       _get(r'\bsganno\s*=\s*(\S+)', header),
            "where":        _get(r'\bwhere\s+([^;]+);', body),
            "by":           _get(r'\bby\s+([^;]+);', body),
            "freq":         _get(r'\bfreq\s+(\w+)', body),
            "weight":       _get(r'\bweight\s+(\w+)', body),
            "plot_statements": parse_plot_statements(body, proc_name),
            "xaxis":  parse_axis_stmt("xaxis", body),
            "yaxis":  parse_axis_stmt("yaxis", body),
            "y2axis": parse_axis_stmt("y2axis", body),
            "x2axis": parse_axis_stmt("x2axis", body),
            "keylegend":  parse_keylegend(body),
            "reflines":   parse_reflines(body),
            "insets":     parse_insets(body),
            "lineparms":  parse_lineparms(body),
            "panelby":    parse_panelby(body),
            "model":      _get(r'\bmodel\s+([^;]+);', body),
            "uniform":    _get(r'\buniform\s*=\s*(\S+)', header),
        }
        # For REG/GLM: extract model vars
        if proc_name.upper() in ("REG", "GLM", "MIXED"):
            block.update(parse_reg_model(body))
        blocks.append(block)
    return blocks


def parse_plot_statements(body, proc_name):
    stmts = []
    # Match known plot statement keywords
    plot_kws = r'scatter|series|reg|loess|band|needle|histogram|vbar|hbar|vbox|hbox|ellipse|bubble|density|pbspline|step|vector|highlow|lineparm|polygon|matrix|compare|heatmapparm'
    for m in re.finditer(rf'\b({plot_kws})\s+([^;]+);', body, re.IGNORECASE):
        kw = m.group(1).lower()
        opts = m.group(2)
        # For VBOX/HBOX the response var is the first bare word before '/'
        vbox_y = ""
        if kw in ("vbox", "hbox"):
            vy = re.match(r'\s*(\w+)', opts)
            vbox_y = vy.group(1) if vy else ""

        # For VBAR/HBAR: first bare word before / is the category axis
        bar_cat = ""
        if kw in ("vbar", "hbar"):
            bc = re.match(r'\s*(\w+)', opts)
            bar_cat = bc.group(1) if bc else ""
        stmt = {
            "type":     kw,
            "x":        _get(r'\bx\s*=\s*(\w+)', opts) or (bar_cat if kw == "vbar" else ""),
            "y":        _get(r'\by\s*=\s*(\w+)', opts) or vbox_y or _get(r'\bresponse\s*=\s*(\w+)', opts),
            "y2":       _get(r'\by2\s*=\s*(\w+)', opts),
            "x2":       _get(r'\bx2\s*=\s*(\w+)', opts),
            "category": _get(r'\bcategory\s*=\s*(\w+)', opts),   # VBOX/HBOX category=
            "response": _get(r'\bresponse\s*=\s*(\w+)', opts),   # VBAR/HBAR response=
            "group":    _get(r'\bgroup\s*=\s*(\w+)', opts),
            "size":  _get(r'\bsize\s*=\s*(\w+)', opts),
            "colorresponse": _get(r'\bcolorresponse\s*=\s*(\w+)', opts),
            "markerchar":    _get(r'\bmarkerchar\s*=\s*(\w+)', opts),
            "datalabel":     _get(r'\bdatalabel\s*=\s*(\w+)', opts),
            "datalabelpos":  _get(r'\bdatalabelpos\s*=\s*(\w+)', opts),
            "transparency":  _get(r'\btransparency\s*=\s*([\d.]+)', opts),
            "freq":          _get(r'\bfreq\s*=\s*(\w+)', opts),
            "weight":        _get(r'\bweight\s*=\s*(\w+)', opts),
            # Marker attrs
            "marker_symbol": _get(r'markerattrs\s*=\s*\([^)]*symbol\s*=\s*(\w+)', opts),
            "marker_size":   _get(r'markerattrs\s*=\s*\([^)]*size\s*=\s*([\d.]+)', opts),
            "marker_color":  _get(r'markerattrs\s*=\s*\([^)]*color\s*=\s*(\w+)', opts),
            # Line attrs
            "line_color":    _get(r'lineattrs\s*=\s*\([^)]*color\s*=\s*(\w+)', opts),
            "line_pattern":  _get(r'lineattrs\s*=\s*\([^)]*pattern\s*=\s*(\w+)', opts),
            "line_thickness":_get(r'lineattrs\s*=\s*\([^)]*thickness\s*=\s*([\d.]+)', opts),
            # Fill attrs
            "fill_color":    _get(r'fillattrs\s*=\s*\([^)]*color\s*=\s*(\w+)', opts),
            # CLM/CLI
            "clm": bool(re.search(r'\bclm\b', opts, re.IGNORECASE)),
            "cli": bool(re.search(r'\bcli\b', opts, re.IGNORECASE)),
            "alpha": _get(r'\balpha\s*=\s*([\d.]+)', opts),
            # LOESS/REG options
            "degree": _get(r'\bdegree\s*=\s*(\d+)', opts),
            "nostat": bool(re.search(r'\bnostat\b', opts, re.IGNORECASE)),
            # Bar options
            "barwidth":     _get(r'\bbarwidth\s*=\s*([\d.]+)', opts),
            "groupdisplay": _get(r'\bgroupdisplay\s*=\s*(\w+)', opts),
            "clusterwidth": _get(r'\bclusterwidth\s*=\s*([\d.]+)', opts),
            # Limit/whisker attrs
            "limitattrs_color":     _get(r'limitattrs\s*=\s*\([^)]*color\s*=\s*(\w+)', opts),
            "limitattrs_thickness": _get(r'limitattrs\s*=\s*\([^)]*thickness\s*=\s*([\d.]+)', opts),
            "whiskerattrs_color":   _get(r'whiskerattrs\s*=\s*\([^)]*color\s*=\s*(\w+)', opts),
            "outlierattrs_symbol":  _get(r'outlierattrs\s*=\s*\([^)]*symbol\s*=\s*(\w+)', opts),
            # Datalabel attrs
            "datalabelattrs_family": _get(r'datalabelattrs\s*=\s*\([^)]*family\s*=\s*["\']?([^"\')\s]+)', opts),
            "datalabelattrs_size":   _get(r'datalabelattrs\s*=\s*\([^)]*size\s*=\s*([\d.]+)', opts),
            "datalabelattrs_color":  _get(r'datalabelattrs\s*=\s*\([^)]*color\s*=\s*(\w+)', opts),
            # Color model
            "colormodel": _get(r'\bcolormodel\s*=\s*([^;\s]+)', opts),
        }
        stmts.append(stmt)
    return stmts


def parse_axis_stmt(axis, body):
    # Anchor to start-of-statement (after newline or semicolon) to avoid
    # matching axis keywords that appear as options inside plot statements
    # e.g. "series ... / y2axis" must not match the y2axis statement itself
    m = re.search(rf'(?:^|;|\n)\s*{axis}\s+([^;]+);', body, re.IGNORECASE)
    if not m:
        return {}
    opts = m.group(1)
    return {
        "label":         _get(r'\blabel\s*=\s*["\']([^"\']+)["\']', opts),
        "min":           _get(r'\bmin\s*=\s*([\d.eE+-]+)', opts),
        "max":           _get(r'\bmax\s*=\s*([\d.eE+-]+)', opts),
        "type":          _get(r'\btype\s*=\s*(\w+)', opts),
        "logbase":       _get(r'\blogbase\s*=\s*(\S+)', opts),
        "logstyle":      _get(r'\blogstyle\s*=\s*(\w+)', opts),
        "values":        _get(r'\bvalues\s*=\s*\(([^)]+)\)', opts),
        "interval":      _get(r'\binterval\s*=\s*(\w+)', opts),
        "grid":          bool(re.search(r'\bgrid\b', opts, re.IGNORECASE)),
        "minorgrid":     bool(re.search(r'\bminorgrid\b', opts, re.IGNORECASE)),
        "gridattrs_color":   _get(r'gridattrs\s*=\s*\([^)]*color\s*=\s*(\w+)', opts),
        "gridattrs_pattern": _get(r'gridattrs\s*=\s*\([^)]*pattern\s*=\s*(\w+)', opts),
        "color":         _get(r'\bcolor\s*=\s*(\w+)', opts),
        "display":       _get(r'\bdisplay\s*=\s*([^;]+)', opts),
        "novalues":      bool(re.search(r'\bnovalues\b', opts, re.IGNORECASE)),
        "noticks":       bool(re.search(r'\bnoticks\b', opts, re.IGNORECASE)),
        "reverse":       bool(re.search(r'\breverse\b', opts, re.IGNORECASE)),
        "integer":       bool(re.search(r'\binteger\b', opts, re.IGNORECASE)),
        "notimesplit":   bool(re.search(r'\bnotimesplit\b', opts, re.IGNORECASE)),
        "offsetmin":     _get(r'\boffsetmin\s*=\s*([\d.]+)', opts),
        "offsetmax":     _get(r'\boffsetmax\s*=\s*([\d.]+)', opts),
        "discreteorder": _get(r'\bdiscreteorder\s*=\s*(\w+)', opts),
        "fitpolicy":     _get(r'\bfitpolicy\s*=\s*(\w+)', opts),
        "minor":         bool(re.search(r'\bminor\b', opts, re.IGNORECASE)),
        "labelattrs_family": _get(r'labelattrs\s*=\s*\([^)]*family\s*=\s*["\']?([^"\')\s]+)', opts),
        "labelattrs_size":   _get(r'labelattrs\s*=\s*\([^)]*size\s*=\s*([\d.]+)', opts),
        "labelattrs_color":  _get(r'labelattrs\s*=\s*\([^)]*color\s*=\s*(\w+)', opts),
        "tickvalueattrs_family": _get(r'tickvalueattrs\s*=\s*\([^)]*family\s*=\s*["\']?([^"\')\s]+)', opts),
        "tickvalueattrs_size":   _get(r'tickvalueattrs\s*=\s*\([^)]*size\s*=\s*([\d.]+)', opts),
        "tickvalueattrs_color":  _get(r'tickvalueattrs\s*=\s*\([^)]*color\s*=\s*(\w+)', opts),
        "tickvaluerotate":   _get(r'\btickvaluerotate\s*=\s*([\d.]+)', opts),
        "format":        _get(r'\bformat\s*=\s*(\S+)', opts),
    }


def parse_keylegend(body):
    m = re.search(r'\bkeylegend\b([^;]*);', body, re.IGNORECASE)
    if not m:
        noleg = bool(re.search(r'\bnolegend\b|\bnoautolegend\b', body, re.IGNORECASE))
        return {"show": not noleg}
    opts = m.group(1)
    return {
        "show": True,
        "position":  _get(r'\bposition\s*=\s*(\w+)', opts),
        "location":  _get(r'\blocation\s*=\s*(\w+)', opts),
        "title":     _get(r'\btitle\s*=\s*["\']([^"\']+)["\']', opts),
        "noborder":  bool(re.search(r'\bnoborder\b', opts, re.IGNORECASE)),
        "titleattrs_family": _get(r'titleattrs\s*=\s*\([^)]*family\s*=\s*["\']?([^"\')\s]+)', opts),
        "titleattrs_size":   _get(r'titleattrs\s*=\s*\([^)]*size\s*=\s*([\d.]+)', opts),
        "valueattrs_family": _get(r'valueattrs\s*=\s*\([^)]*family\s*=\s*["\']?([^"\')\s]+)', opts),
        "valueattrs_size":   _get(r'valueattrs\s*=\s*\([^)]*size\s*=\s*([\d.]+)', opts),
    }


def parse_reflines(body):
    lines = []
    for m in re.finditer(r'\brefline\s+([^;]+);', body, re.IGNORECASE):
        opts = m.group(1)
        lines.append({
            "value":   _get(r'^([\d.\w\-]+)', opts),
            "axis":    _get(r'\baxis\s*=\s*(\w+)', opts),
            "label":   _get(r'\blabel\s*=\s*["\']([^"\']+)["\']', opts),
            "color":   _get(r'lineattrs\s*=\s*\([^)]*color\s*=\s*(\w+)', opts),
            "pattern": _get(r'lineattrs\s*=\s*\([^)]*pattern\s*=\s*(\w+)', opts),
            "thickness":_get(r'lineattrs\s*=\s*\([^)]*thickness\s*=\s*([\d.]+)', opts),
        })
    return lines


def parse_insets(body):
    insets = []
    for m in re.finditer(r'\binset\s+([^;]+);', body, re.IGNORECASE):
        opts = m.group(1)
        # Extract quoted strings as inset text
        texts = re.findall(r'["\']([^"\']+)["\']', opts)
        insets.append({
            "text":       " | ".join(texts),
            "position":   _get(r'\bposition\s*=\s*(\w+)', opts),
            "x":          _get(r'\bx\s*=\s*([\d.]+)', opts),
            "y":          _get(r'\by\s*=\s*([\d.]+)', opts),
            "border":     bool(re.search(r'\bborder\b', opts, re.IGNORECASE)),
            "background": _get(r'\bbackground\s*=\s*(\w+)', opts),
            "font_family":_get(r'textattrs\s*=\s*\([^)]*family\s*=\s*["\']?([^"\')\s]+)', opts),
            "font_size":  _get(r'textattrs\s*=\s*\([^)]*size\s*=\s*([\d.]+)', opts),
            "font_color": _get(r'textattrs\s*=\s*\([^)]*color\s*=\s*(\w+)', opts),
        })
    return insets


def parse_lineparms(body):
    lps = []
    for m in re.finditer(r'\blineparm\s+([^;]+);', body, re.IGNORECASE):
        opts = m.group(1)
        lps.append({
            "x":      _get(r'\bx\s*=\s*([\d.\w\-]+)', opts),
            "y":      _get(r'\by\s*=\s*([\d.\w\-]+)', opts),
            "slope":  _get(r'\bslope\s*=\s*([\d.\w\-]+)', opts),
            "label":  _get(r'\blabel\s*=\s*["\']([^"\']+)["\']', opts),
            "color":  _get(r'lineattrs\s*=\s*\([^)]*color\s*=\s*(\w+)', opts),
            "pattern":_get(r'lineattrs\s*=\s*\([^)]*pattern\s*=\s*(\w+)', opts),
            "thickness":_get(r'lineattrs\s*=\s*\([^)]*thickness\s*=\s*([\d.]+)', opts),
        })
    return lps


def parse_panelby(body):
    m = re.search(r'\bpanelby\s+([^;]+);', body, re.IGNORECASE)
    if not m:
        return {}
    opts = m.group(1)
    var_m = re.match(r'(\w+)', opts)
    return {
        "variable":   var_m.group(1) if var_m else "",
        "colspace":   _get(r'\bcolspace\s*=\s*([\d.]+)', opts),
        "rowspace":   _get(r'\browspace\s*=\s*([\d.]+)', opts),
        "label":      _get(r'\blabel\s*=\s*["\']([^"\']+)["\']', opts),
        "header_fill":  _get(r'headerattrs\s*=\s*\([^)]*fill\s*=\s*(\w+)', opts),
        "header_color": _get(r'headerattrs\s*=\s*\([^)]*color\s*=\s*(\w+)', opts),
        "format":       _get(r'\bformat\s*=\s*(\S+)', opts),
    }


def parse_reg_model(body):
    m = re.search(r'\bmodel\s+(\w+)\s*=\s*([^;/]+)', body, re.IGNORECASE)
    if not m:
        return {}
    dep = m.group(1).strip()
    indeps = m.group(2).strip().split()
    return {
        "model_dep": dep,
        "model_indep": indeps,
        "clm": bool(re.search(r'\bclm\b', body, re.IGNORECASE)),
        "cli": bool(re.search(r'\bcli\b', body, re.IGNORECASE)),
        "r2":  bool(re.search(r'\br2\b|\brsquare\b', body, re.IGNORECASE)),
    }
