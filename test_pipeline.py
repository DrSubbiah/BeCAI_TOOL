from parser import parse_sas_code
from metadata import extract_bcai_metadata
from generator import generate_plotly_code
from validator import build_validation_report

sas = """
ods graphics / width=800px height=600px imagename='salary_plot';
ods html file='salary_analysis.html' style=HTMLBlue;

title 'Salary increases with Age across Departments';
title2 'Company HR Analysis FY2024';
footnote 'Source: HR Database, extract date 2024-01-15';

data work.mydata;
  set hr.employees;
  log_salary = log(salary);
  where dept ne '';
run;

proc sort data=work.mydata;
  by dept;
run;

proc means data=work.mydata out=work.means noprint;
  class dept;
  var salary age;
run;

proc sgplot data=work.mydata noautolegend;
  scatter x=age y=salary / group=dept
    markerattrs=(symbol=circlefilled size=10 color=steelblue)
    transparency=0.2
    datalabel=name datalabelpos=top;
  reg x=age y=salary / clm alpha=0.05
    lineattrs=(color=red pattern=dash thickness=2);
  loess x=age y=salary /
    lineattrs=(color=green pattern=solid thickness=1.5);
  refline 50000 / axis=y label='Median' lineattrs=(color=gray pattern=shortdash);
  inset 'R=0.72' 'N=450' / position=topright border
    textattrs=(size=11 color=black);
  lineparm x=25 y=30000 slope=800 / label='Trend' lineattrs=(color=navy);
  keylegend / position=bottom noborder title='Department';
  xaxis label='Age (years)' grid
    labelattrs=(family=Arial size=12 color=black)
    tickvalueattrs=(size=10) min=20 max=65;
  yaxis label='Annual Salary USD' type=log
    labelattrs=(family=Arial size=12)
    min=20000 max=200000 grid gridattrs=(color=lightgray);
run;
ods html close;
"""

parsed = parse_sas_code(sas)
meta = extract_bcai_metadata(parsed)
print(f"Metadata items: {len(meta)}")
print(f"Non-empty: {sum(1 for m in meta if m['value'])}")

code = generate_plotly_code(meta, parsed["proc_blocks"][0], parsed)
print(f"Generated code lines: {len(code.splitlines())}")

val = build_validation_report(meta, code)
print(f"Score: {val['score']:.1f}%  Full:{val['full']} Approx:{val['approx']} NotFound:{val['none']} NA:{val['na']}")
print("PASS")
