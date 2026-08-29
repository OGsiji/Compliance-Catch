"""Shared library for the Compliance Catch pipeline.

Everything the baselines, agent, and eval harness need in common lives here:
data models, transcript/policy loading, prompt templates, trajectory logging,
and the deterministic offline heuristics used when no LLM key is configured.
"""
