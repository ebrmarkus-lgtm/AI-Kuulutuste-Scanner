"""THANOS: üks app.py. streamlit, requests, beautifulsoup4.
Serveri mälus töötav ajastaja; ei ole välise ajastaja ega püsiva andmebaasi asendus.
"""
import copy
import csv
import hashlib
import html
import io
import json
import os
import re
import threading
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlsplit, urlunsplit, quote
from zoneinfo import ZoneInfo
import requests
import streamlit as st
import streamlit.components.v1 as components
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

VERSION='thanos-1.0'
st.set_page_config(page_title='⚡ Skänner THANOS',page_icon='⚡',layout='wide',initial_sidebar_state='expanded')
st.markdown("""<style>
.stApp{background:#0b0f19;color:#e2e8f0}[data-testid="stSidebar"]{background:#111827}
.hero{padding:12px 0 22px;border-bottom:1px solid #334155;margin-bottom:18px}.hero h1{color:#f8fafc;margin:0;font-size:2.1rem}.hero p{color:#a5b4c7}
.pro-card{background:linear-gradient(130deg,#111827,#16162b);border:1px solid #334155;border-radius:16px;padding:22px;margin:16px 0 5px;box-shadow:0 5px 22px #0004;overflow-wrap:anywhere}.card-row{display:flex;gap:22px;align-items:flex-start}.card-img{width:270px;aspect-ratio:4/3;object-fit:cover;border-radius:12px;flex-shrink:0}.card-body{flex:1;min-width:0}.card-title{font-size:1.22rem;font-weight:750;color:#f8fafc}.card-meta{color:#a5b4c7;font-size:.83rem;margin:8px 0}.card-desc{white-space:pre-wrap;line-height:1.6;color:#cbd5e1}.badge{display:inline-block;padding:5px 11px;border-radius:22px;border:1px solid #475569;margin:4px 5px 10px 0;font-size:.79rem}.price{color:#fde68a;border-color:#a16207}a.pro-btn{display:inline-block;background:#7c3aed;color:#fff!important;padding:11px 18px;border-radius:10px;text-decoration:none;margin:12px 8px 0 0}.secondary{background:#334155!important}
@media(max-width:750px){.card-row{display:block}.card-img{width:100%;max-height:280px;margin-bottom:15px}.pro-card{padding:15px}.hero h1{font-size:1.6rem}}
</style>""",unsafe_allow_html=True)
st.markdown('<div class="hero"><h1>⚡ Kuulutuste Skänner · THANOS</h1><p>RSS 1 h · Autod 48 h · Garaažid 24 h · Kütus 1 h</p></div>',unsafe_allow_html=True)
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
KV_URL='https://kinnisvara24.ee/garaaz/muuk/harju-maakond'
AS_BASE='https://www.autoscout24.com'
AS_URL=AS_BASE+'/lst/renault/r-5/bc_yellow'
FB_GROUP='https://www.facebook.com/groups/1929529077371716'
FUEL_URL='https://www.1182.ee/kytusehinnad'
RATING_URL='https://reitingud.ee/reitingud/'
INTERVALS={'rss':3600,'cars':172800,'kv':86400,'fuel':3600,'food':21600,'ratings':86400}
LABELS={'rss':'Facebooki RSS','cars':'Renault 5 EV','kv':'Harjumaa garaažid','fuel':'Kütusehinnad','food':'Toidupakkumised','ratings':'Eesti reitingud'}
STORES=[('Selver','https://www.selver.ee'),('Rimi','https://www.rimi.ee'),('Maxima','https://www.maxima.ee'),('Coop','https://www.coop.ee')]
TZ=ZoneInfo('Europe/Tallinn')

def esc(x): return html.escape(str(x if x is not None else ''),quote=True).replace('$','&#36;')
def plain(x): return BeautifulSoup(str(x or ''),'html.parser').get_text(' ',strip=True)
def safe_url(value,base=''):
    if not isinstance(value,str) or not value.strip(): return ''
    try:
        value=urljoin(base,value.strip()) if base else value.strip(); p=urlsplit(value)
        if p.scheme in ('http','https') and p.hostname and not p.username and not p.password: return value
    except ValueError: pass
    return ''
def fmt_date(ts): return datetime.fromtimestamp(ts,TZ).strftime('%d.%m.%Y %H:%M') if ts else '—'
def timestamp(x):
    for fn in (parsedate_to_datetime,lambda s:datetime.fromisoformat(s.replace('Z','+00:00'))):
        try:
            d=fn(str(x)); return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).timestamp()
        except (ValueError,TypeError,OverflowError): pass
    return None

def numeric(x):
    if isinstance(x,(int,float)): return float(x)
    s=re.sub(r'[^\d,.]','',str(x or ''))
    if not s: return None
    if ',' in s and '.' in s: s=s.replace(',','') if s.rfind('.')>s.rfind(',') else s.replace('.','').replace(',','.')
    elif re.fullmatch(r'\d{1,3}([,.]\d{3})+',s): s=re.sub('[,.]','',s)
    else: s=s.replace(',','.')
    try: return float(s)
    except ValueError: return None

