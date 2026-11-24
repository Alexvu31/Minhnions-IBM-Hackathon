"""
Bob Logbook -- 4-page PDF submission generator (compact, exactly 4 pages)
Run: python generate_pdf.py
"""
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, white, black
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image as RLImage,
    HRFlowable, Table, TableStyle, PageBreak, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus.flowables import Flowable
import os

# ── Colours ───────────────────────────────────────────────────────────────────
IBM_BLUE  = HexColor("#0F62FE")
IBM_NAVY  = HexColor("#001141")
LGREY     = HexColor("#F4F4F4")
MGREY     = HexColor("#8D8D8D")
DGREY     = HexColor("#393939")
LBLUE     = HexColor("#D0E2FF")
ACCENT    = HexColor("#0043CE")
GREEN     = HexColor("#198038")

W, H = letter
MG = 0.6 * inch          # margin
PW = W - 2 * MG          # usable width
PH = H - 2 * MG          # usable height

# ── Styles ────────────────────────────────────────────────────────────────────
_ss = getSampleStyleSheet()

def _s(name, **kw):
    return ParagraphStyle(name, parent=_ss["Normal"], **kw)

H1  = _s("H1",  fontName="Helvetica-Bold", fontSize=11.5, leading=13,
          textColor=IBM_NAVY, spaceBefore=4, spaceAfter=1)
H2  = _s("H2",  fontName="Helvetica-Bold", fontSize=11, leading=13,
          textColor=IBM_BLUE, spaceBefore=3, spaceAfter=1)
BD  = _s("BD",  fontName="Helvetica",      fontSize=11, leading=13.5,
          textColor=DGREY, alignment=TA_JUSTIFY, spaceAfter=2)
SML = _s("SML", fontName="Helvetica",      fontSize=10, leading=12,
          textColor=DGREY, alignment=TA_JUSTIFY, spaceAfter=2)
BUL = _s("BUL", fontName="Helvetica",      fontSize=10.5, leading=12.5,
          textColor=DGREY, leftIndent=10, spaceAfter=1)
COD = _s("COD", fontName="Courier",        fontSize=8, leading=10,
          textColor=HexColor("#161616"), backColor=LGREY,
          leftIndent=7, rightIndent=7, spaceBefore=2, spaceAfter=2, borderPad=2)
CAP = _s("CAP", fontName="Helvetica-Oblique", fontSize=8, leading=9,
          textColor=MGREY, alignment=TA_CENTER, spaceAfter=3)

# ── Flowable: thin rule under H1 ─────────────────────────────────────────────
class Rule(Flowable):
    def __init__(self, w=PW, t=1.2, color=IBM_BLUE):
        super().__init__(); self.width=w; self.height=t+2; self._t=t; self._c=color
    def draw(self):
        self.canv.setStrokeColor(self._c); self.canv.setLineWidth(self._t)
        self.canv.line(0, self._t/2, self.width, self._t/2)

# ── Helpers ───────────────────────────────────────────────────────────────────
def sp(h=0.05): return Spacer(1, h*inch)
def h1(t): return [Paragraph(t, H1), Rule()]
def h2(t): return [Paragraph(t, H2)]
def p(t): return Paragraph(t, BD)
def ps(t): return Paragraph(t, SML)
def bul(t): return Paragraph(f"<b>&#8226;</b>  {t}", BUL)
def cap(t): return Paragraph(t, CAP)
def code(*lines): return Paragraph("<br/>".join(lines), COD)

def img(path, max_w, max_h, caption_text=None):
    out = []
    try:
        im = RLImage(path)
        iw, ih = im.imageWidth, im.imageHeight
        sc = min(max_w/iw, max_h/ih, 1.0)
        im.drawWidth = iw*sc; im.drawHeight = ih*sc; im.hAlign = "CENTER"
        out.append(im)
        if caption_text: out.append(cap(caption_text))
    except Exception as e:
        out.append(ps(f"[Image: {os.path.basename(path)} -- {e}]"))
    return out

