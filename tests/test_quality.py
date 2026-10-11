import pandas as pd
from dataio import demo,FILES
from app import audit,inject

def test_clean_fixture_and_join_trap(tmp_path):
 raw=demo(tmp_path/'raw',n=70);m=audit(raw,tmp_path/'out')
 assert m['failed_rules']==0
 assert m['join_comparison']['naive_join_payments_brl']>m['join_comparison']['safe_payments_brl']
 assert m['rules']==22

def test_six_injected_error_classes(tmp_path):
 raw=demo(tmp_path/'raw',n=70);expected=inject(raw,tmp_path/'bad');m=audit(tmp_path/'bad',tmp_path/'out')
 hit={s['rule'] for s in m['checks'] if s['failed_records']}
 assert set(expected)<=hit
 assert m['blocking_rules']>=5

def test_reconciliation_tolerance(tmp_path):
 raw=demo(tmp_path/'raw',n=5);p=raw/FILES['payments'];df=pd.read_csv(p);df.loc[1,'payment_value']+=1;df.to_csv(p,index=False)
 m=audit(raw,tmp_path/'out');r=next(x for x in m['checks'] if x['rule']=='payment_reconciliation');assert r['failed_records']==1

def test_nan_rejected(tmp_path):
 raw=demo(tmp_path/'raw',n=5);p=raw/FILES['items'];d=pd.read_csv(p);d['price']=d.price.astype(str);d.loc[0,'price']='NaN';d.to_csv(p,index=False)
 m=audit(raw,tmp_path/'out');assert next(x for x in m['checks'] if x['rule']=='invalid_item_amount')['failed_records']==1


def test_unparseable_payment_reported_not_crashed(tmp_path):
 raw=demo(tmp_path/'raw',n=5);p=raw/FILES['payments'];d=pd.read_csv(p);d['payment_value']='invalid';d.to_csv(p,index=False)
 m=audit(raw,tmp_path/'out');assert next(x for x in m['checks'] if x['rule']=='invalid_payment')['failed_records']==len(d)
 assert m['join_comparison']['safe_payments_brl']==0
