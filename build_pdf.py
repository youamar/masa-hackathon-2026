"""Render draft_report.md -> MASA_Hackathon_Report.pdf with cover page,
1-inch margins, 12pt body. Uses xhtml2pdf (pure-Python)."""
from pathlib import Path
import markdown
from xhtml2pdf import pisa

MD = Path("draft_report.md").read_text(encoding="utf-8")
# Drop the original title block from the report body since the cover page covers it.
body_md = MD.split("---", 2)[-1].lstrip()
body_html = markdown.markdown(body_md, extensions=["tables", "fenced_code"])

TEAM_NAME = "Anna Save Arendelle Data"
MEMBERS = [
    "Chang Kai Yang",
    "Joseph Ang",
    "Yau Zhi Xiong",
    "Ngiam Kian Peng",
    "Wong Kar Chun",
]
UNIVERSITY = "Asia Pacific University of Technology &amp; Innovation (APU)"

members_html = "".join(f"<div class='member'>{m}</div>" for m in MEMBERS)

CSS = """
@page {
  size: A4;
  margin: 1in 1in 1in 1in;
  @frame footer { -pdf-frame-content: footerContent;
                   left: 1in; right: 1in; bottom: 0.5in; height: 0.3in; }
}
body { font-family: Helvetica, Arial, sans-serif; font-size: 12pt;
       line-height: 1.35; color: #111; }
h1 { font-size: 18pt; margin-top: 14pt; margin-bottom: 6pt; }
h2 { font-size: 14pt; margin-top: 12pt; margin-bottom: 4pt; color: #6b1414; }
h3 { font-size: 12pt; margin-top: 8pt; margin-bottom: 2pt; }
p, li { font-size: 12pt; }
table { border-collapse: collapse; margin: 6pt 0; width: 100%; font-size: 11pt; }
th, td { border: 1px solid #888; padding: 3pt 6pt; text-align: left; }
th { background: #f0e6e6; }
hr { border: none; border-top: 1px solid #999; margin: 10pt 0; }
img { max-width: 6.0in; margin: 6pt auto; display: block; }
code { font-family: Consolas, monospace; font-size: 11pt; }

.cover { text-align: center; }
.cover .badge { font-size: 14pt; color: #6b1414; margin-top: 1.2in;
                letter-spacing: 2pt; text-align: center; }
.cover h1.title { font-size: 28pt; margin-top: 0.5in; margin-bottom: 0.1in;
                  text-align: center; }
.cover .subtitle { font-size: 14pt; color: #444; margin-bottom: 1.0in;
                   text-align: center; }
.cover .label { font-size: 12pt; color: #6b1414; margin-top: 24pt;
                text-transform: uppercase; letter-spacing: 2pt;
                text-align: center; }
.cover .team { font-size: 18pt; font-weight: bold; margin-top: 4pt;
               text-align: center; }
.cover .member { font-size: 13pt; margin-top: 2pt; text-align: center; }
.cover .uni { font-size: 13pt; margin-top: 6pt; text-align: center; }
.cover .date { text-align: center; }
.cover a { text-align: center; }
.pagebreak { page-break-after: always; }
"""

HTML = f"""<!doctype html>
<html><head><meta charset="utf-8"><style>{CSS}</style></head>
<body>

<div id="footerContent" style="font-size:9pt; color:#888; text-align:center;">
  MASA Hackathon 2026 · R-Ignite — Submission by {TEAM_NAME}
</div>

<div class="cover">
  <div class="badge">MASA HACKATHON 2026 · R-IGNITE</div>
  <h1 class="title">Igniting Agricultural Climate Resilience<br/>in Southeast Asia</h1>
  <div class="subtitle">A Parametric Reinsurance Strategy for Malaysia &amp; Indonesia</div>

  <div class="label">Team</div>
  <div class="team">{TEAM_NAME}</div>

  <div class="label">Members</div>
  {members_html}

  <div class="label">University</div>
  <div class="uni">{UNIVERSITY}</div>

  <div class="label" style="margin-top:48pt;">Submission Date</div>
  <div class="uni">7 May 2026</div>

  <div class="label" style="margin-top:24pt;">Live Interactive Dashboard</div>
  <div class="uni" style="font-size:11pt;">
    <a href="https://youamar-masa-hackathon-2026-app-pvja9h.streamlit.app/"
       style="color:#6b1414; text-decoration:none;">
      youamar-masa-hackathon-2026-app-pvja9h.streamlit.app
    </a>
  </div>
</div>
<div class="pagebreak"></div>

{body_html}

</body></html>
"""

def _link_callback(uri, rel):
    """Resolve relative image paths (e.g. figures/foo.png) for xhtml2pdf."""
    p = Path(uri)
    if not p.is_absolute():
        p = Path.cwd() / uri
    return str(p)

OUT = "MASA_Hackathon_Report.pdf"
with open(OUT, "wb") as f:
    result = pisa.CreatePDF(HTML, dest=f, link_callback=_link_callback)
if result.err:
    raise SystemExit(f"PDF generation failed with {result.err} errors")
print(f"Rendered -> {OUT}  ({Path(OUT).stat().st_size/1024:.1f} KB)")