def table2(data, widths, header_bg=IBM_NAVY, row_colors=None):
    tbl = Table(data, colWidths=widths)
    styles_ = [
        ("BACKGROUND",    (0,0), (-1,0), header_bg),
        ("TEXTCOLOR",     (0,0), (-1,0), white),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,0), 9),
        ("FONTNAME",      (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE",      (0,1), (-1,-1), 9),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("GRID",          (0,0), (-1,-1), 0.4, MGREY),
        ("LEFTPADDING",   (0,0), (-1,-1), 5),
        ("RIGHTPADDING",  (0,0), (-1,-1), 5),
        ("TOPPADDING",    (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]
    if row_colors:
        styles_.append(("ROWBACKGROUNDS", (0,1), (-1,-1), row_colors))
    tbl.setStyle(TableStyle(styles_))
    return tbl

# ── Page footer callback ───────────────────────────────────────────────────────
def _footer(canvas, doc):
    canvas.saveState()
    y = MG * 0.5
    canvas.setStrokeColor(IBM_BLUE); canvas.setLineWidth(0.5)
    canvas.line(MG, y+8, W-MG, y+8)
    canvas.setFont("Helvetica", 7.5); canvas.setFillColor(MGREY)
    canvas.drawString(MG, y, "Bob Logbook  |  Team Minhnions (jaminleod, alexvu31)  |  CIPS x IBM Hackathon 2024")
    canvas.drawRightString(W-MG, y, f"Page {doc.page} of 4")
    canvas.restoreState()

# ── PAGE 1: Problem, User Story, Solution Overview, Scoring ──────────────────
def page1():
    s = []

    # Banner
    bd = [[
        Paragraph("<b><font color='white' size='16'>Bob Logbook</font></b>", _ss["Normal"]),
        Paragraph("<font color='#D0E2FF' size='10'>Git shadow-branch AI workspace for IBM Bob</font>", _ss["Normal"]),
    ]]
    bt = Table(bd, colWidths=[PW*0.46, PW*0.54])
    bt.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), IBM_NAVY),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
        ("RIGHTPADDING",  (0,0),(-1,-1), 10),
        ("TOPPADDING",    (0,0),(-1,-1), 9),
        ("BOTTOMPADDING", (0,0),(-1,-1), 9),
    ]))
    s.append(bt); s.append(sp(0.03))

    # Meta strip
    md = [["Team: Minhnions  |  CIPS x IBM Hackathon 2024  |  4 pages  |  font >= 11pt"]]
    mt = Table(md, colWidths=[PW])
    mt.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), LBLUE),
        ("FONTNAME",      (0,0),(-1,-1), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,-1), 8.5),
        ("TEXTCOLOR",     (0,0),(-1,-1), IBM_NAVY),
        ("LEFTPADDING",   (0,0),(-1,-1), 7),
        ("TOPPADDING",    (0,0),(-1,-1), 3),
        ("BOTTOMPADDING", (0,0),(-1,-1), 3),
    ]))
    s.append(mt); s.append(sp(0.07))

    # Problem
    s += h1("The Problem")
    s.append(p(
        "IBM Bob is powerful inside a single session -- but that session is ephemeral. "
        "Every new chat starts blank. When two contributors work simultaneously, neither agent "
        "knows what the other is doing. Existing workarounds (pasting context, shared notes docs) "
        "are fragile and do not scale to multi-agent workflows."
    ))

    # User story
    s += h1("User Story")
    qt = Table([[p(
        "<i>\"As an IBM Bob user on a team project, I want Bob to remember what it did last session "
        "and know what my teammate's Bob agent has been doing, so I can pick up exactly where we "
        "left off -- across machines, across sessions, without copy-pasting context.\"</i>"
    )]], colWidths=[PW - 0.15*inch])
    qt.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), LBLUE),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
        ("RIGHTPADDING",  (0,0),(-1,-1), 10),
        ("TOPPADDING",    (0,0),(-1,-1), 6),
        ("BOTTOMPADDING", (0,0),(-1,-1), 6),
        ("LINEAFTER",     (0,0),(0,-1), 4, IBM_BLUE),
    ]))
    s.append(qt); s.append(sp(0.05))

    # Solution
    s += h1("Solution Overview")
    s.append(p(
        "<b>Bob Logbook</b> wires IBM Bob lifecycle hooks into a Python CLI that writes every "
        "chat turn to a <i>git shadow branch</i> (<code>bob-context</code>) -- an orphan branch "
        "that never touches the working tree. A single-file HTML viewer renders the workspace "
        "as a live chat timeline. Multiple agents converge via ordinary git push/pull."
    ))

    s += h2("Deliverables")
    for item in [
        "<b>bob_log.py</b> -- Python 3 stdlib CLI: init, read, write, append, commit, ls, export, log, diff, serve",
        "<b>bob-log-hook.py</b> -- Hook wrapper for Stop, UserPromptSubmit, SessionStart events",
        "<b>viewer.html</b> -- Single-file IBM Carbon chat viewer with SSE live updates and filter panel",
        "<b>README.md + test_bob_log.py</b> -- Full docs and stdlib unittest test suite",
    ]:
        s.append(bul(item))
    s.append(sp(0.05))

    # Score table
    s += h1("Scoring Rubric")
    score_data = [
        ["Criterion", "How We Address It", "pts"],
        ["Innovation & Creativity",
         "Shadow branch as AI shared memory -- novel git-native pattern; tool dogfoods Bob",    "25"],
        ["Relevance to Challenge",
         "Extends IBM Bob hook API end-to-end; complete workflow for both single and multi-agent", "25"],
        ["Practicality & Feasibility",
         "stdlib only, no pip, no accounts; runs anywhere Python 3 + git exist",                "25"],
        ["Quality & Presentation",
         "Viewer + tests + README + serve + PDF -- all deliverables present and working",       "25"],
    ]
    cw = [PW*0.28, PW*0.59, PW*0.13]
    tbl = Table(score_data, colWidths=cw)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0), IBM_NAVY),
        ("TEXTCOLOR",     (0,0),(-1,0), white),
        ("FONTNAME",      (0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,0), 9),
        ("FONTNAME",      (0,1),(-1,-1), "Helvetica"),
        ("FONTSIZE",      (0,1),(-1,-1), 9),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [white, LGREY]),
        ("GRID",          (0,0),(-1,-1), 0.4, MGREY),
        ("ALIGN",         (2,0),(2,-1), "CENTER"),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("LEFTPADDING",   (0,0),(-1,-1), 5),
        ("TOPPADDING",    (0,0),(-1,-1), 4),
        ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("BACKGROUND",    (2,1),(2,-1), LBLUE),
        ("FONTNAME",      (2,1),(2,-1), "Helvetica-Bold"),
        ("TEXTCOLOR",     (2,1),(2,-1), IBM_NAVY),
    ]))
    s.append(tbl)
    return s

