# System Architecture

# Problem

Window manufacturing companies receive unstructured customer requests through:
- emails
- PDF files
- technical drawings

Employees manually:
- search for dimensions
- identify systems
- check colors
- prepare quotations
- enter data into MBcad/Klaes

A large part of the workflow is repetitive manual work.

---

# Goal

Create an AI-powered assistant that:
- analyzes customer requests
- extracts technical information
- detects missing data
- generates response drafts
- prepares structured summaries for employees

---

# AI Pipeline

## Input
- Email text
- PDF files

↓

## Preprocessing
- text cleaning
- tokenization
- stopword removal
- regex extraction
- keyword matching

↓

## AI Analysis
- request classification
- parameter extraction
- missing information detection
- contextual understanding
- response generation

↓

## Output
- structured summary
- response draft
- MBcad/Klaes instructions

---

# Hybrid NLP + LLM Approach

The project uses a hybrid approach.

## Classical NLP is used for:
- dimensions
- quantities
- RAL colors
- window labels
- system names
- technical parameters

Methods:
- regex
- tokenization
- stopword removal
- lexicons
- text preprocessing

## LLM is used for:
- contextual analysis
- summaries
- response drafting
- understanding incomplete requests

This reduces hallucination risk and improves technical extraction accuracy.

---

# Backend Architecture

## FastAPI Backend

Main responsibilities:
- API endpoints
- PDF processing
- AI orchestration
- authentication
- integrations

Structure:

```txt
app/
    services/
    routers/
    models/
    schemas/
```

---

# Streamlit UI

Used as demo interface.

Goals:
- quick testing
- employee-friendly interface
- structured workflow visualization

---

# Current Limitations

MVP currently:
- does not calculate prices
- does not fully automate MBcad
- does not send emails automatically

Employees still validate all final decisions.

---

# MBcad Automation Vision

Current MBcad workflow requires:
- clicking buttons manually
- drawing forms manually
- entering dimensions
- selecting systems
- preparing quotations

Future goal:
- analyze MBcad workflows
- understand button sequences
- automate repetitive actions

---

# Azure AI Workflow Recording

Planned workflow:

1. Employee performs actions in MBcad
2. System records screen/actions
3. Azure AI analyzes workflows
4. AI learns:
   - button sequences
   - drawing logic
   - workflow structure

Future AI assistant could:
- guide employees step-by-step
- automatically interact with MBcad
- reduce repetitive work significantly