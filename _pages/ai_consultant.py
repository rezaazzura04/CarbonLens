"""
CarbonLens V7 — AI Sustainability Consultant
Real Anthropic API integration (claude-sonnet-4-6).
Passes full E+S+G context as system prompt — generates dynamic,
personalized recommendations that go beyond rule-based templates.
Falls back to rule-based analysis if API key not set.
"""

from __future__ import annotations
import streamlit as st
import pandas as pd
import numpy as np
import utils.state as S
from components.ui import page_header, kpi_card, insight_panel, divider
from utils.calculations import (
    dataset_overview, calculate_esg_score, predict_next_emission,
    annual_projection, get_benchmark, benchmark_gap, overshoot_risk,
    generate_demo_data,
)
from config.settings import COLORS


# ── Build rich ESG context string for Anthropic ──────────────────────────────

def _build_context(df, ov, esg, intensity, bench, gap, scope_results,
                   company, sector, area_m2, renew_pct, annual_em, pred) -> str:
    """Serialize full E+S+G state into a structured context string for the LLM."""
    bd = esg.get("breakdown", {})
    dp = esg.get("data_provided", {})
    s  = scope_results

    disclosed = [k for k,v in dp.items() if v]
    using_defaults = [k for k,v in dp.items() if not v]

    ctx = f"""
=== CARBONLENS ESG INTELLIGENCE CONTEXT ===

ORGANIZATION
  Company: {company}
  Sector: {sector}
  Building area: {area_m2:,.0f} m²
  Renewable energy: {renew_pct}%
  Dataset: {ov.get('count',12)} months · {ov.get('completeness',0):.0f}% data quality

EMISSIONS PERFORMANCE (GRI 305)
  Total emissions: {ov.get('total',0):,.0f} tCO₂e/year
  Monthly average: {ov.get('average',0):,.0f} tCO₂e
  Peak month: {ov.get('peak_month','?')} ({ov.get('peak',0):,.0f} tCO₂e)
  Carbon intensity: {intensity:.1f} kg CO₂e/m²
  Sector benchmark: {bench:.1f} kg CO₂e/m²
  Gap vs benchmark: {gap.get('above_benchmark_pct',0):+.1f}% ({'above' if gap.get('above_benchmark') else 'below'} benchmark)
  12-month forecast: {pred.get('forecast',0):,.0f} tCO₂e
  Annual projection: {annual_em:,.0f} tCO₂e

GHG SCOPE BREAKDOWN
  Scope 1 (direct): {s.get('scope1_kg',0)/1000:,.1f} tCO₂e ({s.get('scope1_pct',0):.0f}%)
  Scope 2 (electricity): {s.get('scope2_kg',0)/1000:,.1f} tCO₂e ({s.get('scope2_pct',0):.0f}%)
  Scope 3 (value chain): {s.get('scope3_kg',0)/1000:,.1f} tCO₂e ({s.get('scope3_pct',0):.0f}%)

ESG SCORE BREAKDOWN (GRI 2021 / SASB)
  Overall: {esg.get('score',0)}/100 — Grade {esg.get('grade','?')} ({esg.get('label','?')})
  Environmental (40%): {esg.get('env',0):.1f}/100
    Carbon Intensity (GRI 305): {bd.get('environmental',{}).get('Carbon Intensity (GRI 305)',0):.1f}
    Renewable Energy (GRI 302): {bd.get('environmental',{}).get('Renewable Energy (GRI 302)',0):.1f}
    Waste Recycling (GRI 306): {bd.get('environmental',{}).get('Waste Recycling (GRI 306)',0):.1f}
    Water Recycled (GRI 303): {bd.get('environmental',{}).get('Water Recycled (GRI 303)',0):.1f}
  Social (30%): {esg.get('social',0):.1f}/100
    Employee Retention (GRI 401-1): {bd.get('social',{}).get('Employee Retention (GRI 401-1)',0):.1f}
    Training Hours (GRI 404-1): {bd.get('social',{}).get('Training Hours (GRI 404-1)',0):.1f}
    Gender Diversity (GRI 405-1): {bd.get('social',{}).get('Gender Diversity (GRI 405-1)',0):.1f}
    Workplace Safety (GRI 403-9): {bd.get('social',{}).get('Workplace Safety (GRI 403-9)',0):.1f}
  Governance (30%): {esg.get('gov',0):.1f}/100
    Board Independence (GRI 2-9): {bd.get('governance',{}).get('Board Independence (GRI 2-9/10)',0):.1f}
    Board Diversity (GRI 405-1): {bd.get('governance',{}).get('Board Diversity (GRI 405-1)',0):.1f}
    Ethics & Anti-Corruption (GRI 205): {bd.get('governance',{}).get('Ethics & Anti-Corruption (GRI 2-23/205)',0):.1f}
    Disclosure Quality (GRI 2-3): {bd.get('governance',{}).get('Disclosure Quality (GRI 2-3)',0):.1f}

DATA DISCLOSURE STATUS
  Indicators with real data: {', '.join(disclosed) if disclosed else 'None yet'}
  Using defaults (needs disclosure): {', '.join(using_defaults) if using_defaults else 'All provided'}

ENVIRONMENTAL INDICATORS FROM DATASET
  Energy: {'Available' if 'Energy' in df.columns else 'Not in dataset'}
  Water withdrawal: {'Available' if 'Water_Withdrawal' in df.columns else 'Not in dataset'}
  Waste generated: {'Available' if 'Waste_Generated' in df.columns else 'Not in dataset'}
  Renewable %: {'Available' if 'Renewable_pct' in df.columns else 'Not in dataset'}

=== END CONTEXT ===
"""
    return ctx.strip()


