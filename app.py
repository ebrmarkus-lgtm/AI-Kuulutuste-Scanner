"""Kuulutuste skänner. Ajastaja töötab aktiivses Streamliti seansis.
Sõltuvused: streamlit, requests, beautifulsoup4. RSS ei vaja lxml-i.
"""
import csv
import hashlib
import html
import io
import json
import os
import re
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlsplit, urlunsplit
from zoneinfo import ZoneInfo
import requests
import streamlit as st
import streamlit.components.v1 as components
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

st.set_page_config(page_title='Kuulutuste Skänner Pro',page_icon='⚡',layout='wide')
st.markdown("""<style>
.stApp{background:#0b0f19;color:#e2e8f0}[data-testid="stSidebar"]{background:#111827}
.card{background:#111827;border:1px solid #334155;border-radius:16px;padding:20px;margin:15px 0 5px;overflow-wrap:anywhere}
.row{display:flex;gap:20px;align-items:flex-start}.photo{width:230px;aspect-ratio:4/3;object-fit:cover;border-radius:12px;flex-shrink:0}.body{flex:1;min-width:0}.title{font-size:1.2rem;font-weight:700;color:#f8fafc}.meta{color:#a5b4c7;font-size:.85rem;margin:8px 0}.desc{white-space:pre-wrap;line-height:1.6;color:#cbd5e1}.pill{display:inline-block;padding:4px 10px;border:1px solid #475569;border-radius:18px;margin:3px 5px 9px 0;font-size:.8rem}a.action{display:inline-block;padding:10px 16px;background:#2563eb;color:white!important;border-radius:9px;text-decoration:none;margin-top:12px}
@media(max-width:750px){.row{display:block}.photo{width:100%;max-height:260px;margin-bottom:14px}.card{padding:14px}}
</style>""",unsafe_allow_html=True)
st.title('⚡ Kuulutuste Skänner Pro')
st.caption('Facebooki RSS: 1 h · Autod: 48 h · Kinnisvara: 24 h · Kütusehinna allika laadimine: 1 h')
INTERVALS={'rss':3600,'cars':172800,'kv':86400,'fuel':3600}
LABELS={'rss':'Facebooki RSS','cars':'AutoScout24','kv':'Kinnisvara24','fuel':'Kütusehinnad — 1182'}
RETRY_SECONDS=900
CAR_PAGES=8
FB_GROUP='https://www.facebook.com/groups/1929529077371716'
KV_URL='https://kinnisvara24.ee/garaaz/muuk/harju-maakond'
AS_BASE='https://www.autoscout24.com'
AS_URL=AS_BASE+'/lst/renault/r-5/bc_yellow'
FUEL_URL='https://www.1182.ee/kytusehinnad'
TZ=ZoneInfo('Europe/Tallinn')
for key,default in [('data',{}),('schedule',{}),('favorites',{}),('hidden',set()),('translations',{})]:
    if key not in st.session_state:
        st.session_state[key]=default

def esc(value):
    return html.escape(str(value if value is not None else ''),quote=True).replace('$','&#36;')

def safe_url(value,base=''):
    if not isinstance(value,str) or not value.strip(): return ''
    try:
        value=urljoin(base,value.strip()) if base else value.strip()
        p=urlsplit(value)
        if p.scheme in ('http','https') and p.hostname and not p.username and not p.password: return value
    except ValueError: pass
    return ''

def plain(value):
    return BeautifulSoup(str(value or ''),'html.parser').get_text(' ',strip=True)

def identity(source,link,fallback):
    if link:
        p=urlsplit(link)
        fallback=urlunsplit((p.scheme.lower(),p.netloc.lower(),p.path.rstrip('/'),p.query,''))
    return hashlib.sha256((source+':'+fallback).encode()).hexdigest()[:24]

def item(source,title,description,link,**extra):
    link=safe_url(link); title=str(title or 'Pealkirjata'); description=str(description or '')
    return dict(id=identity(source,link,title+description),source=source,title=title,description=description,link=link,**extra)

def unique(items):
    result={}
    for i in items:
        old=result.get(i['id'])
        if old is None: result[i['id']]=i
        elif old.get('price_val') is None and i.get('price_val') is not None: result[i['id']]=i
    return list(result.values())

def fetch_bytes(url,limit=8_000_000):
    retry=Retry(total=1,backoff_factor=.4,status_forcelist=[429,500,502,503,504],allowed_methods=['GET'],respect_retry_after_header=False)
    with requests.Session() as session:
        for prefix in ('https://','http://'): session.mount(prefix,HTTPAdapter(max_retries=retry))
        with session.get(url,headers={'User-Agent':'Mozilla/5.0 (compatible; ListingsReader/4.0)','Accept-Language':'et-EE,et;q=0.9,en;q=0.8'},timeout=(5,15),stream=True) as response:
            response.raise_for_status(); data=bytearray()
            for chunk in response.iter_content(65536):
                data.extend(chunk)
                if len(data)>limit: raise ValueError('Allika vastus ületab suurusepiirangu.')
            return bytes(data)

