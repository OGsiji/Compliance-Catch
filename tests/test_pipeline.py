"""End-to-end and unit tests for the offline pipeline — no API key required.

Run: python -m unittest discover -s tests -v
"""
import unittest

from agent.flagger import Flagger
from agent.pipeline import run_pipeline
from agent.verifier import Verifier, quote_matches
from baseline import random_sample
from baseline.keyword_match import keyword_flags
from core.data import (load_all_transcripts, load_ground_truth, load_policy,
                       load_transcript, policy_index, TRANSCRIPTS_DIR)
from core.models import Flag
from core.trajectory import TrajectoryLogger
import os


def _agent(policy_idx):
    logger = TrajectoryLogger(enabled=False)
    return Flagger(None, logger), Verifier(None, logger), logger


class DualConventionScoring(unittest.TestCase):
    """Locks both scoring conventions on a synthetic mirror of call_05/call_10:
    two violation calls each grounding the right rule + a second rule, on two
    lines, plus one clean call flagged with nothing."""

    def test_per_call_and_strict_precision(self):
        from eval.run_eval import score
        gt = {
            "v1": {"violation": True, "policy_id": "P-07", "line": 3},
            "v2": {"violation": True, "policy_id": "P-01", "line": 3},
            "clean": {"violation": False},
        }
        four = [(3, "P-01"), (3, "P-07"), (5, "P-01"), (5, "P-07")]
        preds = {
            "v1": {"reviewed": True, "policy_ids": {"P-01", "P-07"}, "grounded": four, "needs_review": 0},
            "v2": {"reviewed": True, "policy_ids": {"P-01", "P-07"}, "grounded": four, "needs_review": 0},
            "clean": {"reviewed": True, "policy_ids": set(), "grounded": [], "needs_review": 0},
        }
        s = score(preds, gt)
        # per-call: 2 TP, 1 wrong-rule FP per call -> precision 2/(2+2)=0.5
        self.assertEqual((s["tp"], s["fp_per_call"]), (2, 2))
        self.assertEqual(s["precision_per_call"], 0.5)
        # strict: only exact (line, rule) is TP; 3 extra flags per call -> 2/(2+6)
        self.assertEqual((s["tp_strict"], s["fp_strict_line_and_rule"]), (2, 6))
        self.assertEqual(s["precision_strict_line_and_rule"], 0.25)
        # recall is 1.0 under both conventions (nothing missed)
        self.assertEqual(s["recall_per_call"], 1.0)
        self.assertEqual(s["recall_strict_line_and_rule"], 1.0)
        # no single ambiguous "precision" field
        self.assertNotIn("precision", s)


class FlaggerOnlyBaseline(unittest.TestCase):
    """The flagger-only ablation (no verifier) runs and reports its diagnostic."""

    def test_offline_flagger_only_runs_and_reports_diagnostic(self):
        from eval.run_eval import flagger_only_predictions, score
        ts = load_all_transcripts(); pol = load_policy(); gt = load_ground_truth()
        preds, diag = flagger_only_predictions(ts, pol, "offline")
        self.assertEqual(len(preds), 10)
        self.assertIn("total_candidate_flags", diag)
        self.assertIn("quote_check_failures", diag)
        self.assertTrue(all("grounded" in p for p in preds.values()))
        # the offline flagger copies line text verbatim -> nothing fails step 1
        self.assertEqual(diag["quote_check_failures"], 0)
        # unverified candidates still catch every violation (recall 1.0)
        self.assertEqual(score(preds, gt)["recall_per_call"], 1.0)


class OfflineReproducesGroundTruth(unittest.TestCase):
    def test_every_fixture_matches_ground_truth(self):
        transcripts = load_all_transcripts()
        policy = load_policy()
        policy_idx = policy_index(policy)
        gt = load_ground_truth()
        flagger, verifier, logger = _agent(policy_idx)

        for t in transcripts:
            if t.id not in gt:
                continue  # skip non-scored artifacts (e.g. audio round-trip demos)
            report = run_pipeline(t, policy, flagger, verifier, policy_idx, logger)
            grounded = {r.policy_id for r in report if r.status == "grounded"}
            truth = gt[t.id]
            if truth.get("violation"):
                self.assertIn(truth["policy_id"], grounded,
                              f"{t.id}: expected {truth['policy_id']} grounded, got {grounded}")
            else:
                self.assertEqual(grounded, set(),
                                 f"{t.id}: expected no grounded flags, got {grounded}")


