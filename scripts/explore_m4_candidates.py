"""Isolated development ablation: both TF-IDF arms use top-k=8/9/12.

Does not modify M2 notebook cells or the shared default configuration.
"""
import argparse
import hashlib
import json
import gzip
import subprocess
import platform
from importlib.metadata import version
from pathlib import Path
from test_member_handoff import ROOT, load


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True)
    args=parser.parse_args()
    if not args.run_id.replace('_','').replace('-','').isalnum():raise ValueError('Invalid run ID')
    root=ROOT/'outputs'/'development'/args.run_id;root.mkdir(parents=True,exist_ok=False)
    try:
        notebook=ROOT/'ARIN7101_Context_Bandit_Release_Notebook.ipynb'
        nb=json.loads(notebook.read_text(encoding='utf-8'))
        selector_source=''.join(next(c['source'] for c in nb['cells'] if c.get('id')=='m2-four-strategies'))
        if selector_source.count('.head(8)')!=1:raise ValueError('M2 changed: re-review experiment adapter')
        ns=load(notebook,'m2');m2_globals=ns['evaluate_episode'].__globals__
        ns.update(load(notebook,'m3'))
        exec(''.join(next(c['source'] for c in nb['cells'] if c.get('id')=='m4-experiment-skeleton')),ns)
        cfg=dict(ns['PROTOCOL_DRAFT']);pd=ns['pd'];np=ns['np'];metric_names=ns['M4_METRICS']
        episodes=[ns['generate_episode'](130000+100*s+i,scenario,cfg)
                  for s,scenario in enumerate(ns['SCENARIOS']) for i in range(3)]
        audits=[ns['audit_truth'](e) for e in episodes]
        if not all(x['passed'] for x in audits):raise ValueError('Truth audit failed')
        (root/'data').mkdir();(root/'config').mkdir();(root/'audit').mkdir()
        (root/'data/dialogues.jsonl.gz').write_bytes(gzip.compress(('\n'.join(json.dumps(e) for e in episodes)+'\n').encode(),mtime=0))
        (root/'audit/truth_checks.json').write_text(json.dumps(audits),encoding='utf-8')
        for name,path in [('notebook.ipynb',notebook),('runner.py',Path(__file__)),('loader.py',ROOT/'scripts/test_member_handoff.py')]:
            (root/'config'/name).write_bytes(path.read_bytes())
        summaries=[];all_metrics=[];queries=[];all_choices=[];base_out=None
        for k in [8,9,12]:
            print('Running top-k='+str(k),flush=True)
            # Only replace the candidate limit in the already reviewed selector.
            exec(compile(selector_source.replace('.head(8)',f'.head({k})'),f'm2-top-{k}-adapter','exec'),m2_globals)
            out,replay=ns['run_evaluation'](episodes,ns['METHODS'],cfg['algorithm_seeds'],cfg)
            folder=root/('k'+str(k));folder.mkdir()
            if k==8:
                base_out=out.copy()
                reference=ROOT/'outputs/development/m4_default_benchmark_20261123/tables/development_outcomes.csv'
                if not reference.exists():raise FileNotFoundError('Run default development benchmark first')
                cols=[c for c in out if c!='construction_ms']
                pd.testing.assert_frame_equal(out[cols].reset_index(drop=True),pd.read_csv(reference)[cols],check_dtype=False)
            else:
                cols=[c for c in out if c!='construction_ms']
                for arm in ['recent_short','recent_long']:
                    pd.testing.assert_frame_equal(out[out.arm==arm][cols].reset_index(drop=True),base_out[base_out.arm==arm][cols].reset_index(drop=True))
            metric=ns['aggregate_dialogues'](replay)
            all_metrics.append(metric.assign(candidate_limit=k))
            summary=metric.groupby(['scenario','method'])[metric_names].mean().reset_index().assign(candidate_limit=k)
            summaries.append(summary)
            annotation=out[['scenario','seed','t','qtype']].drop_duplicates()
            annotated=replay.merge(annotation,on=['scenario','seed','t'],validate='many_to_one')
            grouped=annotated.groupby(['scenario','seed','method','alg_seed','qtype'])[metric_names].mean().groupby(['scenario','seed','method','qtype']).mean().reset_index()
            queries.append(grouped.assign(candidate_limit=k))
            annotated['phase']=np.where(annotated.t<150,'first_150','last_150')
            phase=annotated.groupby(['scenario','seed','method','alg_seed','phase'])[metric_names].mean().groupby(['scenario','seed','method','phase']).mean().reset_index()
            shares=annotated.groupby(['scenario','seed','method','alg_seed','qtype','arm']).size().rename('n').reset_index()
            shares['share']=shares.n/shares.groupby(['scenario','seed','method','alg_seed','qtype']).n.transform('sum')
            all_choices.append(shares.assign(candidate_limit=k))
            out.to_csv(folder/'outcomes.csv',index=False);replay.to_csv(folder/'replay.csv',index=False)
            metric.to_csv(folder/'episode_metrics.csv',index=False);phase.to_csv(folder/'phase_episode_metrics.csv',index=False)
            print('Completed top-k='+str(k),flush=True)
        metrics=pd.concat(all_metrics,ignore_index=True);summary=pd.concat(summaries,ignore_index=True)
        keys=['scenario','seed','method']
        paired=metrics.merge(metrics[metrics.candidate_limit==8][keys+metric_names],on=keys,suffixes=('','_k8'),validate='many_to_one')
        for col in metric_names:paired['delta_'+col]=paired[col]-paired[col+'_k8']
        if not np.allclose(paired.delta_utility,paired.delta_y-.5*paired.delta_cost/512):raise ValueError('Effect decomposition failed')
        paired_summary=paired.groupby(['scenario','method','candidate_limit'])[['delta_'+c for c in metric_names]].mean().reset_index()
        wins=paired.groupby(['scenario','method','candidate_limit']).delta_utility.agg(n='count',wins=lambda x:int((x>1e-12).sum()),losses=lambda x:int((x < -1e-12).sum()),minimum='min',maximum='max').reset_index()
        for name,table in [('method_summary',summary),('paired_dialogue_differences',paired),('paired_summary',paired_summary),('dialogue_wins',wins),('query_episode_metrics',pd.concat(queries)),('arm_choice_counts',pd.concat(all_choices))]:
            table.to_csv(root/(name+'.csv'),index=False)
        report=['# 检索候选数开发探索','',
            '同6条开发对话，两个算法seed；同时改变tfidf与resolved_tfidf候选上限8/9/12。预算与其他默认配置不变。',
            '比较同一方法相对k=8的对话配对差，不在每个候选中重选基线。两检索臂同时变化，不能据此隔离单臂贡献。',
            '并非扩大上下文预算：候选仍经过预算打包；focus锚点规则保持不变。',
            'k=8与上次默认开发四臂表一致（除耗时）；两固定窗口在所有k下相同。',
            '每场景仅3条，参数选择使用开发结果；不能据此宣称正式显著性。','',
            '```',paired_summary.to_string(index=False),'```','', '```',wins.to_string(index=False),'```']
        (root/'report.md').write_text('\n'.join(report),encoding='utf-8')
        manifest=dict(mode='development',run_id=args.run_id,status='computed_pending_review',
            config=cfg,candidate_limits=[8,9,12],changed_arms=['tfidf','resolved_tfidf'],
            seeds=dict(dialogue=[e['seed'] for e in episodes],algorithm=cfg['algorithm_seeds']),
            environment=dict(python=platform.python_version(),packages={k:version(k) for k in ['numpy','pandas','scipy','scikit-learn']}),
            base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            counts=dict(dialogues_per_variant=6,outcomes_per_variant=7200,replay_per_variant=25200),
            files={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()})
        (root/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        for name,sha in manifest['files'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==sha
        print(paired_summary[paired_summary.method.isin(['LaplaceCTS','TS','RuleRouter','resolved_tfidf','tfidf'])].to_string(index=False))
        print(root)
    except BaseException as exc:
        (root/'failure.json').write_text(json.dumps(dict(error=repr(exc))),encoding='utf-8')
        raise


if __name__=='__main__':main()
