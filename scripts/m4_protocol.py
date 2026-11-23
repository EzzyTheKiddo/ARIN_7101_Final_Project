"""M4 protocol binding and append-only formal attempt events.

Human approval files are attestations, not cryptographic identity verification.
"""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False, separators=(',', ':')).encode()).hexdigest()


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.flush()
        os.fsync(f.fileno())


def validate_plan(plan, evidence, code_files):
    import pandas as pd
    cfg = plan['config']
    if set(code_files) != {'notebook','runner','protocol','loader'}:
        raise ValueError('All execution source snapshots required')
    if cfg['T'] != 300 or cfg['n_formal_per_scenario'] != 30:
        raise ValueError('This runner supports the agreed 30 x 300 design only')
    if set(plan['evaluation_seeds']) != {'stable', 'abrupt'}:
        raise ValueError('Two scenarios required')
    seeds = [x for group in plan['evaluation_seeds'].values() for x in group]
    if any(len(v) != 30 for v in plan['evaluation_seeds'].values()) or len(set(seeds)) != 60:
        raise ValueError('Exactly 60 distinct dialogue seeds required')
    if any(type(s) is not int or s < 0 for s in seeds):
        raise ValueError('Seeds must be nonnegative integers')
    excluded = set(plan['used_seeds']) | set(range(20261105,20261135)) | set(range(20261205,20261235))
    # Known development/demo and test seeds from this repository.
    excluded |= set(range(130000,130003)) | set(range(130100,130103))
    excluded |= set(range(730000,730006)) | set(range(730100,730106))
    excluded |= {42,910001,910002,910003,910010}
    if excluded.intersection(seeds):
        raise ValueError('Evaluation seeds overlap used/reference seeds')
    if len(cfg['algorithm_seeds']) != len(set(cfg['algorithm_seeds'])) or not cfg['algorithm_seeds']:
        raise ValueError('Invalid algorithm seeds')
    review = pd.read_csv(evidence['audit_review']).fillna('')
    columns = ['seed','t','m1_reviewer','m2_reviewer','verdict','m1_notes','m2_notes']
    if not set(columns).issubset(review) or len(review)!=10 or review.duplicated(['seed','t']).any():
        raise ValueError('Ten distinct audit records required')
    if not (review.verdict=='pass').all() or not review[columns[2:]].astype(str).apply(lambda c:c.str.strip().ne('')).all().all():
        raise ValueError('Audit pending/failed or unsigned')
    approvals=json.loads(Path(evidence['approvals']).read_text(encoding='utf-8'))
    if approvals.get('plan_sha256')!=canonical_hash(plan):
        raise ValueError('Approval does not bind this exact plan')
    expected_code={k:digest(v) for k,v in code_files.items()}
    if approvals.get('code_sha256')!=expected_code:
        raise ValueError('Approval code hashes differ')
    expected_evidence={k:digest(v) for k,v in evidence.items() if k!='approvals'}
    if approvals.get('evidence_sha256')!=expected_evidence:
        raise ValueError('Approval evidence hashes differ')
    members=approvals.get('members',{})
    for member in ['M1','M2','M3','M4','M5']:
        entry=members.get(member,{})
        if entry.get('approved') is not True or not str(entry.get('name','')).strip() or not str(entry.get('date','')).strip():
            raise ValueError('Missing real team approval: '+member)
    if approvals.get('m3_statistics_reviewed') is not True or approvals.get('all_used_seeds_disclosed') is not True:
        raise ValueError('Statistics review/seed disclosure not confirmed')
    # Require upstream evidence as actual files; signatures bind their content.
    for name in ['truth_checks','strategy_checks','method_checks','development_outcomes']:
        if name not in evidence:
            raise ValueError('Missing upstream evidence: '+name)
    return approvals


def freeze(plan, evidence, code_files, destination):
    approvals=validate_plan(plan,evidence,code_files)
    dest=Path(destination)
    dest.mkdir(parents=True,exist_ok=False)
    files={}
    for category, mapping in [('code',code_files),('evidence',evidence)]:
        for name,path in mapping.items():
            if not name.replace('_','').isalnum():
                raise ValueError('Unsafe snapshot name')
            target=dest/category/name
            target.parent.mkdir(exist_ok=True)
            with target.open('xb') as out: out.write(Path(path).read_bytes())
            files[target.relative_to(dest).as_posix()]=digest(target)
    frozen=dict(plan=plan,plan_sha256=canonical_hash(plan),files=files,
                created_at=datetime.now(timezone.utc).isoformat(),status='frozen_pending_execution')
    write_new(dest/'frozen_config.json',frozen)
    return frozen


def verify_frozen(directory):
    root=Path(directory).resolve()
    frozen=json.loads((root/'frozen_config.json').read_text(encoding='utf-8'))
    if canonical_hash(frozen['plan'])!=frozen['plan_sha256']:
        raise ValueError('Frozen plan changed')
    for name,expected in frozen['files'].items():
        path=(root/name).resolve()
        if not path.is_relative_to(root) or digest(path)!=expected:
            raise ValueError('Frozen artifact changed: '+name)
    codes={p.name:p for p in (root/'code').iterdir()}
    evidence={p.name:p for p in (root/'evidence').iterdir()}
    validate_plan(frozen['plan'],evidence,codes)
    return frozen


def register_event(registry, event):
    """Exclusive lock + atomic replacement; preserve all previous events.

    A crashed process leaves a lock to investigate, never silently discard.
    """
    path=Path(registry)
    lock=path.with_suffix(path.suffix+'.lock')
    with lock.open('x'):
        pass
    try:
        events=json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
        if not isinstance(events,list): raise ValueError('Registry must be a list')
        if event['status']=='started':
            if any(e.get('run_id')==event['run_id'] for e in events):
                raise ValueError('Formal run ID already registered')
            used={s for e in events for s in e.get('evaluation_seeds',[])}
            if used.intersection(event['evaluation_seeds']):
                raise ValueError('Formal seeds already attempted')
        else:
            previous=[e for e in events if e.get('run_id')==event['run_id']]
            if not previous or previous[-1]['status']!='started':
                raise ValueError('No active attempt')
            if event['status'] not in ['failed','computed_pending_review']:
                raise ValueError('Unsupported terminal status')
        event=dict(event, timestamp=datetime.now(timezone.utc).isoformat())
        temporary=path.with_suffix(path.suffix+'.new')
        write_new(temporary,events+[event])
        os.replace(temporary,path)
    finally:
        lock.unlink()
