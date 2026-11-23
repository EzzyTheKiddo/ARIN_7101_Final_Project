"""Freeze approved inputs or run a new registered formal attempt."""
import argparse
import gzip
import json
import platform
import sys
from pathlib import Path
from importlib.metadata import version
from m4_protocol import freeze, verify_frozen, register_event, digest, write_new
from test_member_handoff import ROOT, load
sys.path.insert(0, str(ROOT))


def code_paths():
    return dict(notebook=ROOT/'ARIN7101_Context_Bandit_Release_Notebook.ipynb',
                runner=Path(__file__), protocol=ROOT/'scripts/m4_protocol.py',
                loader=ROOT/'scripts/test_member_handoff.py')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    prep=commands.add_parser('freeze')
    prep.add_argument('--plan',type=Path,required=True)
    prep.add_argument('--evidence',type=Path,required=True,help='JSON mapping evidence names to paths relative to this file')
    prep.add_argument('--destination',type=Path,required=True)
    run=commands.add_parser('run')
    run.add_argument('--frozen',type=Path,required=True)
    run.add_argument('--run-id',required=True)
    args=parser.parse_args()
    if args.command=='freeze':
        evidence={k:(args.evidence.resolve().parent/v).resolve() for k,v in json.loads(args.evidence.read_text(encoding='utf-8')).items()}
        freeze(json.loads(args.plan.read_text(encoding='utf-8')),evidence,code_paths(),args.destination)
        print('Frozen approved plan:',args.destination)
        return
    frozen=verify_frozen(args.frozen)
    for name,path in code_paths().items():
        if digest(path)!=frozen['files']['code/'+name]:
            raise ValueError('Current code differs from approved snapshot: '+name)
    if not args.run_id.replace('-','').replace('_','').isalnum():
        raise ValueError('Invalid run ID')
    plan=frozen['plan'];cfg=plan['config']
    ns=load(code_paths()['notebook'],'m2');ns.update(load(code_paths()['notebook'],'m3'))
    nb=json.loads(code_paths()['notebook'].read_text(encoding='utf-8'))
    exec(''.join(next(c['source'] for c in nb['cells'] if c.get('id')=='m4-experiment-skeleton')),ns)
    # Recompute baselines from exactly the approved development table, never test data.
    development=ns['pd'].read_csv(args.frozen/'evidence'/'development_outcomes')
    if ns['choose_fixed_baselines'](development)!=plan['baselines']:
        raise ValueError('Baseline does not match approved development data')
    if set(development.seed) & {s for v in plan['evaluation_seeds'].values() for s in v}:
        raise ValueError('Development/evaluation seed overlap')
    target=ROOT/'outputs'/'formal'/args.run_id
    if target.exists():raise FileExistsError(target)
    registry=ROOT/'team_workspace'/'formal_runs.json'
    seeds=[s for v in plan['evaluation_seeds'].values() for s in v]
    register_event(registry,dict(run_id=args.run_id,status='started',evaluation_seeds=seeds,
        plan_sha256=frozen['plan_sha256'],frozen_sha256=digest(args.frozen/'frozen_config.json')))
    try:
        target.mkdir(parents=True,exist_ok=False)
        episodes=[ns['generate_episode'](seed,scenario,cfg) for scenario,ss in plan['evaluation_seeds'].items() for seed in ss]
        truth=[ns['audit_truth'](e) for e in episodes]
        if not all(t['passed'] for t in truth):raise ValueError('Truth audit failed')
        outcomes,replay=ns['run_evaluation'](episodes,ns['METHODS'],cfg['algorithm_seeds'],cfg)
        metrics=ns['aggregate_dialogues'](replay)
        primary,secondary=ns['paired_effects'](metrics,plan['baselines'],cfg)
        artifacts={'tables/evaluation_outcomes.csv':outcomes,'tables/replay.csv':replay,
            'tables/episode_metrics.csv':metrics,'tables/primary_effects.csv':primary,
            'tables/secondary_effects.csv':secondary,
            'tables/method_summary.csv':metrics.groupby(['scenario','method'])[ns['M4_METRICS']].mean().reset_index(),
            'data/evaluation_dialogues.jsonl.gz':gzip.compress(('\n'.join(json.dumps(e) for e in episodes)+'\n').encode(),mtime=0),
            'audit/truth_checks.json':json.dumps(truth),
            'config/frozen_config.json':(args.frozen/'frozen_config.json').read_bytes(),
            'config/notebook_snapshot.ipynb':code_paths()['notebook'].read_bytes(),
            'audit/review_snapshot.json':(args.frozen/'evidence'/'approvals').read_bytes(),
            'reports/M4_handoff.md':'# Formal computation completed\nPending M3 statistical and M5 independent review.\n'}
        for relative in frozen['files']:
            artifacts['config/frozen_inputs/'+relative]=(args.frozen/relative).read_bytes()
        env=dict(python=platform.python_version(),packages={k:version(k) for k in ['numpy','pandas','scipy','scikit-learn']})
        artifacts['config/environment.json']=json.dumps(env)
        metadata=dict(mode='formal',run_id=args.run_id,config=cfg,baselines=plan['baselines'],
            frozen_directory=str(args.frozen.resolve()),plan_sha256=frozen['plan_sha256'],
            code_sha256=digest(code_paths()['notebook']),environment=env,
            seeds=dict(evaluation=seeds,algorithm=cfg['algorithm_seeds'],development=sorted(map(int,development.seed.unique()))),
            counts=dict(dialogues=len(episodes),outcomes=len(outcomes),replay=len(replay)))
        manifest=ns['export_run'](target,artifacts,metadata)
        for name,sha in manifest['files'].items():
            if digest(target/name)!=sha:raise ValueError('Archive hash mismatch')
        register_event(registry,dict(run_id=args.run_id,status='computed_pending_review',manifest_sha256=digest(target/'manifest.json')))
        print(target)
    except BaseException as exc:
        if target.exists():write_new(target/'failure.json',dict(type=type(exc).__name__,message=str(exc)))
        register_event(registry,dict(run_id=args.run_id,status='failed',error=repr(exc),evaluation_seeds=seeds))
        raise


if __name__=='__main__':main()
