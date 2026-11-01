#!/usr/bin/env python3
"""Aggregate WorldPop Nigeria 2026 age/sex 1 km estimates to supplied House constituencies."""
import csv, gzip, json, urllib.request, zipfile
from pathlib import Path
import numpy as np
import rasterio
from rasterio.features import rasterize

ROOT=Path(__file__).resolve().parents[1]
ZIP_URL='https://data.worldpop.org/GIS/AgeSex_structures/Global_2015_2030/R2025A/2026/NGA/v1/1km_ua/nga_agesex_structures_2026_CN_1km_R2025A_UA_v1.zip'
zip_path=ROOT/'data/source/worldpop_2026_agesex_1km.zip'
if not zip_path.exists():
    zip_path.parent.mkdir(parents=True,exist_ok=True)
    req=urllib.request.Request(ZIP_URL,headers={'User-Agent':'NDC-Election-Information-System/1.0'})
    with urllib.request.urlopen(req,timeout=180) as r, zip_path.open('wb') as f:
        while b:=r.read(1024*1024): f.write(b)
from shapely.geometry import shape
import json
src_json=ROOT/'data/source/Nig_Elections.json'
if src_json.exists(): house=json.loads(src_json.read_text(encoding='utf8'))['features']
else:
    with gzip.open(str(src_json)+'.gz','rt',encoding='utf8') as f: house=json.load(f)['features']
with zipfile.ZipFile(zip_path) as z:
    names=z.namelist()
    agecodes=['00','01','05','10','15','20','25','30','35','40','45','50','55','60','65','70','75','80','85','90']
    groups=['under_18','18_24','25_34','35_49','50_64','65_plus']
    totals={str(f['properties'].get('const_code') or f['properties'].get('Code')):{f'{sex}_{g}':0.0 for sex in ['male','female'] for g in groups} for f in house}
    tiff_for=lambda sex,age:next(n for n in names if n.endswith(f'{sex}_{age}_2026_CN_1km_R2025A_UA_v1.tif'))
    # Read metadata from the first layer; rasterize constituency IDs once on the exact WorldPop grid.
    with z.open(tiff_for('m','00')) as src:
        import rasterio.io
        with rasterio.io.MemoryFile(src.read()) as mem:
            with mem.open() as ds: meta=ds.meta.copy(); grid_shape=(ds.height,ds.width); grid_transform=ds.transform; grid_crs=ds.crs
    if str(grid_crs).upper() not in ('EPSG:4326','OGC:CRS84'):
        raise ValueError(f'Expected WorldPop WGS84 raster; got {grid_crs}')
    shapes=[(shape(f['geometry']),i+1) for i,f in enumerate(house)]
    zones=rasterize(shapes,out_shape=grid_shape,transform=grid_transform,fill=0,dtype='uint16',all_touched=False)
    active=zones>0; zone_ids=zones[active].astype(np.int64); maxid=len(house)
    fields={'under_18':['00','01','05','10','15'],'18_24':['15','20'],'25_34':['25','30'],'35_49':['35','40','45'],'50_64':['50','55','60'],'65_plus':['65','70','75','80','85','90']}
    for sex in ['m','f']:
        label={'m':'male','f':'female'}[sex]
        for group,ages in fields.items():
            for age in ages:
                with z.open(tiff_for(sex,age)) as src:
                    with rasterio.io.MemoryFile(src.read()) as mem:
                        with mem.open() as ds:
                            arr=ds.read(1,masked=True).filled(0).astype('float64')
                if age=='15':
                    arr=arr*(0.4 if group=='18_24' else 0.6) # approximate 18+ share of age 15–19
                sums=np.bincount(zone_ids,weights=arr[active],minlength=maxid+1)
                col=f'{label}_{group}'
                for i,f in enumerate(house,1):
                    code=str(f['properties'].get('const_code') or f['properties'].get('Code'))
                    totals[code][col]+=float(sums[i])
    out=ROOT/'data/processed/constituency_age_sex_2026.csv'
    columns=['const_code','constituency','state']+[f'{sex}_{g}' for sex in ['male','female'] for g in groups]+['estimated_population_18_plus','source','adult_age_method']
    with out.open('w',encoding='utf8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=columns);w.writeheader()
        for feat in house:
            p=feat['properties']; code=str(p.get('const_code') or p.get('Code')); values=totals[code]
            adult=sum(values[f'{s}_{g}'] for s in ['male','female'] for g in ['18_24','25_34','35_49','50_64','65_plus'])
            w.writerow({'const_code':code,'constituency':p.get('const_name') or p.get('Name'),'state':p.get('State'),'estimated_population_18_plus':round(adult),**{k:round(v) for k,v in values.items()},'source':'WorldPop Nigeria Age & Sex Structures 2026, 1km, R2025A v1','adult_age_method':'40% of age 15-19 bin + all age 20+ bins; estimate only'})
    print(f'Wrote {out}')