# ── Anthropic API call ────────────────────────────────────────────────────────

def _call_anthropic(api_key: str, system_prompt: str, user_message: str,
                    max_tokens: int = 1200) -> tuple[str, bool]:
    """Call Anthropic API. Returns (response_text, success)."""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return msg.content[0].text, True
    except ImportError:
        return ("anthropic package not installed. Run: pip install anthropic"), False
    except Exception as e:
        return str(e), False


SYSTEM_PROMPT = """You are CarbonLens AI — an expert ESG and sustainability consultant
specializing in Indonesian organizations. You have access to the organization's full
GRI 2021-aligned ESG data including Environmental (E), Social (S), and Governance (G)
performance metrics, GHG scope breakdown, and sector benchmarking data.

Your role:
- Provide specific, actionable, data-driven recommendations
- Reference exact metric values from the context (don't generalize)
- Prioritize recommendations by ROI and emission reduction impact
- Consider Indonesian regulatory context (POJK 51, OJK, SNI, Perpres 98/2021)
- Be direct and concise — executives need clarity, not academic language
- Always reference which GRI disclosure standard each recommendation addresses

Format your response in clear sections. Use specific numbers from the data.
Never give generic advice — everything must be grounded in the actual metrics provided."""


# ── Fallback rule-based analysis ─────────────────────────────────────────────