# ── PAGE 2: Architecture + Bob Usage Evidence ─────────────────────────────────
def page2():
    s = []

    s += h1("System Architecture")
    s.append(p(
        "Every component runs inside the git repo -- no external services. "
        "All writes use git plumbing: <code>hash-object</code> -> <code>mktree</code> "
        "-> <code>commit-tree</code> -> <code>update-ref</code>. Working tree never switched."
    ))
    s.append(sp(0.04))

    # Architecture table
    arch_data = [
        ["Component", "Role"],
        ["Hook fires (Stop / UserPromptSubmit / SessionStart)",
         "IBM Bob lifecycle events trigger bob-log-hook.py via JSON stdin"],
        ["bob-log-hook.py",
         "Parses payload, formats Entry-NNN Markdown, calls bob_log.py append"],
        ["bob_log.py CLI",
         "Git plumbing: hash-object -> mktree -> commit-tree -> update-ref (no checkout)"],
        ["bob-context branch",
         "Orphan shadow branch; stores chat/author.md, notes/, state/ files"],
        ["bob-log serve",
         "ThreadingHTTPServer: GET /api/export (JSON), GET /api/stream (SSE)"],
        ["viewer.html",
         "Single-file IBM Carbon UI: chat bubbles, tabbed layout, live SSE updates"],
    ]
    cw = [PW*0.38, PW*0.62]
    s.append(table2(arch_data, cw, row_colors=[white, LGREY]))
    s.append(sp(0.05))

    # Data flow strip
    s += h2("Data Flow")
    flow = ["IBM Bob", "->", "hook.py", "->", "bob_log.py", "->", "bob-context", "->", "viewer"]
    fc   = [IBM_NAVY, None, IBM_BLUE, None, ACCENT, None, GREEN, None, HexColor("#6929C4")]
    fd = [[
        Paragraph(
            f"<b><font color='white'>{t}</font></b>" if c
            else f"<b><font color='#888'>{t}</font></b>",
            _s(f"fl{i}", fontSize=7.5, leading=9, alignment=TA_CENTER, fontName="Helvetica-Bold")
        )
        for i,(t,c) in enumerate(zip(flow,fc))
    ]]
    ft = Table(fd, colWidths=[PW/len(flow)]*len(flow), rowHeights=[0.28*inch])
    ts = [("VALIGN",(0,0),(-1,-1),"MIDDLE"),("ALIGN",(0,0),(-1,-1),"CENTER"),
          ("TOPPADDING",(0,0),(-1,-1),2),("BOTTOMPADDING",(0,0),(-1,-1),2)]
    for i,(_,c) in enumerate(zip(flow,fc)):
        if c: ts.append(("BACKGROUND",(i,0),(i,0),c))
    ft.setStyle(TableStyle(ts))
    s.append(ft); s.append(sp(0.04))

    # Bob usage evidence
    s += h1("IBM Bob Usage Evidence")
    s.append(p(
        "Bob was the <b>primary engineer</b> throughout -- for architecture decisions, brainstorming, "
        "code generation, and debugging. The screenshots below are direct evidence."
    ))
    s.append(sp(0.04))

    # Viewer screenshot (swapped to Figure 1)
    s += h2("Figure 1: Bob Logbook Viewer  (viewer.html)")
    s += img("image1.png", max_w=PW, max_h=1.65*inch,
             caption_text="viewer.html: left sidebar shows file tree with entry-count pills; right panel shows IBM Carbon chat bubbles for alexvu31 and jaminleod interleaved by timestamp.")
    s.append(sp(0.04))

    # image2 -- planning transcript
    s += h2("Figure 2: Bob Brainstorming Transcript")
    s += img("image2.png", max_w=PW, max_h=1.7*inch,
             caption_text="Bob evaluates scoring criteria, pitches four ideas for 4 hours, and pivots to Bob Logbook. This transcript produced hackathon-plan.md.")

    return s