def timestamp(value):
    for fn in (parsedate_to_datetime,lambda x:datetime.fromisoformat(x.replace('Z','+00:00'))):
        try:
            d=fn(str(value)); return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).timestamp()
        except (ValueError,TypeError,OverflowError): pass
    return None

def fmt_date(ts):
    return datetime.fromtimestamp(ts,TZ).strftime('%d.%m.%Y %H:%M') if ts else 'Teadmata'

def numeric(value):
    if isinstance(value,(int,float)): return float(value)
    text=re.sub(r'[^\d,.]','',str(value or ''))
    if not text: return None
    if ',' in text and '.' in text:
        text=text.replace(',','') if text.rfind('.')>text.rfind(',') else text.replace('.','').replace(',','.')
    elif re.fullmatch(r'\d{1,3}([,.]\d{3})+',text): text=re.sub('[,.]','',text)
    else: text=text.replace(',','.')
    try: return float(text)
    except ValueError: return None

def extract_price(text):
    m=re.search(r'(\d[\d\s.,]*?)\s*(?:€|EUR\b|eurot\b)|€\s*(\d[\d\s.,]*)',text,re.I)
    return numeric(next(g for g in m.groups() if g is not None)) if m else None

def fmt_price(value):
    return f'{value:,.0f}'.replace(',',' ')+' €' if value is not None else 'Hind teadmata'

def classify(text):
    for kind,pattern in [
        ('Mitte saadaval',r'\b(broneeritud|müüdud|ära antud|juba läinud)\b'),
        ('Soovikuulutus',r'\b(otsin|soovin|ostan|võtan vastu|ищу|куплю|приму в дар)\b'),
        ('Tingimuslik / tasuline',r'\b(tasu eest|sümboolse tasu|šokolaadi vastu|tasuta transport|tasuta tarne|бесплатная доставка)\b'),
        ('Tasuta pakkumine',r'\b(tasuta|annan ära|ära anda|annab ära|kingin|võib ära viia|free|give away|giving away|отдам|бесплатно|даром)\b')]:
        m=re.search(pattern,text,re.I)
        if m:
            if kind=='Tasuta pakkumine' and (extract_price(text) or 0)>0: return 'Ebaselge','Tekstis leidub tasuta pakkumise väljend ja positiivne hind.'
            return kind,'Reeglipõhine hinnang; leitud väljend: '+m.group(0)
    return 'Ebaselge','Selget tasuta pakkumise märksõna ei leitud.'

def area_hint(text):
    if re.search(r'\b(tallinn\w*|mustamä\w*|lasnamä\w*|õismä\w*|kristiine\w*|nõmme\w*|pirita\w*|таллин\w*)\b',text,re.I): return 'Tallinn (tekstist)'
    if re.search(r'\b(harjumaa\w*|harju\w*|viimsi\w*|maardu\w*|saue\w*|saku\w*|keila\w*|jüri\w*)\b',text,re.I): return 'Harjumaa (tekstist)'
    return 'Teadmata'

def configured_rss():
    value=os.getenv('FACEBOOK_GROUP_RSS_URL','')
    if not value:
        try: value=str(st.secrets.get('FACEBOOK_GROUP_RSS_URL',''))
        except Exception: value=''
    return safe_url(value)

def fetch_rss(url):
    raw=fetch_bytes(url,5_000_000)
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper(): raise ValueError('Toetamata XML DTD või olemideklaratsioon.')
    root=ET.fromstring(raw)
    def tag(n): return n.tag.rsplit('}',1)[-1].lower()
    def field(n,names):
        for name in names:
            for c in n:
                if tag(c)==name and c.text: return c.text.strip()
        return ''
    if tag(root) not in ('rss','rdf','feed'): raise ValueError('Allikas ei tagastanud RSS- ega Atom-kanalit.')
    nodes=[n for n in root.iter() if tag(n) in ('item','entry')]; items=[]
    for n in nodes:
        title=plain(field(n,['title'])) or 'Pealkirjata'; raw_desc=field(n,['encoded','description','content','summary']); desc=plain(raw_desc); link=''; image=''
        for c in n:
            if tag(c)=='link' and c.attrib.get('rel','alternate')=='alternate':
                link=safe_url(c.attrib.get('href') or c.text)
                if link: break
        for c in n.iter():
            if tag(c) in ('enclosure','thumbnail','content'):
                candidate=safe_url(c.attrib.get('url'))
                if candidate and (tag(c)=='thumbnail' or c.attrib.get('type','').startswith('image/') or c.attrib.get('medium')=='image'):
                    image=candidate; break
        if not image:
            img=BeautifulSoup(raw_desc,'html.parser').find('img'); image=safe_url(img.get('src')) if img else ''
        kind,reason=classify(title+' '+desc)
        record=item('Facebook RSS',title,desc,link,image=image,kind=kind,reason=reason,location=area_hint(title+' '+desc),timestamp=timestamp(field(n,['pubdate','published','updated','date'])))
        if not link: record['id']=identity('Facebook RSS','',field(n,['guid','id']) or title+desc)
        items.append(record)
    return dict(items=unique(items),raw_count=len(nodes),report=[])

