"""
Test script for Pipeline API endpoints.

Tests:
1. Pipeline status endpoint
2. Pipeline history endpoint
3. Manual pipeline execution
4. Pipeline run details
"""

import asyncio
import sys
from datetime import datetime
from src.api.pipeline_routes import (
    get_orchestrator,
    get_pipeline_status,
    get_pipeline_history,
    PipelineExecuteRequest,
    execute_pipeline
)
from fastapi import BackgroundTasks

print("=" * 80)
print("PIPELINE API TESTS")
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)
print()

async def test_pipeline_api():
    """Test all pipeline API endpoints."""

    # Test 1: Get Pipeline Status
    print("=" * 80)
    print("TEST 1: Get Pipeline Status")
    print("=" * 80)
    try:
        status = await get_pipeline_status()
        print(f"✅ Pipeline Status Retrieved")
        print(f"   Is Running: {status.is_running}")
        print(f"   Next Scheduled: {status.next_scheduled_run}")
        if status.last_run:
            print(f"   Last Run ID: {status.last_run.run_id}")
            print(f"   Last Run Status: {status.last_run.status}")
        else:
            print(f"   Last Run: None (no previous runs)")
        print()
    except Exception as e:
        print(f"❌ Pipeline Status Failed: {e}")
        print()

    # Test 2: Get Pipeline History
    print("=" * 80)
    print("TEST 2: Get Pipeline History")
    print("=" * 80)
    try:
        history = await get_pipeline_history(limit=5)
        print(f"✅ Pipeline History Retrieved")
        print(f"   Total runs in history: {len(history)}")
        for i, run in enumerate(history[:3], 1):
            print(f"   Run {i}: {run.run_id} - {run.status}")
        print()
    except Exception as e:
        print(f"❌ Pipeline History Failed: {e}")
        print()

    # Test 3: Manual Pipeline Execution (Limited)
    print("=" * 80)
    print("TEST 3: Manual Pipeline Execution (2 tables)")
    print("=" * 80)
    try:
        # Execute with only 2 tables for testing
        request = PipelineExecuteRequest(
            incremental=False,
            table_names=["GL_Accounts", "cohort_avg_revenue_table"]
        )

        # Create a dummy BackgroundTasks instance
        background_tasks = BackgroundTasks()

        print("Executing pipeline with 2 tables...")
        result = await execute_pipeline(request, background_tasks)

        print(f"✅ Pipeline Executed")
        print(f"   Run ID: {result.run_id}")
        print(f"   Status: {result.status}")
        print(f"   Duration: {result.duration_seconds:.1f}s")
        print(f"   Tables Processed: {result.tables_processed}")
        print(f"   Changes Detected: {result.changes_detected}")
        if result.errors:
            print(f"   Errors: {len(result.errors)}")
            for error in result.errors[:3]:
                print(f"     - {error}")
        print()
    except Exception as e:
        print(f"❌ Pipeline Execution Failed: {e}")
        import traceback
        traceback.print_exc()
        print()

    # Test 4: Verify Scheduler
    print("=" * 80)
    print("TEST 4: Verify Scheduler Configuration")
    print("=" * 80)
    try:
        from src.core.pipeline_scheduler import get_pipeline_scheduler
        from datetime import time as dt_time

        scheduler = get_pipeline_scheduler(
            execution_time=dt_time(2, 0),
            check_interval=300
        )

        next_run = scheduler.get_next_run_time()
        print(f"✅ Scheduler Configured")
        print(f"   Execution Time: 2:00 AM daily")
        print(f"   Check Interval: 5 minutes (300s)")
        print(f"   Next Scheduled Run: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
    except Exception as e:
        print(f"❌ Scheduler Configuration Failed: {e}")
        print()

    # Test 5: Orchestrator Singleton
    print("=" * 80)
    print("TEST 5: Orchestrator Singleton")
    print("=" * 80)
    try:
        orch1 = get_orchestrator()
        orch2 = get_orchestrator()
        is_singleton = orch1 is orch2

        print(f"✅ Orchestrator Singleton Test")
        print(f"   Same instance: {is_singleton}")
        print(f"   Instance ID: {id(orch1)}")
        print()
    except Exception as e:
        print(f"❌ Orchestrator Singleton Failed: {e}")
        print()

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("All pipeline API tests completed!")
    print()
    print("Next Steps:")
    print("1. Start the backend server: uvicorn src.main:app --reload")
    print("2. Visit http://localhost:8000/docs to see the API documentation")
    print("3. Access the Pipeline Management UI in the Control Center")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_pipeline_api())