def _rule_based_analysis(df, ov, esg, intensity, bench, gap, sector) -> dict:
    """Structured rule-based analysis when Anthropic API not configured."""
    bd = esg.get("breakdown", {})
    total = ov.get("total", 0)

    weaknesses, strengths, priorities = [], [], []

    # Environmental
    env_sc = esg.get("env", 0)
    if intensity > bench * 1.2:
        weaknesses.append(f"Carbon intensity {intensity:.1f} kg/m² is {(intensity/bench-1)*100:.0f}% above benchmark ({bench:.1f})")
        priorities.append({"action": "Renewable energy transition", "impact": f"Switch 30% of electricity → save ~{total*0.3*0.85:.0f} tCO₂e/yr", "gri": "GRI 302/305"})
    if bd.get("environmental", {}).get("Renewable Energy (GRI 302)", 0) < 40:
        weaknesses.append(f"Renewable energy score low ({bd['environmental'].get('Renewable Energy (GRI 302)',0):.0f}/100)")
    if bd.get("environmental", {}).get("Water Recycled (GRI 303)", 0) < 30:
        weaknesses.append("Water recycling rate not disclosed or very low (GRI 303)")

    # Social
    soc_sc = esg.get("social", 0)
    if not esg.get("data_provided", {}).get("employee_turnover"):
        weaknesses.append("Social indicators using sector defaults — no primary data disclosed")
    if bd.get("social", {}).get("Workplace Safety (GRI 403-9)", 0) < 60:
        weaknesses.append("Workplace safety score below threshold (GRI 403-9)")
        priorities.append({"action": "Safety management system", "impact": "Reduce injury rate to <1.0/200k hrs → GRI 403-9 best practice", "gri": "GRI 403"})
    if soc_sc >= 70:
        strengths.append(f"Social performance strong ({soc_sc:.0f}/100) — above sector average")

    # Governance
    gov_sc = esg.get("gov", 0)
    if bd.get("governance", {}).get("Board Independence (GRI 2-9/10)", 0) < 60:
        weaknesses.append("Board independence below 30% — OJK POJK 33/2014 minimum")
        priorities.append({"action": "Strengthen board independence", "impact": "Increase independent commissioners to ≥33% per OJK recommendation", "gri": "GRI 2-9/2-10"})
    if bd.get("governance", {}).get("Ethics & Anti-Corruption (GRI 2-23/205)", 0) < 50:
        weaknesses.append("Anti-corruption training below 50% coverage (GRI 205-2)")
    if gov_sc >= 70:
        strengths.append(f"Governance structure strong ({gov_sc:.0f}/100)")

    overall_sc = esg.get("score", 0)
    if overall_sc >= 75:
        strengths.append(f"ESG Grade {esg.get('grade','?')} — top quartile performance")
    elif overall_sc >= 60:
        strengths.append(f"ESG Grade {esg.get('grade','?')} — moderate performance with clear improvement pathway")

    priorities.append({"action": "Disclose S+G indicators", "impact": "Fill Social & Governance inputs in ESG Analytics → unlock accurate scoring vs sector defaults", "gri": "GRI 2-3"})

    return {"strengths": strengths, "weaknesses": weaknesses, "priorities": priorities}


# ── Main render ───────────────────────────────────────────────────────────────

