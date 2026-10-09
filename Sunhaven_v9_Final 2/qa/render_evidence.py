"""Offline HTML-to-PDF document rendering, NOT browser screenshots or JS testing."""
from pathlib import Path
import logging
from weasyprint import HTML,CSS
import fitz
logging.getLogger('weasyprint').setLevel(logging.ERROR)
ROOT=Path(__file__).resolve().parents[1]
PAGES=ROOT/'evidence/rendered-pages';TMP=ROOT/'evidence/page-renders';TMP.mkdir(exist_ok=True)
css=CSS(string='''input[type=hidden]{display:none!important}@page{size:1440px 1040px;margin:0}html{font-family:DejaVu Sans,sans-serif}.sidebar{width:238px;height:1040px;position:fixed;top:24px;left:0;overflow:hidden}.main{margin-left:238px;width:1202px}.topbar{position:static;height:auto;min-height:76px}.page-body{padding:24px}.hero{padding:20px}.panel{break-inside:auto}.stats-grid{display:flex;gap:16px}.stats-grid>*{flex:1}.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:20px}.table-wrap{overflow:visible}body:before{content:"STATIC HTML RENDER | Actual HTTP response; not a browser screenshot. JavaScript not executed.";display:block;position:fixed;top:0;left:0;width:100%;height:24px;background:#ffe7a1;color:#393018;font-size:12px;text-align:center;z-index:1000}.topbar{margin-top:24px}.global-search{display:none}.sidebar-foot{display:none}.nav-link{padding:5px 12px;font-size:12px}.page-footer{position:static}form button{white-space:normal}.badge{white-space:normal}''',media_type='screen')
for source in sorted(PAGES.glob('*.html')):
 pdf=TMP/(source.stem+'.pdf')
 HTML(filename=str(source),media_type='screen').write_pdf(str(pdf),stylesheets=[css])
 doc=fitz.open(pdf);doc[0].get_pixmap(matrix=fitz.Matrix(1.3,1.3)).save(str(TMP/(source.stem+'.png')))
 print(source.stem,len(doc))