def price_of(text):
    m=re.search(r'(\d[\d\s.,]*?)\s*(?:€|EUR\b|eurot\b)|€\s*(\d[\d\s.,]*)',text,re.I)
    return numeric(next(g for g in m.groups() if g is not None)) if m else None

def money(value):
    if value is None: return 'Hind teadmata'
    return (f'{value:,.2f}' if value%1 else f'{value:,.0f}').replace(',',' ')+' €'

def record(source,title,desc,link,**extras):
    link=safe_url(link); title=plain(title) or 'Pealkirjata'; desc=plain(desc)
    if link:
        p=urlsplit(link); canonical=urlunsplit((p.scheme,p.netloc.lower(),p.path.rstrip('/'),p.query,''))
    else: canonical=title+desc
    ident=hashlib.sha256((source+':'+canonical).encode()).hexdigest()[:24]
    return dict(id=ident,source=source,title=title,description=desc,link=link,**extras)

def unique(items):
    out={}
    for i in items:
        old=out.get(i['id'])
        if old is None or (old.get('price_val') is None and i.get('price_val') is not None): out[i['id']]=i
    return list(out.values())

def get_bytes(url,limit=10_000_000):
    retry=Retry(total=1,backoff_factor=.4,status_forcelist=[429,500,502,503,504],allowed_methods=['GET'],respect_retry_after_header=False)
    with requests.Session() as s:
        for scheme in ('https://','http://'): s.mount(scheme,HTTPAdapter(max_retries=retry))
        with s.get(url,headers={'User-Agent':UA,'Accept-Language':'et-EE,et;q=0.9,en;q=0.8'},timeout=(5,14),stream=True) as r:
            r.raise_for_status(); data=bytearray(); started=time.monotonic()
            for chunk in r.iter_content(65536):
                data.extend(chunk)
                if len(data)>limit: raise ValueError('Allika vastus ületab suurusepiirangu.')
                if time.monotonic()-started>35: raise TimeoutError('Allika lugemise ajapiir ületatud.')
            return bytes(data)

def dictionaries(value):
    if isinstance(value,dict):
        yield value
        for child in value.values():
            if isinstance(child,(dict,list)): yield from dictionaries(child)
    elif isinstance(value,list):
        for child in value: yield from dictionaries(child)

def json_documents(soup):
    for script in soup.find_all('script'):
        if script.get('type')=='application/ld+json' or script.get('id')=='__NEXT_DATA__':
            try: yield json.loads(script.string or script.get_text())
            except (ValueError,TypeError): pass

def dig(obj,*path):
    for key in path:
        if not isinstance(obj,dict): return None
        obj=obj.get(key)
    return obj

def image_of(obj,base=''):
    if isinstance(obj,list): obj=obj[0] if obj else ''
    if isinstance(obj,dict): obj=obj.get('url') or obj.get('contentUrl') or obj.get('src') or ''
    return safe_url(obj,base)

def structured_offers(soup,base,source):
    out=[]
    for document in json_documents(soup):
        for raw in dictionaries(document):
            types=raw.get('@type',[]); types=types if isinstance(types,list) else [types]
            if not set(types).intersection({'Product','RealEstateListing','House','Apartment','Residence','Accommodation','Vehicle','Car'}): continue
            title=raw.get('name') or raw.get('headline'); link=raw.get('url'); offers=raw.get('offers') or {}
            if isinstance(link,dict): link=link.get('@id')
            if isinstance(offers,list): offers=offers[0] if offers else {}
            price=None
            if isinstance(offers,dict):
                link=link or offers.get('url')
                if str(offers.get('priceCurrency','')).upper()=='EUR': price=numeric(offers.get('price'))
            link=safe_url(link,base)
            if title and link:
                out.append(record(source,title,raw.get('description') or title,link,price_val=price,image=image_of(raw.get('image'),base),location=''))
    return out

def card_image(node,base):
    img=node.find('img')
    if not img: return ''
    return safe_url(img.get('data-src') or img.get('src') or (img.get('srcset') or '').split(',')[0].split(' ')[0],base)

def classify(text):
    for kind,pattern in [('Mitte saadaval',r'\b(broneeritud|ära antud|müüdud|juba läinud)\b'),('Soovikuulutus',r'\b(otsin|soovin|ostan|võtan vastu|ищу|куплю)\b'),('Tingimuslik / tasuline',r'\b(tasu eest|šokolaadi vastu|tasuta transport|tasuta tarne)\b'),('Tasuta pakkumine',r'\b(tasuta|annan ära|ära anda|kingin|võib ära viia|free|giving away|give away|отдам|бесплатно|даром)\b')]:
        m=re.search(pattern,text,re.I)
        if m:
            if kind=='Tasuta pakkumine' and (price_of(text) or 0)>0: return 'Ebaselge','Tekstis on nii tasuta pakkumine kui ka hind.'
            return kind,'Leitud sõnastus: '+m.group(0)
    return 'Ebaselge','Tasuta pakkumise selget tunnust ei leitud.'

