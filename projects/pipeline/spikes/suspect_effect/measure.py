# Measures how much the ranking of Ruta 32 changes if suspect isolations are excluded (A) or re-snapped (B). Needs output/ and work/ of a real run.
# Run from the repo root: uv run --project projects/pipeline python projects/pipeline/spikes/suspect_effect/measure.py
import json, math, collections
from pipeline.impact_scoring import score, _nearest_hospitals, _num
from pipeline.rank_sensitivity import top_overlap, rank_correlation
from pipeline.area_config import load_zone
D='projects/pipeline/'
z=load_zone('ruta-32'); alt=[{'name':a,'vehicles':v} for a,v in z.closure_alternates]
g=json.load(open(D+'output/ruta-32/graph.json',encoding='utf-8')); units=json.load(open(D+'work/ruta-32/closure_units.json',encoding='utf-8'))
orig={c['id']:c for c in json.load(open(D+'work/ruta-32/communities.json',encoding='utf-8'))}
base=score(g,units,alt)
pop={c['id']:c['population'] for c in g['communities']}; name={c['id']:c['name'] for c in g['communities']}
nodes={n['id']:n for n in g['nodes']}; edges={e['id']:e for e in g['edges']}; node_of={c['id']:c['node'] for c in g['communities']}
baseline_route={}
b0=_nearest_hospitals(g,set())
for c in g['communities']: baseline_route[c['id']]=b0.get(c['node'])
penalty=max((p['extra_s'] for u in base['candidates'] for p in u['per_community'] if p['extra_s'] is not None),default=0)
def rescore(rows_by_unit):
    out=[]
    for u in base['candidates']:
        rows=rows_by_unit[u['id']]
        aff=[r['community_id'] for r in rows]; iso=[r['community_id'] for r in rows if r['time_s'] is None]
        fin=[r['extra_s'] for r in rows if r['extra_s'] is not None]
        crit=sum((pop[r['community_id']] or 0)*(penalty if r['extra_s'] is None else r['extra_s']) for r in rows)
        out.append({'id':u['id'],'length_m':u['length_m'],'criticality':crit,'affected_community_ids':aff,'isolated_community_ids':iso,'extra_time_s':max(fin) if fin else (None if aff else 0),'edge_ids':u['edge_ids'],
          'population_dependent':sum(pop[c] or 0 for c in aff)})
    out.sort(key=lambda c:(-c['criticality'],-len(c['isolated_community_ids']),c['extra_time_s'] is None,-(c['extra_time_s'] or 0),min((_num(e) for e in c['edge_ids']),default=0)))
    for i,c in enumerate(out,1): c['rank']=i
    return {'candidates':out}
# variant A: drop suspect isolated rows
A={u['id']:[r for r in u['per_community'] if r['community_id'] not in set(u['suspect_isolated_community_ids'])] for u in base['candidates']}
# variant B: re-snap suspect isolated whose node is an endpoint of the closed edges to the nearest open node
def hav(a,b):
    p=math.radians; R=6371000
    d=math.sin(p(b[1]-a[1])/2)**2+math.cos(p(a[1]))*math.cos(p(b[1]))*math.sin(p(b[0]-a[0])/2)**2
    return 2*R*math.asin(math.sqrt(d))
B={}; resnapped=0; still_iso=0; moved_pop=0
for u in base['candidates']:
    closed=set(u['edge_ids']); ends={x for e in closed for x in (edges[e]['from'],edges[e]['to'])}
    nh=_nearest_hospitals(g,closed)
    rows=[]
    openn=[n for n in g['nodes'] if n['id'] not in ends]
    for r in u['per_community']:
        c=r['community_id']
        if r['time_s'] is None and c in set(u['suspect_isolated_community_ids']) and node_of[c] in ends:
            o=orig[c]; best=min(openn,key=lambda n:hav((o['lon'],o['lat']),(n['lon'],n['lat'])))
            res=nh.get(best['id']); resnapped+=1
            if res is None: still_iso+=1; rows.append(r)
            else:
                b=baseline_route[c]
                if b is not None and res[0]>b[0]: rows.append({'community_id':c,'time_s':res[0],'extra_s':res[0]-b[0],'hospital_id':res[1]})
        else: rows.append(r)
    B[u['id']]=rows
sets={'base':rescore({u['id']:u['per_community'] for u in base['candidates']}),'A exclude suspect':rescore(A),'B resnap':rescore(B)}
# sanity: rescored base equals the pipeline ranking
assert [c['id'] for c in sets['base']['candidates']]==[c['id'] for c in sorted(base['candidates'],key=lambda c:c['rank'])]
print('suspect isolated rows',sum(len(u['suspect_isolated_community_ids']) for u in base['candidates']),'| B resnapped',resnapped,'still isolated after resnap',still_iso)
bs=sets['base']
def imp(s): return [c for c in s['candidates'] if c['affected_community_ids']]
for k in ('A exclude suspect','B resnap'):
    s=sets[k]
    cor,n=rank_correlation({'candidates':[{'id':c['id'],'rank':c['rank'],'affected_community_ids':c['affected_community_ids']} for c in bs['candidates']]},{'candidates':[{'id':c['id'],'rank':c['rank'],'affected_community_ids':c['affected_community_ids']} for c in s['candidates']]})
    mk=lambda x:{'candidates':[{'id':c['id'],'rank':c['rank'],'affected_community_ids':c['affected_community_ids']} for c in x['candidates']]}
    print(f"\n== {k}: units with impact {len(imp(s))} (base {len(imp(bs))}); top5 overlap {top_overlap(mk(bs),mk(s),5)}, top10 {top_overlap(mk(bs),mk(s),10)}, top20 {top_overlap(mk(bs),mk(s),20)}; spearman {None if cor is None else round(cor,3)} over {n}")
    print(' top10:',[(c['id'],c['length_m'],len(c['affected_community_ids']),len(c['isolated_community_ids']),round(c['criticality']/1e6)) for c in s['candidates'][:10]])
    moved=[(c['id'],bs_rank,c['rank']) for c in s['candidates'] for bs_rank in [next(x['rank'] for x in bs['candidates'] if x['id']==c['id'])] if abs(bs_rank-c['rank'])>=10]
    print(' units that move >=10 places:',len(moved),moved[:8])
print('\nbase top10:',[(c['id'],c['length_m'],len(c['affected_community_ids']),len(c['isolated_community_ids']),round(c['criticality']/1e6)) for c in bs['candidates'][:10]])
print('penalty s',penalty,'= h',round(penalty/3600,2))
