"""M4 development/demo integration; deliberately no formal mode."""
import argparse
import gzip
import hashlib
import json
import platform
import subprocess
from datetime import datetime
from importlib.metadata import version
from pathlib import Path
from test_member_handoff import load, ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--quick', action='store_true', help='20-question fixture; not protocol-size demo')
    args = parser.parse_args()
    if not args.run_id.replace('_','').replace('-','').isalnum():
        raise ValueError('Use alphanumeric run ID with dash/underscore')
    notebook = ROOT / 'ARIN7101_Context_Bandit_Release_Notebook.ipynb'
    ns = load(notebook, 'm2')
    m3 = load(notebook, 'm3')
    ns.update({k:v for k,v in m3.items() if not k.startswith('__')})
    nb = json.loads(notebook.read_text(encoding='utf-8'))
    source = next(''.join(c['source']) for c in nb['cells'] if c.get('id') == 'm4-experiment-skeleton')
    exec(compile(source, 'm4-experiment-skeleton', 'exec'), ns)
    cfg = dict(ns['PROTOCOL_DRAFT'])
    if args.quick:
        cfg.update(T=20, n_dev_per_scenario=2, n_demo_per_scenario=2)
    run = ROOT / 'outputs' / 'demo' / args.run_id
    run.mkdir(parents=True, exist_ok=False)
    try:
        dev = [ns['generate_episode'](130000+100*s+i, scenario, cfg)
               for s,scenario in enumerate(ns['SCENARIOS']) for i in range(cfg['n_dev_per_scenario'])]
        episodes = [ns['generate_episode'](730000+100*s+i, scenario, cfg)
                    for s,scenario in enumerate(ns['SCENARIOS']) for i in range(cfg['n_demo_per_scenario'])]
        assert not {e['seed'] for e in dev} & {e['seed'] for e in episodes}
        truth_checks = [ns['audit_truth'](e) for e in dev + episodes]
        if not all(check['passed'] for check in truth_checks):
            raise ValueError('M1 independent truth audit failed')
        pd = ns['pd']
        dev_out = pd.concat([ns['evaluate_episode'](e,cfg) for e in dev], ignore_index=True)
        baselines = ns['choose_fixed_baselines'](dev_out)
        outcomes, replay = ns['run_evaluation'](episodes, ns['METHODS'], cfg['algorithm_seeds'], cfg)
        metrics = ns['aggregate_dialogues'](replay)
        primary, secondary = ns['paired_effects'](metrics,baselines,cfg)
        artifacts = {'tables/development_outcomes.csv':dev_out,
            'tables/evaluation_outcomes.csv':outcomes, 'tables/replay.csv':replay,
            'tables/episode_metrics.csv':metrics,'tables/primary_effects.csv':primary,
            'tables/secondary_effects.csv':secondary,
            'tables/method_summary.csv':metrics.groupby(['scenario','method'])[ns['M4_METRICS']].mean().reset_index(),
            'config/notebook_snapshot.ipynb':notebook.read_bytes(),
            'config/runner_snapshot.py':Path(__file__).read_bytes(),
            'config/loader_snapshot.py':(ROOT/'scripts/test_member_handoff.py').read_bytes(),
            'audit/truth_checks.json':json.dumps(truth_checks),
            'data/evaluation_dialogues.jsonl.gz':gzip.compress(('\n'.join(json.dumps(e) for e in episodes)+'\n').encode(),mtime=0),
            'config/development_plan.json':json.dumps(dict(config=cfg,baselines=baselines,frozen=False)),
            'reports/M4_handoff.md':'# M4 demo handoff\nNot formal results. Human review and formal lifecycle remain pending.\n'}
        env = dict(python=platform.python_version(), packages={k:version(k) for k in ['numpy','pandas','scipy','scikit-learn']})
        artifacts['config/environment.json']=json.dumps(env)
        metadata=dict(mode='demo',run_id=args.run_id,fixture=args.quick,config=cfg,baselines=baselines,
            code_sha256=hashlib.sha256(notebook.read_bytes()).hexdigest(),
            base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            source_has_uncommitted_changes=bool(subprocess.check_output(
                ['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip()),environment=env,
            seeds=dict(development=[e['seed'] for e in dev],evaluation=[e['seed'] for e in episodes],algorithm=cfg['algorithm_seeds']),
            counts=dict(dialogues=len(episodes),outcomes=len(outcomes),replay=len(replay)),
            review_status='pending',created_at=datetime.now().astimezone().isoformat())
        manifest=ns['export_run'](run,artifacts,metadata)
        for name,digest in manifest['files'].items():
            assert hashlib.sha256((run/name).read_bytes()).hexdigest()==digest
        print(run)
        print(json.dumps(metadata['counts']))
        print('Archive hashes verified. DEMO ONLY, human review pending.')
    except Exception as exc:
        (run/'failure.json').write_text(json.dumps(dict(type=type(exc).__name__,error=str(exc))),encoding='utf-8')
        raise


if __name__ == '__main__':
    main()
