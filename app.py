"""MetricTrust: evidence-based SQL quality gates and reconciliation."""
import argparse,html,json,time,shutil
from pathlib import Path
import duckdb,pandas as pd
import dataio
from reporting import report,table,save_json,environment

def audit(raw,output,rules_path=None):
    start=time.perf_counter();output=Path(output);output.mkdir(parents=True,exist_ok=True);evidence=output/'exceptions';evidence.mkdir(exist_ok=True)
    frames=dataio.load(raw);rules=json.loads(Path(rules_path or Path(__file__).with_name('rules.json')).read_text());c=duckdb.connect()
    summaries=[]
    try:
        for name,frame in frames.items():c.register(name,frame)
        for r in rules:
            if not r['id'].replace('_','').isalnum():raise ValueError('Unsafe rule identifier')
            df=c.execute(r['sql']).df();count=len(df)
            df.to_csv(evidence/(r['id']+'.csv'),index=False)
            summaries.append({'rule':r['id'],'severity':r['severity'],'failed_records':count,'status':'FAIL' if count else 'PASS','description':r['description']})
        # Deliberately contrast a naive multi-child join with reconciliation-safe sums.
        comparison=c.execute("SELECT (SELECT COALESCE(SUM(TRY_CAST(payment_value AS DECIMAL(18,2))),0) FROM payments) safe_payments_brl,(SELECT COALESCE(SUM(TRY_CAST(p.payment_value AS DECIMAL(18,2))),0) FROM payments p JOIN items i USING(order_id)) naive_join_payments_brl").df().iloc[0].to_dict()
    finally:c.close()
    m={'dataset':'synthetic demo' if (Path(raw)/'DEMO.txt').exists() else 'Olist public marketplace data','source_rows':{k:len(v) for k,v in frames.items()},'rules':len(rules),'failed_rules':sum(s['status']=='FAIL' for s in summaries),'blocking_rules':sum(s['status']=='FAIL' and s['severity']=='error' for s in summaries),'audit_seconds':time.perf_counter()-start,'join_comparison':comparison,'checks':summaries,'environment':environment(),'source_manifest':dataio.manifest(raw)}
    save_json(output/'metrics.json',m)
    pd.DataFrame(summaries).to_csv(output/'quality_summary.csv',index=False)
    sections=[('Quality gate results',table(summaries,['rule','severity','failed_records','status','description'])),('Why reporting totals disagree',table([comparison],list(comparison))+'<p>The naive join repeats each payment for every item. The safe total sums payment records at their original grain. These diagnostic sums omit unparseable amounts; use the invalid_payment check before treating them as complete totals. Neither total represents recognized revenue or profit.</p>'),('Evidence and policy','<p>Every rule has a CSV in exceptions/ and executable SQL in rules.json. Failed-record counts are per rule and must not be added as unique defective records. Errors block --strict; warnings remain investigation items. Payment reconciliation uses a BRL 0.05 tolerance for rounding. Rules are trusted local configuration, not untrusted user input.</p>')]
    report(output/'dashboard.html','MetricTrust','Trace reporting discrepancies to their source records. '+m['dataset'],sections,{'SQL checks':m['rules'],'Failed rules':m['failed_rules'],'Blocking rules':m['blocking_rules']})
    return m

def inject(raw,target):
    shutil.copytree(raw,target,dirs_exist_ok=True);target=Path(target)
    def edit(name,fn):
        p=target/dataio.FILES[name];d=pd.read_csv(p);d=fn(d);d.to_csv(p,index=False)
    edit('orders',lambda d:pd.concat([d,d.iloc[:1]],ignore_index=True))
    def payment(d):
        d.loc[0,'order_id']='missing_parent';d.loc[1,'payment_value']=-100;return d
    edit('payments',payment)
    def times(d):
        d.loc[2,'order_purchase_timestamp']='not-a-date';d.loc[3,'order_delivered_customer_date']=None;d.loc[3,'order_status']='delivered';return d
    edit('orders',times)
    edit('reviews',lambda d:d.assign(review_score=d.review_score.where(d.index!=0,9)))
    return ['orders_key','payments_orders_fk','negative_payment','invalid_purchase_time','missing_delivered_time','invalid_review_score']

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['demo','download','audit','inject']);p.add_argument('--raw',default='data/raw');p.add_argument('--output',default='results');p.add_argument('--strict',action='store_true');a=p.parse_args()
    if a.command=='download':dataio.fetch(a.raw);return
    if a.command=='demo':dataio.demo(a.raw)
    if a.command=='inject':
        target=Path(a.output)/'injected';expected=inject(a.raw,target);m=audit(target,a.output)
        hit={s['rule'] for s in m['checks'] if s['status']=='FAIL'}
        validation={'expected_rules':expected,'detected_expected':sorted(set(expected)&hit),'all_expected_detected':set(expected)<=hit};save_json(Path(a.output)/'injection_validation.json',validation)
        assert validation['all_expected_detected'];print(json.dumps(validation));return
    m=audit(a.raw,a.output);print(json.dumps(m,indent=2))
    if a.strict and m['blocking_rules']:raise SystemExit(2)
if __name__=='__main__':main()
