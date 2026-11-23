"""Synthetic approval fixtures only, isolated from real team records."""
import json
import tempfile
import unittest
from pathlib import Path
from m4_protocol import canonical_hash, digest, freeze, verify_frozen, register_event


class ProtocolTests(unittest.TestCase):
    def test_binding_and_attempt_history(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            plan=dict(config=dict(T=300,n_formal_per_scenario=30,algorithm_seeds=[17,37]),
                evaluation_seeds=dict(stable=list(range(800000,800030)),abrupt=list(range(800100,800130))),
                used_seeds=[],baselines=dict(stable='recent_short',abrupt='tfidf'))
            codes={k:root/k for k in ['notebook','runner','protocol','loader']}
            for p in codes.values():p.write_text('fixture',encoding='utf-8')
            evidence={k:root/(k+'.json') for k in ['truth_checks','strategy_checks','method_checks','development_outcomes']}
            for p in evidence.values():p.write_text('{}',encoding='utf-8')
            review=root/'audit.csv';review.write_text('seed,t,m1_reviewer,m2_reviewer,verdict,m1_notes,m2_notes\n'+''.join(f'1,{i},fixture_m1,fixture_m2,pass,fixture,fixture\n' for i in range(10)),encoding='utf-8')
            evidence['audit_review']=review
            approval=dict(plan_sha256=canonical_hash(plan),code_sha256={k:digest(v) for k,v in codes.items()},
                evidence_sha256={k:digest(v) for k,v in evidence.items()},
                members={k:dict(name='SYNTHETIC',date='fixture',approved=True) for k in ['M1','M2','M3','M4','M5']},
                m3_statistics_reviewed=True,all_used_seeds_disclosed=True)
            evidence['approvals']=root/'approval.json';evidence['approvals'].write_text(json.dumps(approval),encoding='utf-8')
            dest=root/'frozen';freeze(plan,evidence,codes,dest);verify_frozen(dest)
            with self.assertRaises(FileExistsError):freeze(plan,evidence,codes,dest)
            (dest/'code'/'notebook').write_text('tampered')
            with self.assertRaises(ValueError):verify_frozen(dest)
            altered=dict(plan,used_seeds=[800000])
            with self.assertRaises(ValueError):freeze(altered,evidence,codes,root/'bad')
            review.write_text(review.read_text().replace('pass','pending'))
            with self.assertRaises(ValueError):freeze(plan,evidence,codes,root/'unsigned')
            registry=root/'runs.json'
            register_event(registry,dict(run_id='a',status='started',evaluation_seeds=[800000]))
            register_event(registry,dict(run_id='a',status='failed'))
            with self.assertRaises(ValueError):register_event(registry,dict(run_id='b',status='started',evaluation_seeds=[800000]))
            with self.assertRaises(ValueError):register_event(registry,dict(run_id='a',status='started',evaluation_seeds=[800001]))
            self.assertEqual(len(json.loads(registry.read_text())),2)


if __name__=='__main__':unittest.main()
