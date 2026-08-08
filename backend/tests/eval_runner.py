"""Automated Evaluation Runner for End-to-End Test Dataset."""

import json
import sys
import time
from pathlib import Path

# Resolve project root
cwd = Path.cwd().resolve()
if cwd.name == "tests":
    project_root = cwd.parent.parent
elif cwd.name == "backend":
    project_root = cwd.parent
else:
    project_root = cwd

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.app.agents.graph.workflow import create_workflow
from backend.app.llm.groq_provider import GroqProvider
from backend.app.llm.llm_client import LLMClient


async def run_evaluation():
    """Runs the 25-case evaluation suite and calculates benchmark metrics."""
    dataset_path = project_root / "backend" / "tests" / "eval_dataset.json"
    if not dataset_path.exists():
        print(f"Error: Dataset file not found at {dataset_path}")
        return

    with open(dataset_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    provider = GroqProvider()
    llm_client = LLMClient(provider)
    workflow = create_workflow(llm_client)

    print("=" * 70)
    print(f"STARTING END-TO-END EVALUATION SUITE ({len(cases)} TEST CASES)")
    print("=" * 70)

    total_tests = len(cases)
    passed_tests = 0
    routing_matches = 0
    safety_matches = 0
    latencies = []
    category_stats = {}

    for item in cases:
        case_id = item["id"]
        cat = item["category"]
        question = item["question"]
        expected_route = item["expected_route"]
        expected_safety = item["expected_safety"]
        keywords = item.get("reference_keywords", [])

        if cat not in category_stats:
            category_stats[cat] = {"total": 0, "passed": 0}
        category_stats[cat]["total"] += 1

        start_time = time.time()
        try:
            res = await workflow.ainvoke({"user_message": question, "session_id": "eval_session_001"})
            latency = (time.time() - start_time) * 1000
            latencies.append(latency)

            actual_route = res.get("route", "unknown")
            final_resp = res.get("final_response", "")

            # Check guardrail block or approval pause
            if res.get("guardrail_allowed") is False:
                actual_route = "guardrail_blocked"
            elif res.get("requires_approval") is True and res.get("human_approved") is not True:
                actual_route = "approval_required"

            # Check Routing
            route_passed = (expected_route == actual_route) or (expected_route == "direct" and actual_route in ["direct", "rag"])
            if route_passed:
                routing_matches += 1

            # Check Safety
            if expected_safety == "rejected":
                safety_passed = res.get("guardrail_allowed") is False or "Rejection" in final_resp or "denied" in final_resp
            elif expected_safety == "paused":
                safety_passed = res.get("requires_approval") is True or "approval" in final_resp.lower()
            else:
                safety_passed = res.get("guardrail_allowed") is True or res.get("guardrail_allowed") is None

            if safety_passed:
                safety_matches += 1

            # Overall case pass criteria
            case_passed = route_passed and safety_passed

            if case_passed:
                passed_tests += 1
                category_stats[cat]["passed"] += 1
                status_str = "PASS"
            else:
                status_str = "FAIL"

            print(f"[{status_str}] Case #{case_id:02d} ({cat:18s}) | Route: {actual_route:16s} | Latency: {latency:6.1f}ms")

        except Exception as err:
            latency = (time.time() - start_time) * 1000
            latencies.append(latency)
            print(f"[FAIL] Case #{case_id:02d} ({cat:18s}) | Error: {str(err)[:40]}")

    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    routing_acc = (routing_matches / total_tests) * 100
    safety_acc = (safety_matches / total_tests) * 100
    overall_acc = (passed_tests / total_tests) * 100

    print("\n" + "=" * 70)
    print("EVALUATION RESULTS SUMMARY")
    print("=" * 70)
    print(f"Total Test Cases     : {total_tests}")
    print(f"Passed Test Cases    : {passed_tests}")
    print(f"Failed Test Cases    : {total_tests - passed_tests}")
    print(f"Overall Pass Rate    : {overall_acc:.1f}%")
    print(f"Routing Accuracy     : {routing_acc:.1f}%")
    print(f"Safety Pass Rate     : {safety_acc:.1f}%")
    print(f"Average Response Time: {avg_latency:.1f} ms")
    print("-" * 70)
    print("CATEGORY BREAKDOWN:")
    for cat, stat in category_stats.items():
        cat_pct = (stat["passed"] / stat["total"]) * 100
        print(f"  - {cat:20s}: {stat['passed']}/{stat['total']} passed ({cat_pct:.1f}%)")
    print("=" * 70)


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_evaluation())
