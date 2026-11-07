import html
import random
from datetime import datetime
from zoneinfo import ZoneInfo
import streamlit as st

st.set_page_config(page_title="X-Market", page_icon="🚀", layout="wide",
                   initial_sidebar_state="collapsed")
TZ = ZoneInfo("Europe/Tallinn")
PAGE_INCREMENT = 50

TABS = ["🎁 Tasuta asjad", "🚘 Garaažid", "🌿 Aiatööd", "🛒 Toit", "🛠️ Tööriistad", "📈 Aktsiad"]

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family:'Inter',sans-serif; -webkit-text-size-adjust:100%; }
.stApp { background:#030712; color:#f3f4f6; }
.hero { padding:1.4rem 1.6rem; background:linear-gradient(135deg,#0f172a,#1e1b4b);
  border:1px solid #312e81; border-radius:16px; margin-bottom:1.2rem; }
.hero h1 { font-size:2rem; font-weight:800; margin:0 0 .3rem; color:#fff; letter-spacing:-.5px; }
.hero p { margin:0; color:#a5b4fc; font-size:.95rem; }

.card { background:#0f172a; border:1px solid #1e293b; border-radius:14px; padding:16px; margin-bottom:12px; }
.card:hover { border-color:#6366f1; }
.row { display:flex; gap:18px; align-items:stretch; }
.media { flex:0 0 220px; max-width:220px; }
.media img, .ph { width:100%; height:100%; min-height:150px; border-radius:10px; object-fit:cover; display:block; background:#1e293b; }
.ph { display:flex; align-items:center; justify-content:center; font-size:3rem; }
.body { flex:1; min-width:0; display:flex; flex-direction:column; gap:10px; }
.head { display:flex; justify-content:space-between; gap:12px; align-items:flex-start; }
.title { font-size:1.1rem; font-weight:700; color:#f9fafb; line-height:1.35; }
.when { font-size:.78rem; color:#9ca3af; white-space:nowrap; }
.price { font-size:1.35rem; font-weight:800; color:#fff; white-space:nowrap; text-align:right; }
.price small { display:block; font-size:.72rem; font-weight:500; color:#9ca3af; }
.desc { font-size:.9rem; color:#cbd5e1; line-height:1.5; }

.facts { display:grid; grid-template-columns:repeat(auto-fit,minmax(120px,1fr)); gap:8px; }
.fact { background:#111c33; border:1px solid #1e293b; border-radius:9px; padding:8px 10px; }
.fact span { display:block; font-size:.72rem; color:#94a3b8; margin-bottom:2px; }
.fact b { font-size:.9rem; color:#f1f5f9; font-weight:600; }
.up { color:#34d399 !important; } .down { color:#f87171 !important; }

.tag { display:inline-block; padding:3px 10px; border-radius:99px; font-size:.75rem; font-weight:600; margin-right:6px;
  background:rgba(99,102,241,.15); color:#a5b4fc; border:1px solid rgba(99,102,241,.3); }
.tag.green { background:rgba(16,185,129,.15); color:#34d399; border-color:rgba(16,185,129,.3); }
.tag.amber { background:rgba(234,179,8,.18); color:#fde047; border-color:rgba(234,179,8,.35); }

.btn { display:block; text-align:center; padding:11px 16px; background:#4f46e5; color:#fff !important;
  font-weight:700; font-size:.9rem; border-radius:10px; text-decoration:none !important; margin-top:auto; }
.btn:hover { background:#4338ca; }
.btn.off { background:#1f2937; color:#9ca3af !important; }

.range { height:6px; background:#1e293b; border-radius:9px; position:relative; margin:6px 0 2px; }
.range i { position:absolute; top:-3px; width:12px; height:12px; border-radius:50%; background:#818cf8; border:2px solid #0f172a; }
.rangelbl { display:flex; justify-content:space-between; font-size:.72rem; color:#94a3b8; }
.demo { background:#3b2f0b; border:1px solid #854d0e; color:#fde68a; padding:7px 12px; border-radius:8px;
  font-size:.8rem; display:inline-block; margin-bottom:10px; }

@media (max-width:768px) {
  .hero h1 { font-size:1.6rem; }
  .row { flex-direction:column; }
  .media { flex:none; max-width:100%; width:100%; }
  .media img, .ph { min-height:0; aspect-ratio:16/10; }
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def esc(v):
    return html.escape(str(v if v is not None else ""), quote=True)


def show(markup):
    st.markdown("\n".join(l.strip() for l in markup.splitlines() if l.strip()), unsafe_allow_html=True)


def matches(q, *fields):
    if not q:
        return True
    q = q.casefold().strip()
    return any(q in str(f or "").casefold() for f in fields)


def paginate(items, key):
    total = len(items)
    ck = f"count_{key}"
    st.session_state.setdefault(ck, PAGE_INCREMENT)
    n = min(total, st.session_state[ck])
    st.caption(f"Kokku {total} kirjet, näidatud {n}.")
    if n < total:
        c1, c2, _ = st.columns([1, 1, 4])
        if c1.button(f"Laadi veel {min(PAGE_INCREMENT, total - n)}", key=f"more_{key}"):
            st.session_state[ck] = n + PAGE_INCREMENT
            st.rerun()
        if c2.button(f"Laadi kõik ({total})", key=f"all_{key}"):
            st.session_state[ck] = total
            st.rerun()
    return items[:n]


def media(item):
    emoji = item.get("emoji", "📦")
    if item.get("image"):
        # onerror: kui pilt ei lae, asendub emoji-plokiga
        return (f'<div class="media"><img src="{esc(item["image"])}" loading="lazy" referrerpolicy="no-referrer" '
                f'alt="{esc(item["title"])}" onerror="this.outerHTML=\'<div class=ph>{emoji}</div>\'"></div>')
    return f'<div class="media"><div class="ph">{emoji}</div></div>'


def card(item, button_text):
    price = ""
    if item.get("price"):
        sub = f"<small>{esc(item['price_note'])}</small>" if item.get("price_note") else ""
        price = f'<div class="price">{esc(item["price"])}{sub}</div>'
    when = f'<div class="when">{esc(item["when"])}</div>' if item.get("when") else ""
    facts = "".join(
        f'<div class="fact"><span>{esc(k)}</span><b class="{cls}">{esc(v)}</b></div>'
        for k, v, cls in [(f + ("",))[:3] if len(f) == 2 else f for f in item.get("facts", [])]
    )
    tags = "".join(f'<span class="tag {c}">{esc(t)}</span>' for c, t in item.get("tags", []))
    link = item.get("link")
    btn = (f'<a class="btn" href="{esc(link)}" target="_blank" rel="noopener noreferrer">{esc(button_text)}</a>'
           if link else '<span class="btn off">Link puudub</span>')
    show(f"""
    <div class="card"><div class="row">
      {media(item)}
      <div class="body">
        <div class="head"><div><div class="title">{esc(item['title'])}</div>{when}</div>{price}</div>
        <div class="desc">{esc(item.get('description', ''))}</div>
        {f'<div class="facts">{facts}</div>' if facts else ''}
        {f'<div>{tags}</div>' if tags else ''}
        {btn}
      </div>
    </div></div>
    """)


def render(items, key, button_text, q, empty):
    flt = [i for i in items if matches(q, i["title"], i.get("description"), *[v for _, v, *_ in i.get("facts", [])])]
    if not flt:
        st.info(empty)
    for i in paginate(flt, key):
        card(i, button_text)


# ----------------------------- ANDMED ---------------------------------------
FB = "https://www.facebook.com/marketplace"
FREE = [
    {"title": "Kasutatud diivan (heas korras)", "emoji": "🛋️", "when": "Täna 12:30",
     "description": "Mugav lahtikäiv diivan. Ise äraviimisega.", "link": FB,
     "image": "https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=600&auto=format&fit=crop",
     "price": "Tasuta", "facts": [("Asukoht", "Tallinn"), ("Seisukord", "Hea"), ("Kätte saamine", "Ise järele")],
     "tags": [("green", "Tasuta")]},
    {"title": "Laste kirjutuslaud ja tool", "emoji": "🪑", "when": "Täna 10:15",
     "description": "Vähekasutatud reguleeritav kirjutuslaud koolijütsile.", "link": FB,
     "image": "https://images.unsplash.com/photo-1518455027359-f3f8164ba6bd?w=600&auto=format&fit=crop",
     "price": "Tasuta", "facts": [("Asukoht", "Tartu"), ("Seisukord", "Vähekasutatud"), ("Kätte saamine", "Ise järele")],
     "tags": [("green", "Tasuta")]},
    {"title": "Ehitusjäägid / puitmaterjal", "emoji": "🪵", "when": "Eile",
     "description": "Küttepuudeks või meisterdamiseks sobivad puidujäägid ja lauad.", "link": FB,
     "price": "Tasuta", "facts": [("Asukoht", "Pärnu"), ("Seisukord", "Jäägid"), ("Kätte saamine", "Ise järele")],
     "tags": [("green", "Tasuta")]},
]
GARAGES = [
    {"title": "Soe garaažiboks Mustamäel", "emoji": "🚘", "when": "Uus", "link": "https://www.kinnisvara24.ee",
     "description": "Kuiv ja turvaline garaaž, elekter olemas. Sobib auto hoidmiseks või laoks.",
     "image": "https://images.unsplash.com/photo-1506521781263-d8422e82f27a?w=600&auto=format&fit=crop",
     "price": "95 €", "price_note": "kuus",
     "facts": [("Asukoht", "Tallinn, Mustamäe"), ("Elekter", "Jah"), ("Küte", "Soe"), ("Aastas", "1 140 €")]},
    {"title": "Garaaž Annelinnas", "emoji": "🚘", "when": "2 päeva tagasi", "link": "https://www.kinnisvara24.ee",
     "description": "Metallist garaažiboks heas asukohas.",
     "image": "https://images.unsplash.com/photo-1590674899484-d5640e854abe?w=600&auto=format&fit=crop",
     "price": "75 €", "price_note": "kuus",
     "facts": [("Asukoht", "Tartu, Annelinn"), ("Valgustus", "Jah"), ("Ligipääs", "24/7"), ("Aastas", "900 €")]},
]
GARDEN = [
    {"title": "Heki pügamine ja korrastus", "emoji": "🌿", "when": "Täna", "link": "https://www.hange.ee",
     "description": "Vaja pügada umbes 30 m elupuuheekki ja viia oksad ära.",
     "image": "https://images.unsplash.com/photo-1585320806297-9794b3e4eeae?w=600&auto=format&fit=crop",
     "price": "350 €", "price_note": "keskmine pakkumine",
     "facts": [("Maht", "30 m hekk"), ("Pakkujaid", "4"), ("Hind / m", "11,67 €")]},
    {"title": "Muru rajamine ja tasandamine", "emoji": "🌱", "when": "Eile", "link": "https://www.hange.ee",
     "description": "Uue muru külvamine 600 m² alale, pinnase freesimine ja silumine.",
     "image": "https://images.unsplash.com/photo-1557429287-b2e26467fc2b?w=600&auto=format&fit=crop",
     "price": "1 200 €", "price_note": "keskmine pakkumine",
     "facts": [("Maht", "600 m²"), ("Pakkujaid", "7"), ("Hind / m²", "2,00 €")]},
]
GROCERIES = [  # nimi, hind, ühik, pood, link, emoji
    ("Banaanid", 0.99, "kg", "Lidl", "https://www.lidl.ee/et/search?q=banaan", "🍌"),
    ("Värske piim 2,5%", 0.69, "1 l", "Prisma", "https://www.prismamarket.ee/products/search/piim", "🥛"),
    ("Sea välisfilee", 5.99, "kg", "Rimi", "https://www.rimi.ee/epood/ee/otsing?query=sea%20välisfilee", "🥩"),
    ("Kohviuba President", 9.99, "1 kg", "Selver", "https://www.selver.ee/catalogsearch/result/?q=kohviuba", "☕"),
    ("Eesti või 82%", 1.89, "200 g", "Coop", "https://kodu.coop.ee/et/catalogsearch/result/?q=või", "🧈"),
    ("Värske kurk", 2.49, "kg", "Maxima", "https://www.barbora.ee/otsing?q=kurk", "🥒"),
]
TOOLS = [
    ("Akutrell DeWalt 18V (komplekt)", 149.00, "Bauhof", "https://www.bauhof.ee/et/catalogsearch/result/?q=akutrell", "🔧"),
    ("Ketassaag Makita 1200 W", 119.00, "K-Rauta", "https://www.k-rauta.ee/et/search?query=ketassaag", "🪚"),
    ("Survepesur Kärcher K5", 269.00, "Bauhof", "https://www.bauhof.ee/et/catalogsearch/result/?q=survepesur", "💦"),
]
STOCKS = [
    {"symbol": "NVDA", "name": "NVIDIA Corp.", "base": 128.50, "sector": "Tehisintellekt"},
    {"symbol": "AAPL", "name": "Apple Inc.", "base": 224.20, "sector": "Tarbeelektroonika"},
    {"symbol": "MSFT", "name": "Microsoft Corp.", "base": 448.30, "sector": "Pilv ja AI"},
    {"symbol": "TSLA", "name": "Tesla Inc.", "base": 242.10, "sector": "Autonoomsüsteemid ja energia"},
]




from urllib.parse import quote_plus
FB_SLUGS = {"Tallinn": "tallinn", "Tartu": "tartu"}  # teiste linnade slugid pole kontrollitud


def fb_search(title, city):
    """Facebook Marketplace'i otsing: linn + märksõna + hind 0 €."""
    kw = title.split("(")[0].strip()
    slug = FB_SLUGS.get(city)
    base = f"https://www.facebook.com/marketplace/{slug}/search/" if slug else "https://www.facebook.com/marketplace/search/"
    return f"{base}?query={quote_plus(kw)}&maxPrice=0&exact=false"

# ----------------------------- LAIENDATUD ANDMED ----------------------------
_rng = random.Random(42)
CITIES = ["Tallinn", "Tartu", "Pärnu", "Narva", "Viljandi", "Kuressaare", "Rakvere", "Haapsalu", "Jõhvi", "Võru"]
WHEN = ["Täna", "Eile", "2 päeva tagasi", "3 päeva tagasi", "Nädal tagasi"]

_free_t = [("Diivan", "🛋️"), ("Kirjutuslaud", "🪑"), ("Puitmaterjal", "🪵"), ("Lastevanker", "👶"), ("Raamaturiiul", "📚"),
           ("Külmik", "🧊"), ("Pesumasin", "🧺"), ("Jalgratas", "🚲"), ("Telekas", "📺"), ("Aiamööbel", "⛱️"),
           ("Laste mänguasjad", "🧸"), ("Riidekapp", "🚪"), ("Voodi", "🛏️"), ("Potililled", "🪴"), ("Kütteklotsid", "🔥")]
_cond = ["Hea", "Vähekasutatud", "Kulunud, töötab", "Remonti vajav"]
for n, e in _free_t:
    for c in _rng.sample(CITIES, 2):
        FREE.append({"title": f"{n} ({c})", "emoji": e, "when": _rng.choice(WHEN), "link": FB,
                     "description": f"{n} annetatakse tasuta. Ise äraviimisega.", "price": "Tasuta",
                     "facts": [("Asukoht", c), ("Seisukord", _rng.choice(_cond)), ("Kätte saamine", "Ise järele")],
                     "tags": [("green", "Tasuta")]})

for _it in FREE:
    _it["link"] = fb_search(_it["title"], dict(_it["facts"]).get("Asukoht", ""))

_dist = [("Tallinn", d) for d in ["Mustamäe", "Lasnamäe", "Õismäe", "Kristiine", "Nõmme", "Pirita", "Haabersti"]] + \
        [("Tartu", d) for d in ["Annelinn", "Karlova", "Ropka", "Tähtvere"]] + [("Pärnu", "Ranna"), ("Narva", "Kreenholm")]
for c, d in _dist:
    p = _rng.choice([60, 70, 75, 85, 95, 110, 130])
    el = _rng.choice([True, False]); warm = _rng.choice([True, False])
    GARAGES.append({"title": f"Garaažiboks, {d}", "emoji": "🚘",
                    "when": _rng.choice(WHEN), "link": "https://www.kinnisvara24.ee",
                    "description": "Garaažiboks auto või lao jaoks.", "price": f"{p} €", "price_note": "kuus",
                    "facts": [("Asukoht", f"{c}, {d}"), ("Elekter", "Jah" if el else "Ei"), ("Küte", "Soe" if warm else "Külm"),
                              ("Aastas", f"{p*12:,} €".replace(",", " ")), ("Pind", f"{_rng.choice([16, 18, 20, 24, 28])} m²")]})

_jobs = [("Heki pügamine", "m", 8, 15), ("Muru rajamine", "m²", 1.5, 3), ("Puude langetamine", "tk", 80, 250),
         ("Aia ehitus", "m", 40, 90), ("Platside sillutamine", "m²", 35, 70), ("Muruniitmine", "m²", 0.1, 0.3),
         ("Lume lükkamine", "korda", 25, 60), ("Peenarde rajamine", "m²", 6, 14), ("Terrassi ehitus", "m²", 60, 120)]
for name, unit, lo, hi in _jobs:
    for c in _rng.sample(CITIES, 2):
        qty = _rng.choice([10, 20, 30, 50, 100, 200, 600]) if unit != "tk" else _rng.randint(1, 6)
        up = _rng.uniform(lo, hi); tot = round(up * qty, -1) or round(up * qty)
        GARDEN.append({"title": f"{name} ({c})", "emoji": "🌿", "when": _rng.choice(WHEN), "link": "https://www.hange.ee",
                       "description": f"{name}, maht {qty} {unit}.", "price": f"{int(tot):,} €".replace(",", " "),
                       "price_note": "keskmine pakkumine",
                       "facts": [("Asukoht", c), ("Maht", f"{qty} {unit}"), ("Pakkujaid", str(_rng.randint(1, 9))),
                                 (f"Hind / {unit}", f"{tot/qty:.2f} €")]})

_gro = [("Rukkileib", 1.79, "800 g", "🍞"), ("Munad M (10 tk)", 3.09, "10 tk", "🥚"), ("Kartul", 0.89, "kg", "🥔"), ("Sibul", 0.99, "kg", "🧅"),
        ("Porgand", 0.95, "kg", "🥕"), ("Õunad", 1.79, "kg", "🍎"), ("Tomatid", 3.49, "kg", "🍅"), ("Kanafilee", 7.49, "kg", "🍗"),
        ("Hakkliha", 6.29, "kg", "🥩"), ("Juust Edam", 8.99, "kg", "🧀"), ("Jogurt naturaalne", 1.29, "400 g", "🥣"), ("Riis", 2.19, "kg", "🍚"),
        ("Makaronid", 1.39, "500 g", "🍝"), ("Päevalilleõli", 2.49, "1 l", "🌻"), ("Suhkur", 1.19, "kg", "🍬"), ("Jahu", 1.09, "kg", "🌾"),
        ("Šokolaad Kalev", 1.99, "100 g", "🍫"), ("Apelsinimahl", 1.99, "1 l", "🍊"), ("Tee Lipton", 2.79, "20 kotti", "🍵"), ("Lõhefilee", 16.9, "kg", "🐟")]
_stores = {"Lidl": "https://www.lidl.ee/et/search?q=", "Prisma": "https://www.prismamarket.ee/products/search/",
           "Rimi": "https://www.rimi.ee/epood/ee/otsing?query=", "Selver": "https://www.selver.ee/catalogsearch/result/?q=",
           "Coop": "https://kodu.coop.ee/et/catalogsearch/result/?q=", "Maxima": "https://www.barbora.ee/otsing?q="}
for n, p, u, e in _gro:
    for st_name in _rng.sample(list(_stores), 3):
        GROCERIES.append((n, round(p * _rng.uniform(0.92, 1.12), 2), u, st_name, _stores[st_name] + n.split()[0].lower(), e))

_tools = [("Kruvikeeraja komplekt Bosch", 39, "🪛"), ("Lööktrell Makita", 129, "🔨"), ("Nurklihvija Metabo 125 mm", 89, "⚙️"),
          ("Tikksaag Bosch", 99, "🪚"), ("Kompressor 50 l", 179, "🌬️"), ("Keevitusaparaat MIG", 259, "🔥"), ("Redel 3x9", 149, "🪜"),
          ("Tööriistakast 3-osaline", 69, "🧰"), ("Laserloodid", 79, "📏"), ("Aiakäärid Fiskars", 29, "✂️"), ("Murutraktor", 1499, "🚜"),
          ("Mootorsaag Stihl", 329, "🪵"), ("Veepump", 119, "💧"), ("Generaator 3 kW", 549, "⚡")]
for n, p, e in _tools:
    for s_ in _rng.sample(["Bauhof", "K-Rauta", "Espak", "Ehituse ABC", "Decora"], 2):
        TOOLS.append((n, round(p * _rng.uniform(0.9, 1.15), 2), s_, f"https://www.google.com/search?q={n.replace(' ', '+')}+{s_}", e))

_more = [("GOOGL", "Alphabet Inc.", 178, "Internet"), ("AMZN", "Amazon.com", 186, "E-kaubandus ja pilv"), ("META", "Meta Platforms", 520, "Sotsiaalmeedia"),
         ("AMD", "Advanced Micro Devices", 160, "Kiibid"), ("AVGO", "Broadcom", 165, "Kiibid"), ("TSM", "TSMC", 175, "Kiibitootmine"),
         ("NFLX", "Netflix", 680, "Voogedastus"), ("ASML", "ASML Holding", 900, "Kiibiseadmed"), ("PLTR", "Palantir", 30, "Andmeanalüütika"),
         ("CRM", "Salesforce", 270, "Pilvetarkvara"), ("INTC", "Intel", 31, "Kiibid"), ("ORCL", "Oracle", 140, "Pilv ja andmebaasid"),
         ("ADBE", "Adobe", 520, "Tarkvara"), ("UBER", "Uber", 70, "Mobiilsus"), ("SHOP", "Shopify", 75, "E-kaubandus"), ("COIN", "Coinbase", 230, "Krüpto")]
for sym, nm, b, sec in _more:
    STOCKS.append({"symbol": sym, "name": nm, "base": float(b), "sector": sec})


@st.cache_data(ttl=300, show_spinner=False)
def live_quotes(symbols):
    """Päris hinnad yfinance'ist; tagastab {} kui pole saadaval."""
    try:
        import yfinance as yf
        df = yf.download(list(symbols), period="5d", interval="1d", progress=False, group_by="ticker", auto_adjust=True)
        out = {}
        for sym in symbols:
            c = df[sym]["Close"].dropna()
            if len(c) >= 2:
                out[sym] = (float(c.iloc[-1]), float(c.iloc[-2]))
        return out
    except Exception:
        return {}


def store_filter(key, stores):
    return st.selectbox("Pood:", ["Kõik"] + sorted(stores), key=key)


def demo_notice(text):
    show(f'<div class="demo">⚠️ {esc(text)}</div>')


# ----------------------------- VAATED ---------------------------------------
def food(q):
    demo_notice("Hinnad on demo: need on juhuslikult muudetud, mitte poodidest loetud.")
    sel = store_filter("sf_food", {g[3] for g in GROCERIES})
    minute = datetime.now(TZ).minute
    items = []
    for name, base, unit, store, link, emoji in GROCERIES:
        random.seed(f"{name}{minute}")
        p = round(base * random.uniform(0.95, 1.05), 2)
        diff = (p / base - 1) * 100
        items.append({
            "title": name, "emoji": emoji, "link": link,
            "description": f"Hind pakendi kohta ({unit}).",
            "price": f"{p:.2f} €", "price_note": f"/ {unit}",
            "facts": [("Pood", store), ("Viitehind", f"{base:.2f} €"),
                      ("Muutus", f"{diff:+.1f}%", "up" if diff <= 0 else "down")],
            "tags": [("green", "Alla viitehinna")] if diff < 0 else [],
        })
    flt = [i for i in items if (sel == "Kõik" or i["facts"][0][1] == sel) and matches(q, i["title"], i["facts"][0][1])]
    for i in paginate(flt, "food"):
        card(i, "Ava toote leht")


def tools(q):
    sel = store_filter("sf_tools", {t[2] for t in TOOLS})
    items = [{"title": n, "emoji": e, "link": l, "description": "Tööriist ehituseks ja mehaanikaks.",
              "price": f"{p:.2f} €", "facts": [("Tarnija", s)]} for n, p, s, l, e in TOOLS]
    flt = [i for i in items if (sel == "Kõik" or i["facts"][0][1] == sel) and matches(q, i["title"], i["facts"][0][1])]
    for i in paginate(flt, "tools"):
        card(i, "Vaata toodet")


def invest(q):
    quotes = live_quotes(tuple(a["symbol"] for a in STOCKS))
    if quotes:
        st.caption(f"Päris hinnad (yfinance, viimane sulgemine). Kaetud {len(quotes)}/{len(STOCKS)} tickerit. See ei ole investeerimisnõuanne.")
    else:
        demo_notice("Päris hindu ei saanud laadida (lisa requirements.txt faili yfinance). Näidatakse juhuslikke demoandmeid.")
    minute = datetime.now(TZ).minute
    shown = [a for a in STOCKS if matches(q, a["name"], a["symbol"], a["sector"])]
    for a in paginate(shown, "stocks"):
        is_live = a["symbol"] in quotes
        if is_live:
            price, prev = quotes[a["symbol"]]
        else:
            random.seed(f"{a['symbol']}{minute}")
            prev = a["base"]; price = prev * (1 + random.uniform(-1.8, 1.8) / 100)
        ch = (price / prev - 1) * 100
        lo, hi = prev * 0.982, prev * 1.018
        pos = max(0, min(100, (price - lo) / (hi - lo) * 100))
        cls = "up" if ch >= 0 else "down"
        signal, tcls = (("Odav hetk", "green") if ch < -1.0 else ("Kallis hetk", "amber") if ch > 1.2 else ("Neutraalne", ""))
        show(f"""
        <div class="card"><div class="body">
          <div class="head">
            <div><div class="title">{esc(a['name'])} ({esc(a['symbol'])})</div><div class="when">{esc(a['sector'])}</div></div>
            <div class="price">${price:,.2f}<small class="{cls}">{ch:+.2f}%</small></div>
          </div>
          <div class="facts">
            <div class="fact"><span>Eelmine sulgemine</span><b>${prev:,.2f}</b></div>
            <div class="fact"><span>Muutus dollarites</span><b class="{cls}">${price - prev:+.2f}</b></div>
            <div class="fact"><span>Vahemik ±1,8%</span><b>${lo:,.2f} – ${hi:,.2f}</b></div>
          </div>
          <div><div class="range"><i style="left:{pos}%"></i></div>
          <div class="rangelbl"><span>${lo:,.2f}</span><span>${hi:,.2f}</span></div></div>
          <div><span class="tag {tcls}">{signal}</span>{'' if is_live else '<span class="tag amber">Demohind</span>'}</div>
        </div></div>
        """)


# ----------------------------- ROUTER ---------------------------------------
show('<div class="hero"><h1>🚀 X-Market</h1><p>Tasuta asjad, garaažid, aiatööd, toidukaupade hinnad, tööriistad ja aktsiad ühes kohas.</p></div>')
q = st.text_input("Otsi", placeholder="nt muru, piim, akutrell, NVIDIA…", label_visibility="collapsed")
tab = st.radio("Moodul", TABS, horizontal=True, label_visibility="collapsed")

if tab == TABS[0]:
    render(FREE, "free", "Otsi Facebook Marketplace'ist", q, "Tasuta asju ei leitud.")
elif tab == TABS[1]:
    render(GARAGES, "garages", "Ava kuulutus", q, "Garaaže ei leitud.")
elif tab == TABS[2]:
    render(GARDEN, "garden", "Ava Hange.ee", q, "Hankeid ei leitud.")
elif tab == TABS[3]:
    food(q)
elif tab == TABS[4]:
    tools(q)
else:
    invest(q)