def location_hint(text):
    if re.search(r'\b(tallinn\w*|mustamä\w*|lasnamä\w*|õismä\w*|nõmme\w*|kristiine\w*|pirita\w*|таллин\w*)\b',text,re.I): return 'Tallinn (tekstist)'
    if re.search(r'\b(harju\w*|viimsi\w*|maardu\w*|keila\w*|saue\w*|saku\w*)\b',text,re.I): return 'Harjumaa (tekstist)'
    return 'Asukoht teadmata'

def fetch_rss(url):
    raw=get_bytes(url,5_000_000)
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper(): raise ValueError('XML DTD pole toetatud.')
    root=ET.fromstring(raw)
    def tag(n): return n.tag.rsplit('}',1)[-1].lower()
    def field(n,names):
        for name in names:
            for child in n:
                if tag(child)==name and child.text: return child.text.strip()
        return ''
    if tag(root) not in ('rss','rdf','feed'): raise ValueError('Vastus ei ole RSS ega Atom.')
    nodes=[n for n in root.iter() if tag(n) in ('item','entry')]; out=[]
    for n in nodes:
        title=plain(field(n,['title'])); raw_desc=field(n,['encoded','description','content','summary']); desc=plain(raw_desc); link=''; image=''
        for c in n:
            if tag(c)=='link' and c.attrib.get('rel','alternate')=='alternate':
                link=safe_url(c.attrib.get('href') or c.text)
                if link: break
        for c in n.iter():
            if tag(c) in ('thumbnail','enclosure','content') and (tag(c)=='thumbnail' or c.attrib.get('type','').startswith('image/') or c.attrib.get('medium')=='image'):
                image=safe_url(c.attrib.get('url'))
                if image: break
        image=image or card_image(BeautifulSoup(raw_desc,'html.parser'),url)
        kind,reason=classify(title+' '+desc)
        out.append(record('rss',title,desc,link,image=image,kind=kind,reason=reason,location=location_hint(title+' '+desc),timestamp=timestamp(field(n,['pubdate','published','updated','date']))))
    return dict(items=unique(out),report=[f'RSS-is {len(nodes)} kirjet.'])

def fetch_kv():
    soup=BeautifulSoup(get_bytes(KV_URL),'html.parser'); out=structured_offers(soup,KV_URL,'kv'); report=[f'Struktureeritud pakkumisi: {len(out)}']
    def detail(value):
        link=safe_url(value,KV_URL)
        if not link or urlsplit(link).hostname not in ('kinnisvara24.ee','www.kinnisvara24.ee'): return ''
        path=urlsplit(link).path.rstrip('/')
        if path==urlsplit(KV_URL).path.rstrip('/'): return ''
        if re.search(r'/(login|blog|kontakt|statistika|privaatsus)(/|$)',path): return ''
        return link if re.search(r'/(kinnisvara|objekt)/|(?:-\d{4,}|/[0-9a-f]{8}-[0-9a-f-]{20,})$',path,re.I) else ''
    # Next.js and JSON-LD: search object fields, not undocumented external APIs.
    for document in json_documents(soup):
        for obj in dictionaries(document):
            title=obj.get('title') or obj.get('name') or obj.get('heading')
            link=detail(obj.get('url') or obj.get('link') or obj.get('href'))
            if not isinstance(title,str) or not link: continue
            price=obj.get('price') or obj.get('salePrice')
            if isinstance(price,dict): price=price.get('value') or price.get('amount')
            out.append(record('kv',title,obj.get('description') or title,link,price_val=numeric(price),image=image_of(obj.get('images') or obj.get('image'),KV_URL),location='Harjumaa otsing'))
    def links(node): return {detail(a.get('href')).split('?')[0] for a in node.find_all('a',href=True) if detail(a.get('href'))}
    for a in soup.find_all('a',href=True):
        link=detail(a.get('href'))
        if not link: continue
        card=a
        for _ in range(8):
            text=card.get_text(' ',strip=True)
            if len(links(card))==1 and len(text)>25 and ('€' in text or card.name=='article'): break
            parent=card.parent
            if not parent or parent.name in ('body','html') or len(links(parent))>1: break
            card=parent
        heading=card.find(['h2','h3','h4']); title=heading.get_text(' ',strip=True) if heading else a.get_text(' ',strip=True)
        title=title or a.get('aria-label') or a.get('title') or ''
        if len(title)<5: continue
        text=card.get_text(' ',strip=True); price_text=re.sub(r'\d[\d\s.,]*\s*€\s*/\s*m(?:²|2)?','',text,flags=re.I)
        out.append(record('kv',title,text,link,price_val=price_of(price_text),image=card_image(card,KV_URL),location='Harjumaa otsing'))
    out=unique(out); report.append(f'Kokku unikaalseid: {len(out)}')
    if not out: raise RuntimeError('KV24 vastas, aga JSON/HTML parser ei leidnud detailpakkumisi. Varasemat tulemust ei kustutatud.')
    return dict(items=out,report=report)

def electric_r5(title,text,url):
    t=(title+' '+text).lower()
    model='renault-r-5' in url.lower() or re.search(r'\brenault\s*(?:r[- ]?)?5\b|\br[- ]?5\b',t)
    electric=re.search(r'e[ -]?tech|electric|elektr|électri|elettric|eléctri|evolution|iconic|techno|comfort range|urban range',t)
    return bool(model and electric)

