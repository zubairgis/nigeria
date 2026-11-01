#!/usr/bin/env python3
"""Build the static NDC election dashboard data from the documented source files."""
import csv, gzip, json, math, re, time, urllib.parse, urllib.request
from pathlib import Path
from collections import defaultdict
from pyproj import Transformer
from shapely.geometry import shape, mapping
from shapely.ops import transform

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data/source'; OUT=ROOT/'data/processed'; OUT.mkdir(parents=True,exist_ok=True)

def load_source_json(name):
    raw=SRC/name
    compressed=SRC/(name+'.gz')
    if raw.exists(): return json.load(open(raw,encoding='utf-8'))
    with gzip.open(compressed,'rt',encoding='utf-8') as f: return json.load(f)
def get_json(url):
    req=urllib.request.Request(url,headers={'User-Agent':'NDC-Election-Information-System/1.0'})
    with urllib.request.urlopen(req,timeout=120) as r: return json.load(r)

def norm(v): return re.sub(r'[^A-Z0-9]','',str(v or '').upper())
def gzip_json(obj,path):
    with gzip.open(path,'wt',encoding='utf-8',compresslevel=7) as f: json.dump(obj,f,separators=(',',':'),ensure_ascii=False)
def fix_geom(feature, transformer=None):
    g=shape(feature['geometry'])
    if transformer: g=transform(transformer.transform,g)
    p=feature.get('properties') or {}
    return {'type':'Feature','geometry':mapping(g),'properties':p}

# Load uploaded source layers. Uploaded Nigeria LGA file uses UTM 32N; convert to WGS84.
house=load_source_json('Nig_Elections.json')
senate=load_source_json('Nig_Senate_Elections.json')
states=load_source_json('States.json')
lgas=load_source_json('Nig_LGA.json')
# Check CRS by inspecting typical coordinate magnitudes; convert projected coordinates.
first=lgas['features'][0]['geometry']['coordinates'][0][0]
trans=Transformer.from_crs('EPSG:32632','EPSG:4326',always_xy=True) if abs(first[0])>180 else None
lgas={'type':'FeatureCollection','features':[fix_geom(f,trans) for f in lgas['features']]}
for label,obj in [('house_constituencies',house),('senate_districts',senate),('states',states),('lgas',lgas)]:
    gzip_json(obj,OUT/f'{label}.geojson.gz')

# Get nationwide operational ward polygons for red estimated markers.
ward_file=SRC/'operational_wards.geojson.gz'
if not ward_file.exists():
    base='https://services1.arcgis.com/XBhYkoXKJCRHbe7M/ArcGIS/rest/services/NGA_Ward_Boundaries/FeatureServer/0/query'
    params={'where':'1=1','outFields':'wardname,wardcode,lganame,lgacode,statename,statecode','returnGeometry':'true','outSR':'4326','f':'geojson','resultRecordCount':'2000'}
    features=[]; offset=0
    while True:
        q=urllib.parse.urlencode({**params,'resultOffset':str(offset)})
        page=get_json(base+'?'+q); batch=page.get('features',[])
        if not batch: break
        features.extend(batch); offset+=len(batch)
        if len(batch)<2000: break
    if not features: raise RuntimeError('Ward boundary service returned no features')
    with gzip.open(ward_file,'wt',encoding='utf8',compresslevel=7) as f: json.dump({'type':'FeatureCollection','features':features},f,separators=(',',':'))
with gzip.open(ward_file,'rt',encoding='utf-8') as f: wards=json.load(f)
# Lookup operational ward and LGA polygons; unmatched ward labels fall back to an LGA representative point.
ward_lookup={}
ward_counts=defaultdict(int)
lga_lookup={}
for f in wards['features']:
    p=f.get('properties',{})
    key='|'.join(norm(p.get(k)) for k in ['statename','lganame','wardname'])
    if key.strip('|'):
        try:
            g=shape(f['geometry']); rp=g.representative_point()
            ward_lookup[key]=(rp.x,rp.y)
            lk='|'.join(norm(p.get(k)) for k in ['statename','lganame'])
            lga_lookup.setdefault(lk,[]).append(g)
        except Exception: pass
# Build conservative exact normalized name-key coordinate candidates from the supplemental Google Places CSV.
coord_path=SRC/'mykeels-polling-units.csv'
if not coord_path.exists() and not (SRC/'mykeels-polling-units.csv.gz').exists():
    url='https://raw.githubusercontent.com/mykeels/inec-polling-units/master/polling-units.csv'
    req=urllib.request.Request(url,headers={'User-Agent':'NDC-Election-Information-System/1.0'})
    with urllib.request.urlopen(req,timeout=120) as r: coord_path.write_bytes(r.read())
