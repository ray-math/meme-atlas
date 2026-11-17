"""Meaning lookup and structural gates; not new natural-language accuracy."""
import copy
import json
from pathlib import Path
from build_usage_index import build_usage_index
from usage_profiles import ROOT,load_vocabulary
from search_usage import search

def evaluate(root=ROOT):
    root=Path(root)
    original=build_usage_index(root);index=copy.deepcopy(original)
    entry=next(e for e in index['entries'] if e['id']=='shake-a-carrot')
    original_status=entry['review_status'];entry['review_status']='reviewed'
    vocab=load_vocabulary(root)
    cases=[
        ('title-lookup',{'query':entry['title'],'mode':'lookup'}),
        ('title-recommend',{'query':entry['title'],'mode':'recommend'}),
        ('other-check-in',{'intents':['안부확인'],'targets':['상대'],'mode':'lookup'}),
        ('self-check-in',{'intents':['안부확인'],'targets':['자기'],'mode':'lookup'}),
        ('self-comfort',{'intents':['위로요청'],'targets':['자기'],'mode':'lookup'}),
        ('exclude-downplaying',{'query':entry['title'],'exclude_risks':['고통축소'],'mode':'lookup'}),
        ('exclude-factual-risk',{'query':entry['title'],'exclude_risks':['사실오인'],'mode':'lookup'}),
    ]
    rows=[{'id':identity,'filters':filters,'retrieval':search(index,vocab,**filters)}
          for identity,filters in cases]
    preserved=[]
    for folder,identity in [('carrot-scope','C-check-in'),('carrot-scope','A18'),
                            ('carrot-scope','A23'),('direction-scope','A20')]:
        plans=json.loads((root/f'eval/{folder}/plans.json').read_text())['plans']
        answers=json.loads((root/f'eval/{folder}/answers.json').read_text())['answers']
        plan=next(p for p in plans if p['id']==identity)
        answer=next(a for a in answers if a['id']==identity)
        if plan['action'] not in ('clarify','abstain') or answer['action']!=plan['action']:
            raise ValueError('existing public clarification/abstention changed')
        preserved.append({'source':folder,'id':identity,'prompt':plan['prompt'],
                          'action':plan['action'],'answer':answer['text'],
                          'retrieval':{'status':'not_searched','results':[]}})
    if original!=build_usage_index(root):raise ValueError('source index mutated')
    return {'schema_version':1,'execution':'actual Python provisional meaning lookup and structural probes',
            'source_review_status':original_status,'baseline_coverage':original['coverage'],
            'results':rows,'preserved_public_decisions':preserved,
            'limitations':['Title lookup has an explicit dictionary-explanation purpose; no natural-language intent detection claim.',
                           'No user answer or relationship consent is invented.',
                           'Public counterexample AI decisions are preserved, not newly inferred by this script.',
                           'Source profile is not promoted by this script.']}

if __name__=='__main__':
    result=evaluate()
    print('CHECKIN_META='+json.dumps({k:v for k,v in result.items() if k!='results'},ensure_ascii=False))
    for row in result['results']:
        print('CHECKIN_CASE='+json.dumps(row,ensure_ascii=False))