def fetch_kv():
    soup=BeautifulSoup(fetch_bytes(KV_URL),'html.parser'); items=[]; report=[]
    def valid_link(value):
        link=safe_url(value,KV_URL)
        if not link: return ''
        p=urlsplit(link)
        if p.hostname not in ('kinnisvara24.ee','www.kinnisvara24.ee') or p.path.rstrip('/')==urlsplit(KV_URL).path.rstrip('/'): return ''
        return link
    def add(title,description,link,price=None,image=''):
        link=valid_link(link); title=plain(title)
        if link and len(title)>=5:
            items.append(item('Kinnisvara24',title[:240],plain(description)[:4000],link,price_val=price,location='Harjumaa garaažide otsing',image=safe_url(image,KV_URL)))
    def walk(value):
        if isinstance(value,list):
            for child in value: walk(child)
        elif isinstance(value,dict):
            types=value.get('@type',[]); types=types if isinstance(types,list) else [types]
            if {'Product','RealEstateListing','Apartment','House','Residence','Accommodation'}.intersection(types):
                title=value.get('name') or value.get('headline'); link=value.get('url'); offers=value.get('offers') or {}; image=value.get('image') or ''; price=None
                if isinstance(link,dict): link=link.get('@id')
                if isinstance(offers,list): offers=offers[0] if offers else {}
                if isinstance(offers,dict):
                    link=link or offers.get('url')
                    if str(offers.get('priceCurrency','')).upper()=='EUR': price=numeric(offers.get('price'))
                if isinstance(image,list): image=image[0] if image else ''
                if isinstance(image,dict): image=image.get('url') or image.get('contentUrl') or ''
                add(title,value.get('description') or title or '',link,price,image)
            for child in value.values():
                if isinstance(child,(dict,list)): walk(child)
    for script in soup.find_all('script',attrs={'type':'application/ld+json'}):
        try: walk(json.loads(script.string or script.get_text()))
        except (ValueError,TypeError): pass
    report.append(f'JSON-LD: {len(unique(items))} pakkumist')
    def looks_like_listing(link):
        link=valid_link(link)
        if not link: return False
        path=urlsplit(link).path.rstrip('/')
        if re.search(r'/(login|registreeri|kontakt|blog|statistika|privaatsus)(/|$)',path,re.I): return False
        return bool(re.search(r'/(kinnisvara|objekt)/|(?:-\d{4,}|/[0-9a-f]{8}-[0-9a-f-]{20,})$',path,re.I))
    def offer_links(node):
        return {safe_url(a.get('href'),KV_URL).split('?')[0] for a in node.find_all('a',href=True) if looks_like_listing(safe_url(a.get('href'),KV_URL))}
    for a in soup.find_all('a',href=True):
        link=safe_url(a.get('href'),KV_URL)
        if not looks_like_listing(link): continue
        card=a
        for _ in range(7):
            text=card.get_text(' ',strip=True)
            if len(offer_links(card))==1 and len(text)>=25 and ('€' in text or card.name in ('article','li')): break
            parent=card.parent
            if not parent or parent.name in ('body','html') or len(offer_links(parent))>1: break
            card=parent
        text=card.get_text(' ',strip=True); heading=card.find(['h2','h3','h4'])
        title=heading.get_text(' ',strip=True) if heading else a.get_text(' ',strip=True)
        if len(title)<5: title=a.get('aria-label') or a.get('title')
        if not title: continue
        img=card.find('img'); image=(img.get('data-src') or img.get('src') or '') if img else ''
        price_text=re.sub(r'\d[\d\s.,]*\s*€\s*/\s*m(?:²|2)?','',text,flags=re.I)
        add(title,text,link,extract_price(price_text),image)
    items=unique(items); report.append(f'Kokku unikaalseid: {len(items)}')
    if not items: raise RuntimeError('Kinnisvara24 detailpakkumisi ei õnnestunud lehelt eraldada. Kasuta portaali otselinki.')
    return dict(items=items,raw_count=len(items),report=report)

def dig(obj,*keys):
    for key in keys:
        if not isinstance(obj,dict): return None
        obj=obj.get(key)
    return obj

def is_r5(title,text,link):
    text=(title+' '+text).casefold()
    return bool((re.search(r'\brenault\s*(?:r[- ]?)?5\b|\br[- ]?5\b',text) or 'renault-r-5' in link.lower()) and re.search(r'e[ -]?tech|electric|elektr|électri|elettric|eléctri|urban range|comfort range',text))

def battery(text):
    m=re.search(r'\b(40|52)\s*kwh\b',text,re.I)
    return m.group(0)+' (tekstist)' if m else ''