coords=defaultdict(set)
coord_open=gzip.open(SRC/'mykeels-polling-units.csv.gz','rt',encoding='utf-8-sig',newline='') if (SRC/'mykeels-polling-units.csv.gz').exists() and not coord_path.exists() else open(coord_path,encoding='utf-8-sig',newline='')
with coord_open as f:
    for row in csv.DictReader(f):
        try: lat=float(row['location.latitude']); lng=float(row['location.longitude'])
        except (ValueError,KeyError,TypeError): continue
        # Remove clearly non-Nigerian Google Places matches; these are not verified INEC coordinates.
        if not (4 <= lat <= 14 and 2.5 <= lng <= 15): continue
        key='|'.join(norm(row.get(k)) for k in ['state_name','local_government_name','ward_name','name'])
        coords[key].add((round(lat,7),round(lng,7)))

poll_path=SRC/'polling-units.csv'
if not poll_path.exists() and not (SRC/'polling-units.csv.gz').exists():
    url='https://raw.githubusercontent.com/saidiadegoke/nigeria-inec-geo/main/data/polling-units.csv'
    req=urllib.request.Request(url,headers={'User-Agent':'NDC-Election-Information-System/1.0'})
    with urllib.request.urlopen(req,timeout=120) as r: poll_path.write_bytes(r.read())
# LGA lookup from the attached administrative boundaries, transformed above.
lga_reps={}
for f in lgas['features']:
    p=f.get('properties',{})
    lk='|'.join(norm(p.get(k)) for k in ['ADM1_EN','ADM2_EN'])
    try:
        rp=shape(f['geometry']).representative_point(); lga_reps[lk]=(rp.x,rp.y)
    except Exception: pass
state_reps={}
for f in states['features']:
    p=f.get('properties',{}); sk=norm(p.get('ADM1_EN'))
    try:
        rp=shape(f['geometry']).representative_point(); state_reps[sk]=(rp.x,rp.y)
    except Exception: pass
features=[]; located=0; ward_est=0; lga_est=0; state_est=0; no_admin=0; count=0
poll_open=gzip.open(SRC/'polling-units.csv.gz','rt',encoding='utf-8-sig',newline='') if (SRC/'polling-units.csv.gz').exists() and not poll_path.exists() else open(poll_path,encoding='utf-8-sig',newline='')
with poll_open as f:
    for row in csv.DictReader(f):
        count+=1
        key='|'.join(norm(row.get(k)) for k in ['state_name','lga_name','ward_name','pu_name'])
        c=coords.get(key,set())
        if len(c)==1:
            lat,lng=next(iter(c)); status='located_candidate'; source='Mykeels polling-unit Google Places geocodes; name-matched and Nigeria-bbox filtered; unverified'
            located+=1
        else:
            wkey='|'.join(norm(row.get(k)) for k in ['state_name','lga_name','ward_name'])
            point=ward_lookup.get(wkey)
            if point is not None:
                lng,lat=point; status='ward_estimate'; source='Operational ward polygon representative point; estimated, not polling-unit coordinates'; ward_est+=1
            else:
                lkey='|'.join(norm(row.get(k)) for k in ['state_name','lga_name'])
                point=lga_reps.get(lkey)
                if point is None:
                    point=state_reps.get(norm(row.get('state_name')))
                    if point is None:
                        lat=lng=None; status='no_admin_geometry'; source='No matched operational polygon'; no_admin+=1
                    else:
                        lng,lat=point; status='state_estimate'; source='State representative point fallback; not a ward or polling-unit location'; state_est+=1
                else:
                    lng,lat=point; status='admin_estimate'; source='LGA representative point fallback; not a ward or polling-unit location'; lga_est+=1
        props={k:row.get(k,'') for k in ['state_code','state_name','lga_code','lga_name','ward_code','ward_name','pu_code','pu_name','pu_location','full_code','portal_id']}
        props.update({'lat':lat,'lng':lng,'location_status':status,'coordinate_source':source})
        features.append({'type':'Feature','geometry':None if lat is None else {'type':'Point','coordinates':[lng,lat]},'properties':props})
fc={'type':'FeatureCollection','features':features}
gzip_json(fc,OUT/'polling_units.geojson.gz')
blue={'type':'FeatureCollection','features':[x for x in features if x['properties']['location_status']=='located_candidate']}
red={'type':'FeatureCollection','features':[x for x in features if x['properties']['location_status']!='located_candidate']}
gzip_json(blue,OUT/'polling_units_located.geojson.gz'); gzip_json(red,OUT/'polling_units_estimated.geojson.gz')
# Compact status/provenance record for the UI and README.
summary={'polling_units_total':count,'located_candidate':located,'ward_estimate':ward_est,'lga_estimate':lga_est,'state_estimate':state_est,'no_admin_geometry':no_admin,'ward_polygons':len(wards['features']),'house_constituencies':len(house['features']),'senate_districts':len(senate['features']),'states':len(states['features']),'coordinate_match_method':'Normalized state + LGA + ward + polling-unit name; unique coordinate only; 4–14N and 2.5–15E bounding box','coordinate_source':'Mykeels INEC polling units CSV, Google Places-derived and unverified','ward_source':'ArcGIS NGA Ward Boundaries operational layer (national coverage)'}
(OUT/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
print(json.dumps(summary,indent=2))