def battery(text):
    m=re.search(r'\b(40|52)\s*kwh\b',text,re.I)
    return m.group(0) if m else ''

def fetch_car_page(page):
    report=[]
    for suffix in (f'?sort=price&desc=0&page={page}',f'?page={page}'):
        try:
            soup=BeautifulSoup(get_bytes(AS_URL+suffix),'html.parser'); out=[]
            for document in json_documents(soup):
                for obj in dictionaries(document):
                    vehicle=obj.get('vehicle')
                    if not isinstance(vehicle,dict): continue
                    model=vehicle.get('model') or 'R 5'
                    if isinstance(model,dict): model=model.get('name','R 5')
                    title='Renault '+str(model)+' '+str(vehicle.get('modelVersionInput') or vehicle.get('variant') or '')
                    link=safe_url(obj.get('url'),AS_BASE)
                    if not link or not electric_r5(title,json.dumps(obj,ensure_ascii=False),link): continue
                    price=dig(obj,'price','priceRaw') or dig(obj,'prices','public','priceRaw') or dig(obj,'price','priceFormatted') or dig(obj,'tracking','price')
                    loc=obj.get('location') or {}; loc=loc if isinstance(loc,dict) else {}
                    location=', '.join(str(loc.get(k)) for k in ('city','countryCode') if loc.get(k)) or 'Euroopa'
                    km=dig(obj,'tracking','mileage') or vehicle.get('mileageInKm'); reg=dig(obj,'tracking','firstRegistration'); seller=dig(obj,'seller','companyName')
                    desc=' · '.join(x for x in [('Esmane reg. '+str(reg)) if reg else '',str(km)+' km' if km is not None else '',str(seller or '')] if x)
                    out.append(record('cars',title,desc,link,price_val=numeric(price),image=image_of(obj.get('images'),AS_BASE),location=location,battery=battery(title)))
            if not out:
                for a in soup.find_all('a',href=re.compile('/offers/')):
                    link=safe_url(a.get('href'),AS_BASE); card=a
                    if not link: continue
                    for _ in range(9):
                        if card.find(['h2','h3']) and '€' in card.get_text(): break
                        if not card.parent or card.parent.name in ('body','html'): break
                        card=card.parent
                    distinct={x.get('href','').split('?')[0] for x in card.find_all('a',href=re.compile('/offers/'))}
                    if len(distinct)>1: continue
                    heading=card.find(['h2','h3']); title=heading.get_text(' ',strip=True) if heading else a.get_text(' ',strip=True); text=card.get_text(' ',strip=True)
                    if electric_r5(title,text,link): out.append(record('cars',title,text,link,price_val=price_of(text),image=card_image(card,AS_BASE),location='Euroopa — vt kirjeldust',battery=battery(text)))
            if out: return unique(out),f'Leht {page}: {len(unique(out))} tulemust'
        except Exception as exc:
            report.append(type(exc).__name__)
    return [],f'Leht {page}: tulemusi ei eraldatud ({", ".join(report) or "HTML struktuur"})'

def fetch_cars():
    out=[]; report=[]
    with ThreadPoolExecutor(max_workers=3) as pool:
        for rows,message in pool.map(fetch_car_page,range(1,9)): out.extend(rows); report.append(message)
    out=unique(out)
    if not out: raise RuntimeError('AutoScout24: '+'; '.join(report[:4]))
    return dict(items=out,report=report)

def table_grid(table):
    grid=[]; occupied={}
    for r,tr in enumerate(table.find_all('tr')):
        row={c:v for (rr,c),v in occupied.items() if rr==r}; col=0
        for cell in tr.find_all(['th','td'],recursive=False):
            while col in row: col+=1
            text=cell.get_text(' ',strip=True) or ' '.join(img.get('alt','') for img in cell.find_all('img'))
            try: rowspan=min(100,max(1,int(cell.get('rowspan',1)))); colspan=min(100,max(1,int(cell.get('colspan',1))))
            except ValueError: rowspan=colspan=1
            for dr in range(rowspan):
                for dc in range(colspan):
                    occupied[(r+dr,col+dc)]=text
                    if dr==0: row[col+dc]=text
            col+=colspan
        if row: grid.append([row.get(c,'') for c in range(max(row)+1)])
    return grid

def fuel_kind(text):
    text=re.sub(r'\s+',' ',text.casefold()).strip()
    for pattern,name in [(r'^(?:bensiin\s*)?95(?:\s*euro)?$','Bensiin 95'),(r'^(?:bensiin\s*)?98(?:\s*euro)?$','Bensiin 98'),(r'^(diesel|diisel)$','Diisel'),(r'^lpg$','LPG'),(r'^cng$','CNG')]:
        if re.search(pattern,text): return name
    return ''

