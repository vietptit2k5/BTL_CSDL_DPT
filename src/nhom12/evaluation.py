"""ND4c: evaluate explicit relevance, not fabricated accuracy from similarity."""
from .core import ContractError

def evaluate(rankings, judgments, splits):
    """rankings={query_id:[video_id...]}; judgments={qid:[relevant ids]}.

    Threshold/weight selection uses validation only. This routine scores test only.
    Empty-relevance queries are reported separately, never divide by zero.
    """
    if set(rankings)!=set(judgments) or set(rankings)!=set(splits):
        raise ContractError('Query IDs/splits/judgments do not align')
    result=[]
    for qid, ranked in rankings.items():
        if splits[qid]!='test':
            raise ContractError('Final evaluation accepts test queries only')
        if len(ranked)!=5 or len(set(ranked))!=5:
            raise ContractError('Each query must return five distinct videos')
        relevant=set(judgments[qid]); count=0; ap=0
        for i,v in enumerate(ranked,1):
            if v in relevant:
                count+=1;ap+=count/i
        result.append(dict(query_id=qid,precision_at_5=count/5,
          recall_at_5=count/len(relevant) if relevant else None,
          ap_at_5=ap/min(5,len(relevant)) if relevant else None,
          has_relevant=bool(relevant)))
    return result