class QuoteCheckGrounding(unittest.TestCase):
    def setUp(self):
        self.t = load_transcript(os.path.join(TRANSCRIPTS_DIR, "call_01.json"))
        self.policy_idx = policy_index(load_policy())
        self.verifier = Verifier(None, TrajectoryLogger(enabled=False))

    def test_fabricated_quote_routed_to_needs_review(self):
        fake = Flag(line=7, quote="I promise you will become a millionaire",
                    policy_id="P-01", reasoning="x", severity="high")
        verdict = self.verifier.verify(self.t, fake, self.policy_idx)
        self.assertFalse(verdict.quote_ok)
        self.assertEqual(verdict.status, "needs review")

    def test_whitespace_normalized_match(self):
        real = self.t.line_text(7)
        spaced = "   " + "   ".join(real.split()) + "  "
        flag = Flag(line=7, quote=spaced, policy_id="P-01", reasoning="x", severity="high")
        self.assertTrue(quote_matches(self.t, flag))

    def test_wrong_line_number_fails_quote_check(self):
        real = self.t.line_text(7)
        flag = Flag(line=5, quote=real, policy_id="P-01", reasoning="x", severity="high")
        self.assertFalse(quote_matches(self.t, flag))


class PatternAggregation(unittest.TestCase):
    def test_groups_policy_across_two_or_more_calls(self):
        from eval.run_eval import aggregate_patterns
        preds = {
            "call_01": {"reviewed": True, "policy_ids": {"P-01"}},
            "call_05": {"reviewed": True, "policy_ids": {"P-01", "P-07"}},
            "call_10": {"reviewed": True, "policy_ids": {"P-01"}},
            "call_03": {"reviewed": True, "policy_ids": {"P-03"}},   # single call -> not a pattern
        }
        patterns = aggregate_patterns(preds)
        by_id = {p["policy_id"]: p for p in patterns}
        self.assertIn("P-01", by_id)
        self.assertEqual(by_id["P-01"]["count"], 3)
        self.assertEqual(by_id["P-01"]["calls"], ["call_01", "call_05", "call_10"])
        self.assertNotIn("P-03", by_id, "single-call rule must not be a pattern")
        self.assertNotIn("P-07", by_id, "P-07 grounded on only one call")

    def test_unreviewed_calls_excluded(self):
        from eval.run_eval import aggregate_patterns
        preds = {
            "call_01": {"reviewed": True, "policy_ids": {"P-01"}},
            "call_02": {"reviewed": False, "policy_ids": {"P-01"}},  # unreviewed -> ignored
        }
        self.assertEqual(aggregate_patterns(preds), [])


class BaselineWeaknesses(unittest.TestCase):
    def test_keyword_flags_external_deadline_false_positive(self):
        t = load_transcript(os.path.join(TRANSCRIPTS_DIR, "call_09.json"))
        flags = keyword_flags(t)
        self.assertTrue(flags, "keyword baseline should (wrongly) flag call_09")

    def test_keyword_misses_implied_guarantee(self):
        t = load_transcript(os.path.join(TRANSCRIPTS_DIR, "call_10.json"))
        policy_ids = {f["policy_id"] for f in keyword_flags(t)}
        self.assertNotIn("P-01", policy_ids,
                         "keyword baseline should miss the implied guarantee in call_10")

    def test_random_sample_low_coverage(self):
        transcripts = load_all_transcripts()
        reviewed = random_sample.review(transcripts)
        n_reviewed = sum(1 for v in reviewed.values() if v["reviewed"])
        self.assertEqual(n_reviewed, 1, "5% of 10 rounds up to exactly 1 reviewed call")


if __name__ == "__main__":
    unittest.main()