def parse_fuel(soup):
    rows=[]
    for table in soup.find_all('table'):
        grid=table_grid(table)
        for idx,row in enumerate(grid):
            if not row: continue
            kind=fuel_kind(row[0])
            if kind:
                # Choose the closest preceding station header with matching width.
                header=None
                for candidate in reversed(grid[:idx]):
                    if len(candidate) in (len(row),len(row)-1) and any(re.search(r'krooning|olerex|circle|alexela|premium|neste|terminal',x,re.I) for x in candidate):
                        header=candidate; break
                if header:
                    stations=header[1:] if len(header)==len(row) else header
                    for station,value in zip(stations,row[1:]):
                        if station.strip() and re.fullmatch(r'\d{1,2}[.,]\d{2,3}',value.strip()):
                            price=float(value.replace(',','.'))
                            if 0<price<10: rows.append({'Tankla':station.strip(),'Kütus':kind,'Hind €/l':price})
            else:
                # Alternative orientation: station rows, fuel column headings.
                for header in reversed(grid[:idx]):
                    if len(header)==len(row) and sum(bool(fuel_kind(x)) for x in header)>=2:
                        for name,value in zip(header[1:],row[1:]):
                            if fuel_kind(name) and re.fullmatch(r'\d{1,2}[.,]\d{2,3}',value.strip()):
                                price=float(value.replace(',','.'))
                                if 0<price<10: rows.append({'Tankla':row[0],'Kütus':fuel_kind(name),'Hind €/l':price})
                        break
    seen=set(); out=[]
    for row in rows:
        key=tuple(row.values())
        if key not in seen: seen.add(key); out.append(row)
    return out

def fetch_fuel():
    rows=parse_fuel(BeautifulSoup(get_bytes(FUEL_URL),'html.parser'))
    if not rows: raise RuntimeError('1182 tabelit ei eraldatud. Ei asenda seda näidishindadega.')
    return dict(rows=rows,report=['Allikas 1182. Laadimisaeg ei ole hinna mõõtmise aeg.'])

def fetch_food_store(pair):
    name,url=pair
    try:
        soup=BeautifulSoup(get_bytes(url),'html.parser'); out=structured_offers(soup,url,'food')
        # Only real priced structured products; do not invent campaign discounts.
        out=[i for i in out if i.get('price_val') is not None]
        for i in out: i['title']=name+': '+i['title']; i['location']=name
        return out,f'{name}: {len(out)} hinnaga toodet'
    except Exception as exc: return [],f'{name}: {type(exc).__name__}'

def fetch_food():
    out=[]; report=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for rows,message in pool.map(fetch_food_store,STORES): out.extend(rows); report.append(message)
    if not out: raise RuntimeError('Poodide avalikust HTML-ist hinnaga tooteid ei leitud. '+'; '.join(report))
    return dict(items=unique(out),report=report)

def fetch_ratings():
    soup=BeautifulSoup(get_bytes(RATING_URL),'html.parser')
    tables=[]
    for table in soup.find_all('table'):
        grid=table_grid(table)
        if grid: tables.append(grid)
    # Preserve original attribution. Strip active HTML in the local snapshot.
    for n in soup.find_all(['script','iframe','form','nav','footer']): n.decompose()
    article=soup.find('main') or soup.find('article') or soup.body or soup
    text=article.get_text('\n',strip=True)
    return dict(text=text[:25000],tables=tables,report=['Algallika tekst ja HTML-tabelid; JS-graafikud eraldi manustatud vaates.'])

class ScanEngine:
    def __init__(self,rss_url):
        self.rss_url=rss_url; self.lock=threading.RLock(); self.wake=threading.Event(); self.stop_event=threading.Event()
        self.data={}; self.status={name:dict(next_attempt=0,running=False,error='') for name in INTERVALS}; self.revision=0
        self.pool=ThreadPoolExecutor(max_workers=4,thread_name_prefix='scanner')
        self.thread=threading.Thread(target=self.loop,daemon=True,name='scanner-clock'); self.thread.start()
    def loop(self):
        while not self.stop_event.is_set():
            with self.lock:
                due=[name for name,s in self.status.items() if not s['running'] and time.time()>=s['next_attempt']]
                for name in due: self.status[name]['running']=True; self.status[name]['last_attempt']=time.time()
            for name in due: self.pool.submit(self.scan,name)
            self.wake.wait(10); self.wake.clear()
    def scan(self,name):
        try:
            if name=='rss' and not self.rss_url: raise ValueError('FACEBOOK_GROUP_RSS_URL puudub Secrets seadistuses.')
            functions={'rss':lambda:fetch_rss(self.rss_url),'cars':fetch_cars,'kv':fetch_kv,'fuel':fetch_fuel,'food':fetch_food,'ratings':fetch_ratings}
            result=functions[name](); now=time.time(); result['fetched']=now
            with self.lock:
                previous=self.data.get(name)
                if 'items' in result:
                    previous_ids={i['id'] for i in previous.get('items',[])} if previous else None
                    result['new_ids']=[i['id'] for i in result['items'] if previous_ids is not None and i['id'] not in previous_ids]
                self.data[name]=result
                self.status[name].update(last_success=now,next_attempt=now+INTERVALS[name],running=False,error='')
                self.revision+=1
        except Exception as exc:
            message=re.sub(r'https?://\S+','[URL peidetud]',str(exc))
            with self.lock:
                self.status[name].update(next_attempt=time.time()+900,running=False,error=type(exc).__name__+': '+message[:1000]); self.revision+=1
    def refresh(self,name):
        with self.lock:
            if not self.status[name]['running']: self.status[name]['next_attempt']=0
        self.wake.set()
    def snapshot(self):
        with self.lock: return copy.deepcopy(self.data),copy.deepcopy(self.status),self.revision

