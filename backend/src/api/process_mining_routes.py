"""
FastAPI routes for Process Mining
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import structlog
from ..core.process_mining import EventExtractor, ProcessDiscovery, PerformanceAnalyzer
from ..core.process_mining.simulator import ProcessSimulator
from ..core.process_mining.conformance_checker import ConformanceChecker
from ..core.process_mining.insights_engine import InsightsEngine

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/process-mining", tags=["process-mining"])

# Lazy initialize extractor to avoid startup failures when BigQuery isn't configured
_event_extractor = None


def get_event_extractor():
    """Lazy initialization of EventExtractor"""
    global _event_extractor
    if _event_extractor is None:
        try:
            _event_extractor = EventExtractor()
        except Exception as e:
            logger.warning("Failed to initialize EventExtractor", error=str(e))
            raise HTTPException(status_code=503, detail="Process mining service unavailable - BigQuery not configured")
    return _event_extractor


# Request/Response Models
class DiscoverProcessRequest(BaseModel):
    process_type: str  # 'order-to-cash', 'quote-to-cash', 'procure-to-pay'
    date_from: str  # YYYY-MM-DD
    date_to: str  # YYYY-MM-DD
    filters: Optional[Dict[str, Any]] = None


class AnalyzeProcessRequest(BaseModel):
    events: List[Dict[str, Any]]  # Pre-extracted events for analysis
    analysis_types: List[str] = ['dfg', 'variants', 'bottlenecks', 'performance']


class ConformanceCheckRequest(BaseModel):
    process_type: str
    date_from: str
    date_to: str
    reference_model: List[str]  # Expected sequence of activities
    strict: bool = False  # If True, requires exact match


@router.get("/processes")
async def get_available_processes():
    """
    Get list of processes that can be mined from available data
    """
    try:
        extractor = get_event_extractor()
        processes = extractor.get_available_processes()

        return {
            "success": True,
            "processes": processes,
            "total": len(processes)
        }

    except Exception as e:
        logger.error(f"Error getting available processes: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get available processes: {str(e)}"
        )


@router.post("/discover")
async def discover_process(request: DiscoverProcessRequest):
    """
    Discover process from BigQuery event data

    Steps:
    1. Extract events from BigQuery based on process type and date range
    2. Discover process model (DFG)
    3. Identify variants
    4. Analyze performance
    5. Find bottlenecks
    """
    try:
        logger.info(f"Discovering {request.process_type} process from {request.date_from} to {request.date_to}")

        # Step 1: Extract events
        extractor = get_event_extractor()
        if request.process_type == 'order-to-cash':
            events = extractor.extract_o2c_events(
                date_from=request.date_from,
                date_to=request.date_to,
                filters=request.filters
            )
        elif request.process_type == 'quote-to-cash':
            events = extractor.extract_q2c_events(
                date_from=request.date_from,
                date_to=request.date_to,
                filters=request.filters
            )
        elif request.process_type == 'procure-to-pay':
            events = extractor.extract_p2p_events(
                date_from=request.date_from,
                date_to=request.date_to,
                filters=request.filters
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown process type: {request.process_type}"
            )

        if not events:
            return {
                "success": True,
                "message": "No events found for the specified criteria",
                "events_count": 0,
                "process_model": None,
                "variants": [],
                "bottlenecks": [],
                "performance": None
            }

        # Step 2: Discover process model
        discovery = ProcessDiscovery(events)
        process_model = discovery.discover_dfg()

        # Step 3: Identify variants
        variants = discovery.discover_variants()

        # Step 4: Find bottlenecks
        bottlenecks = discovery.find_bottlenecks()

        # Step 5: Analyze performance
        performance = PerformanceAnalyzer(events)
        cycle_times = performance.analyze_cycle_times()
        throughput = performance.analyze_throughput(time_unit='day')
        resource_utilization = performance.analyze_resource_utilization()
        rework = performance.identify_rework()

        # Step 6: Get overall summary
        summary = discovery.get_summary()

        return {
            "success": True,
            "process_type": request.process_type,
            "date_range": {
                "from": request.date_from,
                "to": request.date_to
            },
            "events_count": len(events),
            "summary": summary,
            "process_model": process_model,
            "variants": variants[:20],  # Top 20 variants
            "bottlenecks": bottlenecks[:10],  # Top 10 bottlenecks
            "performance": {
                "cycle_times": cycle_times,
                "throughput": throughput,
                "resource_utilization": resource_utilization[:10],  # Top 10 resources
                "rework": rework
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error discovering process: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to discover process: {str(e)}"
        )


@router.post("/analyze")
async def analyze_process(request: AnalyzeProcessRequest):
    """
    Analyze pre-extracted events

    This endpoint allows frontend to analyze a subset of events
    or re-analyze with different parameters
    """
    try:
        logger.info(f"Analyzing process with {len(request.events)} events")

        if not request.events:
            raise HTTPException(status_code=400, detail="No events provided")

        results = {}

        # DFG Discovery
        if 'dfg' in request.analysis_types:
            discovery = ProcessDiscovery(request.events)
            results['dfg'] = discovery.discover_dfg()

        # Variant Analysis
        if 'variants' in request.analysis_types:
            discovery = ProcessDiscovery(request.events)
            results['variants'] = discovery.discover_variants()

        # Bottleneck Analysis
        if 'bottlenecks' in request.analysis_types:
            discovery = ProcessDiscovery(request.events)
            results['bottlenecks'] = discovery.find_bottlenecks()

        # Performance Analysis
        if 'performance' in request.analysis_types:
            performance = PerformanceAnalyzer(request.events)
            results['performance'] = {
                'cycle_times': performance.analyze_cycle_times(),
                'activity_durations': performance.analyze_activity_durations(),
                'throughput': performance.analyze_throughput(),
                'resource_utilization': performance.analyze_resource_utilization(),
                'rework': performance.identify_rework()
            }

        return {
            "success": True,
            "events_analyzed": len(request.events),
            "results": results
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing process: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze process: {str(e)}"
        )


@router.get("/variants/{process_type}")
async def get_process_variants(
    process_type: str,
    date_from: str = Query(..., description="Start date (YYYY-MM-DD)"),
    date_to: str = Query(..., description="End date (YYYY-MM-DD)"),
    limit: int = Query(50, description="Number of variants to return", ge=1, le=200)
):
    """
    Get process variants for a specific process type
    """
    try:
        # Extract events
        extractor = get_event_extractor()
        if process_type == 'order-to-cash':
            events = extractor.extract_o2c_events(date_from, date_to)
        elif process_type == 'quote-to-cash':
            events = extractor.extract_q2c_events(date_from, date_to)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown process type: {process_type}")

        if not events:
            return {
                "success": True,
                "variants": [],
                "total": 0
            }

        # Discover variants
        discovery = ProcessDiscovery(events)
        variants = discovery.discover_variants()

        return {
            "success": True,
            "variants": variants[:limit],
            "total": len(variants),
            "events_analyzed": len(events)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting variants: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get variants: {str(e)}"
        )


@router.get("/performance/{process_type}")
async def get_process_performance(
    process_type: str,
    date_from: str = Query(..., description="Start date (YYYY-MM-DD)"),
    date_to: str = Query(..., description="End date (YYYY-MM-DD)"),
    metric: Optional[str] = Query(None, description="Specific metric (cycle_time, throughput, rework)")
):
    """
    Get performance metrics for a specific process type
    """
    try:
        # Extract events
        extractor = get_event_extractor()
        if process_type == 'order-to-cash':
            events = extractor.extract_o2c_events(date_from, date_to)
        elif process_type == 'quote-to-cash':
            events = extractor.extract_q2c_events(date_from, date_to)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown process type: {process_type}")

        if not events:
            return {
                "success": True,
                "message": "No events found",
                "performance": None
            }

        # Analyze performance
        performance = PerformanceAnalyzer(events)

        # Return specific metric or all metrics
        if metric == 'cycle_time':
            result = performance.analyze_cycle_times()
        elif metric == 'throughput':
            result = performance.analyze_throughput()
        elif metric == 'rework':
            result = performance.identify_rework()
        else:
            # Return summary
            result = performance.get_performance_summary()

        return {
            "success": True,
            "process_type": process_type,
            "date_range": {"from": date_from, "to": date_to},
            "events_analyzed": len(events),
            "performance": result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get performance metrics: {str(e)}"
        )


@router.get("/activities/{process_type}")
async def get_activity_statistics(
    process_type: str,
    date_from: str = Query(..., description="Start date (YYYY-MM-DD)"),
    date_to: str = Query(..., description="End date (YYYY-MM-DD)")
):
    """
    Get detailed statistics for each activity
    """
    try:
        # Extract events
        extractor = get_event_extractor()
        if process_type == 'order-to-cash':
            events = extractor.extract_o2c_events(date_from, date_to)
        elif process_type == 'quote-to-cash':
            events = extractor.extract_q2c_events(date_from, date_to)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown process type: {process_type}")

        if not events:
            return {
                "success": True,
                "activities": [],
                "total": 0
            }

        # Get activity statistics
        discovery = ProcessDiscovery(events)
        activity_stats = discovery.get_activity_statistics()

        return {
            "success": True,
            "process_type": process_type,
            "activities": activity_stats,
            "total": len(activity_stats)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting activity statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get activity statistics: {str(e)}"
        )


@router.post("/simulate")
async def simulate_process_changes(
    process_model: Dict[str, Any],
    historical_performance: Dict[str, Any],
    modifications: Optional[Dict[str, Any]] = None,
    num_cases: int = Query(1000, description="Number of cases to simulate", ge=100, le=10000)
):
    """
    Run What-If simulation with modified process parameters

    Args:
        process_model: Process model with nodes and edges
        historical_performance: Historical performance metrics for comparison
        modifications: Changes to apply:
            - activity_durations: {activity_name: new_avg_hours}
            - transition_probabilities: {"Activity A → Activity B": new_frequency}
        num_cases: Number of cases to simulate

    Returns:
        Simulation results with projected metrics and comparison to current state
    """
    try:
        logger.info(f"Running simulation with {num_cases} cases")

        # Initialize simulator
        simulator = ProcessSimulator(process_model, historical_performance)

        # Run simulation
        results = simulator.simulate_cases(
            num_cases=num_cases,
            modifications=modifications
        )

        return {
            "success": True,
            "simulation_results": results,
            "message": f"Simulated {num_cases} cases successfully"
        }

    except Exception as e:
        logger.error(f"Error running simulation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to run simulation: {str(e)}"
        )


@router.post("/conformance")
async def check_conformance(request: ConformanceCheckRequest):
    """
    Check conformance between actual process execution and reference model

    Returns fitness score, deviations, and non-conforming cases
    """
    try:
        logger.info(f"Checking conformance for {request.process_type}")

        # Extract events
        extractor = get_event_extractor()
        if request.process_type == 'order-to-cash':
            events = extractor.extract_o2c_events(
                date_from=request.date_from,
                date_to=request.date_to
            )
        elif request.process_type == 'quote-to-cash':
            events = extractor.extract_q2c_events(
                date_from=request.date_from,
                date_to=request.date_to
            )
        elif request.process_type == 'procure-to-pay':
            events = extractor.extract_p2p_events(
                date_from=request.date_from,
                date_to=request.date_to
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown process type: {request.process_type}"
            )

        if not events:
            return {
                "success": True,
                "message": "No events found",
                "conformance": None
            }

        # Check conformance
        checker = ConformanceChecker(events)
        conformance_result = checker.check_conformance(
            reference_model=request.reference_model,
            strict=request.strict
        )

        return {
            "success": True,
            "process_type": request.process_type,
            "date_range": {
                "from": request.date_from,
                "to": request.date_to
            },
            "events_analyzed": len(events),
            "reference_model": request.reference_model,
            "conformance": conformance_result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking conformance: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check conformance: {str(e)}"
        )


@router.post("/insights")
async def generate_insights(
    process_model: Dict[str, Any],
    performance: Dict[str, Any],
    variants: List[Dict[str, Any]]
):
    """
    Generate AI-powered insights from process mining results

    Detects:
    - Bottlenecks
    - Automation opportunities
    - Rework patterns
    - Variant insights
    - Resource imbalances
    - Handover inefficiencies
    """
    try:
        logger.info("Generating AI insights")

        # Generate insights
        engine = InsightsEngine(
            process_model=process_model,
            performance=performance,
            variants=variants
        )

        insights = engine.generate_insights()

        return {
            "success": True,
            "insights": insights,
            "total_insights": len(insights),
            "message": f"Generated {len(insights)} insights"
        }

    except Exception as e:
        logger.error(f"Error generating insights: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate insights: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """
    Health check endpoint for process mining service
    """
    try:
        # Test BigQuery connection
        extractor = get_event_extractor()
        processes = extractor.get_available_processes()

        return {
            "success": True,
            "status": "healthy",
            "available_processes": len(processes),
            "message": "Process mining service is operational"
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Service unhealthy: {str(e)}"
        )
