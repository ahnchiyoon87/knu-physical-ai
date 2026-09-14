"""Same lab content, different calendar groupings. Durations are teaching estimates."""
ORDER = {
 '실전반': [('intro',), ('quality','visual'), ('table',), ('rules','pipeline'),
           ('vision','rul'), ('integration',), ('rag',), ('eval','deploy'), ('agent','transfer')],
 '통합반': [('intro',), ('quality','visual'), ('table',), ('rules','pipeline'),
           ('vision',), ('rul','integration'), ('rag',), ('eval',), ('deploy',), ('agent','transfer')],
}
FEATURES = {
 'intro': {'data'}, 'quality': {'quality'}, 'visual': {'visual','judge'},
 'table': {'models','table'}, 'rules': {'rules'}, 'pipeline': {'pipeline','models','pyod','forecast'},
 'vision': {'models','vision'}, 'rul': {'models','rul','forecast'}, 'integration': {'integration'},
 'rag': {'rag'}, 'eval': {'eval'}, 'deploy': {'deploy'}, 'agent': {'agent'}, 'transfer': {'transfer'},
}
THEORY = {'intro':[1], 'quality':[1], 'visual':[2], 'table':[2], 'rules':[3],
          'pipeline':[3,4], 'vision':[5], 'rul':[5], 'integration':[4], 'rag':[6],
          'eval':[7], 'deploy':[7], 'agent':[8], 'transfer':[8]}


def stages():
    records=[]
    for group, days in ORDER.items():
        done=set()
        for day, keys in enumerate(days,1):
            before=set(done)
            for key in keys: done |= FEATURES[key]
            records.append({'group':group,'day':day,'keys':list(keys),
                            'start_features':sorted(before),'complete_features':sorted(done)})
    return records