@st.cache_resource(show_spinner=False)
def engine_resource(rss_url,version):
    return ScanEngine(rss_url)

def rss_configuration():
    value=os.getenv('FACEBOOK_GROUP_RSS_URL','')
    if not value:
        try: value=str(st.secrets.get('FACEBOOK_GROUP_RSS_URL',''))
        except Exception: value=''
    return safe_url(value)

engine=engine_resource(rss_configuration(),VERSION)
for key,default in [('favorites',{}),('hidden',set()),('translations',{})]:
    if key not in st.session_state: st.session_state[key]=default
TABS=['🎁 Tasuta asjad','🏢 Kinnisvara objektid','⚡ Renault 5 EV','🛒 Toidu sooduspakkumised','🚗 Kütusehinnad & Parkimine','📈 Eesti reitingud','⭐ Lemmikud']
selected=st.radio('Vali vaade',TABS,horizontal=True); source=dict(zip(TABS,['rss','kv','cars','food','fuel','ratings','favorites']))[selected]
with st.sidebar:
    st.header('Juhtpaneel')
    with st.form('search'):
        query=st.text_input('Otsingusõnad (komaga)',placeholder='diivan, laud, tool'); excluded=st.text_input('Välista sõnad',placeholder='katki, broneeritud'); st.form_submit_button('Otsi')
    view=st.selectbox('Vaade',['Tulemused','Lemmikud','Peidetud']); images=st.checkbox('Näita pilte',value=True); page_size=st.selectbox('Tulemusi lehel',[12,24,48])
    if st.button('↻ Skänni valitud allikas kohe'):
        if source in INTERVALS: engine.refresh(source)
    if st.button('↻ Skänni kõik kohe'):
        for name in INTERVALS: engine.refresh(name)
    if st.button('Taasta peidetud'): st.session_state.hidden.clear()
    st.caption('Lemmikud ja peitmised on kasutajaseansis. Allikate tulemused ja ajastaja on selle serveriprotsessi mälus ühised. Ära kasuta privaatseid isiklikke RSS-e mitme kasutajaga rakenduses.')

def status_panel():
    data,status,revision=engine.snapshot()
    with st.expander('🕒 Skänneri seisund ja ajakava'):
        rows=[]
        for name in INTERVALS:
            s=status[name]; d=data.get(name,{})
            rows.append({'Allikas':LABELS[name],'Olek':'Laen…' if s['running'] else 'Viga; kordus 15 min pärast' if s['error'] else 'Valmis' if d else 'Ootel','Viimane edu':fmt_date(s.get('last_success')),'Järgmine katse':fmt_date(s['next_attempt']),'Kirjeid':len(d.get('items',d.get('rows',[])))})
        st.dataframe(rows,hide_index=True,use_container_width=True)
        st.caption('Taustalõim töötab ka vaadete vahetamise ajal ja seni, kuni serveriprotsess töötab. Majutuse uinumine või taaskäivitamine peatab selle ning mälus olev ajalugu kaob. See pole garanteeritud 24/7 teenus.')
        for name,s in status.items():
            if s['error']: st.caption(LABELS[name]+': '+s['error'])
    old=st.session_state.get('shown_revision')
    if old is not None and revision!=old:
        st.session_state.shown_revision=revision; st.rerun()
    st.session_state.shown_revision=revision

if hasattr(st,'fragment'): st.fragment(run_every='10s')(status_panel)()
else:
    status_panel(); st.info('Automaatne ekraaniuuendus vajab st.fragment-i toetavat Streamliti versiooni. Taustalõim töötab sellest sõltumatult.')
data,status,_=engine.snapshot()

def search_match(i):
    text=' '.join(str(i.get(k,'')) for k in ('title','description','location')).casefold()
    yes=[s.strip().casefold() for s in query.split(',') if s.strip()]; no=[s.strip().casefold() for s in excluded.split(',') if s.strip()]
    return (not yes or any(s in text for s in yes)) and not any(s in text for s in no)

def csv_bytes(rows,columns):
    out=io.StringIO(newline=''); w=csv.writer(out); w.writerow(columns)
    for row in rows:
        values=[row.get(k,'') for k in columns]
        w.writerow([("'"+str(v)) if str(v).lstrip().startswith(('=','+','-','@')) else str(v) for v in values])
    return out.getvalue().encode('utf-8-sig')

def export_items(items):
    rows=[{'Allikas':LABELS.get(i['source'],i['source']),'Pealkiri':i['title'],'Kirjeldus':i['description'],'Hind EUR':i.get('price_val',''),'Asukoht':i.get('location',''),'Link':i['link']} for i in items]
    return csv_bytes(rows,['Allikas','Pealkiri','Kirjeldus','Hind EUR','Asukoht','Link'])

def toggle_fav(i):
    if i['id'] in st.session_state.favorites: del st.session_state.favorites[i['id']]
    else: st.session_state.favorites[i['id']]=dict(i)