def fetch_car_page(page):
    try:
        soup=BeautifulSoup(fetch_bytes(AS_URL+f'?sort=price&desc=0&page={page}'),'html.parser'); items=[]
        script=soup.find('script',id='__NEXT_DATA__')
        if script:
            try:
                listings=dig(json.loads(script.string or script.get_text()),'props','pageProps','listings') or []
                for raw in listings:
                    if not isinstance(raw,dict): continue
                    vehicle=raw.get('vehicle') or {}
                    if not isinstance(vehicle,dict): continue
                    model=vehicle.get('model') or 'R 5'
                    if isinstance(model,dict): model=model.get('name','R 5')
                    title='Renault '+str(model)+' '+str(vehicle.get('modelVersionInput') or vehicle.get('variant') or '')
                    link=safe_url(raw.get('url'),AS_BASE)
                    if not link or not is_r5(title,json.dumps(raw,ensure_ascii=False),link): continue
                    price=dig(raw,'price','priceRaw') or dig(raw,'prices','public','priceRaw') or dig(raw,'price','priceFormatted') or dig(raw,'tracking','price')
                    loc=raw.get('location') or {}; loc=loc if isinstance(loc,dict) else {}
                    location=', '.join(str(loc.get(k)) for k in ('city','countryCode') if loc.get(k)) or 'Vaata originaalist'
                    images=raw.get('images') or []; image=images[0] if isinstance(images,list) and images else ''
                    if isinstance(image,dict): image=image.get('url') or image.get('src') or ''
                    reg=dig(raw,'tracking','firstRegistration'); km=dig(raw,'tracking','mileage') or vehicle.get('mileageInKm')
                    desc=' · '.join(x for x in [('Esmane registreerimine: '+str(reg)) if reg else '',str(km)+' km' if km is not None else ''] if x)
                    items.append(item('AutoScout24',title,desc,link,price_val=numeric(price),location=location,image=safe_url(image),battery=battery(title)))
            except (ValueError,TypeError,AttributeError): pass
        if not items:
            for a in soup.find_all('a',href=re.compile(r'/offers/')):
                link=safe_url(a.get('href'),AS_BASE)
                if not link: continue
                card=a
                for _ in range(8):
                    if card.find(['h2','h3']) and ('€' in card.get_text() or card.name=='article'): break
                    if not card.parent or card.parent.name in ('body','html'): break
                    card=card.parent
                links={x.get('href','').split('?')[0] for x in card.find_all('a',href=re.compile(r'/offers/'))}
                if len(links)>1: continue
                heading=card.find(['h2','h3']); title=heading.get_text(' ',strip=True) if heading else a.get_text(' ',strip=True); text=card.get_text(' ',strip=True)
                if not is_r5(title,text,link): continue
                img=card.find('img'); image=safe_url(img.get('src') or img.get('data-src'),AS_BASE) if img else ''
                items.append(item('AutoScout24',title,text[:4000],link,price_val=extract_price(text),location='Vaata originaalist',image=image,battery=battery(text)))
        return unique(items),f'Leht {page}: {len(unique(items))} eraldatud kuulutust'
    except Exception as exc:
        status=exc.response.status_code if isinstance(exc,requests.HTTPError) and exc.response is not None else type(exc).__name__
        return [],f'Leht {page}: laadimisviga ({status})'

def fetch_cars():
    items=[]; report=[]
    with ThreadPoolExecutor(max_workers=2) as pool:
        for rows,message in pool.map(fetch_car_page,range(1,CAR_PAGES+1)):
            items.extend(rows); report.append(message)
    items=unique(items)
    if not items: raise RuntimeError('AutoScout24 ei andnud loetavaid tulemusi. '+'; '.join(report[:4]))
    return dict(items=items,raw_count=len(items),report=report)

def parse_fuel_tables(soup):
    names={'95 euro':'Bensiin 95','98 euro':'Bensiin 98','diesel':'Diisel','diisel':'Diisel','lpg':'LPG','cng':'CNG'}; records=[]
    for table in soup.find_all('table'):
        header=None
        for tr in table.find_all('tr'):
            cells=tr.find_all(['th','td'],recursive=False)
            if not cells: continue
            labels=[]
            for cell in cells:
                text=cell.get_text(' ',strip=True)
                if not text: text=' '.join(img.get('alt','').strip() for img in cell.find_all('img') if img.get('alt'))
                labels.append(text)
            first=labels[0].casefold().strip()
            if first not in names:
                if len(labels)>=2 and any(re.search(r'krooning|olerex|circle|alexela|premium|neste|terminal',label,re.I) for label in labels): header=labels
                continue
            if header is None: continue
            if len(header)==len(cells): stations=header[1:]
            elif len(header)==len(cells)-1: stations=header
            else: continue
            for station,cell in zip(stations,cells[1:]):
                text=cell.get_text(' ',strip=True)
                if not station.strip() or not re.fullmatch(r'\d{1,2}[.,]\d{2,3}',text): continue
                price=float(text.replace(',','.'))
                if 0<price<10: records.append({'Tankla':station.strip(),'Kütus':names[first],'Hind €/l':price})
    seen=set(); result=[]
    for row in records:
        key=(row['Tankla'],row['Kütus'],row['Hind €/l'])
        if key not in seen: seen.add(key); result.append(row)
    return result

def fetch_fuel():
    rows=parse_fuel_tables(BeautifulSoup(fetch_bytes(FUEL_URL),'html.parser'))
    if not rows: raise RuntimeError('1182 hinnatabelit ei õnnestunud usaldusväärselt eraldada. Ava algallikas.')
    return dict(rows=rows,report=['Laadimisaeg ei ole hinna mõõtmisaeg.'])

