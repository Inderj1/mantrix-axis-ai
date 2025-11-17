"""Financial metrics pre-calculation service for optimized query performance."""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import structlog
from pydantic import BaseModel, Field
import asyncio
import json

from src.db.base_connector import BaseDatabaseConnector
from src.core.financial_hierarchy import financial_hierarchy
from src.core.cache_manager import CacheManager
from src.config import settings

logger = structlog.get_logger()


class TimeGranularity(Enum):
    """Time granularities for metric aggregation."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    MTD = "mtd"  # Month-to-date
    QTD = "qtd"  # Quarter-to-date
    YTD = "ytd"  # Year-to-date


class MetricCalculation(BaseModel):
    """Represents a pre-calculated metric."""
    metric_code: str
    metric_name: str
    time_period: str
    granularity: TimeGranularity
    dimensions: Dict[str, str] = Field(default_factory=dict)
    value: float
    calculated_at: datetime
    row_count: int = 0
    cache_key: str
    


class PreCalculationConfig(BaseModel):
    """Configuration for pre-calculation jobs."""
    enabled: bool = True
    metrics: List[str] = Field(default_factory=list)  # Empty = all metrics
    granularities: List[TimeGranularity] = Field(
        default_factory=lambda: [
            TimeGranularity.DAILY,
            TimeGranularity.MONTHLY,
            TimeGranularity.MTD,
            TimeGranularity.YTD
        ]
    )
    dimensions: List[str] = Field(
        default_factory=lambda: ["Sales_Region", "Product_Category", "Customer_Segment"]
    )
    lookback_days: int = 365
    refresh_interval_hours: int = 1
    batch_size: int = 10
    

class FinancialMetricsPreCalculator:
    """Service for pre-calculating financial metrics."""

    def __init__(
        self,
        db_client: BaseDatabaseConnector = None,  # Made optional for backward compat
        cache_manager: Optional[CacheManager] = None,
        config: Optional[PreCalculationConfig] = None,
        bq_client: BaseDatabaseConnector = None,  # Deprecated parameter for backward compatibility
        database_qualifier: Optional[str] = None,
        schema_qualifier: Optional[str] = None
    ):
        """Initialize FinancialMetricsPreCalculator with database-agnostic client.

        Args:
            db_client: Database connector instance (preferred)
            cache_manager: Optional cache manager
            config: Pre-calculation configuration
            bq_client: Deprecated, use db_client instead
            database_qualifier: Database/project qualifier
            schema_qualifier: Schema/dataset qualifier
        """
        # Handle backward compatibility
        self.db_client = db_client or bq_client
        self.bq_client = self.db_client  # Backward compatibility alias

        if self.db_client is None:
            raise ValueError("Either db_client or bq_client must be provided")

        self.cache_manager = cache_manager
        self.config = config or PreCalculationConfig()
        self.hierarchy = financial_hierarchy
        self._running = False

        # Store qualifiers
        self.database_qualifier = database_qualifier
        self.schema_qualifier = schema_qualifier

        # Get database capabilities
        if hasattr(self.db_client, 'get_capabilities'):
            self.db_capabilities = self.db_client.get_capabilities()
            self.db_type = self.db_capabilities.database_type
        else:
            self.db_type = 'bigquery'  # Fallback for old clients
        
    def _generate_time_ranges(self) -> Dict[TimeGranularity, List[Dict[str, str]]]:
        """Generate time ranges for each granularity."""
        today = datetime.now().date()
        ranges = {}
        
        # Daily - last 30 days
        if TimeGranularity.DAILY in self.config.granularities:
            daily_ranges = []
            for i in range(30):
                date = today - timedelta(days=i)
                daily_ranges.append({
                    "start": date.isoformat(),
                    "end": date.isoformat(),
                    "label": date.isoformat()
                })
            ranges[TimeGranularity.DAILY] = daily_ranges
        
        # Monthly - last 12 months
        if TimeGranularity.MONTHLY in self.config.granularities:
            monthly_ranges = []
            current_date = today.replace(day=1)
            for i in range(12):
                # Calculate month start and end
                month_start = current_date - timedelta(days=current_date.day - 1)
                if current_date.month == 12:
                    month_end = current_date.replace(year=current_date.year + 1, month=1, day=1) - timedelta(days=1)
                else:
                    month_end = current_date.replace(month=current_date.month + 1, day=1) - timedelta(days=1)
                
                monthly_ranges.append({
                    "start": month_start.isoformat(),
                    "end": month_end.isoformat(),
                    "label": month_start.strftime("%Y-%m")
                })
                
                # Move to previous month
                if current_date.month == 1:
                    current_date = current_date.replace(year=current_date.year - 1, month=12)
                else:
                    current_date = current_date.replace(month=current_date.month - 1)
                    
            ranges[TimeGranularity.MONTHLY] = monthly_ranges
        
        # Quarter - last 4 quarters
        if TimeGranularity.QUARTERLY in self.config.granularities:
            quarterly_ranges = []
            current_quarter = (today.month - 1) // 3 + 1
            current_year = today.year
            
            for i in range(4):
                quarter_start_month = (current_quarter - 1) * 3 + 1
                quarter_start = datetime(current_year, quarter_start_month, 1).date()
                
                if current_quarter == 4:
                    quarter_end = datetime(current_year + 1, 1, 1).date() - timedelta(days=1)
                else:
                    quarter_end = datetime(current_year, quarter_start_month + 3, 1).date() - timedelta(days=1)
                
                quarterly_ranges.append({
                    "start": quarter_start.isoformat(),
                    "end": quarter_end.isoformat(),
                    "label": f"{current_year}-Q{current_quarter}"
                })
                
                # Move to previous quarter
                current_quarter -= 1
                if current_quarter == 0:
                    current_quarter = 4
                    current_year -= 1
                    
            ranges[TimeGranularity.QUARTERLY] = quarterly_ranges
        
        # MTD, QTD, YTD
        if TimeGranularity.MTD in self.config.granularities:
            month_start = today.replace(day=1)
            ranges[TimeGranularity.MTD] = [{
                "start": month_start.isoformat(),
                "end": today.isoformat(),
                "label": "MTD"
            }]
        
        if TimeGranularity.QTD in self.config.granularities:
            current_quarter = (today.month - 1) // 3 + 1
            quarter_start_month = (current_quarter - 1) * 3 + 1
            quarter_start = today.replace(month=quarter_start_month, day=1)
            ranges[TimeGranularity.QTD] = [{
                "start": quarter_start.isoformat(),
                "end": today.isoformat(),
                "label": "QTD"
            }]
        
        if TimeGranularity.YTD in self.config.granularities:
            year_start = today.replace(month=1, day=1)
            ranges[TimeGranularity.YTD] = [{
                "start": year_start.isoformat(),
                "end": today.isoformat(),
                "label": "YTD"
            }]
        
        return ranges
    
    def _build_metric_query(
        self,
        metric_code: str,
        time_range: Dict[str, str],
        dimension: Optional[str] = None
    ) -> str:
        """Build SQL query for a specific metric and time range."""
        metric = self.hierarchy.l1_metrics.get(metric_code)
        if not metric:
            raise ValueError(f"Unknown metric: {metric_code}")
        
        # Get the table name (handle hyphenated names)
        # Build table reference based on database type
        if hasattr(self.db_client, 'qualify_table_name'):
            table_ref = self.db_client.qualify_table_name("dataset_25m_table")
        else:
            # Fallback: construct manually
            if self.database_qualifier and self.schema_qualifier:
                if self.db_type == 'bigquery':
                    table_ref = f"`{self.database_qualifier}.{self.schema_qualifier}.dataset_25m_table`"
                else:
                    table_ref = f"{self.database_qualifier}.{self.schema_qualifier}.dataset_25m_table"
            else:
                table_ref = "dataset_25m_table"
        
        # Build SELECT clause based on metric components
        select_parts = []
        if dimension:
            select_parts.append(f"{dimension}")
        
        # Add metric calculations
        for component_name, sql_expr in metric.formula_components.items():
            select_parts.append(f"{sql_expr} as {component_name}")
        
        # Build WHERE clause
        where_clauses = [
            f"Posting_Date >= '{time_range['start']}'",
            f"Posting_Date <= '{time_range['end']}'"
        ]
        
        # Build GROUP BY clause
        group_by = f"GROUP BY {dimension}" if dimension else ""
        
        # Construct final query
        query = f"""
        SELECT 
            {', '.join(select_parts)}
        FROM {table_ref}
        WHERE {' AND '.join(where_clauses)}
        {group_by}
        """
        
        return query.strip()
    
    def _calculate_metric_value(self, row: Dict[str, Any], metric_code: str) -> float:
        """Calculate the final metric value from components."""
        metric = self.hierarchy.l1_metrics.get(metric_code)
        if not metric:
            return 0.0
        
        # Simple calculations based on metric type
        if metric_code == "GROSS_MARGIN":
            return row.get("revenue", 0) - row.get("cogs", 0)
        elif metric_code == "GROSS_MARGIN_PCT":
            revenue = row.get("gross_margin_pct", 0)
            return revenue if revenue else 0.0
        elif metric_code == "OPERATING_INCOME":
            gross_margin = row.get("gross_margin", 0)
            opex = row.get("operating_expenses", 0)
            return gross_margin - opex
        elif metric_code == "EBITDA":
            operating_income = row.get("operating_income", 0)
            depreciation = row.get("depreciation", 0)
            amortization = row.get("amortization", 0)
            return operating_income + depreciation + amortization
        elif metric_code == "NET_INCOME":
            return row.get("net_income", 0)
        elif metric_code == "NET_MARGIN_PCT":
            return row.get("net_margin_pct", 0)
        else:
            # Default: return first component value
            return next(iter(row.values()), 0)
    
    async def calculate_metrics(self) -> List[MetricCalculation]:
        """Calculate all configured metrics."""
        calculations = []
        time_ranges = self._generate_time_ranges()
        
        # Get metrics to calculate
        metrics_to_calc = self.config.metrics or list(self.hierarchy.l1_metrics.keys())
        
        for metric_code in metrics_to_calc:
            metric = self.hierarchy.l1_metrics.get(metric_code)
            if not metric:
                continue
            
            logger.info(f"Calculating metric: {metric.metric_name}")
            
            for granularity, ranges in time_ranges.items():
                for time_range in ranges:
                    # Calculate without dimensions (overall)
                    try:
                        query = self._build_metric_query(metric_code, time_range)
                        results = self.bq_client.execute_query(query)
                        
                        if results:
                            value = self._calculate_metric_value(results[0], metric_code)
                            
                            calc = MetricCalculation(
                                metric_code=metric_code,
                                metric_name=metric.metric_name,
                                time_period=time_range["label"],
                                granularity=granularity,
                                dimensions={},
                                value=value,
                                calculated_at=datetime.now(),
                                row_count=len(results),
                                cache_key=self._generate_cache_key(
                                    metric_code, granularity, time_range["label"], {}
                                )
                            )
                            calculations.append(calc)
                            
                            # Cache the result
                            if self.cache_manager:
                                await self._cache_calculation(calc)
                    
                    except Exception as e:
                        logger.error(f"Failed to calculate {metric_code} for {time_range['label']}: {e}")
                    
                    # Calculate by dimensions
                    for dimension in self.config.dimensions:
                        try:
                            query = self._build_metric_query(metric_code, time_range, dimension)
                            results = self.bq_client.execute_query(query)
                            
                            for row in results:
                                dimension_value = row.get(dimension, "Unknown")
                                value = self._calculate_metric_value(row, metric_code)
                                
                                calc = MetricCalculation(
                                    metric_code=metric_code,
                                    metric_name=metric.metric_name,
                                    time_period=time_range["label"],
                                    granularity=granularity,
                                    dimensions={dimension: dimension_value},
                                    value=value,
                                    calculated_at=datetime.now(),
                                    row_count=1,
                                    cache_key=self._generate_cache_key(
                                        metric_code, granularity, time_range["label"],
                                        {dimension: dimension_value}
                                    )
                                )
                                calculations.append(calc)
                                
                                # Cache the result
                                if self.cache_manager:
                                    await self._cache_calculation(calc)
                        
                        except Exception as e:
                            logger.error(
                                f"Failed to calculate {metric_code} by {dimension} "
                                f"for {time_range['label']}: {e}"
                            )
                    
                    # Add small delay to avoid overwhelming BigQuery
                    await asyncio.sleep(0.1)
        
        logger.info(f"Completed {len(calculations)} metric calculations")
        return calculations
    
    def _generate_cache_key(
        self,
        metric_code: str,
        granularity: TimeGranularity,
        time_period: str,
        dimensions: Dict[str, str]
    ) -> str:
        """Generate a cache key for a metric calculation."""
        dim_str = json.dumps(dimensions, sort_keys=True) if dimensions else "overall"
        return f"precalc:{metric_code}:{granularity.value}:{time_period}:{dim_str}"
    
    async def _cache_calculation(self, calc: MetricCalculation):
        """Cache a metric calculation."""
        if not self.cache_manager:
            return
        
        try:
            # Store in cache with 24 hour TTL
            self.cache_manager.redis.setex(
                calc.cache_key,
                86400,  # 24 hours
                json.dumps({
                    "metric_code": calc.metric_code,
                    "metric_name": calc.metric_name,
                    "value": calc.value,
                    "time_period": calc.time_period,
                    "granularity": calc.granularity.value,
                    "dimensions": calc.dimensions,
                    "calculated_at": calc.calculated_at.isoformat(),
                    "row_count": calc.row_count
                })
            )
        except Exception as e:
            logger.error(f"Failed to cache calculation: {e}")
    
    def get_precalculated_metric(
        self,
        metric_code: str,
        granularity: TimeGranularity,
        time_period: str,
        dimensions: Optional[Dict[str, str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a pre-calculated metric from cache."""
        if not self.cache_manager:
            return None
        
        cache_key = self._generate_cache_key(
            metric_code, granularity, time_period, dimensions or {}
        )
        
        try:
            cached_data = self.cache_manager.redis.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            logger.error(f"Failed to retrieve cached metric: {e}")
        
        return None
    
    async def run_continuous(self):
        """Run pre-calculation service continuously."""
        self._running = True
        logger.info("Starting continuous metric pre-calculation service")
        
        while self._running:
            try:
                # Run calculations
                start_time = datetime.now()
                calculations = await self.calculate_metrics()
                duration = (datetime.now() - start_time).total_seconds()
                
                logger.info(
                    f"Completed pre-calculation cycle: "
                    f"{len(calculations)} metrics in {duration:.2f}s"
                )
                
                # Wait for next cycle
                await asyncio.sleep(self.config.refresh_interval_hours * 3600)
                
            except Exception as e:
                logger.error(f"Error in pre-calculation cycle: {e}")
                # Wait a bit before retrying
                await asyncio.sleep(300)  # 5 minutes
    
    def stop(self):
        """Stop the continuous pre-calculation service."""
        self._running = False
        logger.info("Stopping metric pre-calculation service")
    
    def get_available_calculations(self) -> List[Dict[str, Any]]:
        """Get list of all available pre-calculated metrics."""
        if not self.cache_manager:
            return []
        
        available = []
        pattern = "precalc:*"
        
        try:
            # Scan for all precalc keys
            cursor = 0
            while True:
                cursor, keys = self.cache_manager.redis.scan(
                    cursor, match=pattern, count=100
                )
                
                for key in keys:
                    try:
                        data = self.cache_manager.redis.get(key)
                        if data:
                            calc_data = json.loads(data)
                            available.append({
                                "cache_key": key,
                                "metric_code": calc_data.get("metric_code"),
                                "metric_name": calc_data.get("metric_name"),
                                "time_period": calc_data.get("time_period"),
                                "granularity": calc_data.get("granularity"),
                                "dimensions": calc_data.get("dimensions"),
                                "calculated_at": calc_data.get("calculated_at")
                            })
                    except Exception as e:
                        logger.error(f"Failed to parse cached metric {key}: {e}")
                
                if cursor == 0:
                    break
                    
        except Exception as e:
            logger.error(f"Failed to list available calculations: {e}")
        
        return available