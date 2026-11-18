"""Visual theme and small HTML builders for the Streamlit UI."""
from html import escape

from waste_utils import CATEGORIES, CATEGORY_INFO

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@500;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

:root {
  --ink: #10231B;
  --field: #EDF2EF;
  --panel: #FFFFFF;
  --sprout: #0F7B55;
  --muted: #5B6B63;
  --line: #D5DFD9;
}

html, body, [data-testid="stAppViewContainer"], [data-testid="stMarkdownContainer"] {
  font-family: 'IBM Plex Sans', 'Segoe UI', Helvetica, Arial, sans-serif;
}
[data-testid="stAppViewContainer"] { background: var(--field); }
[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 2rem; max-width: 1180px; }

h1, h2, h3, .hero h1 {
  font-family: 'Bricolage Grotesque', 'Segoe UI', Helvetica, Arial, sans-serif;
  color: var(--ink);
  letter-spacing: -0.01em;
}
h2, h3 { font-weight: 700; }

/* Hero */
.hero {
  background: var(--ink);
  color: #F2F7F4;
  border-radius: 20px;
  padding: 2rem 2.2rem 1.6rem;
  display: flex;
  flex-wrap: wrap;
  gap: 1.5rem 2.5rem;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 1.4rem;
}
.hero-text { flex: 1 1 340px; max-width: 520px; }
.hero h1 { color: #F2F7F4; font-size: 2.3rem; line-height: 1.1; margin: 0 0 .7rem; padding: 0; }
.hero p { color: #B8CBC1; font-size: 1rem; line-height: 1.55; margin: 0; }

.bins { display: flex; gap: 10px; align-items: flex-end; flex-wrap: wrap; }
.bin { width: 54px; text-align: center; }
.bin .lid { height: 8px; border-radius: 4px 4px 1px 1px; margin: 0 -3px; }
.bin .body { height: 58px; border-radius: 2px 2px 8px 8px; }
.bin span { display: block; margin-top: 6px; font-size: .72rem; color: #B8CBC1; line-height: 1.2; }

/* Steps for the empty state */
.steps { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; margin-top: .6rem; }
.step { background: var(--panel); border: 1px solid var(--line); border-radius: 14px; padding: 1rem 1.1rem; }
.step b { font-family: 'Bricolage Grotesque', sans-serif; font-size: 1.05rem; color: var(--ink); }
.step p { margin: .35rem 0 0; color: var(--muted); font-size: .92rem; line-height: 1.5; }
.step .n { display: inline-block; width: 1.7rem; height: 1.7rem; line-height: 1.7rem; text-align: center;
  background: var(--sprout); color: #fff; border-radius: 50%; margin-right: .5rem; font-weight: 600; font-size: .9rem; }

/* Disposal guide: the left stripe is the bin colour itself */
.guide { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; }
.guide-item {
  background: var(--panel); border: 1px solid var(--line); border-left-width: 8px;
  border-radius: 12px; padding: .9rem 1rem;
}
.guide-item .top { display: flex; justify-content: space-between; align-items: baseline; gap: .5rem; }
.guide-item .cat { font-family: 'Bricolage Grotesque', sans-serif; font-weight: 700; font-size: 1.1rem; color: var(--ink); }
.guide-item .share { font-weight: 600; color: var(--ink); }
.guide-item .where { color: var(--muted); font-size: .88rem; margin: .15rem 0 .45rem; }
.guide-item .tip { color: #2B3B33; font-size: .92rem; line-height: 1.5; margin: 0; }
.route { display: inline-block; font-size: .78rem; font-weight: 600; padding: .1rem .55rem; border-radius: 999px;
  background: var(--field); color: var(--ink); margin-left: .4rem; }

/* Metrics */
[data-testid="stMetric"] {
  background: var(--panel); border: 1px solid var(--line); border-radius: 14px; padding: .8rem 1rem;
}
[data-testid="stMetricValue"] { font-family: 'Bricolage Grotesque', sans-serif; color: var(--ink); }

/* Tabs + buttons */
.stTabs [data-baseweb="tab-list"] { gap: 6px; }
.stTabs [data-baseweb="tab"] { font-weight: 600; }
.stDownloadButton button, .stButton button { border-radius: 10px; font-weight: 600; }

[data-testid="stSidebar"] { background: #E2EAE5; }
.footer { margin-top: 2.5rem; padding-top: 1rem; border-top: 1px solid var(--line); color: var(--muted); font-size: .85rem; }

@media (max-width: 640px) { .hero h1 { font-size: 1.7rem; } .hero { padding: 1.4rem 1.2rem; } }
@media (prefers-reduced-motion: reduce) { * { transition: none !important; animation: none !important; } }
</style>
"""


def hero_html() -> str:
    bins = "".join(
        f'<div class="bin"><div class="lid" style="background:{CATEGORY_INFO[c]["color"]}"></div>'
        f'<div class="body" style="background:{CATEGORY_INFO[c]["color"]}"></div>'
        f'<span>{escape(c.split(" / ")[0])}</span></div>'
        for c in CATEGORIES
    )
    return (
        '<div class="hero"><div class="hero-text">'
        "<h1>Photograph your waste. Get it into the right bin.</h1>"
        "<p>The app outlines every object it can see, lets you confirm what it is made of, "
        "and shows how much of the pile can be recycled, composted or reused.</p>"
        f'</div><div class="bins">{bins}</div></div>'
    )


def steps_html() -> str:
    steps = [
        ("Add a photo", "Upload an image or take one with your camera."),
        ("Check the outlines", "Each object gets a mask. Fix any category the model guessed wrong."),
        ("Read the guide", "See area shares, where each item goes, and download the report."),
    ]
    items = "".join(
        f'<div class="step"><span class="n">{i}</span><b>{escape(t)}</b><p>{escape(d)}</p></div>'
        for i, (t, d) in enumerate(steps, 1)
    )
    return f'<div class="steps">{items}</div>'


def guide_html(shares: dict[str, float]) -> str:
    """shares: category -> percent of detected area."""
    cards = []
    for category, share in shares.items():
        info = CATEGORY_INFO[category]
        cards.append(
            f'<div class="guide-item" style="border-left-color:{info["color"]}">'
            f'<div class="top"><span class="cat">{escape(category)}</span>'
            f'<span class="share">{share:.1f}%</span></div>'
            f'<div class="where">{escape(info["bin"])}<span class="route">{escape(info["route"])}</span></div>'
            f'<p class="tip">{escape(info["tip"])}</p></div>'
        )
    return f'<div class="guide">{"".join(cards)}</div>'
