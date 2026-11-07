

|  |  |
| :---- | :---- |

**PROJECT REQUIREMENTS DOCUMENT**

**AI Architecture Review**

**& Optimisation Assistant**

*An AI-powered chatbot that reviews AWS architectures against company policies and AWS best practices — grounded in real sources, not guesswork.*

| AUTHOR | Amariah Rigodon |
| :---- | :---- |
| **MENTOR** | Pulkit Bahl — AWS She Builds Mentorship Programme |
| **VERSION** | 1.0  —  Initial Draft |
| **STATUS** | In Progress |
| **PROGRAMME** | AWS She Builds Mentorship |
| **REPOSITORY** | GitHub (TBC) |

|  |
| :---- |

|  | CORE THESIS *A portfolio project that demonstrates practical AI engineering skills — RAG, MCP, guardrails, and logging — through a real-world use case: reviewing AWS architectures against both public best practices and private company policies. Designed to position Amariah for Solutions Architect roles.* |
| :---- | :---- |

**1  Project Overview**

|  |
| :---- |

The AI Architecture Review & Optimisation Assistant is a chatbot application that allows businesses to upload their internal policies and describe their current AWS architecture. The chatbot then evaluates the architecture against two authoritative sources: live AWS documentation and best practices (via the AWS MCP Server), and the business's own internal policies (via Amazon Bedrock Knowledge Bases / RAG). It identifies gaps, risks, policy violations, and cost inefficiencies, and recommends improvements — with source citations on every claim to prove the responses are grounded in real documentation, not guesswork.

This project was developed as part of the AWS She Builds Mentorship Programme under the guidance of mentor Pulkit Bahl. The technical direction was shaped through a series of mentorship sessions that refined the scope from a general architecture advisor to a more focused, defensible project that demonstrates genuine AI engineering skills.

**Origin & Context**

Amariah's original project idea — a general AI Architecture Review tool — was refined by Pulkit to address a more specific and technically interesting problem: what happens when you ground an AI in two distinct, authoritative sources and compare its output to a bare LLM? The result is a project that not only works as a functional tool but also tells a compelling story in a job interview.

***"Can AI review a customer's architecture against their own internal policies (RAG) and against AWS best practices (MCP)? Then compare that with how a bare LLM reviews the same architecture."***

*— Pulkit Bahl, Mentor*

**Purpose**

* Showcase practical AI engineering skills for Solutions Architect and other  job applications

* Demonstrate understanding of RAG, MCP, guardrails, logging, and Amazon Bedrock 

* Build a functional tool that businesses could genuinely use to review their AWS architectures

* Create a clear interview narrative: "I built this, here's why each decision was made, and here's the evidence it works"

**2  Problem Statement**

|  |
| :---- |

Reviewing an AWS architecture for correctness, security, and cost-efficiency is a complex, expert-level task. Solutions Architects spend significant time cross-referencing AWS documentation, the Well-Architected Framework, and a client's own internal standards to identify gaps and make recommendations. This process is manual, time-consuming, and requires deep expertise that many organisations cannot easily access.

While large language models (LLMs) can attempt architecture reviews, they have a critical limitation: they rely entirely on their training data. They lack access to current AWS documentation, up-to-date pricing, and — most importantly — a business's own internal policies. The result is advice that is generic, potentially outdated, and impossible to verify.

| Problem | Impact |
| :---- | :---- |
| Architecture review is manual and time-consuming | Teams lack bandwidth for thorough assessments |
| Bare LLMs lack access to current AWS docs | Advice is generic, outdated, or hallucinated |
| Company-specific policies are disconnected from reviews | Violations of internal standards go undetected |
| No source transparency in AI-generated advice | Impossible to trust or verify recommendations |

This project addresses all four problems by grounding the AI in two authoritative, up-to-date sources — the AWS MCP Server for public best practices, and Amazon Bedrock Knowledge Bases for private company policies — while providing source citations on every response to ensure full transparency and traceability.

**3  Target Users**

|  |
| :---- |

The primary users of this application are businesses and technical teams who need to evaluate their AWS cloud architecture. This includes:

* Solutions Architects and Cloud Engineers reviewing their organisation's infrastructure

* Technical teams seeking to validate their architecture against internal compliance policies

* Businesses wanting to identify cost inefficiencies or security gaps before an audit

* Teams preparing for an AWS Well-Architected Review and wanting to self-assess first

**How Users Interact With the App**

1. Arrive at the app — no account required to start (guest session available)

2. Upload their company's internal policies (PDF, Word, text) — these are stored in the knowledge base

3. Describe or upload their current AWS architecture (text description, diagram, or structured format)

