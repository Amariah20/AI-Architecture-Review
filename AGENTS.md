# AI Architecture Review & Optimisation Assistant — Codex Instructions

## Project Overview

This project is developed under the AWS She Builds Mentorship Programme, guided by Pulkit Bahl.

The application reviews AWS architectures against two authoritative sources:

1. Internal company policies retrieved through Amazon Bedrock Knowledge Bases (RAG).
2. AWS documentation and best practices accessed through MCP.

It identifies architecture gaps, security risks, policy violations and cost inefficiencies, providing recommendations supported by source citations.

## Source of Truth

- Read `docs/PRD.md` before proposing architecture or implementing major features.
- Follow the PRD's MoSCoW prioritisation and MVP scope.
- Do not introduce additional features or change the technology stack without approval.
- If documentation is missing, identify the gap rather than inventing requirements.

## Technology Stack

- Language: Python 3
- LLM: Amazon Bedrock
- RAG: Amazon Bedrock Knowledge Bases
- External documentation: AWS MCP Server
- Guardrails: Amazon Bedrock Guardrails
- Frontend: Streamlit (provisional; subject to confirmation)
- Version control: GitHub
- Deployment: To be confirmed

## Development Standards

- Write readable, modular, maintainable Python code.
- Use appropriate type hints, error handling and logging.
- Separate UI, AWS integrations, application logic and configuration.
- Write tests for important functionality.
- Never hardcode API keys, AWS credentials or sensitive information.
- Use environment variables or appropriate AWS credential mechanisms.
- Do not commit `.env` files, secrets or private company policies.
- Minimise AWS costs and flag potentially chargeable services before provisioning resources.
- Verify current AWS APIs and library usage rather than assuming they exist.

## Working Process

1. Read relevant project documentation before starting a task.
2. Explain the planned changes and affected files.
3. Implement only the requested functionality.
4. Run relevant tests where possible.
5. Report changes, test results, limitations and remaining work.
6. Never claim a feature is working without verification.

## Collaboration and Learning

The developer has professional experience in C#, Java, PHP, .NET, Java, PHP and SQL but is learning Python and AI engineering.

Explain unfamiliar Python and AI concepts when relevant, without overexplaining general software engineering principles.

Prefer small, understandable changes over generating the entire application at once.

## Core Objective

Build a functional, secure and demonstrable portfolio application while developing a strong understanding of RAG, MCP, Amazon Bedrock, guardrails, source attribution and AI evaluation.

Every major architectural decision should be explainable and defensible in a Solutions Architect or AI Engineering interview.