def refresh(name):
    st.session_state.schedule.setdefault(name,{})['next_attempt']=0

def scan_due():
    changed=False; rss=configured_rss()
    for name in INTERVALS:
        now=time.time(); status=st.session_state.schedule.get(name,{})
        signature=hashlib.sha256(rss.encode()).hexdigest() if name=='rss' else name
        source_changed=status.get('signature')!=signature
        if not source_changed and now<status.get('next_attempt',0): continue
        previous=st.session_state.data.get(name)
        if source_changed: st.session_state.data.pop(name,None); previous=None
        base=dict(signature=signature,last_attempt=now,last_success=previous.get('fetched') if previous else None)
        try:
            if name=='rss' and not rss: raise ValueError('Lisa FACEBOOK_GROUP_RSS_URL Streamliti Secrets väljale.')
            result=fetch_rss(rss) if name=='rss' else fetch_cars() if name=='cars' else fetch_kv() if name=='kv' else fetch_fuel()
            result['fetched']=time.time()
            if 'items' in result:
                old_ids={i['id'] for i in previous.get('items',[])} if previous else None
                result['new_ids']=[i['id'] for i in result['items'] if old_ids is not None and i['id'] not in old_ids]
            st.session_state.data[name]=result
            st.session_state.schedule[name]=dict(base,error='',last_success=result['fetched'],next_attempt=result['fetched']+INTERVALS[name])
        except Exception as exc:
            message=re.sub(r'https?://\S+','[URL peidetud]',str(exc))
            st.session_state.schedule[name]=dict(base,error=type(exc).__name__+': '+message[:1000],next_attempt=time.time()+RETRY_SECONDS)
        changed=True
    return changed

def automatic_panel():
    with st.spinner('Kontrollin saabunud ajaga allikaid…'): changed=scan_due()
    with st.expander('🕒 Kontrollgraafik ja seisund'):
        for name in INTERVALS:
            status=st.session_state.schedule.get(name,{}); data=st.session_state.data.get(name)
            state='⚠️ Viimane laadimine ebaõnnestus' if status.get('error') else '✅ Laaditud' if data else '⏳ Ootel'
            st.write(f'{LABELS[name]} — {state}')
            st.caption(f'Intervall: {INTERVALS[name]//3600} h · Viimane edu: {fmt_date(status.get("last_success"))} · Järgmine katse: {fmt_date(status.get("next_attempt"))}')
            if data: st.caption(f'Kirjeid: {len(data.get("items",data.get("rows",[])))}')
            if status.get('error'): st.caption(status['error'])
        st.info('Kontroll töötab ainult aktiivses Streamliti seansis. Uus seanss alustab uut ajakava. Vea järel korduskatse 15 minuti pärast. See ei ole ööpäevaringne taustateenus.')
    if changed: st.rerun()

def get_data(name):
    data=st.session_state.data.get(name); status=st.session_state.schedule.get(name,{})
    if status.get('error'):
        st.warning('Viimane laadimine ebaõnnestus. Näitan varasemaid andmeid.' if data else 'Allika laadimine ebaõnnestus. Kasuta algallika linki.')
        with st.expander('Tehniline info'): st.code(status['error'])
    if data: st.caption('Andmed laaditud: '+fmt_date(data['fetched']))
    return data

def toggle_favorite(record):
    if record['id'] in st.session_state.favorites: del st.session_state.favorites[record['id']]
    else: st.session_state.favorites[record['id']]=dict(record)

def toggle_hidden(ident):
    if ident in st.session_state.hidden: st.session_state.hidden.remove(ident)
    else: st.session_state.hidden.add(ident)

def search_match(record):
    text=' '.join(str(record.get(k,'')) for k in ('title','description','location','source')).casefold()
    terms=[s.strip().casefold() for s in query.split(',') if s.strip()]; blocked=[s.strip().casefold() for s in excluded.split(',') if s.strip()]
    return (not terms or any(s in text for s in terms)) and not any(s in text for s in blocked)

def csv_bytes(rows,columns):
    out=io.StringIO(newline=''); writer=csv.writer(out); writer.writerow(columns)
    for row in rows:
        values=[row.get(k,'') for k in columns]
        writer.writerow([("'"+str(v)) if str(v).lstrip().startswith(('=','+','-','@')) else str(v) for v in values])
    return out.getvalue().encode('utf-8-sig')

def export_items(items):
    rows=[{'Allikas':i['source'],'Pealkiri':i['title'],'Kirjeldus':i.get('description',''),'Asukoht':i.get('location',''),'Hind EUR':i.get('price_val',''),'Liigitus':i.get('kind',''),'Avaldatud':fmt_date(i.get('timestamp')) if i.get('timestamp') else '','Link':i.get('link','')} for i in items]
    return csv_bytes(rows,['Allikas','Pealkiri','Kirjeldus','Asukoht','Hind EUR','Liigitus','Avaldatud','Link'])