4. Ask questions such as: "What are the gaps?", "Does this follow best practices?", "Where am I wasting budget?", "How does this compare to the Well-Architected Framework?"

5. Receive recommendations with full source citations — showing which document, page, and line each piece of advice came from

6. Continue the conversation for follow-up questions and deeper exploration

|  | Note: Portfolio Context While the app is designed to be genuinely useful to businesses, its primary purpose is as a portfolio piece. The "target user" framing here serves both as a functional design guide and as evidence of product thinking in an interview context. |
| :---- | :---- |

**4  Key Features & User Flow**

|  |
| :---- |

**Core Feature Set**

| Feature | Description |
| :---- | :---- |
| **Chatbot Interface** | Text-based conversation UI where users describe their architecture and ask questions about it |
| **Policy Upload & Knowledge Base** | Users upload internal policy documents (PDF, Word, text). These are stored in Amazon Bedrock Knowledge Bases and made searchable via RAG |
| **AWS Best Practices (MCP)** | The app connects to the AWS MCP Server, which provides live, up-to-date access to AWS documentation, the Well-Architected Framework, and AWS pricing data |
| **Dual-Source Review** | Every architecture review checks against both sources simultaneously: company policies (RAG) and AWS best practices (MCP) |
| **Gap & Risk Analysis** | Identifies specific gaps, risks, policy violations, and cost inefficiencies in the architecture with clear explanations |
| **Source Citations** | Every response includes citations showing exactly where each piece of information came from: document name, page, and line number where possible |
| **Guardrails** | Blocks off-topic questions (anything unrelated to AWS architecture), hate speech, dangerous content, and sensitive information (e.g., credentials, PII) |
| **Logging & Tracing** | Full provenance tracking for every response — records which sources were retrieved, which documents were referenced, and the reasoning chain used |
| **Live Deployment** | The application is deployed live and accessible to anyone via URL  |

**5  MoSCoW Prioritisation**

|  |
| :---- |

Requirements are prioritised using the MoSCoW method to manage scope and ensure the most valuable features are delivered first. This is especially important given the learning curve involved and the \~8 hours per week available for development.

| M Must Have | *Without these, the project is not considered complete. These form the MVP.* |
| :---- | :---- |
|  | Chatbot interface where users can interact via text Upload company policy documents → stored in Amazon Bedrock Knowledge Base (RAG) Connect to AWS MCP Server for AWS documentation, Well-Architected Framework, and pricing data Review architecture against both sources (company policies \+ AWS best practices) Identify gaps, risks, policy violations, and cost inefficiencies Recommend improvements based on both sources Source citations on every response (document name, page/section, line where possible) Guardrails: block off-topic questions, hate speech, dangerous content, and sensitive information Logging and tracing: capture full provenance of all information sources used in every response Bare LLM comparison: behind-the-scenes evaluation benchmarking the app vs a bare LLM (for interviews — not user-facing) Live deployment: app published and accessible via public URL |
| **S** **Should Have** | *Important but not critical for MVP. Should be included if time allows.* |
|  | Guest-to-account authentication flow: use the app without an account (temporary session, data lost after cache clear/timeout), with the option to create an account to persist policies, chat history, and uploaded documents Session migration: if a guest decides to create an account, their uploaded policies and chat history transfer to the new account Session persistence for logged-in users across visits Explicit alignment to the six AWS Well-Architected Framework pillars in reviews (Security, Reliability, Cost Optimisation, Performance Efficiency, Operational Excellence, Sustainability) |
| **C** **Could Have** | *Nice-to-have features that add value but will not affect core functionality if omitted.* |
|  | Generate recommended architecture diagrams visually based on proposed improvements Compare the user's architecture to common reference architectures for similar industries Export assessment reports as PDF or Word documents |
| **W** **Won't Have** | *Explicitly out of scope for now. Candidates for future iterations.* |
|  | Multi-agent architecture (e.g., separate Policy Agent, AWS Agent, Report Agent) — revisit once core is working and the use case for agents is clearer Real-time collaboration — multiple users reviewing the same architecture simultaneously Auto-detect architecture from live AWS accounts (e.g., reading CloudFormation / Terraform templates via API) Support for non-AWS cloud providers (Azure, GCP) |

**6  Technology Stack**

|  |
| :---- |

The technology stack has been selected based on mentor guidance from Pulkit Bahl, alignment with AWS services already being explored for the AWS Solutions Architect Associate certification, and practical accessibility for a beginner building their first AI project. Where possible, managed services are preferred to reduce operational overhead and keep costs low.