def toggle_hide(ident):
    if ident in st.session_state.hidden: st.session_state.hidden.remove(ident)
    else: st.session_state.hidden.add(ident)

def render_card(i,new=False):
    image=safe_url(i.get('image')); desc=i['description']; link=safe_url(i['link']); ident=i['id']
    photo=f'<img class="card-img" src="{esc(image)}" loading="lazy" referrerpolicy="no-referrer" alt="Kuulutuse foto">' if images and image else ''
    tags=['Uus' if new else '',i.get('kind'),money(i.get('price_val')) if 'price_val' in i else '',i.get('location'),i.get('battery')]
    badges=''.join('<span class="badge">'+esc(t)+'</span>' for t in tags if t)
    action=f'<a class="pro-btn" href="{esc(link)}" target="_blank" rel="noopener noreferrer">Ava see kuulutus ↗</a>' if link else ''
    date=fmt_date(i.get('timestamp')) if i.get('timestamp') else LABELS.get(i['source'],i['source'])
    markup=f'<div class="pro-card"><div class="card-row">{photo}<div class="card-body"><div class="card-title">{esc(i["title"])}</div><div class="card-meta">{esc(date)}</div>{badges}<div class="card-desc">{esc(desc[:550])}{"…" if len(desc)>550 else ""}</div>{action}</div></div></div>'
    st.markdown(markup,unsafe_allow_html=True)
    with st.expander('Täistekst / tõlge'):
        st.text(desc)
        if i.get('reason'): st.caption(i['reason'])
        st.caption('Tõlkimisel saadetakse kuni 4000 märki Google’i tõlketeenusesse.')
        if st.button('Tõlgi eesti keelde',key='tr_'+ident):
            try:
                r=requests.get('https://translate.googleapis.com/translate_a/single',params={'client':'gtx','sl':'auto','tl':'et','dt':'t','q':desc[:4000]},timeout=(4,10)); r.raise_for_status(); st.session_state.translations[ident]=''.join(p[0] for p in r.json()[0] if p and p[0])
            except Exception: st.warning('Tõlketeenus ei vastanud.')
        if ident in st.session_state.translations: st.text(st.session_state.translations[ident])
    a,b=st.columns(2); a.button('★ Eemalda lemmik' if ident in st.session_state.favorites else '☆ Lisa lemmikuks',key='fav_'+ident,on_click=toggle_fav,args=(i,)); b.button('Taasta' if ident in st.session_state.hidden else 'Peida',key='hide_'+ident,on_click=toggle_hide,args=(ident,))