def show_card(record,new=False):
    ident=record['id']; image=safe_url(record.get('image','')); desc=record.get('description',''); link=safe_url(record.get('link'))
    photo=f'<img class="photo" src="{esc(image)}" loading="lazy" referrerpolicy="no-referrer" alt="Kuulutuse pilt">' if images and image else ''
    tags=['Uus võrreldes eelmise kontrolliga' if new else '',record.get('kind'),fmt_price(record.get('price_val')) if 'price_val' in record else '',record.get('location'),record.get('battery')]
    pills=''.join('<span class="pill">'+esc(t)+'</span>' for t in tags if t)
    action=f'<a class="action" href="{esc(link)}" target="_blank" rel="noopener noreferrer">Ava originaal ↗</a>' if link else '<p>Originaallink puudub</p>'
    date=' · Avaldatud: '+fmt_date(record.get('timestamp')) if record['source']=='Facebook RSS' else ''
    st.markdown(f'<div class="card"><div class="row">{photo}<div class="body"><div class="title">{esc(record["title"])}</div><div class="meta">{esc(record["source"]+date)}</div>{pills}<div class="desc">{esc(desc[:420])}{"…" if len(desc)>420 else ""}</div>{action}</div></div></div>',unsafe_allow_html=True)
    with st.expander('Täistekst ja selgitused'):
        st.text(desc or 'Kirjeldus puudub.')
        if record.get('reason'): st.caption(record['reason'])
        if record['source']=='AutoScout24': st.caption('Kollane on otsingufilter, mitte iga auto eraldi kontrollitud värv. Aku suurus kuvatakse ainult selge kWh-mainimise korral.')
        st.caption('Tõlkimisel saadetakse kuni 4000 märki Google’i tõlketeenusesse. Otsing ja liigitus kasutavad originaalteksti.')
        if st.button('Tõlgi eesti keelde',key='tr_'+ident):
            try:
                response=requests.get('https://translate.googleapis.com/translate_a/single',params={'client':'gtx','sl':'auto','tl':'et','dt':'t','q':desc[:4000]},timeout=(4,10)); response.raise_for_status()
                st.session_state.translations[ident]=''.join(p[0] for p in response.json()[0] if p and p[0])
            except Exception: st.warning('Tõlketeenus ei vastanud.')
        if ident in st.session_state.translations: st.text(st.session_state.translations[ident])
    a,b=st.columns(2)
    a.button('★ Eemalda lemmik' if ident in st.session_state.favorites else '☆ Lisa lemmikuks',key='fav_'+ident,on_click=toggle_favorite,args=(record,))
    b.button('Taasta' if ident in st.session_state.hidden else 'Peida',key='hide_'+ident,on_click=toggle_hidden,args=(ident,))