def render():
    S.init()

    page_header(
        title="AI Sustainability Consultant",
        subtitle="Claude-powered ESG analysis · Full E+S+G context · GRI 2021 aligned recommendations",
        badge="Powered by Claude", badge_type="indigo",
    )

    df = S.get("uploaded_df")

    if df is None:
        from components.ui import empty_state
        empty_state("✦", "AI Consultant Requires ESG Data",
                    "Upload your ESG dataset in ESG Analytics. The AI Consultant will "
                    "automatically analyze root causes, benchmark performance, and generate "
                    "a personalized decarbonization roadmap covering E, S, and G dimensions.")
        if st.button("◈  Go to ESG Analytics →", type="primary", key="ac_goto"):
            st.session_state.active_page = "esg_analytics"
            st.rerun()
        return

    # ── Pull all ESG state ────────────────────────────────────────────────────
    ov       = dataset_overview(df)
    company  = S.get("company_name", "Your Organization")
    sector   = S.get("sector", "Manufacturing")
    area_m2  = S.get("area_m2", 5000)
    renew_pct= S.get("renew_pct", 5)

    from utils.state import compute_canonical_esg, get_scope_results
    esg      = compute_canonical_esg()
    scopes   = get_scope_results()
    intensity= scopes.get("intens_m2", 0)
    bench    = get_benchmark(sector)
    gap      = benchmark_gap(intensity, bench)
    pred     = predict_next_emission(df)
    annual_em= annual_projection(df)

    # ── API Key input ─────────────────────────────────────────────────────────
    with st.expander("🔑  Anthropic API Key — required for AI analysis", expanded=not st.session_state.get("ac_api_key")):
        st.markdown("""
        <div style="font-size:12px;color:#64748B;margin-bottom:10px;">
            Enter your Anthropic API key to enable real AI analysis powered by <strong>Claude</strong>.
            The key is only stored in your browser session and never persisted to disk.
            Get a key at <a href="https://console.anthropic.com" target="_blank">console.anthropic.com</a>.
        </div>
        """, unsafe_allow_html=True)

        api_key_input = st.text_input(
            "Anthropic API Key",
            value=st.session_state.get("ac_api_key", ""),
            type="password",
            placeholder="sk-ant-...",
            key="ac_api_key_input",
            label_visibility="collapsed",
        )
        if api_key_input:
            st.session_state["ac_api_key"] = api_key_input
            st.success("✅ API key saved for this session.")

    def _safe_secret(key: str) -> str:
        # st.secrets.get() raises StreamlitSecretNotFoundError (not just a
        # missing-key default) when no secrets.toml exists at all — which is
        # the common case for local dev / a fresh clone, so this must be
        # wrapped rather than relying on the dict-style default.
        try:
            return st.secrets.get(key, "")
        except Exception:
            return ""

    api_key = (
        st.session_state.get("ac_api_key", "")
        or _safe_secret("ANTHROPIC_API_KEY")
        or __import__("os").environ.get("ANTHROPIC_API_KEY", "")
    )
    use_ai  = bool(api_key.strip())

    if not use_ai:
        st.info("💡 No API key provided — showing rule-based analysis. Add your Anthropic API key above for AI-powered insights.")

    # ── ESG Scorecard summary ─────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4, gap="medium")
    _c = lambda s: "#10B981" if s>=70 else "#F59E0B" if s>=50 else "#F43F5E"
    with k1: kpi_card("ESG Overall", f"{esg['score']}/100", icon="🎯", icon_bg="#EFF6FF",
                        delta=esg.get("grade","?"), delta_label=f"· {esg.get('label','')}",
                        icon_color=_c(esg["score"]))
    with k2: kpi_card("Environmental", f"{esg['env']:.0f}/100", icon="🌿", icon_bg="#ECFDF5",
                        delta="40% weight", delta_label="· GRI 302-306", icon_color="#10B981")
    with k3: kpi_card("Social", f"{esg['social']:.0f}/100", icon="👥", icon_bg="#EEF2FF",
                        delta="30% weight", delta_label="· GRI 401-405", icon_color="#6366F1")
    with k4: kpi_card("Governance", f"{esg['gov']:.0f}/100", icon="⚖️", icon_bg="#F5F3FF",
                        delta="30% weight", delta_label="· GRI 2/205", icon_color="#8B5CF6")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── AI Analysis interface ─────────────────────────────────────────────────
    context = _build_context(df, ov, esg, intensity, bench, gap, scopes,
                              company, sector, area_m2, renew_pct, annual_em, pred)

    tab_overview, tab_chat, tab_roadmap, tab_raw = st.tabs([
        "📊 Full ESG Analysis", "💬 Ask the AI", "🗺️ Roadmap", "📋 Raw Context"
    ])

    # ── Tab 1: Full ESG Analysis ──────────────────────────────────────────────
    with tab_overview:
        analysis_key = f"ac_full_analysis_{hash(context[:200])}"

        if analysis_key not in st.session_state:
            st.session_state[analysis_key] = None

        if st.button("🔍  Generate Full ESG Analysis", type="primary",
                     key="ac_run_full", use_container_width=False):
            if use_ai:
                prompt = f"""Based on this organization's ESG performance data, provide a comprehensive
sustainability analysis covering all three dimensions (Environmental, Social, Governance).

Structure your response as:

## Executive Summary (2-3 sentences)

## Key Findings — Environmental (GRI 300-series)
[3-4 specific findings with data references]

## Key Findings — Social (GRI 400-series)
[3-4 specific findings with data references]

## Key Findings — Governance (GRI 2 / SASB)
[3-4 specific findings with data references]

## Top 5 Priority Actions
[Numbered list with specific impact estimates and GRI codes]

## Indonesia Regulatory Context
[Relevant POJK, OJK, Perpres requirements this data touches]

{context}"""

                with st.spinner("Claude is analyzing your full E+S+G profile..."):
                    result, success = _call_anthropic(api_key, SYSTEM_PROMPT, prompt, max_tokens=1500)
                    if success:
                        st.session_state[analysis_key] = {"text": result, "ai": True}
                    else:
                        st.error(f"API error: {result}")
                        st.session_state[analysis_key] = None
            else:
                # Rule-based fallback
                rb = _rule_based_analysis(df, ov, esg, intensity, bench, gap, sector)
                st.session_state[analysis_key] = {"rb": rb, "ai": False}

        cached = st.session_state.get(analysis_key)
        if cached:
            if cached["ai"]:
                # Show AI markdown response
                st.markdown("""
                <div style="background:white;border:1px solid #E2E8F0;border-radius:12px;
                     padding:24px;border-top:3px solid #6366F1;margin-top:12px;">
                <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;
                     color:#6366F1;margin-bottom:14px;">✦ Generated by Claude · Powered by Anthropic</div>
                """, unsafe_allow_html=True)
                st.markdown(cached["text"])
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                # Rule-based display
                rb = cached["rb"]
                col_s, col_w = st.columns(2, gap="medium")
                with col_s:
                    st.markdown("""<div class="cl-card">
                    <div class="cl-card-title">✅ Strengths</div>""", unsafe_allow_html=True)
                    for s_item in rb.get("strengths", ["No significant strengths identified yet"]):
                        st.markdown(f'<div style="font-size:12px;padding:6px 0;border-bottom:1px solid #F8FAFC;color:#374151;">✓ {s_item}</div>', unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                with col_w:
                    st.markdown("""<div class="cl-card">
                    <div class="cl-card-title">⚠️ Areas for Improvement</div>""", unsafe_allow_html=True)
                    for w_item in rb.get("weaknesses", ["Upload more data for deeper analysis"]):
                        st.markdown(f'<div style="font-size:12px;padding:6px 0;border-bottom:1px solid #F8FAFC;color:#374151;">→ {w_item}</div>', unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)

                st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
                st.markdown("""<div class="cl-card">
                <div class="cl-card-title">🚀 Priority Actions</div>""", unsafe_allow_html=True)
                for i, p in enumerate(rb.get("priorities", []), 1):
                    st.markdown(f"""
                    <div style="display:flex;gap:12px;padding:10px 0;border-bottom:1px solid #F8FAFC;">
                        <div style="width:24px;height:24px;background:#6366F1;color:white;border-radius:50%;
                             display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;flex-shrink:0;">{i}</div>
                        <div>
                            <div style="font-size:13px;font-weight:700;color:#0F172A;">{p['action']}</div>
                            <div style="font-size:11px;color:#64748B;margin-top:2px;">{p['impact']}</div>
                            <div style="font-size:10px;color:#6366F1;margin-top:2px;">{p.get('gri','')}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="text-align:center;padding:36px;background:#F8FAFC;border-radius:12px;border:1.5px dashed #CBD5E1;">
                <div style="font-size:28px;margin-bottom:8px;">✦</div>
                <div style="font-size:14px;font-weight:600;color:#374151;margin-bottom:4px;">
                    Click Generate to start analysis</div>
                <div style="font-size:12px;color:#94A3B8;">
                    {'AI-powered by Claude · ESG context ready' if use_ai else 'Rule-based analysis · Add API key for Claude AI'}</div>
            </div>
            """, unsafe_allow_html=True)

    # ── Tab 2: Chat with AI ───────────────────────────────────────────────────
    with tab_chat:
        if not use_ai:
            st.warning("💬 AI Chat requires an Anthropic API key. Add it in the panel above.")
        else:
            st.markdown("""
            <div style="font-size:12px;color:#64748B;margin-bottom:12px;">
                Ask anything about your ESG performance. Claude has full access to your E+S+G data,
                scope breakdown, benchmarks, and sector context.
            </div>
            """, unsafe_allow_html=True)

            # Chat history
            if "ac_chat_history" not in st.session_state:
                st.session_state["ac_chat_history"] = []

            chat_history = st.session_state["ac_chat_history"]

            # Display history
            for msg in chat_history:
                with st.chat_message(msg["role"], avatar="✦" if msg["role"]=="assistant" else "👤"):
                    st.markdown(msg["content"])

            # Quick question chips
            if not chat_history:
                st.markdown("**Suggested questions:**")
                q_cols = st.columns(2, gap="small")
                quick_questions = [
                    ("🔍 What's my biggest ESG gap?",            "What is my biggest ESG gap and the single most impactful action I can take to improve it?"),
                    ("📉 How do I reduce emissions 30%?",         "Give me a specific 3-year roadmap to reduce our total GHG emissions by 30% with cost estimates."),
                    ("👥 How do I improve Social score?",         "My Social score is lower than I'd like. What specific interventions would most improve it based on our data?"),
                    ("⚖️ Governance gaps for POJK 51?",          "What governance improvements do we need to be compliant with POJK 51 OJK requirements?"),
                    ("💰 ROI on renewable energy?",               "What's the estimated ROI and payback period if we increase renewable energy to 50%?"),
                    ("🏆 How to reach ESG Grade A?",              "What specific improvements are needed to reach ESG Grade A from our current position?"),
                ]
                for i, (label, _) in enumerate(quick_questions):
                    with q_cols[i % 2]:
                        if st.button(label, key=f"ac_q_{i}", use_container_width=True):
                            st.session_state["ac_pending_question"] = quick_questions[i][1]
                            st.rerun()

            # Process pending question from chip click
            if "ac_pending_question" in st.session_state:
                user_q = st.session_state.pop("ac_pending_question")
                chat_history.append({"role": "user", "content": user_q})
                full_prompt = f"{context}\n\n---\n\nUser question: {user_q}"
                with st.spinner("Claude is thinking..."):
                    reply, ok = _call_anthropic(api_key, SYSTEM_PROMPT, full_prompt, max_tokens=1000)
                chat_history.append({"role": "assistant", "content": reply if ok else f"Error: {reply}"})
                st.session_state["ac_chat_history"] = chat_history
                st.rerun()

            # Chat input
            user_input = st.chat_input("Ask about your ESG performance, regulations, or strategy...")
            if user_input:
                chat_history.append({"role": "user", "content": user_input})
                # Build conversation history for multi-turn
                messages = []
                for msg in chat_history:
                    messages.append({"role": msg["role"], "content": msg["content"]})
                # First message always includes full context
                if len(messages) == 1:
                    messages[0]["content"] = f"{context}\n\n---\n\n{user_input}"

                try:
                    import anthropic
                    client = anthropic.Anthropic(api_key=api_key)
                    response = client.messages.create(
                        model="claude-sonnet-4-6",
                        max_tokens=1000,
                        system=SYSTEM_PROMPT,
                        messages=messages,
                    )
                    reply = response.content[0].text
                    ok = True
                except Exception as e:
                    reply = f"Error: {e}"
                    ok = False

                chat_history.append({"role": "assistant", "content": reply})
                st.session_state["ac_chat_history"] = chat_history
                st.rerun()

            if chat_history:
                if st.button("🗑️  Clear chat", key="ac_clear_chat"):
                    st.session_state["ac_chat_history"] = []
                    st.rerun()

    # ── Tab 3: Decarbonization Roadmap ────────────────────────────────────────
    with tab_roadmap:
        roadmap_key = f"ac_roadmap_{hash(context[:200])}"

        if roadmap_key not in st.session_state:
            st.session_state[roadmap_key] = None

        if st.button("🗺️  Generate Decarbonization Roadmap", type="primary", key="ac_run_roadmap"):
            if use_ai:
                prompt = f"""Generate a detailed 3-year decarbonization roadmap for this organization.

Structure exactly as follows:

## Decarbonization Target
State a science-based target (SBTi aligned) with specific % reduction and year.

## Phase 1 — Quick Wins (Year 1)
3 specific actions with: estimated tCO₂e reduction, implementation cost range (IDR), GRI code

## Phase 2 — Structural Changes (Year 2)
3 specific actions with: estimated tCO₂e reduction, implementation cost range (IDR), GRI code

## Phase 3 — Transformation (Year 3+)
3 specific actions with: estimated tCO₂e reduction, technology/approach, GRI code

## Social & Governance Roadmap
3 non-environmental improvements that will most improve overall ESG score

## Expected ESG Score Trajectory
Estimate ESG score at end of Year 1, 2, 3 if roadmap is followed

## Key Risks & Mitigations
2-3 implementation risks specific to Indonesia context

{context}"""

                with st.spinner("Claude is building your roadmap..."):
                    result, success = _call_anthropic(api_key, SYSTEM_PROMPT, prompt, max_tokens=1600)
                    if success:
                        st.session_state[roadmap_key] = result
                    else:
                        st.error(f"API error: {result}")
            else:
                # Rule-based roadmap
                total_em = ov.get("total", 0)
                roadmap_text = f"""## Decarbonization Roadmap — Rule-Based Analysis

**Target:** Reduce GHG emissions 30% by 2027 from {total_em:,.0f} tCO₂e baseline

**Phase 1 — Quick Wins (Year 1)**
1. Renewable energy procurement — target 20% of electricity (GRI 302-1)
   *Estimated saving: {total_em*0.2*0.85:.0f} tCO₂e | Cost: ~IDR 50-200M*
2. Energy efficiency audit — identify top 20% energy consumers (GRI 302-4)
   *Estimated saving: {total_em*0.05:.0f} tCO₂e | Cost: ~IDR 20-50M*
3. Disclose S+G indicators — fill Social & Governance inputs for accurate ESG score

**Phase 2 — Structural Changes (Year 2)**
1. On-site solar PV installation — 30% electricity self-generation (GRI 302-1)
   *Estimated saving: {total_em*0.15:.0f} tCO₂e | Cost: ~IDR 500M-2B*
2. Employee green training program (GRI 404-1) — 40 hrs/year target
3. Board ESG committee formation — improve Governance score (GRI 2-9)

**Phase 3 — Transformation (Year 3+)**
1. Scope 3 supplier engagement — top 5 suppliers disclose emissions (GRI 308-1)
2. Science-Based Target submission — SBTi commitment
3. Zero-waste-to-landfill certification — ISO 14001 + GRI 306-4

*Add Anthropic API key for AI-generated personalized roadmap*"""
                st.session_state[roadmap_key] = roadmap_text

        roadmap_cached = st.session_state.get(roadmap_key)
        if roadmap_cached:
            st.markdown("""
            <div style="background:white;border:1px solid #E2E8F0;border-radius:12px;
                 padding:24px;border-top:3px solid #10B981;margin-top:12px;">
            """, unsafe_allow_html=True)
            if use_ai:
                st.markdown('<div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;color:#10B981;margin-bottom:14px;">✦ Generated by Claude · Powered by Anthropic</div>', unsafe_allow_html=True)
            st.markdown(roadmap_cached)

            # Download roadmap
            col_dl, _ = st.columns([1, 3])
            with col_dl:
                st.download_button(
                    "⬇️  Download Roadmap",
                    data=roadmap_cached.encode(),
                    file_name=f"carbonlens_roadmap_{company.replace(' ','_')}.md",
                    mime="text/markdown",
                    use_container_width=True,
                    key="ac_dl_roadmap",
                )
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="text-align:center;padding:36px;background:#F8FAFC;border-radius:12px;border:1.5px dashed #CBD5E1;">
                <div style="font-size:28px;margin-bottom:8px;">🗺️</div>
                <div style="font-size:14px;font-weight:600;color:#374151;margin-bottom:4px;">
                    Generate a personalized 3-year roadmap</div>
                <div style="font-size:12px;color:#94A3B8;">
                    Covers GHG reduction targets, cost estimates, Social & Governance improvements</div>
            </div>
            """, unsafe_allow_html=True)

    # ── Tab 4: Raw Context ────────────────────────────────────────────────────
    with tab_raw:
        st.markdown("""
        <div style="font-size:12px;color:#64748B;margin-bottom:8px;">
            This is the full ESG context passed to Claude. Useful for debugging or
            understanding what data is being used for AI analysis.
        </div>
        """, unsafe_allow_html=True)
        st.code(context, language="text")