| Component | Technology | Rationale |
| :---- | :---- | :---- |
| **LLM** | Amazon Bedrock (Claude or Titan) | Mentor-recommended. Hosts the LLM, knowledge base, and guardrails in a single managed platform, reducing complexity for a beginner. |
| **Knowledge Base (RAG)** | Amazon Bedrock Knowledge Bases | Managed RAG service. Handles document ingestion, embedding, vector storage, and retrieval without requiring a separate vector database. |
| **AWS Best Practices** | AWS MCP Server | Publicly available, open-source MCP server maintained by AWS. Provides live access to AWS documentation, Well-Architected Framework content, and pricing data via the Model Context Protocol. |
| **Guardrails** | Amazon Bedrock Guardrails | Natively integrated with Bedrock. Manages topic restrictions (off-topic blocking), content safety (hate speech, harmful content), and sensitive data filtering (PII, credentials). |
| **Programming Language** | Python 3.x | Industry standard for AI/ML. Best framework and community support for LLM-based applications. Being learned as part of this project. |
| **IDE** | Visual Studio Code | Integrate with Codex. Assists in writing code locally. |
| **Version Control** | GitHub | Industry standard. Hosts the codebase publicly as part of the portfolio. |
| **Frontend / UI** | TBD (likely Streamlit) | Streamlit is a Python-native UI framework ideal for chatbot interfaces. Simple to learn and deploy. To be confirmed. |
| **Deployment** | TBD  | Must be publicly accessible via URL. Options under consideration: Streamlit Community Cloud (free, deploys from GitHub), AWS Amplify, or AWS App Runner. Note: GitHub Pages is not suitable as it only hosts static sites. |
| **Cloud Account** | AWS Account (personal) | Required for Amazon Bedrock, MCP server access, and deployment. Costs to be kept minimal using free tier where available. |

|  | About the AWS MCP Server The AWS MCP Server is an open-source server published by AWS Labs that implements the Model Context Protocol. It gives AI models live access to AWS documentation, service guides, the Well-Architected Framework content, and pricing information. Unlike static document retrieval (RAG), MCP provides real-time tool access — meaning the AI can look things up dynamically rather than relying on pre-ingested content. This distinction is a key part of the project's technical story. |
| :---- | :---- |

**7  Architecture Overview**

|  |
| :---- |

