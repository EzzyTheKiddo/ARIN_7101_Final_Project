"""Default-parameter, six-dialogue development benchmark; no formal data."""
import argparse
import gzip
import hashlib
import json
import platform
import subprocess
from datetime import datetime
from importlib.metadata import version
from pathlib import Path
from test_member_handoff import ROOT, load


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True)
    args=parser.parse_args()
    if not args.run_id.replace('_','').replace('-','').isalnum():raise ValueError('Invalid run ID')
    run=ROOT/'outputs'/'development'/args.run_id
    run.mkdir(parents=True,exist_ok=False)
    try:
        notebook=ROOT/'ARIN7101_Context_Bandit_Release_Notebook.ipynb'
        ns=load(notebook,'m2');ns.update(load(notebook,'m3'))
        nb=json.loads(notebook.read_text(encoding='utf-8'))
        exec(''.join(next(c['source'] for c in nb['cells'] if c.get('id')=='m4-experiment-skeleton')),ns)
        cfg=dict(ns['PROTOCOL_DRAFT']);pd=ns['pd'];np=ns['np'];metrics_names=ns['M4_METRICS']
        episodes=[ns['generate_episode'](130000+100*s+i,scenario,cfg)
                  for s,scenario in enumerate(ns['SCENARIOS']) for i in range(3)]
        checks=[ns['audit_truth'](e) for e in episodes]
        if not all(x['passed'] for x in checks):raise ValueError('Truth audit failed')
        print('Six development dialogues generated and truth-checked.',flush=True)
        outcomes,replay=ns['run_evaluation'](episodes,ns['METHODS'],cfg['algorithm_seeds'],cfg)
        metrics=ns['aggregate_dialogues'](replay)
        assert len(outcomes)==7200 and len(replay)==25200 and len(metrics)==42
        baselines=ns['choose_fixed_baselines'](outcomes)
        summary=metrics.groupby(['scenario','method'])[metrics_names].mean().reset_index()
        meta=outcomes[['seed','scenario','t','qtype','state']].drop_duplicates()
        annotated=replay.merge(meta,on=['seed','scenario','t'],validate='many_to_one')
        annotated['phase']=np.where(annotated.t<150,'first_150','last_150')
        def subgroup(group):
            per_seed=annotated.groupby(['scenario','seed','method','alg_seed',group])[metrics_names].mean()
            per_dialogue=per_seed.groupby(['scenario','seed','method',group]).mean().reset_index()
            return per_dialogue,per_dialogue.groupby(['scenario','method',group])[metrics_names].mean().reset_index()
        phase_dialogues,phase_summary=subgroup('phase')
        query_dialogues,query_summary=subgroup('qtype')
        def differences(table,extra):
            keys=['scenario','seed']+extra
            baseline_rows=pd.concat([table[(table.scenario==s)&(table.method==b)] for s,b in baselines.items()])
            joined=table.merge(baseline_rows[keys+metrics_names],on=keys,suffixes=('','_baseline'),validate='many_to_one')
            for col in metrics_names:joined['delta_'+col]=joined[col]-joined[col+'_baseline']
            assert np.allclose(joined.delta_utility,joined.delta_y-cfg['lambda']*joined.delta_cost/cfg['cost_reference'])
            return joined[keys+['method']+['delta_'+c for c in metrics_names]]
        delta=differences(metrics,[]);phase_delta=differences(phase_dialogues,['phase'])
        win=delta.groupby(['scenario','method']).delta_utility.agg(n='count',wins=lambda x:int((x>1e-12).sum()),ties=lambda x:int((abs(x)<=1e-12).sum()),losses=lambda x:int((x < -1e-12).sum()),mean='mean',minimum='min',maximum='max').reset_index()
        choice=annotated.groupby(['scenario','seed','method','alg_seed','qtype','arm']).size().rename('count').reset_index()
        choice['share']=choice['count']/choice.groupby(['scenario','seed','method','alg_seed','qtype'])['count'].transform('sum')
        # Explicit zero cells avoid averaging only seeds that selected a given arm.
        wide=choice.pivot(index=['scenario','seed','method','alg_seed','qtype'],columns='arm',values='share').reindex(columns=ns['ARMS']).fillna(0)
        choice_summary=wide.groupby(['scenario','method','qtype']).mean().reset_index()
        tables={'development_outcomes':outcomes,'development_replay':replay,'episode_metrics':metrics,
            'method_summary':summary,'phase_episode_metrics':phase_dialogues,'phase_summary':phase_summary,
            'query_episode_metrics':query_dialogues,'query_summary':query_summary,
            'paired_dialogue_differences':delta,'phase_paired_differences':phase_delta,
            'dialogue_wins':win,'arm_choice_by_query':choice_summary}
        for area in ['data','tables','audit','config','reports','figures']:(run/area).mkdir()
        for name,table in tables.items():table.to_csv(run/'tables'/(name+'.csv'),index=False)
        for name,data in [('environment',dict(python=platform.python_version(),packages={k:version(k) for k in ['numpy','pandas','scipy','scikit-learn']})),('development_plan',dict(config=cfg,baselines=baselines,selection_and_comparison_use_same_data=True))]:
            (run/'config'/(name+'.json')).write_text(json.dumps(data,indent=2),encoding='utf-8')
        (run/'audit/truth_checks.json').write_text(json.dumps(checks),encoding='utf-8')
        (run/'data/development_dialogues.jsonl.gz').write_bytes(gzip.compress(('\n'.join(json.dumps(e) for e in episodes)+'\n').encode(),mtime=0))
        for name,path in [('notebook_snapshot.ipynb',notebook),('runner_snapshot.py',Path(__file__)),('loader_snapshot.py',ROOT/'scripts/test_member_handoff.py')]:
            (run/'config'/name).write_bytes(path.read_bytes())
        report=['# 默认参数开发基准','',
            '6条开发对话，每场景3条、每条300题；算法seed 17/37。全部结果是开发诊断，不是独立正式评估。',
            '固定基线用同一开发集选择，存在选择影响；不据此作确认性显著性结论。阶段分析沿用全程选定基线，不在各阶段重新挑基线。',
            '主指标先在算法seed内平均题目，再在对话内平均seed；按对话等权汇总。题型统计只描述该题型条件下表现。',
            '成本是完整输入正则长度代理，非实际token/API费用。','', '基线：'+json.dumps(baselines),'',
            '## 场景汇总','```',summary.to_string(index=False),'```','',
            '## 前后半程','```',phase_summary.to_string(index=False),'```','',
            '## 对话配对胜负（包含基线自身平局）','```',win.to_string(index=False),'```',
            '','每场景仅3条对话，胜负/均值不构成稳定优越性的证据；保留所有方法和负结果。']
        (run/'reports/development_benchmark.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
        files={p.relative_to(run).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in run.rglob('*') if p.is_file()}
        manifest=dict(mode='development',run_id=args.run_id,status='computed_pending_review',config=cfg,baselines=baselines,
            seeds=dict(dialogue=[e['seed'] for e in episodes],algorithm=cfg['algorithm_seeds']),
            counts=dict(dialogues=6,questions=1800,outcomes=len(outcomes),replay=len(replay)),
            created_at=datetime.now().astimezone().isoformat(),files=files,
            code_sha256=hashlib.sha256(notebook.read_bytes()).hexdigest(),
            base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            working_tree_dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()))
        (run/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        for name,sha in files.items():assert hashlib.sha256((run/name).read_bytes()).hexdigest()==sha
        print(summary.to_string(index=False));print('Baselines:',baselines);print('Archive:',run)
    except BaseException as exc:
        (run/'failure.json').write_text(json.dumps(dict(type=type(exc).__name__,message=str(exc))),encoding='utf-8')
        raise


if __name__=='__main__':main()