# ── PAGE 3: Code Highlights ───────────────────────────────────────────────────
def page3():
    s = []

    s += h1("Code Highlights")
    s.append(ps("All code was written collaboratively with Bob. Three extracts show the most technically interesting parts of the system."))
    s.append(sp(0.06))

    # 1 -- Hook config
    s += h2("1 -- Hook Configuration  (.bob/settings.json)")
    s.append(ps(
        "Three lifecycle events wired to the same script. "
        "<code>UserPromptSubmit</code> must NOT print to stdout (stdout is injected into model context). "
        "<code>SessionStart</code> returns <code>additionalContext</code> JSON so Bob always knows what changed."
    ))
    s.append(code(
        '{ "hooks": {',
        '    "Stop":             [{ "command": "python3 bob-log-hook.py" }],',
        '    "UserPromptSubmit": [{ "command": "python3 bob-log-hook.py" }],',
        '    "SessionStart":     [{ "command": "python3 bob-log-hook.py" }]',
        '  }',
        '}',
    ))
    s.append(sp(0.04))

    # 2 -- Write plumbing
    s += h2("2 -- Shadow Branch Write via Git Plumbing  (bob_log.py)")
    s.append(ps(
        "Never switch branches. Every write uses git plumbing -- content becomes a blob, "
        "a tree is rebuilt, a commit is created, and <code>update-ref</code> advances the pointer atomically."
    ))
    s.append(code(
        "def _write_blob(path, content, message='update'):",
        "    # 1. Store content as a git blob object",
        "    blob = _git('hash-object','-w','--stdin', input=content).stdout.strip()",
        "    # 2. Build a new tree containing the blob at <path>",
        "    parent   = _git('rev-parse', BRANCH).stdout.strip()",
        "    base_tree = _git('rev-parse', f'{BRANCH}^{{tree}}').stdout.strip()",
        "    new_tree  = _update_tree(base_tree, path, blob)",
        "    # 3. Commit the tree on top of the current HEAD",
        "    commit = _git('commit-tree', new_tree, '-p', parent,",
        "                  '-m', message).stdout.strip()",
        "    # 4. Advance the branch ref -- no checkout required",
        "    _git('update-ref', f'refs/heads/{BRANCH}', commit)",
    ))
    s.append(sp(0.04))

    # 3 -- SSE serve
    s += h2("3 -- Live SSE Server  (bob-log serve)")
    s.append(ps(
        "<code>ThreadingHTTPServer</code> -- SSE loop and export endpoint run concurrently. "
        "Viewer auto-detects <code>http:</code> vs <code>file:</code> and either connects the "
        "event stream or falls back to the JSON file picker."
    ))
    s.append(code(
        "class Handler(BaseHTTPRequestHandler):",
        "    def do_GET(self):",
        "        if self.path == '/api/stream':",
        "            self.send_header('Content-Type','text/event-stream')",
        "            last = ''",
        "            while True:  # poll every second",
        "                sha = _git('rev-parse', BRANCH).stdout.strip()",
        "                if sha != last:",
        "                    self.wfile.write(b'data: new-data\\n\\n'); last = sha",
        "                time.sleep(1)  # BrokenPipeError exits loop on disconnect",
        "        elif self.path == '/api/export':",
        "            data = cmd_export_json_inline()",
        "            self.wfile.write(json.dumps(data).encode())",
    ))
    s.append(sp(0.04))

    # Planning session screenshot (swapped to Figure 3)
    s += h2("Figure 3: Planning Session in IBM Bob Shell")
    s.append(ps(
        "Bob Shell v2.1.0 used throughout the hackathon. Bob read the slides, activated "
        "the create-plan skill, and drove the brainstorm that produced the full project plan."
    ))
    s += img("Image of application.png", max_w=PW, max_h=1.5*inch,
             caption_text="Bob Shell v2.1.0 -- Bob reads hackathon slides, activates create-plan skill, asks clarifying questions, brainstorms project ideas A-H, and writes CONTEXT.md.")

    return s

