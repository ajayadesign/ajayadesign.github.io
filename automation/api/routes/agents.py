"""
Agent Heartbeat Routes — Paperclip Integration.

Provides HTTP endpoints that Paperclip calls on scheduled heartbeats.
Each endpoint wraps existing AjayaDesign services (crawl, intel, template).

Routes:
  POST /api/v1/agents/scout/heartbeat       — Business discovery
  POST /api/v1/agents/audit/heartbeat       — Website analysis
  POST /api/v1/agents/copywriter/heartbeat  — Email generation
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("agents")
router = APIRouter(prefix="/agents", tags=["agents"])


# ─── Request/Response Models ──────────────────────────────────────────

class HeartbeatRequest(BaseModel):
    """Standard Paperclip heartbeat payload."""
    agent_id: str = Field(..., description="Unique agent identifier")
    company_id: str = Field(..., description="Company this agent belongs to")
    goal: str = Field(..., description="Agent's current goal/mission")
    budget_remaining: float = Field(..., description="USD remaining in monthly budget")
    context: Dict[str, Any] = Field(default_factory=dict, description="Persistent agent context")


class HeartbeatResponse(BaseModel):
    """Standard Paperclip heartbeat response."""
    status: str = Field(..., description="success | paused | error")
    message: str = Field(..., description="Human-readable summary")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Execution metrics")
    next_heartbeat_in_seconds: int = Field(
        default=3600,
        description="When Paperclip should call again (0 = ASAP)",
    )
    output: str = Field(default="", description="Detailed execution log")
    cost_incurred: float = Field(default=0.0, description="USD spent this heartbeat")
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Updated context to persist for next heartbeat",
    )


# ─── Scout Agent (Business Discovery) ────────────────────────────────

@router.post("/scout/heartbeat", response_model=HeartbeatResponse)
async def scout_heartbeat(request: HeartbeatRequest) -> HeartbeatResponse:
    """
    Scout Agent — Discovers local businesses via Google Maps API.

    Context:
      - geo_ring: str (manor, pflugerville, round_rock, austin, etc.)
      - limit: int (max businesses to discover per cycle)

    Returns:
      - businesses_discovered: int
      - api_calls_made: int
      - cost_incurred: float
    """
    from api.agents.scout_agent import execute_scout_cycle

    logger.info(f"[{request.agent_id}] Scout heartbeat — goal: {request.goal}")

    # Budget check
    if request.budget_remaining < 1.0:
        logger.warning(f"[{request.agent_id}] Budget depleted: ${request.budget_remaining:.2f}")
        return HeartbeatResponse(
            status="paused",
            message=f"Budget depleted (${request.budget_remaining:.2f} remaining)",
            next_heartbeat_in_seconds=86400,  # Check again tomorrow
        )

    try:
        result = await execute_scout_cycle(
            geo_ring=request.context.get("geo_ring", "manor"),
            limit=request.context.get("limit", 30),
        )

        return HeartbeatResponse(
            status="success",
            message=f"Discovered {result['count']} businesses in {result['geo_ring']}",
            metrics={
                "businesses_discovered": result["count"],
                "api_calls_made": result["api_calls"],
                "duplicates_skipped": result.get("duplicates", 0),
            },
            next_heartbeat_in_seconds=21600,  # 6 hours
            output=result.get("log", ""),
            cost_incurred=result.get("cost", 0.0),
            context=request.context,  # Persist geo_ring for next cycle
        )

    except Exception as e:
        logger.error(f"[{request.agent_id}] Scout error: {e}", exc_info=True)
        return HeartbeatResponse(
            status="error",
            message=f"Scout execution failed: {str(e)}",
            next_heartbeat_in_seconds=3600,  # Retry in 1 hour
        )


# ─── Audit Agent (Website Analysis) ───────────────────────────────────

@router.post("/audit/heartbeat", response_model=HeartbeatResponse)
async def audit_heartbeat(request: HeartbeatRequest) -> HeartbeatResponse:
    """
    Audit Agent — Runs Lighthouse audits on discovered prospects.

    Picks up prospects with status='discovered', runs analysis, updates to 'audited'.

    Context:
      - batch_size: int (max audits per cycle, default 10)
      - timeout_seconds: int (per-audit timeout, default 60)

    Returns:
      - audits_completed: int
      - audits_failed: int
    """
    from api.agents.audit_agent import execute_audit_cycle

    logger.info(f"[{request.agent_id}] Audit heartbeat — goal: {request.goal}")

    # Budget check (Lighthouse is free, but check anyway)
    if request.budget_remaining < 0.5:
        return HeartbeatResponse(
            status="paused",
            message="Budget low, pausing audits",
            next_heartbeat_in_seconds=86400,
        )

    try:
        result = await execute_audit_cycle(
            batch_size=request.context.get("batch_size", 10),
            timeout_seconds=request.context.get("timeout_seconds", 60),
        )

        return HeartbeatResponse(
            status="success",
            message=f"Completed {result['completed']} audits ({result['failed']} failed)",
            metrics={
                "audits_completed": result["completed"],
                "audits_failed": result["failed"],
                "avg_performance_score": result.get("avg_perf", 0),
            },
            next_heartbeat_in_seconds=1800,  # 30 minutes
            output=result.get("log", ""),
            cost_incurred=0.0,  # Lighthouse is free
            context=request.context,
        )

    except Exception as e:
        logger.error(f"[{request.agent_id}] Audit error: {e}", exc_info=True)
        return HeartbeatResponse(
            status="error",
            message=f"Audit execution failed: {str(e)}",
            next_heartbeat_in_seconds=3600,
        )


# ─── Copywriter Agent (Email Generation) ──────────────────────────────

@router.post("/copywriter/heartbeat", response_model=HeartbeatResponse)
async def copywriter_heartbeat(request: HeartbeatRequest) -> HeartbeatResponse:
    """
    Copywriter Agent — Generates personalized outreach emails.

    Picks up prospects with status='scored' and wp_score >= threshold.
    Uses AI (GPT-4o or Claude) to write unique emails.

    Context:
      - min_wp_score: int (minimum score to qualify, default 60)
      - batch_size: int (max emails per cycle, default 20)
      - ai_provider: str (github-models | anthropic)

    Returns:
      - emails_generated: int
      - avg_confidence_score: float
      - tokens_used: int
    """
    from api.agents.copywriter_agent import execute_copywriter_cycle

    logger.info(f"[{request.agent_id}] Copywriter heartbeat — goal: {request.goal}")

    # Budget check (AI is expensive)
    if request.budget_remaining < 5.0:
        logger.warning(f"[{request.agent_id}] Budget low: ${request.budget_remaining:.2f}")
        return HeartbeatResponse(
            status="paused",
            message="Budget too low for AI generation",
            next_heartbeat_in_seconds=86400,
        )

    try:
        result = await execute_copywriter_cycle(
            min_wp_score=request.context.get("min_wp_score", 60),
            batch_size=request.context.get("batch_size", 20),
            ai_provider=request.context.get("ai_provider", "github-models"),
            budget_limit=request.budget_remaining,
        )

        return HeartbeatResponse(
            status="success",
            message=f"Generated {result['count']} personalized emails",
            metrics={
                "emails_generated": result["count"],
                "avg_confidence_score": result.get("avg_confidence", 0),
                "tokens_used": result.get("tokens", 0),
                "avg_wp_score": result.get("avg_wp_score", 0),
            },
            next_heartbeat_in_seconds=14400,  # 4 hours
            output=result.get("log", ""),
            cost_incurred=result.get("cost", 0.0),
            context=request.context,
        )

    except Exception as e:
        logger.error(f"[{request.agent_id}] Copywriter error: {e}", exc_info=True)
        return HeartbeatResponse(
            status="error",
            message=f"Copywriter execution failed: {str(e)}",
            next_heartbeat_in_seconds=3600,
        )


# ─── Enrichment Agent (Deep Data Collection) ─────────────────────────

@router.post("/enrichment/heartbeat", response_model=HeartbeatResponse)
async def enrichment_heartbeat(request: HeartbeatRequest) -> HeartbeatResponse:
    """
    Enrichment Agent — Collects deep business intelligence.

    Context:
      - batch_size: int (max prospects to enrich per cycle)
      - timeout_seconds: int (per-prospect timeout)

    Returns:
      - enriched: int
      - failed: int
      - avg_data_points: int
      - cost: float
    """
    from api.agents.enrichment_agent import execute_enrichment_cycle

    logger.info(f"[{request.agent_id}] Enrichment heartbeat — goal: {request.goal}")

    if request.budget_remaining < 2.0:
        return HeartbeatResponse(
            status="paused",
            message="Budget low for enrichment APIs",
            next_heartbeat_in_seconds=86400,
        )

    try:
        result = await execute_enrichment_cycle(
            batch_size=request.context.get("batch_size", 20),
            timeout_seconds=request.context.get("timeout_seconds", 120),
        )

        return HeartbeatResponse(
            status="success",
            message=f"Enriched {result['enriched']} prospects ({result['failed']} failed)",
            metrics={
                "enriched": result["enriched"],
                "failed": result["failed"],
                "avg_data_points": result.get("avg_data_points", 0),
            },
            next_heartbeat_in_seconds=3600,  # 1 hour
            output=result.get("log", ""),
            cost_incurred=result.get("cost", 0.0),
            context=request.context,
        )

    except Exception as e:
        logger.error(f"[{request.agent_id}] Enrichment error: {e}", exc_info=True)
        return HeartbeatResponse(
            status="error",
            message=f"Enrichment execution failed: {str(e)}",
            next_heartbeat_in_seconds=3600,
        )


# ─── Scoring Agent (WP Score Calculation) ────────────────────────────

@router.post("/scoring/heartbeat", response_model=HeartbeatResponse)
async def scoring_heartbeat(request: HeartbeatRequest) -> HeartbeatResponse:
    """
    Scoring Agent — Calculates Website Purchase Likelihood Score.

    Context:
      - batch_size: int (max prospects to score per cycle)

    Returns:
      - scored: int
      - avg_score: float
      - tier_breakdown: dict
    """
    from api.agents.scoring_agent import execute_scoring_cycle

    logger.info(f"[{request.agent_id}] Scoring heartbeat — goal: {request.goal}")

    try:
        result = await execute_scoring_cycle(
            batch_size=request.context.get("batch_size", 50),
        )

        return HeartbeatResponse(
            status="success",
            message=f"Scored {result['scored']} prospects (avg: {result['avg_score']:.1f})",
            metrics={
                "scored": result["scored"],
                "avg_score": result.get("avg_score", 0),
                "tier_breakdown": result.get("tier_breakdown", {}),
            },
            next_heartbeat_in_seconds=1800,  # 30 minutes
            output=result.get("log", ""),
            cost_incurred=0.0,  # Scoring is computational, no API costs
            context=request.context,
        )

    except Exception as e:
        logger.error(f"[{request.agent_id}] Scoring error: {e}", exc_info=True)
        return HeartbeatResponse(
            status="error",
            message=f"Scoring execution failed: {str(e)}",
            next_heartbeat_in_seconds=3600,
        )


# ─── Email QA Agent (Quality Review) ─────────────────────────────────

@router.post("/email-qa/heartbeat", response_model=HeartbeatResponse)
async def email_qa_heartbeat(request: HeartbeatRequest) -> HeartbeatResponse:
    """
    Email QA Agent — Reviews generated emails for quality.

    Context:
      - batch_size: int (max emails to review per cycle)
      - auto_approve_threshold: float (0.90 = 90% confidence)
      - ai_provider: str (github-models | anthropic)

    Returns:
      - reviewed: int
      - auto_approved: int
      - flagged: int
      - avg_confidence: float
    """
    from api.agents.email_qa_agent import execute_email_qa_cycle

    logger.info(f"[{request.agent_id}] EmailQA heartbeat — goal: {request.goal}")

    if request.budget_remaining < 3.0:
        return HeartbeatResponse(
            status="paused",
            message="Budget low for AI review",
            next_heartbeat_in_seconds=86400,
        )

    try:
        result = await execute_email_qa_cycle(
            batch_size=request.context.get("batch_size", 30),
            auto_approve_threshold=request.context.get("auto_approve_threshold", 0.90),
            ai_provider=request.context.get("ai_provider", "github-models"),
        )

        return HeartbeatResponse(
            status="success",
            message=f"Reviewed {result['reviewed']} emails ({result['auto_approved']} approved, {result['flagged']} flagged)",
            metrics={
                "reviewed": result["reviewed"],
                "auto_approved": result["auto_approved"],
                "flagged": result["flagged"],
                "avg_confidence": result.get("avg_confidence", 0),
            },
            next_heartbeat_in_seconds=1800,  # 30 minutes
            output=result.get("log", ""),
            cost_incurred=result.get("cost", 0.0),
            context=request.context,
        )

    except Exception as e:
        logger.error(f"[{request.agent_id}] EmailQA error: {e}", exc_info=True)
        return HeartbeatResponse(
            status="error",
            message=f"EmailQA execution failed: {str(e)}",
            next_heartbeat_in_seconds=3600,
        )


# ─── Pipeline Monitor Agent (Health Check & Recovery) ────────────────

@router.post("/pipeline-monitor/heartbeat", response_model=HeartbeatResponse)
async def pipeline_monitor_heartbeat(request: HeartbeatRequest) -> HeartbeatResponse:
    """
    Pipeline Monitor Agent — Detects and recovers stuck prospects.

    No context needed (fully autonomous).

    Returns:
      - stuck_found: int
      - recovered: int
      - marked_manual: int
      - bottlenecks: dict
    """
    from api.agents.pipeline_monitor_agent import execute_monitor_cycle

    logger.info(f"[{request.agent_id}] PipelineMonitor heartbeat — goal: {request.goal}")

    try:
        result = await execute_monitor_cycle()

        return HeartbeatResponse(
            status="success",
            message=f"Recovered {result['recovered']} stuck prospects ({result['stuck_found']} found)",
            metrics={
                "stuck_found": result["stuck_found"],
                "recovered": result["recovered"],
                "marked_manual": result["marked_manual"],
                "bottlenecks": result.get("bottlenecks", {}),
            },
            next_heartbeat_in_seconds=1800,  # 30 minutes
            output=result.get("log", ""),
            cost_incurred=0.0,  # Monitoring is computational, no API costs
            context=request.context,
        )

    except Exception as e:
        logger.error(f"[{request.agent_id}] PipelineMonitor error: {e}", exc_info=True)
        return HeartbeatResponse(
            status="error",
            message=f"PipelineMonitor execution failed: {str(e)}",
            next_heartbeat_in_seconds=3600,
        )


# ─── Sales Qualification Agent (Auto-Book Meetings) ──────────────────

@router.post("/sales-qualification/heartbeat", response_model=HeartbeatResponse)
async def sales_qualification_heartbeat(request: HeartbeatRequest) -> HeartbeatResponse:
    """
    Sales Qualification Agent — Analyzes replies, books meetings.

    Context:
      - batch_size: int
      - ai_provider: str
      - calendly_link: str

    Returns:
      - processed: int
      - meetings_booked: int
      - questions_answered: int
    """
    from api.agents.sales_qualification_agent import execute_sales_qualification_cycle

    logger.info(f"[{request.agent_id}] SalesQual heartbeat — goal: {request.goal}")

    if request.budget_remaining < 5.0:
        return HeartbeatResponse(
            status="paused",
            message="Budget low for AI qualification",
            next_heartbeat_in_seconds=86400,
        )

    try:
        result = await execute_sales_qualification_cycle(
            batch_size=request.context.get("batch_size", 20),
            ai_provider=request.context.get("ai_provider", "github-models"),
            calendly_link=request.context.get("calendly_link", "https://calendly.com/ajayadesign/30min"),
        )

        return HeartbeatResponse(
            status="success",
            message=f"Processed {result['processed']} replies, booked {result['meetings_booked']} meetings",
            metrics={
                "processed": result["processed"],
                "meetings_booked": result["meetings_booked"],
                "questions_answered": result["questions_answered"],
                "nurtured": result.get("nurtured", 0),
            },
            next_heartbeat_in_seconds=3600,  # 1 hour
            output=result.get("log", ""),
            cost_incurred=result.get("cost", 0.0),
            context=request.context,
        )

    except Exception as e:
        logger.error(f"[{request.agent_id}] SalesQual error: {e}", exc_info=True)
        return HeartbeatResponse(
            status="error",
            message=f"SalesQual execution failed: {str(e)}",
            next_heartbeat_in_seconds=3600,
        )


# ─── Proposal Generator Agent (Auto-Create Quotes) ───────────────────

@router.post("/proposal-generator/heartbeat", response_model=HeartbeatResponse)
async def proposal_generator_heartbeat(request: HeartbeatRequest) -> HeartbeatResponse:
    """
    Proposal Generator Agent — Creates quotes for qualified leads.

    Context:
      - batch_size: int
      - ai_provider: str

    Returns:
      - generated: int
      - avg_quote_value: float
    """
    from api.agents.proposal_generator_agent import execute_proposal_generator_cycle

    logger.info(f"[{request.agent_id}] ProposalGen heartbeat — goal: {request.goal}")

    if request.budget_remaining < 5.0:
        return HeartbeatResponse(
            status="paused",
            message="Budget low for AI proposal generation",
            next_heartbeat_in_seconds=86400,
        )

    try:
        result = await execute_proposal_generator_cycle(
            batch_size=request.context.get("batch_size", 5),
            ai_provider=request.context.get("ai_provider", "github-models"),
        )

        return HeartbeatResponse(
            status="success",
            message=f"Generated {result['generated']} proposals (avg value: ${result['avg_quote_value']:,.0f})",
            metrics={
                "generated": result["generated"],
                "avg_quote_value": result.get("avg_quote_value", 0),
            },
            next_heartbeat_in_seconds=7200,  # 2 hours
            output=result.get("log", ""),
            cost_incurred=result.get("cost", 0.0),
            context=request.context,
        )

    except Exception as e:
        logger.error(f"[{request.agent_id}] ProposalGen error: {e}", exc_info=True)
        return HeartbeatResponse(
            status="error",
            message=f"ProposalGen execution failed: {str(e)}",
            next_heartbeat_in_seconds=3600,
        )


# ─── Contract Agent (Auto-Send Contracts) ─────────────────────────────

@router.post("/contract/heartbeat", response_model=HeartbeatResponse)
async def contract_heartbeat(request: HeartbeatRequest) -> HeartbeatResponse:
    """
    Contract Agent — Sends contracts, tracks signatures, closes deals.

    Context:
      - batch_size: int
      - use_docusign: bool

    Returns:
      - contracts_sent: int
      - deals_closed: int
      - total_deal_value: float
    """
    from api.agents.contract_agent import execute_contract_cycle

    logger.info(f"[{request.agent_id}] Contract heartbeat — goal: {request.goal}")

    try:
        result = await execute_contract_cycle(
            batch_size=request.context.get("batch_size", 10),
            use_docusign=request.context.get("use_docusign", False),
        )

        return HeartbeatResponse(
            status="success",
            message=f"Sent {result['contracts_sent']} contracts, closed {result['deals_closed']} deals (${result['total_deal_value']:,.0f})",
            metrics={
                "contracts_sent": result["contracts_sent"],
                "contracts_signed": result.get("contracts_signed", 0),
                "deals_closed": result["deals_closed"],
                "total_deal_value": result["total_deal_value"],
            },
            next_heartbeat_in_seconds=3600,  # 1 hour
            output=result.get("log", ""),
            cost_incurred=0.0,
            context=request.context,
        )

    except Exception as e:
        logger.error(f"[{request.agent_id}] Contract error: {e}", exc_info=True)
        return HeartbeatResponse(
            status="error",
            message=f"Contract execution failed: {str(e)}",
            next_heartbeat_in_seconds=3600,
        )


# ─── Onboarding Agent (Auto-Welcome Clients) ──────────────────────────

@router.post("/onboarding/heartbeat", response_model=HeartbeatResponse)
async def onboarding_heartbeat(request: HeartbeatRequest) -> HeartbeatResponse:
    """
    Onboarding Agent — Welcomes new clients, schedules kickoff.

    Context:
      - batch_size: int

    Returns:
      - onboarded: int
      - welcome_emails_sent: int
      - kickoff_meetings_scheduled: int
    """
    from api.agents.onboarding_agent import execute_onboarding_cycle

    logger.info(f"[{request.agent_id}] Onboarding heartbeat — goal: {request.goal}")

    try:
        result = await execute_onboarding_cycle(
            batch_size=request.context.get("batch_size", 10),
        )

        return HeartbeatResponse(
            status="success",
            message=f"Onboarded {result['onboarded']} new clients",
            metrics={
                "onboarded": result["onboarded"],
                "welcome_emails_sent": result["welcome_emails_sent"],
                "kickoff_meetings_scheduled": result["kickoff_meetings_scheduled"],
            },
            next_heartbeat_in_seconds=7200,  # 2 hours
            output=result.get("log", ""),
            cost_incurred=0.0,
            context=request.context,
        )

    except Exception as e:
        logger.error(f"[{request.agent_id}] Onboarding error: {e}", exc_info=True)
        return HeartbeatResponse(
            status="error",
            message=f"Onboarding execution failed: {str(e)}",
            next_heartbeat_in_seconds=3600,
        )


# ─── Health Check ──────────────────────────────────────────────────────

@router.get("/health")
async def agents_health():
    """Health check for agent endpoints."""
    return {
        "status": "healthy",
        "agents": [
            # Phase 1
            "scout",
            "audit",
            "copywriter",
            # Phase 2
            "enrichment",
            "scoring",
            "email-qa",
            "pipeline-monitor",
            # Phase 3
            "sales-qualification",
            "proposal-generator",
            "contract",
            "onboarding",
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
