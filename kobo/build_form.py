from pathlib import Path
import csv, gzip, re
from openpyxl import Workbook
ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'data/source/polling-units.csv'; media=ROOT/'kobo/media/polling_units.csv'
media.parent.mkdir(parents=True,exist_ok=True)
source_gz=Path(str(source)+'.gz')
source_stream=gzip.open(source_gz,'rt',encoding='utf-8-sig',newline='') if source_gz.exists() and not source.exists() else source.open(encoding='utf-8-sig',newline='')
rows=list(csv.DictReader(source_stream)); source_stream.close()
with media.open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['name','label','state_code','lga_code','ward_code','full_code'])
    for r in rows:
        label=(r['pu_name']+' — '+r['pu_location']).strip(' —')
        w.writerow([r['full_code'],label,r['state_code'],r['lga_code'],r['ward_code'],r['full_code']])

wb=Workbook(); survey=wb.active; survey.title='survey'
survey.append(['type','name','label','hint','required','relevant','constraint','constraint_message','choice_filter'])
survey_rows=[
['begin_group','agent_info','Polling-agent registration','','','','','',''],
['note','privacy_notice','Your name, age, mobile number and polling-unit assignment are collected for NDC polling-agent recruitment, deployment and coordination. Data controller contact: [DATA CONTROLLER CONTACT]. Retention period: [RETENTION PERIOD]. Access is limited to authorized coordinators. Do not deploy until the bracketed details are completed.','','','','','',''],
['select_one consent','consent','I have read the notice and agree to this collection and use.','','yes','','','',''],
['text','agent_name','Full name','Enter your name as used for official coordination.','yes','${consent}=\'yes\'','','',''],
['integer','agent_age','Age in completed years','','yes','${consent}=\'yes\'','. >= 18 and . <= 100','Agents must be at least 18 and age must be 100 or below.',''],
['text','mobile_number','Mobile number','Include country code where possible, e.g. +2348012345678.','yes','${consent}=\'yes\'','regex(., "^[+]?[0-9]{8,15}$")','Enter 8–15 digits, with an optional leading +.',''],
['select_one state','state','State','','yes','${consent}=\'yes\'','','',''],
['select_one lga','lga','Local Government Area','','yes','${consent}=\'yes\'','','','state_code=${state}'],
['select_one ward','ward','Ward','','yes','${consent}=\'yes\'','','','state_code=${state} and lga_code=${lga}'],
['select_one_from_file polling_units.csv','polling_unit','Polling unit','','yes','${consent}=\'yes\'','','','state_code=${state} and lga_code=${lga} and ward_code=${ward}'],
['end_group','','','','','','','','']]
for r in survey_rows:survey.append(r)
choices=wb.create_sheet('choices');choices.append(['list_name','name','label','state_code','lga_code'])
seen_state=set();seen_lga=set();seen_ward=set()
for r in rows:
    sc,sn,lc,ln,wc,wn=(r[k] for k in ['state_code','state_name','lga_code','lga_name','ward_code','ward_name'])
    if sc not in seen_state:choices.append(['state',sc,sn,'','']);seen_state.add(sc)
    lk=(sc,lc)
    if lk not in seen_lga:choices.append(['lga',lc,ln,sc,'']);seen_lga.add(lk)
    wk=(sc,lc,wc)
    if wk not in seen_ward:choices.append(['ward',wc,wn,sc,lc]);seen_ward.add(wk)
for value,label in [('yes','Yes'),('no','No')]:choices.append(['consent',value,label,'',''])
settings=wb.create_sheet('settings');settings.append(['form_title','form_id','version','allow_choice_duplicates']);settings.append(['NDC Polling Agent Registration','ndc_polling_agent_registration','2026103101','yes'])
out=ROOT/'kobo/ndc_polling_agent_registration.xlsx';wb.save(out)
print(f'Created {out} and {media} ({len(rows):,} polling-unit choices)')