def show_items(items,new_ids=()):
    if source=='favorites': items=list(st.session_state.favorites.values())
    elif view=='Lemmikud': items=[i for i in st.session_state.favorites.values() if i['source']==source]
    elif view=='Peidetud': items=[i for i in items if i['id'] in st.session_state.hidden]
    else: items=[i for i in items if i['id'] not in st.session_state.hidden]
    items=[i for i in items if search_match(i)]
    st.caption(f'Selles vaates {len(items)} tulemust')
    if not items: st.info('Selle vaate filtritele vastavaid tulemusi pole. Allika täpne seisund on üleval skänneri paneelis.'); return
    st.download_button('Ekspordi CSV',export_items(items),file_name='pakkumised.csv',mime='text/csv')
    page=st.selectbox('Lehekülg',range(1,(len(items)+page_size-1)//page_size+1),key='page_'+source+'_'+view)
    for i in items[(page-1)*page_size:page*page_size]: render_card(i,i['id'] in new_ids)

current=data.get(source,{})
if source in status:
    s=status[source]
    if s['running']: st.info('Skännin taustal. Olemasolevad tulemused jäävad nähtavaks.')
    if s['error']: st.warning('Viimane katse ebaõnnestus; varasem edukas tulemus säilib. Täpsem info skänneri paneelis.')
    if current: st.caption('Viimane edukas laadimine: '+fmt_date(current.get('fetched')))

if source=='rss':
    st.subheader('🎁 Tasuta asjad — RSS')
    st.caption('RSS-kanali katvus sõltub teenusepakkujast. See kood ei muuda grupi RSS-i automaatselt Marketplace’i otsinguks.')
    with st.expander('Filtrid',expanded=True):
        a,b=st.columns(2); kinds=a.multiselect('Liigitus',['Tasuta pakkumine','Ebaselge','Soovikuulutus','Tingimuslik / tasuline','Mitte saadaval'],default=['Tasuta pakkumine','Ebaselge']); days=b.selectbox('Vanus päevades',[30,7,3,1,0],format_func=lambda n:'Kõik' if not n else str(n)); area=a.selectbox('Asukoht tekstist',['Kõik','Tallinn','Tallinn ja Harjumaa']); unknown=b.checkbox('Ka teadmata asukoht ja aeg',value=True)
    items=[]
    for i in current.get('items',[]):
        if i.get('kind') not in kinds: continue
        ts=i.get('timestamp')
        if not ts and not unknown: continue
        if ts and days and time.time()-ts>days*86400: continue
        if area!='Kõik':
            if i['location']=='Asukoht teadmata':
                if not unknown: continue
            elif area=='Tallinn' and not i['location'].startswith('Tallinn'): continue
        items.append(i)
    items.sort(key=lambda i:i.get('timestamp') or 0,reverse=True); show_items(items,current.get('new_ids',[]))

elif source in ('kv','cars'):
    st.subheader('🏢 Harjumaa garaažid' if source=='kv' else '⚡ Renault 5 E-Tech · kollase värvi otsing')
    if source=='cars': st.caption('Kollane on portaali otsingufilter. Aku suurus on tekstist; värvi ja tehnilisi andmeid ei kinnitata eraldi.')
    a,b=st.columns(2); maximum=a.number_input('Maksimaalne hind € (0 = piiranguta)',min_value=0,value=0,step=1000,key='max_'+source); order=b.selectbox('Järjesta',['Odavamad ees','Kallimad ees']); unknown=b.checkbox('Ka teadmata hinnaga',value=True)
    variant=a.selectbox('Variant',['Kõik','Evolution','Techno','Iconic']) if source=='cars' else 'Kõik'
    items=[i for i in current.get('items',[]) if (variant=='Kõik' or variant.lower() in i['title'].lower()) and ((i.get('price_val') is None and unknown) or (i.get('price_val') is not None and (not maximum or i['price_val']<=maximum)))]
    items.sort(key=lambda i:(i.get('price_val') is None,-(i.get('price_val') or 0) if order=='Kallimad ees' else i.get('price_val') or 0)); show_items(items,current.get('new_ids',[]))
    with st.expander('Parseri aruanne ja lisaotsing'):
        st.code('\n'.join(current.get('report',[])) or 'Laadimine pole veel õnnestunud.')
        st.link_button('Ava sama otsing',KV_URL if source=='kv' else AS_URL+'?sort=price&desc=0')

elif source=='food':
    st.subheader('🛒 Poodidest loetud hinnaga tooted')
    st.caption('Skännin poodide avaliku HTML-i struktureeritud tooteandmeid. Toote leidmine ei kinnita kampaaniasoodustust ega lao olemasolu. JS-põhine või blokeeritud pood ei pruugi tulemusi anda.')
    show_items(current.get('items',[]),current.get('new_ids',[]))
    with st.expander('Poodide laadimise aruanne'):
        st.code('\n'.join(current.get('report',[])) or status['food'].get('error','Laen…'))

elif source=='fuel':
    st.subheader('⛽ Tanklate hinnavõrdlus')
    st.caption('Allikas 1182. Laadimisaeg pole hinna mõõtmisaeg. Näidatakse ainult allikast leitud tanklaid, mitte kõiki Eesti tanklaid.')
    rows=current.get('rows',[])
    if rows:
        a,b=st.columns(2); fuel=a.selectbox('Kütus',sorted({r['Kütus'] for r in rows})); station=b.text_input('Tankla või asukoht').strip().casefold()
        rows=sorted([r for r in rows if r['Kütus']==fuel and (not station or station in r['Tankla'].casefold())],key=lambda r:r['Hind €/l'])
        if rows:
            st.metric('Madalaim hind valikus',f'{rows[0]["Hind €/l"]:.3f} €/l'); st.caption(rows[0]['Tankla']); st.dataframe(rows,hide_index=True,use_container_width=True)
            litres=st.number_input('Tangitav kogus liitrites',min_value=1,max_value=200,value=50)
            st.info(f'Valiku kalleima ja odavaima hinna vahe {litres} liitril: {(rows[-1]["Hind €/l"]-rows[0]["Hind €/l"])*litres:.2f} €. Sõidukulu ja kliendisoodustusi pole arvestatud.')
            st.download_button('Ekspordi hinnad CSV',csv_bytes(rows,['Tankla','Kütus','Hind €/l']),file_name='kutus.csv',mime='text/csv')
        else: st.info('Tanklafilter ei andnud tulemusi.')
    st.caption('Lõplik hind ja parkimistingimused tuleb kontrollida kohapeal.')
    with st.expander('🅿️ Parkimise kaart'): components.iframe('https://www.parkimine.ee',height=650,scrolling=True)

elif source=='ratings':
    st.subheader('📈 Eesti reitingud')
    for table in current.get('tables',[]): st.dataframe(table,use_container_width=True)
    with st.expander('Loetud algallika tekst',expanded=not bool(current.get('tables'))): st.text(current.get('text') or 'Laadimine pole veel õnnestunud.')
    if st.checkbox('Kuva algallika interaktiivne graafik',value=True):
        components.iframe(RATING_URL,height=850,scrolling=True)
    st.caption('Algallika uuringufirma ja metoodika on säilitatud; manustamist võib allikas piirata.')
else:
    st.subheader('⭐ Kõik lemmikud'); st.caption('Salvestatud koopiad võivad olla aegunud.'); show_items([])
st.divider(); st.caption('Serveriprotsessi ajastaja ei taga majutuse uinumise või taaskäivituse ajal tööd. Andmed ei ole püsivas andmebaasis. CAPTCHA, sisselogimise ja ligipääsupiirangute ületamist see rakendus ei tee.')
