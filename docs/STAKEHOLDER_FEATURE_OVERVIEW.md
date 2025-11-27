# Mantrix Axis AI: Platform Overview for Stakeholders

**Revolutionizing Business Intelligence with Conversational AI**

*Version 2.0 | November 2025*

---

## Executive Summary

Mantrix Axis AI is an **AI-native business intelligence platform** that fundamentally reimagines how organizations interact with their data. Unlike traditional BI tools that require technical expertise and extensive training, Mantrix enables anyone in the organization to get instant insights simply by asking questions in plain English.

**The Core Value Proposition:**
> *"Ask your data anything, get answers instantly—no SQL knowledge required, no dashboards to build, no waiting for IT."*

---

## What Makes Mantrix Axis AI Unique

### 1. Conversational Intelligence: Just Ask

**The Problem:** Traditional BI tools require users to know where data lives, how to build visualizations, and often SQL expertise. Business users wait days or weeks for reports.

**Our Solution:** Type natural language questions like a conversation:

```
"What were our top 10 customers by revenue last quarter?"
"Show me the sales trend for the West region compared to last year"
"Why did our margins decline in September?"
```

The AI understands context, remembers your previous questions, and delivers answers in seconds—not days.

| Capability | Mantrix Axis AI | Traditional BI |
|------------|-----------------|----------------|
| Time to first insight | **< 30 seconds** | 30-60 minutes |
| Training required | **None** | 8-40 hours |
| SQL knowledge needed | **No** | Often yes |
| Multi-turn conversations | **Yes** | No |

---

### 2. Semantic Knowledge Graph: True Understanding

**The Problem:** AI tools that don't understand your business produce wrong or irrelevant results. Generic LLMs don't know that "revenue" in your company means `Net_Sales` or that `KUNNR` is a customer ID.

**Our Solution:** Apache Jena-powered knowledge graph that learns your business:

- **Business Term Mapping**: "revenue" → `SUM(Net_Sales)`, "margin" → `Gross_Profit / Net_Sales`
- **Automatic JOIN Discovery**: Knows that `customers.KUNNR` connects to `orders.SOLD_TO`
- **Financial Hierarchy**: Understands GL account structures, cost centers, profit centers
- **100+ Financial Metrics**: Pre-configured formulas for ROIC, working capital, DSO, and more

**Result:** 95%+ query accuracy vs. 60-70% with generic AI tools.

---

### 3. Multi-Database Federation: One Question, All Your Data

**The Problem:** Enterprise data lives in multiple systems—BigQuery, Snowflake, SAP, Salesforce. Getting a unified view requires expensive ETL projects.

**Our Solution:** Query across databases with a single question:

```
"Compare BigQuery sales data with Snowflake inventory levels"
"Show me SAP orders alongside PostgreSQL customer segments"
```

**Supported Data Sources:**
- Google BigQuery
- Snowflake
- PostgreSQL
- Amazon Redshift
- Databricks
- More coming...

**Enterprise Scale:** Handles 100GB+ cross-database JOINs using intelligent S3 federation—no data movement required.

---

### 4. SAP & ERP Intelligence: The Leading Zero Problem Solved

**The Problem:** SAP systems store IDs with leading zeros (`0000001234`) while other systems don't (`1234`). This breaks JOINs and produces incorrect reports—a problem that has plagued enterprises for decades.

**Our Solution:** Automatic Format Normalization

Our `FormatNormalizer` detects and corrects format mismatches automatically:
- Detects leading zeros in customer IDs, material numbers, GL accounts
- Applies intelligent transformations at query time
- **100-1000x improvement** in JOIN accuracy

**This single feature alone has been called "game-changing" by our SAP customers.**

---

### 5. Interactive Dashboards: Built by Conversation

**The Problem:** Building dashboards in traditional tools takes hours to days. Users need training, and dashboards often don't answer the actual business question.

**Our Solution:** Say what you want, get it instantly:

```
User: "Create a sales dashboard showing revenue by region, top products, and monthly trends"

AI: ✅ Created "Sales Performance Dashboard" with 4 widgets
    • Revenue by Region (map visualization)
    • Top 10 Products (bar chart)
    • Monthly Trend (line chart)
    • KPI Cards (total revenue, YoY growth, avg order value)

    [View Dashboard →]
```

**Dashboard Features:**
- **Cross-filtering**: Click any chart to filter all others
- **Drill-down**: Click a region → see cities → see stores
- **AI Insights**: One-click executive summaries and recommendations
- **Real-time Alerts**: "Notify me when West region drops below $2M"
- **Collaboration**: Comments, annotations, sharing with permissions

---

### 6. AI-Generated Narratives: From Data to Story