# ── PAGE 4: Testing, How to Run, Reflection ──────────────────────────────────
def page4():
    s = []

    s += h1("Testing")
    s.append(ps("Full <code>unittest</code> suite in <code>test_bob_log.py</code> -- zero external dependencies, runs against a real temp git repo."))
    s.append(sp(0.05))
    test_data = [
        ["Test", "Assertion"],
        ["test_init",       "bob-context ref exists after init; idempotent on second call"],
        ["test_write_read", "Write a file, read it back -- content matches exactly"],
        ["test_append",     "Write then append -- both parts present in final content"],
        ["test_ls",         "Write two files -- both appear in ls output"],
        ["test_export",     "Write a file, export to temp path -- file exists with correct content"],
        ["test_commit",     "Commit creates new SHA; log shows the commit message"],
        ["test_log",        "log returns commit history; --since filters to new commits only"],
        ["test_diff",       "diff shows unified diff between two versions of a file"],
    ]
    cw = [PW*0.28, PW*0.72]
    s.append(table2(test_data, cw, row_colors=[white, LGREY]))
    s.append(sp(0.06))

    s += h1("How to Run")
    s.append(code(
        "# 1. Clone the repo",
        "git clone https://github.com/Alexvu31/Minhnions-IBM-Hackathon.git",
        "# 2. Initialise the shadow branch",
        "python bob_log.py init",
        "# 3. Start the live viewer  (opens http://localhost:4242)",
        "python bob_log.py serve --port 4242",
        "# 4. Run the test suite",
        "python -m pytest test_bob_log.py -v",
    ))
    s.append(sp(0.06))

    s += h1("Team Reflection -- How We Built It With Bob")
    s.append(p(
        "<b>Bob was not just a code generator -- it was an active collaborator.</b> "
        "The project started with Bob reading the hackathon slides (see Figures 1 and 2). "
        "Bob proposed eight ideas, analysed each against the scoring rubric, converged on "
        "Bob Logbook, then wrote the full project plan with nine sub-tasks and a division of labour."
    ))
    s.append(sp(0.03))
    s.append(p(
        "Bob wrote the core git plumbing, debugged PowerShell encoding issues, designed the "
        "IBM Carbon chat UI for <code>viewer.html</code>, fixed the hook/viewer entry-format "
        "mismatch, and built the SSE server. Every decision was recorded in <code>CONTEXT.md</code> "
        "on the shadow branch -- evidence of the tool working."
    ))
    s.append(sp(0.03))
    s.append(p(
        "<b>Meta result: we used Bob Logbook to build Bob Logbook.</b> The shadow branch "
        "captured 40+ turns across two contributors. The SessionStart hook meant each new "
        "session started with a full summary of what changed -- no manual context-pasting."
    ))
    s.append(sp(0.05))

    s += h2("What We Would Do Next")
    for item in [
        "Remote sync: <code>bob-log pull/push</code> for true multi-machine coordination",
        "Conflict detection when two agents write the same file concurrently",
        "VS Code extension: sidebar surfacing the shadow branch without a browser",
        "LLM summarisation: <code>bob-log summarise</code> -- compress old entries",
    ]:
        s.append(bul(item))
    s.append(sp(0.05))

    # Footer credits bar
    fd = [[
        Paragraph("<b>Team Minhnions</b>  --  jaminleod &amp; alexvu31", SML),
        Paragraph("CIPS x IBM Hackathon 2024", SML),
        Paragraph("github.com/Alexvu31/Minhnions-IBM-Hackathon", SML),
    ]]
    ft = Table(fd, colWidths=[PW*f for f in [0.33, 0.27, 0.40]])
    ft.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), IBM_NAVY),
        ("TEXTCOLOR",     (0,0),(-1,-1), white),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ("RIGHTPADDING",  (0,0),(-1,-1), 8),
        ("TOPPADDING",    (0,0),(-1,-1), 7),
        ("BOTTOMPADDING", (0,0),(-1,-1), 7),
        ("ALIGN",         (2,0),(2,0), "RIGHT"),
    ]))
    s.append(ft)
    return s

# ── Build ─────────────────────────────────────────────────────────────────────
def build():
    out = "FinalSubmission.pdf"
    doc = SimpleDocTemplate(
        out, pagesize=letter,
        leftMargin=MG, rightMargin=MG, topMargin=MG, bottomMargin=MG + 0.12*inch,
        title="Bob Logbook -- CIPS x IBM Hackathon Submission",
        author="Team Minhnions (jaminleod, alexvu31)",
    )
    story = []
    story += page1(); story.append(PageBreak())
    story += page2(); story.append(PageBreak())
    story += page3(); story.append(PageBreak())
    story += page4()
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    print(f"[OK] PDF written -> {out}")

if __name__ == "__main__":
    build()
