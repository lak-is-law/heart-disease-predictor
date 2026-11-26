"""Evaluate frozen Cleveland models against the original UCI archive. Pass the zip path."""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd
from scipy.stats import binomtest
from sklearn.model_selection import train_test_split

import core
from external_validation import FIRST_VISIT, _fit_cols, boot_ci

ROOT = Path(__file__).parent
LIMITS = dict(zip(core.FEATURES, [(18,110),(0,1),(1,4),(70,260),(80,700),(0,1),(0,2),
                                  (40,230),(0,1),(0,8),(1,3),(0,3),(3,7)]))


def estimate(n, total):
    if not total:
        return None
    ci = binomtest(n, total).proportion_ci()
    return {'count': n, 'total': total, 'rate': n / total, 'ci95': [ci.low, ci.high]}


def evaluate(y, p):
    if not len(y):
        return {'n': 0}
    result = {'n': len(y), 'observed_rate': float(y.mean()), 'mean_prediction': float(p.mean()),
              'brier': float(np.mean((y - p)**2))}
    if len(np.unique(y)) == 2:
        from sklearn.metrics import roc_auc_score
        result.update(auc=float(roc_auc_score(y,p)), auc_ci95=boot_ci(y,p))
    for t in [0.28, 0.5]:
        result[str(t)] = {'missed': estimate(int(((p<t)&(y==1)).sum()),int((y==1).sum())),
                          'false_alarms': estimate(int(((p>=t)&(y==0)).sum()),int((y==0).sum()))}
    return result


def eligible(x, cols):
    valid = pd.Series(True, index=x.index)
    for k in cols:
        v = x[k]
        scale = 10 if k == 'oldpeak' else 1
        valid &= v.between(*LIMITS[k]) & ((v * scale) % 1 == 0)
        if k == 'thal':
            valid &= v.isin([3,6,7])
    return valid


def run(path):
    weights_path = ROOT / 'portal/model_weights.json'
    w = json.loads(weights_path.read_text())
    def shipped(x):
        z = (x[w['numeric']].to_numpy() - w['num_mean']) / w['num_scale']
        vectors = [z] + [(x[k].to_numpy()[:,None] == categories)
                         for k,categories in zip(w['categorical'],w['cat_categories'])]
        return 1 / (1 + np.exp(-(np.column_stack(vectors) @ w['coef'] + w['intercept'])))

    x,y = core.normalize(core.load_raw(str(ROOT/'data/processed.cleveland.data')))
    train,_,labels,_ = train_test_split(x,y,test_size=.2,stratify=y,random_state=42)
    first = _fit_cols(train,labels,FIRST_VISIT)
    result = {'archive_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
              'weights_sha256':hashlib.sha256(weights_path.read_bytes()).hexdigest(),'sites':{}}
    with ZipFile(path) as archive:
        for site in ['hungarian','switzerland','va']:
            with archive.open(f'processed.{site}.data') as stream:
                x,y = core.normalize(pd.read_csv(stream,header=None,names=core.RAW_COLUMNS,na_values='?'))
            common = eligible(x,core.FEATURES)
            entry = {'total':len(y)}
            for name,cols,predict in [('full',core.FEATURES,shipped),
                                      ('first_visit',FIRST_VISIT,lambda x:first.predict_proba(x[FIRST_VISIT])[:,1])]:
                mask = eligible(x,cols)
                entry[name] = {'coverage':estimate(int(mask.sum()),len(y))}
                for key,m in [('eligible',mask),('paired',common)]:
                    entry[name][key] = evaluate(y[m].to_numpy(), predict(x[m]) if m.any() else [])
            result['sites'][site] = entry
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive',type=Path)
    print(json.dumps(run(parser.parse_args().archive),indent=2))
