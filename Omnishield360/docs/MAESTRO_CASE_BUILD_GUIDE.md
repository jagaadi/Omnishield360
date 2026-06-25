# OmniShield 360 — Maestro Case Private Preview Build Guide

**Owner:** [Aditya Panigrahy](https://www.linkedin.com/in/aditya-narayan-panigrahy/)  
**Repository:** [jagaadi/Omnishield360](https://github.com/jagaadi/Omnishield360)  
**License:** Apache 2.0  
**Created for:** UiPath AgentHack 2026 — Track 1: Agentic Case Management

## Architecture

OmniShield 360 is a **Maestro Case Management** solution. The Case Plan is the
persistent outer lifecycle. Python agents, RPA workflows, API integrations,
Action apps, and the existing BPMN are task implementations inside the case.

The current private-preview guide is the authority for this build:

- create the case in Studio Web as a Case Management project;
- use an external claim ID as the case key;
- hydrate case fields through a Wait for Connector trigger;
- model primary and secondary stages;
- configure entry, exit, re-entry, and skip conditions;
- configure case/stage SLAs and escalations;
- attach Human, RPA, API/Integration, AI Agent, Agentic Process, or Child Case
  implementations;
- expose the operational experience through Case App.

## Preview-specific choices

Native Data Fabric case-entity support and stage-aware role/access enforcement
are described in the supplied preview guide as planned extensions. Therefore:

- this solution uses the **case trigger payload** as its case entity;
- human task assignments and folder permissions implement personas today;
- the schema remains Data Fabric/VDO-ready for later migration;
- the repository does not claim the JSON specification is directly importable.

## Repository artifacts

- `case-models/omnishield360-case-plan.json` — exact Studio Web build spec.
- `case-models/case-entity-schema.json` — trigger payload and case-field schema.
- `case_workers.py` — coded workers attached to AI Agent/API tasks.
- `uipath.json` — function mappings for each case worker.
- `process-models/process-model.bpmn` — optional Maestro Agentic Process task,
  not the outer lifecycle.

## Primary stages

1. **Intake** — IXP extraction, policy/history lookup, PHI isolation, and
   low-confidence human validation.
2. **Review** — referral, medical necessity, duplicate/fraud, COB, Clinical
   Director, Fraud Investigator, and COB Specialist work.
3. **Settlement** — compliance shield, Agent-as-Judge, Claims Adjuster
   approval, and guarded synchronization.
4. **Closure** — claim packet, audit report, notifications, and case completion.

## Secondary stages

- **Pending with Provider** returns to the stage that requested information.
- **Fraud Hold** requires an investigator disposition.
- **Legal Estates Hold** requires a legal disposition.
- **Denied** is terminal after denial communications and audit generation.
- **Withdrawn** is connector-driven and terminal.

## Human control points

Agents can analyze and recommend. They cannot accept unreliable extraction,
approve non-routine medical necessity, clear fraud/legal holds, confirm
ambiguous COB, resolve judge conflicts, approve settlement, or reopen/redirect
the case.

## Studio Web build steps

1. Create **Case Management Project** → `OmniShield360ClaimCase`.
2. Choose an external case key mapped to `claimId`.
3. Configure **Wait for Connector** → `ClaimSubmitted`.
4. Add trigger fields from `case-entity-schema.json`.
5. Add Intake, Review, Settlement, and Closure as primary stages.
6. Add Pending with Provider, Fraud Hold, Legal Estates Hold, Denied, and
   Withdrawn as secondary stages.
7. Configure conditions and task implementations from the case-plan JSON.
8. Publish the coded-agent package and map functions from `uipath.json`.
9. Build the Action app forms and configure assignments/SLAs.
10. Configure Case App title, details, timeline fields, and human task views.
11. Validate, publish, deploy, and activate in the hackathon folder.
12. Demonstrate live instances, re-entry, SLA state, incidents, and Case App.

## Demo flow

1. Happy path moves Intake → Review → Settlement → Closure.
2. Low OCR creates an Intake Specialist Action app task.
3. Missing referral enters Pending with Provider and returns to Review.
4. Duplicate billing enters Fraud Hold.
5. Deceased member enters Legal Estates Hold and activates the breaker.
6. Settlement cannot synchronize until the Claims Adjuster approves.

## Official references

- [Introduction to Maestro Case](https://docs.uipath.com/maestro/automation-cloud/latest/user-guide/introduction-to-maestro-case)
- [Building an insurance claims case](https://docs.uipath.com/maestro/automation-cloud/latest/user-guide/building-an-insurance-claims-case-in-30-minutes)
- [Primary and secondary stages](https://docs.uipath.com/maestro/automation-cloud/latest/user-guide/how-to-model-primary-secondary-stages)
- [SLAs and escalations](https://docs.uipath.com/maestro/automation-cloud/latest/user-guide/how-to-set-slas-and-automated-escalation-rules)
- [Rework and re-entry](https://docs.uipath.com/maestro/automation-cloud/latest/user-guide/how-to-configure-a-rework-loop-re-entry)