The system is built around a single Amazon Bedrock LLM that is given access to two distinct information sources at inference time: a private knowledge base (containing the user's company policies, retrieved via RAG) and the AWS MCP Server (providing live AWS documentation and best practices via the Model Context Protocol). Amazon Bedrock Guardrails sit as a filter layer on both input and output. All requests and responses are logged with full traceability.

| 1 | User Input The user uploads their company policy documents and describes their AWS architecture. They then ask questions via the chatbot interface. |
| :---: | :---- |
| **2** | **Guardrails (Input Filter)** Amazon Bedrock Guardrails filter the input. Off-topic questions (not related to AWS architecture), harmful content, hate speech, and sensitive information are blocked before reaching the LLM. |
| **3** | **Dual-Source Retrieval** The LLM queries two sources simultaneously: (a) the Amazon Bedrock Knowledge Base via RAG to retrieve relevant company policies, and (b) the AWS MCP Server to retrieve live AWS documentation and Well-Architected Framework guidance relevant to the query. |
| **4** | **LLM Response Generation** Amazon Bedrock generates a response grounded in both retrieved sources. The response includes gap analysis, risk identification, recommendations, and inline source citations (document name, page, and line number where available). |
| **5** | **Guardrails (Output Filter)** The generated response passes through a second guardrails check before being returned to the user, filtering any hallucinated or harmful content in the output. |
| **6** | **Logging & User Response** The full trace is logged (query, retrieved sources, LLM reasoning, response). The final response is returned to the user with source citations visible inline — similar to how ChatGPT shows sources when browsing the web. |

| \[ ARCHITECTURE DIAGRAM PLACEHOLDER \] *Insert architecture diagram here* Diagram should show: User → Chatbot UI → Guardrails → Amazon Bedrock LLM → Knowledge Base (RAG / company policies) \+ AWS MCP Server (live AWS docs) → Logging & Tracing → Response with source citations |
| :---: |

*Figure 1: High-level system architecture — based on Pulkit's whiteboard diagram from mentorship session*

**8  Success Criteria**

|  |
| :---- |

The project is considered complete when all of the following criteria are met. These criteria are designed to be objectively verifiable — not subjective — so that success can be demonstrated clearly in an interview or to a reviewer.

| \# | Success Criterion | Status |
| ----- | :---- | :---- |
| **1** | The chatbot accepts policy document uploads and stores them in the knowledge base successfully | Not started |
| **2** | The chatbot accepts architecture descriptions (text) and processes them correctly | Not started |
| **3** | Responses accurately identify gaps and violations against AWS best practices (MCP source) | Not started |
| **4** | Responses accurately identify gaps and violations against the uploaded company policies (RAG source) | Not started |
| **5** | Every response includes source citations (document name, page/section) — no unsourced claims | Not started |
| **6** | Guardrails successfully block off-topic questions, hate speech, dangerous content, and sensitive data | Not started |
| **7** | Logging and tracing captures full provenance of information for every response | Not started |
| **8** | The application is deployed live and accessible via a public URL | Not started |
| **9** | The bare LLM comparison demonstrates measurable improvement in accuracy/relevance vs the grounded application | Not started |
| **10** | The project can be demonstrated end-to-end in a job interview with a clear explanation of every technical decision made | Not started |

**9  Constraints & Risks**

|  |
| :---- |

| Constraint / Risk | Description | Mitigation |
| :---- | :---- | :---- |
| **Python beginner** | Amariah is new to Python and AI/ML development | Use Kiro (AI IDE) to assist with code; learn incrementally while building; AI-assisted debugging |
| **Limited time** | \~8 hours per week available while completing MBA | MoSCoW prioritisation ensures focus stays on MVP; stretch goals are clearly separated |
| **AWS costs** | Amazon Bedrock and other AWS services incur usage costs | Use AWS Free Tier where available; keep test volumes low; set billing alerts on the AWS account |
| **Mentor dependency** | Some architectural decisions require Pulkit's guidance before proceeding | Prepare questions before each session; document decisions in this PRD so context is preserved |
| **Kiro student licence** | Kiro is free for students for one year; licence may expire during the project | Begin build before licence expires; VS Code with Copilot is a viable fallback |
| **MCP server availability** | The AWS MCP Server is open-source and subject to changes or rate limits | Monitor AWS Labs GitHub for updates; design the MCP layer to be replaceable if needed |
| **Scope creep** | Risk of adding features beyond MVP before core is working | Refer to MoSCoW priorities; nothing moves from "Won't Have" to "Must Have" without mentor sign-off |

**10  Learning Objectives**

|  |
| :---- |

One of the explicit goals of this project is to develop and demonstrate a specific set of AI engineering skills. Each component of the build corresponds to a concept that Amariah will be able to explain, justify, and demonstrate in an interview. The table below maps each technology to the skill it teaches and the interview narrative it supports.

| Technology | Skill Developed | Interview Narrative |
| :---- | :---- | :---- |
| **Amazon Bedrock Knowledge Bases** | RAG (Retrieval-Augmented Generation) | "I built a retrieval pipeline over private documents. I understand how chunking, embedding, and vector search work together to ground an LLM in specific knowledge." |
| **AWS MCP Server** | Model Context Protocol (MCP) | "I connected an AI agent to live external tools using MCP. I understand the difference between static RAG retrieval and dynamic tool access." |
| **Amazon Bedrock Guardrails** | AI safety, content filtering, topic restriction | "I implemented guardrails that block off-topic questions, harmful content, and sensitive data. I understand why this matters in production AI systems." |
| **Logging & Tracing** | Provenance, anti-hallucination, observability | "Every response in my app shows exactly where the information came from. I understand why source traceability is essential for trustworthy AI." |
| **Amazon Bedrock (general)** | Managed AI services on AWS | "I used Amazon Bedrock as the core platform. I can explain its components, why I chose it over alternatives, and what trade-offs that involved." |
| **Python** | Practical Python for AI development | "I learned Python specifically for this project. It's now my primary language for AI/ML work." |
| **Bare LLM benchmarking** | AI evaluation and model assessment | "I benchmarked my grounded application against a bare LLM on the same input. I can show the improvement in accuracy and explain why RAG \+ MCP made the difference." |
| **(Future) Multi-agent architecture** | Agent design and orchestration | "After the core is working, I plan to explore splitting the review into specialist agents. I can explain the trade-offs between a single-LLM approach and multi-agent architectures." |

**11  Document History**

|  |
| :---- |

| Version | Date | Author | Notes |
| ----- | :---- | :---- | :---- |
| 1.0 | 2025 | Amariah Rigodon | Initial draft. Scope, MoSCoW, tech stack, and architecture overview based on AWS She Builds Mentorship sessions with Pulkit Bahl. |

*This document will be updated as the project evolves. Significant scope changes require review against the MoSCoW priorities in Section 5\.*