def show_items(items,source,new_ids=()):
    if view=='Lemmikud':
        items=[dict(i) for i in st.session_state.favorites.values() if i['source']==source]
        st.caption('Seansi salvestatud koopiad võivad olla aegunud. Allika erifiltrid siin ei kehti; märksõnaotsing kehtib.')
    elif view=='Peidetud': items=[i for i in items if i['id'] in st.session_state.hidden]
    else: items=[i for i in items if i['id'] not in st.session_state.hidden]
    items=[i for i in items if search_match(i)]; st.caption(f'Selles vaates: {len(items)} tulemust')
    if not items: st.info('Tulemusi pole. Muuda filtreid või vali teine tulemuste vaade.'); return
    st.download_button('Laadi tulemused CSV-na',export_items(items),file_name='kuulutused.csv',mime='text/csv',key='export_'+source)
    page=st.selectbox('Lehekülg',range(1,(len(items)+page_size-1)//page_size+1),key='page_'+source+'_'+view)
    for record in items[(page-1)*page_size:page*page_size]: show_card(record,record['id'] in new_ids)

TABS=['🎁 Tasuta asjad','🏢 Kinnisvara objektid','⚡ Renault 5 EV','🛒 Toidu sooduspakkumised','🚗 Kütusehinnad & Parkimine','📈 Eesti reitingud','⭐ Kõik lemmikud']
selected=st.radio('Vali vaade',TABS,horizontal=True)
with st.sidebar:
    st.header('Otsing ja seadistused')
    with st.form('search'):
        query=st.text_input('Märksõnad, komaga eraldatud',placeholder='diivan, laud, tool'); excluded=st.text_input('Välistatud sõnad',placeholder='katki, broneeritud')
        st.caption('Piisab ühest otsingusõnast. Otsitakse originaaltekstist. Kütusevaatel on eraldi tanklafilter.'); st.form_submit_button('Rakenda otsing')
    view=st.selectbox('Tulemuste vaade',['Tulemused','Lemmikud','Peidetud']); images=st.checkbox('Näita pilte',value=True); page_size=st.selectbox('Kuulutusi lehel',[8,16,32])
    current={TABS[0]:'rss',TABS[1]:'kv',TABS[2]:'cars',TABS[4]:'fuel'}.get(selected)
    if st.button('↻ Värskenda valitud allikat'):
        if current: refresh(current)
        else: st.info('Selles vaates pole laaditavat allikat.')
    if st.button('↻ Värskenda kõiki allikaid'):
        for name in INTERVALS: refresh(name)
    if st.button('Taasta peidetud kuulutused'): st.session_state.hidden.clear()
    st.caption(f'Lemmikuid: {len(st.session_state.favorites)}. Salvestus on seansipõhine; ekspordi olulised tulemused CSV-na.')

if hasattr(st,'fragment'): st.fragment(run_every='60s')(automatic_panel)()
else:
    st.warning('Automaatkontroll vajab st.fragment-i toetavat Streamliti versiooni. Praegu kontrollitakse ainult lehe kasutamisel.'); automatic_panel()

if selected==TABS[0]:
    st.subheader('🎁 Facebooki RSS-kuulutused'); st.link_button('Ava määratud Facebooki grupp ↗',FB_GROUP)
    st.info('See on seadistatud RSS-kanali lugeja, mitte sisseehitatud Marketplace’i otsing. Marketplace’i jaoks peab RSS päriselt sisaldama Marketplace’i pakkumisi. Kanali seost grupiga ei kontrollita.')
    with st.expander('Kuulutuste filtrid',expanded=True):
        a,b=st.columns(2)
        kinds=a.multiselect('Liigitus',['Tasuta pakkumine','Ebaselge','Soovikuulutus','Tingimuslik / tasuline','Mitte saadaval'],default=['Tasuta pakkumine','Ebaselge'])
        days=b.selectbox('Maksimaalne vanus päevades',[30,7,3,1,0],format_func=lambda n:'Kõik ajad' if not n else f'{n} päeva')
        area=a.selectbox('Asukoha tekstimainimine',['Kõik','Tallinn','Tallinn ja Harjumaa']); unknown_area=b.checkbox('Ka teadmata asukohaga',value=True); unknown_date=b.checkbox('Ka teadmata avaldamisajaga',value=True)
    data=get_data('rss'); items=[]
    if data:
        for record in data['items']:
            if record['kind'] not in kinds: continue
            ts=record.get('timestamp')
            if not ts and not unknown_date: continue
            if ts and days and time.time()-ts>days*86400: continue
            if area!='Kõik':
                if record['location']=='Teadmata':
                    if not unknown_area: continue
                elif area=='Tallinn' and not record['location'].startswith('Tallinn'): continue
            items.append(record)
        items.sort(key=lambda i:i.get('timestamp') or 0,reverse=True)
        a,b,c=st.columns(3); a.metric('Kirjeid kanalis',data['raw_count']); b.metric('Unikaalseid',len(data['items'])); c.metric('Filtritele vastab',len(items))
        if not data['items']: st.info('RSS laaditi edukalt, kuid selles pole kirjeid.')
    show_items(items,'Facebook RSS',data.get('new_ids',[]) if data else [])

elif selected==TABS[1]:
    st.subheader('🏢 Harjumaa garaažide müügipakkumised'); st.link_button('Ava Kinnisvara24 otsing ↗',KV_URL)
    st.caption('Kontroll iga 24 h aktiivses seansis. HTML-ist ja JSON-LD-st eraldatud hind ning aktiivsus tuleb üle kontrollida originaalist.')
    a,b=st.columns(2); max_price=a.number_input('Maksimaalne hind € (0 = piiranguta)',min_value=0,value=0,step=1000,key='kv_max'); unknown=b.checkbox('Ka teadmata hinnaga',value=True,key='kv_unknown')
    data=get_data('kv'); items=data['items'] if data else []
    items=[i for i in items if (i.get('price_val') is None and unknown) or (i.get('price_val') is not None and (not max_price or i['price_val']<=max_price))]
    items.sort(key=lambda i:(i.get('price_val') is None,i.get('price_val') or 0)); show_items(items,'Kinnisvara24',data.get('new_ids',[]) if data else [])
    if data:
        with st.expander('Parseri aruanne'): st.code('\n'.join(data['report']))

elif selected==TABS[2]:
    st.subheader('⚡ Renault 5 E-Tech — kollase värvi otsing'); st.link_button('Ava AutoScout24 otsing ↗',AS_URL+'?sort=price&desc=0')
    st.caption(f'Kontroll iga 48 h aktiivses seansis, kuni {CAR_PAGES} lehte. Portaal võib automaatpäringuid piirata. Kollane on otsingufilter.')
    a,b=st.columns(2); variant=a.selectbox('Variant',['Kõik','Evolution','Techno','Iconic']); order=b.selectbox('Järjekord',['Odavamad enne','Kallimad enne']); max_price=a.number_input('Maksimaalne auto hind € (0 = piiranguta)',min_value=0,value=0,step=1000); unknown=b.checkbox('Ka teadmata hinnaga autod',value=True)
    data=get_data('cars'); items=data['items'] if data else []
    items=[i for i in items if (variant=='Kõik' or variant.casefold() in i['title'].casefold()) and ((i.get('price_val') is None and unknown) or (i.get('price_val') is not None and (not max_price or i['price_val']<=max_price)))]
    items.sort(key=lambda i:(i.get('price_val') is None,-(i.get('price_val') or 0) if order=='Kallimad enne' else i.get('price_val') or 0)); show_items(items,'AutoScout24',data.get('new_ids',[]) if data else [])
    if data:
        with st.expander('Laadimise aruanne'): st.code('\n'.join(data['report']))
    with st.expander('Teised otsingulingid'):
        st.link_button('AutoScout24.de — kollase värvi otsing','https://www.autoscout24.de/lst/renault/r-5/bc_gelb'); st.link_button('Das Parking — Renault R 5 gelb','https://www.dasparking.de/gebrauchtwagen/renault-r-5-gelb.html'); st.link_button('AutoUncle — Renault 5 E-Tech','https://www.autouncle.de/de/gebrauchtwagen/Renault/5%20E-Tech')
        st.caption('Varasemast koodist üle võetud lingid. Kontrolli portaalis mudelit, elektriajamit ja värvi.')

elif selected==TABS[3]:
    st.subheader('🛒 Toidupakkumiste allikad'); st.info('Linkide kogu, mitte automaatne hinnavõrdlus. Kontrollimata näidishinnad on eemaldatud.')
    for name,url in [('Selver','https://www.selver.ee'),('Rimi','https://www.rimi.ee'),('Maxima','https://www.maxima.ee'),('Coop','https://www.coop.ee')]:
        if search_match(dict(title=name)): st.link_button('Ava '+name+' ↗',url)

elif selected==TABS[4]:
    st.subheader('⛽ Kütusehindade võrdlus'); st.link_button('Ava 1182 hinnatabel ↗',FUEL_URL)
    st.caption('Allika laadimine iga 1 h aktiivses seansis. Laadimisaeg ei ole hinna mõõtmise aeg. Kuvatakse ainult allikast eraldatud hinnad, mitte kogu Eesti odavaim hind.')
    data=get_data('fuel')
    if data:
        a,b=st.columns(2); fuel=a.selectbox('Kütus',sorted({r['Kütus'] for r in data['rows']})); station=b.text_input('Tankla või asukoha filter',placeholder='nt Laki, Circle K').strip().casefold()
        rows=sorted([r for r in data['rows'] if r['Kütus']==fuel and (not station or station in r['Tankla'].casefold())],key=lambda r:r['Hind €/l'])
        if rows:
            st.metric('Madalaim hind praeguses valikus',f'{rows[0]["Hind €/l"]:.3f} €/l'); st.caption('Tankla: '+rows[0]['Tankla']); st.dataframe(rows,hide_index=True,use_container_width=True)
            litres=st.number_input('Võrdluseks tangitav kogus liitrites',min_value=1,max_value=200,value=50,step=5)
            if len(rows)>1:
                difference=(rows[-1]['Hind €/l']-rows[0]['Hind €/l'])*litres
                st.info(f'Valiku kõrgeima ja madalaima hinna vahe {litres} liitri puhul: {difference:.2f} €. Sõidukulu ja kliendisoodustusi pole arvestatud.')
            st.download_button('Laadi hinnavõrdlus CSV-na',csv_bytes(rows,['Tankla','Kütus','Hind €/l']),file_name='kutusehinnad.csv',mime='text/csv')
        else: st.info('Valitud filtriga tanklaid pole.')
    st.warning('Kontrolli lõplikku hinda tanklas. Allika hinnad võivad olla aegunud ja kliendisoodustused võivad erineda.')
    st.divider(); st.subheader('🅿️ Parkimine'); st.link_button('Ava Parkimine.ee ↗','https://www.parkimine.ee'); st.caption('Tasuta aeg, registreerimine ja parkimiskell tuleb kontrollida konkreetse parkla tingimustest.')

elif selected==TABS[5]:
    st.subheader('📈 Eesti reitingud'); st.link_button('Ava algallikas ↗','https://reitingud.ee/reitingud/'); st.caption('Allika sisu ja uuringufirma nime ei muudeta. Vaata algallikast avaldamiskuupäeva ja metoodikat.')
    if st.checkbox('Proovi kuvada allikat lehe sees'):
        components.iframe('https://reitingud.ee/reitingud/',height=850,scrolling=True); st.caption('Kui manustamine on blokeeritud, kasuta algallika linki.')

else:
    st.subheader('⭐ Kõik selle seansi lemmikud'); items=[dict(i) for i in st.session_state.favorites.values() if search_match(i)]
    st.caption('Salvestatud koopiad võivad olla aegunud. Allika erifiltrid siin ei kehti. Ekspordi olulised tulemused enne seansi lõppu.')
    if items:
        st.download_button('Ekspordi lemmikud CSV-na',export_items(items),file_name='lemmikud.csv',mime='text/csv'); page=st.selectbox('Lehekülg',range(1,(len(items)+page_size-1)//page_size+1),key='all_favorites_page')
        for record in items[(page-1)*page_size:page*page_size]: show_card(record)
    else: st.info('Lemmikuid pole või need ei vasta otsingule.')
st.divider(); st.caption('Seansipõhine abivahend, mitte ööpäevaringne taustateenus ega AI-mudeli tehinguhinnang. Püsiv taustaskännimine vajab eraldi ajastajat ja andmehoidlat. Facebooki katvus sõltub seadistatud RSS-ist.')
