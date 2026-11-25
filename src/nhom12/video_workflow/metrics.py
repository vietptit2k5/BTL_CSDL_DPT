"""Macro metrics on queries, exact random-gallery baseline and grouped SE."""
import numpy as np
from ..core import ContractError

METRICS = ('class','d1','d2','d5')


def top_five(matrices, weights, query_indices):
    scores = sum(weights[f]*matrices[f][query_indices] for f in weights)
    scores = scores.copy(); scores[np.arange(len(query_indices)),query_indices] = -np.inf
    return np.argsort(-scores,axis=1,kind='stable')[:,:5]


def values(labels, query_indices, top):
    return np.column_stack([(labels[f][top] == labels[f][query_indices,None]).mean(1) for f in METRICS])


def macro(x, classes, groups):
    """Query-weighted mean within each class, equally weighted across classes.

    SE uses cluster sums within class. With one query/group it reduces to s/sqrt(n).
    The combined objective is formed per query before this function, retaining covariance.
    """
    x = np.asarray(x,np.float64); classes=np.asarray(classes); groups=np.asarray(groups)
    means={}; variance=0.0
    for c in sorted(set(classes)):
        mask=classes==c; v=x[mask]; g=groups[mask]; units=sorted(set(g))
        if len(units)<2:
            raise ContractError(f'Need two independent query groups in class {c} to estimate SE')
        mean=float(v.mean()); means[c]=mean
        sums=np.array([(v[g==u]-mean).sum() for u in units])
        variance += len(units)/(len(units)-1)*float((sums*sums).sum())/len(v)**2
    return dict(mean=float(np.mean(list(means.values()))),se=float(np.sqrt(variance)/len(means)),per_class=means)


def summarize(v, classes, groups):
    result={f:macro(v[:,i],classes,groups) for i,f in enumerate(METRICS)}
    result['objective']=macro(v.mean(1),classes,groups)
    return result


def random_expectation(labels, queries):
    n=len(labels['class'])
    return np.column_stack([np.array([(labels[f]==labels[f][q]).sum()-1 for q in queries])/(n-1)
                            for f in METRICS])


def joint_values(labels, queries, top):
    same_class=labels['class'][top] == labels['class'][queries,None]
    return {f:(same_class & (labels[f][top]==labels[f][queries,None])).mean(1) for f in METRICS[1:]}


def split_queries(ids, classes, groups, seed=2026):
    rng=np.random.default_rng(seed); assignments={}
    # Group IDs must not silently straddle classes; these need manual duplicate review.
    for group in set(groups):
        if len(set(classes[np.array(groups)==group])) != 1:
            raise ContractError('A group spans classes; resolve labels/duplicates before splitting')
    for c in sorted(set(classes)):
        units=np.array(sorted(set(np.array(groups)[classes==c])))
        rng.shuffle(units)
        if len(units)<4:
            raise ContractError('Need four groups per class for development/test SE')
        half=len(units)//2
        assignments.update({str(g):'development' if i<half else 'test' for i,g in enumerate(units)})
    return [dict(video_id=vid,class_code=str(c),group=str(g),split=assignments[str(g)])
            for vid,c,g in zip(ids,classes,groups,strict=True)]
