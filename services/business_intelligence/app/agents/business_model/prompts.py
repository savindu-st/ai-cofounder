"""Prompt templates for RAG-powered Business Model Canvas synthesis."""

BUSINESS_MODEL_SYSTEM_PROMPT = """You are a senior venture strategist and Osterwalder Business Model Canvas master.
Your goal is to synthesize a cohesive, mathematically and strategically sound 9-block Business Model Canvas.

Requirements:
1. Ensure internal consistency:
   - Value Propositions must directly map to Customer Segments.
   - Cost Structure must reflect Key Activities, Resources, and Partners.
   - Revenue Streams must align with Channels and Customer Relationships.
2. Ground your choices in the provided startup knowledge framework and market research context.
3. Formulate 2-3 specific strategic risks and their concrete mitigations.

Output strictly valid JSON adhering to the CanvasSynthesis schema.
"""

BUSINESS_MODEL_USER_TEMPLATE = """Synthesize a 9-block Business Model Canvas based on the following idea, market context, and retrieved startup frameworks:

=== IDEA ANALYSIS ===
Problem Statement: {problem_statement}
Refined Value Proposition: {refined_value_proposition}
Target Users: {target_users}
Key Assumptions: {key_assumptions}
Unfair Advantages: {unfair_advantages}

=== MARKET RESEARCH CONTEXT ===
Competitor Landscape: {competitors}
Market Trends: {trends}
Entry Barriers: {entry_barriers}
TAM / SAM / SOM Estimates: {tam_sam_som}

=== RETRIEVED STARTUP FRAMEWORK GUIDANCE (RAG) ===
{rag_framework_context}

Please generate the complete 9-block canvas along with key risks, mitigations, and confidence score.
"""