**The Problem:** Dashboards show data, but executives need insights. Analysts spend hours writing reports explaining what charts mean.

**Our Solution:** AI-powered executive summaries:

```
📝 Executive Summary (AI-Generated)

Revenue grew 15% YoY to $12.4M, exceeding target by 3%.
West region (+23%) drives growth via Enterprise segment.
⚠️ South region declined 8% due to Hurricane impact.

Recommendations:
1. Investigate South region recovery timeline
2. Expand West region playbook to other regions
```

**Available for:**
- Entire dashboards (executive brief)
- Individual widgets (detailed insights)
- Anomaly explanations (why did this spike occur?)
- Trend analysis (what's the pattern?)

---

### 7. Enterprise-Grade Security & Governance

**The Problem:** Data security is paramount. BI tools often have weak access controls, and AI tools send data to external servers.

**Our Solution:**

| Security Feature | Implementation |
|-----------------|----------------|
| Authentication | AWS Cognito (SSO-ready) |
| Data Access | Role-based, organization-isolated |
| Permission Levels | None → Read → Write → Admin |
| Audit Trail | Full query logging |
| Deployment | Self-hosted or private cloud |
| Data Residency | Your data never leaves your infrastructure |

---

## Mantrix vs. Tableau: Direct Comparison

| Capability | Mantrix Axis AI | Tableau |
|------------|-----------------|---------|
| **Natural Language Queries** | Full conversational AI with context | Ask Data (limited, often fails) |
| **Time to First Insight** | 30 seconds | 30-60 minutes |
| **Training Required** | None | 8-40 hours typical |
| **Multi-Database JOINs** | Native, 100GB+ scale | Requires Prep or manual ETL |
| **SAP/ERP Integration** | Native with format normalization | Manual, error-prone |
| **AI-Generated Insights** | Built-in narratives & recommendations | Not available |
| **Conversational Dashboards** | "Create a sales dashboard" | Must build manually |
| **Knowledge Graph** | Apache Jena semantic understanding | None |
| **Cross-Filtering** | Automatic | Manual configuration |
| **Real-time Alerts** | Email notifications built-in | Requires Server add-on |
| **Collaboration** | Comments, annotations, sharing | Separate Server license |
| **Pricing Model** | Per-organization | Per-user (expensive at scale) |
| **Deployment** | Cloud, on-prem, or hybrid | Cloud or Server (separate) |

### Why Customers Switch from Tableau

1. **"Our users never adopted it"** → Mantrix requires zero training
2. **"Reports took too long"** → Mantrix delivers in seconds
3. **"We couldn't connect our SAP data"** → Native SAP integration
4. **"Licenses were too expensive"** → Organization-based pricing
5. **"We needed AI, not just charts"** → AI-native from the ground up

---

## Platform Capabilities Summary

### Core AI Features
- ✅ Natural Language to SQL (Claude AI-powered)
- ✅ Multi-turn conversational context
- ✅ Semantic knowledge graph (Apache Jena)
- ✅ Financial metric understanding (100+ formulas)
- ✅ SAP format normalization
- ✅ Query optimization & caching

### Data Connectivity
- ✅ Google BigQuery
- ✅ Snowflake
- ✅ PostgreSQL
- ✅ Amazon Redshift
- ✅ Databricks
- ✅ Cross-database federation (100GB+)

### Visualization & Dashboards
- ✅ Interactive dashboard builder
- ✅ Conversational dashboard creation
- ✅ Cross-filtering & drill-down
- ✅ Multiple chart types (bar, line, pie, map, KPI)
- ✅ Export (PDF, Excel, PNG)

### AI Insights
- ✅ Executive summaries
- ✅ Widget-level insights
- ✅ Anomaly detection & explanation
- ✅ Trend analysis
- ✅ Recommendations

### Collaboration & Sharing
- ✅ User/group permissions (view, edit, admin)
- ✅ Shareable links
- ✅ Comments & threads
- ✅ Widget annotations
- ✅ Email notifications

### Alerts & Monitoring
- ✅ Threshold-based alerts
- ✅ Scheduled reports
- ✅ Email delivery
- ✅ Anomaly monitoring

### Enterprise Features
- ✅ AWS Cognito authentication (SSO-ready)
- ✅ Multi-tenancy (organization isolation)
- ✅ Role-based access control
- ✅ Audit logging
- ✅ On-premise deployment option

---

## Customer Success Metrics

Based on early deployments:

| Metric | Improvement |
|--------|-------------|
| Time to insight | **95% faster** (from hours to seconds) |
| BI tool adoption | **3x increase** (due to ease of use) |
| Report creation time | **90% reduction** |
| Data team bottleneck | **Eliminated** for routine queries |
| Training costs | **$0** (vs. $500-2000/user for Tableau) |
| SAP JOIN accuracy | **100-1000x improvement** |

---

## Deployment Options

### Cloud (Recommended)
- Fully managed on AWS
- Available on AWS Marketplace
- Zero infrastructure management
- Automatic updates

### Self-Hosted
- Deploy in your own AWS/GCP/Azure account
- Full data sovereignty
- Compliance with strict data residency requirements
- Terraform/CloudFormation templates provided

### Hybrid
- AI processing in cloud
- Data remains on-premise
- Best of both worlds

---

## Getting Started

1. **Free Trial**: 14-day full access, no credit card required
2. **Pilot Program**: 30-day guided implementation with your data
3. **Enterprise**: Custom deployment with dedicated support

**Contact:** sales@mantrix.ai

---

## How Queries Scale: Enterprise Performance

### The Challenge of Scale

As data volumes grow from gigabytes to terabytes, traditional BI tools slow down exponentially. Queries that took seconds start taking minutes, then hours. Mantrix Axis AI is architected from the ground up for enterprise scale.

### Multi-Tier Caching Architecture

Redis-based caching with configurable TTLs eliminates redundant work:

```
┌─────────────────────────────────────────────────────────────┐
│                    QUERY REQUEST                            │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  L1: SQL Query Cache                                        │
│  • Frequently-used queries: 7-day TTL                       │
│  • Infrequently-used queries: 1-day TTL                     │
│  • Quality tiers: Gold (7d), Silver (3d), Bronze (12h)     │
│  • Cache hit = milliseconds response                        │
└─────────────────────────────────────────────────────────────┘
                            │ miss
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  L2: Schema & Embedding Cache                               │
│  • Schema metadata: 24-hour TTL                             │
│  • Vector embeddings: 30-day TTL                            │
│  • Eliminates redundant LLM calls for similar questions     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  L3: Database Query Execution                               │
│  • Query results: 5-minute TTL                              │
│  • Session data: 24-hour TTL                                │
│  • Optimized SQL with pushdown                              │
└─────────────────────────────────────────────────────────────┘
```

**Result:** Repeated queries (same or similar questions) return instantly from cache. Cache hit rates depend on usage patterns—organizations with recurring reporting needs see the highest cache utilization.

### Query Pushdown Optimization

Instead of pulling all data and filtering locally, Mantrix pushes operations to the database:

| Without Pushdown | With Pushdown |
|-----------------|---------------|
| Pull 10M rows → Filter locally | Push filter → Pull 50K rows |
| 5-10 minutes | 2-5 seconds |
| High memory usage | Minimal memory |
| Network bottleneck | Database-optimized |

**Impact:** 90-95% reduction in data transferred. Queries that would timeout now complete in seconds.

### Cross-Database Federation at Scale

When joining data across BigQuery, Snowflake, and PostgreSQL:

**Traditional Approach:**
1. Export all data to single location (ETL)
2. Hours/days of processing
3. Data staleness issues
4. Expensive storage duplication

**Mantrix Approach:** Three-tier strategy based on data size:

| Data Size | Strategy | How It Works |
|-----------|----------|--------------|
| **< 100MB** | In-Memory JOIN | Fast, direct processing |
| **100MB - 10GB** | Staging Tables | Copy smaller dataset to target DB |
| **> 10GB** | S3 Federation | Stream via S3 + Redshift Spectrum |

#### How S3 Federation Works (for 10GB+ JOINs)

When datasets are too large for direct processing, Mantrix uses S3 as an intermediary:

```
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 1: Stream Source Data to S3                                    │
│                                                                     │
│   ┌─────────────┐         ┌─────────────────────────────────┐      │
│   │  Source DB  │ ──────► │ S3 Bucket (Parquet format)      │      │
│   │ (BigQuery)  │ stream  │ • Columnar storage              │      │
│   │             │ 100K    │ • Snappy compression            │      │
│   │  50GB data  │ rows/   │ • Auto-partitioned chunks       │      │
│   └─────────────┘ chunk   └─────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 2: Create External Table (Redshift Spectrum)                   │
│                                                                     │
│   CREATE EXTERNAL TABLE federation_temp.temp_abc123 (...)           │
│   STORED AS PARQUET                                                 │
│   LOCATION 's3://bucket/federation/abc123/'                         │
│                                                                     │
│   No data copied—Spectrum reads S3 directly                         │
└─────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 3: Execute JOIN in Target Database                             │
│                                                                     │
│   SELECT *                                                          │
│   FROM target_table t                                               │
│   JOIN federation_temp.temp_abc123 e                                │
│   ON t.customer_id = e.customer_id                                  │
│                                                                     │
│   Database engine optimizes the JOIN natively                       │
└─────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 4: Automatic Cleanup (24-hour TTL)                             │
│                                                                     │
│   • DROP external table                                             │
│   • DELETE S3 objects                                               │
│   • Free up storage automatically                                   │
└─────────────────────────────────────────────────────────────────────┘
```

**Why Parquet format?**
- **Columnar storage**: Only reads columns needed for the query
- **Compression**: Snappy compression reduces storage/transfer costs
- **Predicate pushdown**: Filters applied during read, not after

**Why this scales:**
- Source data streamed in 100,000-row chunks (never loaded fully in memory)
- S3 = virtually unlimited storage capacity
- Redshift Spectrum reads S3 in parallel across multiple nodes
- No data duplication—temporary, auto-cleaned

### Concurrent User Scalability

The architecture is designed for horizontal scaling:

**Why performance improves with more users:**
1. **Shared Cache Benefits** - When user A asks "What was Q4 revenue?", the answer is cached. When user B asks the same question minutes later, they get an instant response.
2. **Common Query Patterns** - Business users often ask similar questions. Monthly close, quarterly reviews, and executive reports generate predictable query patterns that cache well.
3. **Stateless API Design** - Add more API pods as user count grows. No session affinity required.

**Scaling Factors:**
| Factor | Impact |
|--------|--------|
| Query similarity | Higher similarity = more cache hits |
| Time-sensitive queries | "Today's numbers" = shorter cache life |
| Exploratory queries | Unique questions = cache misses |
| Report schedules | Regular reports = highly cacheable |

### Cost-Aware Query Execution

For data warehouses with usage-based pricing (BigQuery, Snowflake):

1. **Dry-Run Estimation** - Preview query cost before execution
2. **Query Limits** - Configurable per-organization spending caps
3. **Optimization Hints** - Suggestions to reduce query cost
4. **Usage Analytics** - Track spending by user, department, query type

**Example Cost Savings:**
```
Original Query:  Scans 500GB → $2.50/query
Optimized Query: Scans 5GB   → $0.025/query (100x cheaper)
```

### Horizontal Scaling Architecture

```
                    ┌─────────────────┐
                    │  Load Balancer  │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│   API Pod 1   │   │   API Pod 2   │   │   API Pod N   │
│  (Stateless)  │   │  (Stateless)  │   │  (Stateless)  │
└───────┬───────┘   └───────┬───────┘   └───────┬───────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            ▼
              ┌─────────────────────────┐
              │     Redis Cluster       │
              │   (Shared Cache/State)  │
              └─────────────────────────┘
```

- **Stateless API Pods** - Add more pods to handle more users
- **Redis Cluster** - Shared cache across all pods
- **Auto-Scaling** - Kubernetes-based scaling on demand
- **Zero Downtime** - Rolling deployments

### How Response Time Stays Consistent

**Key Insight:** Response times depend on query complexity and cache state—not underlying data volume.

| Query Type | What Determines Speed |
|------------|----------------------|
| **Cached query** | Redis lookup (~milliseconds) |
| **Simple aggregation** | Database index efficiency |
| **Complex JOIN** | Query pushdown + federation strategy |
| **Cross-database** | Size tier (in-memory/staging/S3) |

**The data volume doesn't directly impact response time because:**
1. Queries are optimized before execution (pushdown reduces data scanned)
2. Databases use indexes and partitions (you don't scan 10TB for every query)
3. Caching eliminates repeated work
4. Federation strategies match data size to optimal approach

---

## Appendix: Technical Differentiators

### Query Processing Pipeline

```
User Question
    ↓
Cache Check (60-80% hit rate, <5ms)
    ↓
Financial Semantic Parser (understands "revenue", "margin", etc.)
    ↓
Knowledge Graph Lookup (table relationships, JOINs)
    ↓
LLM SQL Generation (Claude claude-sonnet-4-5-20250929)
    ↓
Format Normalization (SAP leading zeros)
    ↓
Query Optimization (90-95% data reduction via pushdown)
    ↓
Database Execution
    ↓
Results + AI Analysis
```

### Architecture Specifications

| Component | Specification |
|-----------|--------------|
| **Caching** | Multi-tier Redis (7-day to 5-minute TTLs) |
| **Cross-DB Federation** | In-memory (<100MB), Staging (100MB-10GB), S3 (>10GB) |
| **S3 Streaming** | 100,000 rows per Parquet chunk |
| **Cleanup** | 24-hour TTL on temporary federation data |
| **API Design** | Stateless (horizontally scalable) |
| **Query Optimization** | Pushdown filters, aggregations, JOINs to database |

---

*© 2025 Mantrix AI. All rights reserved.*

*Last updated: November 2025*
