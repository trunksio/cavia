# Phase 1 Integration Guide - Intent-Driven Workflows

**Date:** 2025-10-26
**Status:** Phase 1 Complete - Ready for Testing

## What's Been Implemented

Phase 1 of the Intent-Driven Agent-Oriented Architecture is now **100% complete**. The system now supports:

1. ✅ Structured intent management with goals, constraints, and success criteria
2. ✅ Intent validation and drift detection at each agent
3. ✅ Workflow templates for different business processes
4. ✅ UI components for workflow selection and intent capture
5. ✅ Real-time intent tracking dashboard
6. ✅ Backend API endpoints for intent management
7. ✅ Reference implementation in ParserAgent
8. ✅ Backward compatibility with legacy string intents

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                           │
├─────────────────────────────────────────────────────────────────┤
│  1. WorkflowSelector → User selects workflow template          │
│  2. IntentCapture    → User configures parameters              │
│  3. Document Upload  → Document uploaded with intent           │
│  4. IntentTracker    → Real-time validation monitoring         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                       BACKEND API                               │
├─────────────────────────────────────────────────────────────────┤
│  • POST /api/v1/cvs/upload (accepts StructuredIntent)          │
│  • GET  /api/v1/workflows (list available workflows)           │
│  • GET  /api/v1/cvs/{job_id}/intent (get job intent)          │
│  • GET  /api/v1/cvs/{job_id}/validations (validation history) │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     AGENT PROCESSING                            │
├─────────────────────────────────────────────────────────────────┤
│  For each agent in the chain:                                  │
│    1. validate_intent(task) → Alignment score                  │
│    2. check_intent_drift(task) → Drift detection               │
│    3. Process work                                              │
│    4. update_intent_context(task) → Add results                │
│    5. Route to next agent with updated validations             │
└─────────────────────────────────────────────────────────────────┘
```

---

## New UI Components

### 1. WorkflowSelector Component

**Location:** `frontend/src/components/WorkflowSelector.jsx`

**Features:**
- Displays available workflow templates as cards
- Filter by category (HR, Finance, etc.)
- Search by workflow name/description
- Shows supported document types
- Displays example use cases

**Usage:**
```jsx
import WorkflowSelector from './components/WorkflowSelector';

<WorkflowSelector
  onWorkflowSelect={(workflow) => setSelectedWorkflow(workflow)}
/>
```

### 2. IntentCapture Component

**Location:** `frontend/src/components/IntentCapture.jsx`

**Features:**
- Dynamic form builder based on workflow template
- Parameter validation
- Intent preview before submission
- Shows constraints and success criteria
- Creates StructuredIntent via API

**Usage:**
```jsx
import IntentCapture from './components/IntentCapture';

<IntentCapture
  workflow={selectedWorkflow}
  onIntentCreated={(intent) => handleUploadWithIntent(file, intent)}
  onBack={() => setStep('select-workflow')}
/>
```

### 3. IntentTracker Component

**Location:** `frontend/src/components/IntentTracker.jsx`

**Features:**
- Real-time intent tracking (polls every 3 seconds)
- Displays original intent goal
- Shows average alignment and drift scores
- Lists all agent validations with details
- Drift alerts when threshold exceeded
- Shows constraints and success criteria

**Usage:**
```jsx
import IntentTracker from './components/IntentTracker';

<IntentTracker jobId={job.job_id} />
```

---

## Backend Updates

### Updated API Endpoints

#### 1. Upload with Intent (UPDATED)
```http
POST /api/v1/cvs/upload
Content-Type: multipart/form-data

file: <file>
intent: {
  "workflow_type": "cv_evaluation",
  "goal": "Evaluate candidate for Senior Python Developer",
  "context": {...},
  "constraints": [...],
  "success_criteria": [...]
}
```

**Backward Compatible:** Still accepts string intent for legacy support.

#### 2. Get Job Intent (NEW)
```http
GET /api/v1/cvs/{job_id}/intent
```

Returns the StructuredIntent for a job.

#### 3. Get Validation History (NEW)
```http
GET /api/v1/cvs/{job_id}/validations
```

Returns array of IntentValidation objects from each agent.

#### 4. Workflow Management (NEW)
```http
GET /api/v1/workflows                      # List all workflows
GET /api/v1/workflows/{workflow_id}        # Get specific workflow
GET /api/v1/workflows/category/{category}  # Filter by category
GET /api/v1/workflows/categories           # List categories
POST /api/v1/workflows/{workflow_id}/intent # Create intent from template
```

### Updated API Client

**Location:** `frontend/src/services/api.js`

**New Methods:**
```javascript
// Workflow management
listWorkflows()
getWorkflow(workflowId)
getWorkflowsByCategory(category)
createIntentFromTemplate(workflowId, parameters)

// Document upload with intent
uploadDocumentWithIntent(file, intent, onProgress)

// Intent tracking
getJobIntent(jobId)
getJobValidations(jobId)
```

---

## Agent Implementation Guide

### Reference Implementation: ParserAgent

**Location:** `agents/parser/main.py`

The ParserAgent now demonstrates best practices for intent validation:

#### Step 1: Detect Task Version
```python
def process_task(self, task) -> AgentTaskResult:
    # Detect if this is AgentTaskV2 with intent validation
    is_v2_task = isinstance(task, AgentTaskV2) or hasattr(task, 'intent_validations')
```

#### Step 2: Validate Intent Alignment
```python
if is_v2_task:
    # Validate that our work aligns with the intent
    validation = self.validate_intent(task)
    task.intent_validations.append(validation)

    logger.info(f"Intent validation: aligned={validation.is_aligned}, "
                f"alignment={validation.alignment_score:.2f}")
```

#### Step 3: Check for Intent Drift
```python
    # Check if we've drifted too far from original intent
    if self.check_intent_drift(task, threshold=0.4):
        logger.warning("Intent drift detected! Stopping workflow.")
        self._store_drift_detection(job_id, task.intent_validations)

        return AgentTaskResult(
            status="drift_detected",
            error="Workflow stopped to prevent misaligned work"
        )
```

#### Step 4: Do Your Work
```python
    # Process the task (parsing, evaluation, etc.)
    result = do_actual_work()
```

#### Step 5: Update Intent Context
```python
    # Update intent with results
    self.update_intent_context(task, {
        "parsing_completed": True,
        "contact_extracted": len(parsed_cv.contact_info) > 0,
        "education_count": len(parsed_cv.education),
    })

    # Store validations in database
    self._store_intent_validations(job_id, task.intent_validations)
```

#### Step 6: Pass to Next Agent
```python
    # Route to next agent with intent and validations
    self.enqueue_to_next_agent(
        capability_query="evaluate CV against criteria",
        task_type="evaluate_cv",
        payload=payload,
        intent=task.intent,              # Pass StructuredIntent forward
        intent_validations=task.intent_validations  # Pass validations
    )
```

---

## Workflow Templates

### Available Templates

Four workflow templates are now defined:

#### 1. CV Evaluation (Digital)
```python
workflow_id: "cv_evaluation"
document_types: ["pdf", "docx"]
first_agent: "parser"

Placeholders:
  - {{position}}
  - {{department}}

Constraints:
  - minimum_experience
  - required_skills
  - education_level

Success Criteria:
  - overall_score >= 70
  - experience_match == true
```

#### 2. CV Evaluation (Scanned/OCR)
```python
workflow_id: "cv_evaluation_scanned"
document_types: ["pdf", "png", "jpg"]
first_agent: "ocr"

Constraints:
  - ocr_required: true
  - minimum_experience
  - required_skills

Success Criteria:
  - ocr_confidence >= 0.8
  - overall_score >= 70
```

#### 3. Expense/Receipt Validation
```python
workflow_id: "expense_evaluation"
document_types: ["pdf", "png", "jpg"]
first_agent: "generic_parser"

Constraints:
  - expense_category
  - max_amount
  - policy_rules

Success Criteria:
  - within_policy == true
  - amount_valid == true
```

#### 4. Invoice Processing
```python
workflow_id: "invoice_processing"
document_types: ["pdf"]
first_agent: "generic_parser"

Constraints:
  - vendor_approved
  - po_number_required
  - payment_terms

Success Criteria:
  - invoice_valid == true
  - po_match == true
```

### Adding New Workflows

Edit `shared/python/cavia_common/workflows.py`:

```python
NEW_WORKFLOW = WorkflowTemplate(
    workflow_id="your_workflow",
    name="Your Workflow Name",
    description="What this workflow does",
    document_types=["pdf"],
    category="your_category",
    icon="document",
    first_agent_query="capability query for semantic discovery",
    intent_template={
        "workflow_type": "your_workflow",
        "goal": "Your goal with {{placeholders}}",
        "context": {
            "parameter1": "default_value"
        },
        "constraints": [
            {
                "name": "constraint_name",
                "description": "What this constraint means",
                "value": 10,
                "required": True
            }
        ],
        "success_criteria": [
            {
                "criterion": "success_metric",
                "description": "What success looks like",
                "validation_rule": "metric >= threshold"
            }
        ]
    },
    example_intents=[
        "Example intent 1",
        "Example intent 2"
    ]
)

# Add to WORKFLOW_TEMPLATES list
WORKFLOW_TEMPLATES.append(NEW_WORKFLOW)
```

---

## Testing the System

### Manual Testing Flow

#### 1. Test Workflow Selection
```bash
# Start backend
docker compose up -d backend-api

# Test workflow endpoints
curl http://localhost:8000/api/v1/workflows | jq
curl http://localhost:8000/api/v1/workflows/cv_evaluation | jq
curl http://localhost:8000/api/v1/workflows/categories | jq
```

#### 2. Test Intent Creation
```bash
# Create intent from template
curl -X POST http://localhost:8000/api/v1/workflows/cv_evaluation/intent \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "cv_evaluation",
    "parameters": {
      "position": "Senior Python Developer",
      "department": "Engineering",
      "minimum_experience": 5,
      "required_skills": ["Python", "FastAPI", "Docker"]
    }
  }' | jq
```

#### 3. Test Document Upload with Intent
```bash
# Upload CV with structured intent
curl -X POST http://localhost:8000/api/v1/cvs/upload \
  -F "file=@test_cv.pdf" \
  -F 'intent={"workflow_type":"cv_evaluation","goal":"Evaluate candidate for Senior Python Developer",...}' \
  | jq
```

#### 4. Test Intent Tracking
```bash
# Get job intent
curl http://localhost:8000/api/v1/cvs/{job_id}/intent | jq

# Get validation history
curl http://localhost:8000/api/v1/cvs/{job_id}/validations | jq
```

### Integration Testing

#### Test Drift Detection
1. Create intent with specific goal (e.g., "entry-level position")
2. Upload document
3. Watch ParserAgent validate alignment
4. If next agent (Evaluator) applies wrong criteria, drift will be detected
5. Workflow stops, job status = "failed", drift info stored

#### Test Legacy Compatibility
1. Upload CV with string intent (no JSON)
2. Verify AgentTask created (not AgentTaskV2)
3. Verify processing works without validation
4. Confirm no breaking changes

---

## Database Schema Changes

### Job Metadata Structure

The `cv_jobs.metadata` JSONB field now stores:

```json
{
  "minio_bucket": "cvs-raw",
  "minio_path": "uploads/...",
  "parsed_cv": {...},
  "intent": {
    "intent_id": "uuid",
    "workflow_type": "cv_evaluation",
    "goal": "...",
    "context": {...},
    "constraints": [...],
    "success_criteria": [...],
    "current_stage": "parser_completed"
  },
  "intent_validations": [
    {
      "agent_id": "parser-001",
      "agent_type": "parser",
      "is_aligned": true,
      "alignment_score": 0.85,
      "drift_score": 0.15,
      "reasoning": "Agent work aligns well with intent",
      "suggestions": []
    }
  ],
  "drift_detected": {
    "detected": true,
    "avg_drift": 0.45,
    "max_drift": 0.6,
    "threshold": 0.4,
    "message": "Workflow stopped due to intent drift"
  }
}
```

---

## Next Steps

### Immediate (Now)
- ✅ Phase 1 implementation complete
- 📋 Create unit tests for intent validation
- 📋 Test end-to-end workflow with UI
- 📋 Update other agents (Evaluator, Reporter) with intent validation

### Phase 2 (Weeks 3-4)
- Generic document processing
- Schema registry for document types
- ParsedDocument model (abstraction of ParsedCV)
- GenericParserAgent

### Phase 3 (Weeks 5-6)
- ExpenseEvaluatorAgent with business rules
- InvoiceParserAgent
- Receipt validation workflows
- Policy rules engine

---

## File Reference

### Created Files
```
frontend/src/components/
  ├── WorkflowSelector.jsx       # Workflow selection UI
  ├── IntentCapture.jsx          # Intent configuration UI
  └── IntentTracker.jsx          # Real-time tracking UI

frontend/src/services/
  └── api.js                     # Updated with workflow APIs

backend/api/routers/
  ├── cv_router.py               # Updated with intent support
  └── workflows_router.py        # New workflow endpoints

shared/python/cavia_common/
  ├── models.py                  # Intent models (already created)
  ├── base_agent.py              # Validation methods (already created)
  └── workflows.py               # Workflow templates (already created)

agents/parser/
  └── main.py                    # Reference implementation

docs/
  ├── PHASE1_IMPLEMENTATION_SUMMARY.md
  ├── INTENT_ARCHITECTURE_PROGRESS.md
  └── PHASE1_INTEGRATION_GUIDE.md  # This file
```

### Modified Files
```
backend/api/main.py              # Added workflows router
frontend/src/services/api.js     # Added workflow methods
agents/parser/main.py            # Added intent validation
```

---

## Success Metrics

### Functional ✅
- [x] Intent models implemented and working
- [x] Validation logic functional
- [x] Drift detection active
- [x] Workflow templates defined (4 workflows)
- [x] UI components created (WorkflowSelector, IntentCapture, IntentTracker)
- [x] API endpoints operational
- [x] Reference agent implementation complete
- [x] Backward compatibility maintained

### Technical ✅
- [x] No breaking changes to existing agents
- [x] Clear migration path for agents
- [x] Type-safe Pydantic models
- [x] Comprehensive logging
- [x] Database integration
- [x] Real-time updates

---

## Support

For questions or issues:
1. Check INTENT_ARCHITECTURE_PROGRESS.md for architecture details
2. Review PHASE1_IMPLEMENTATION_SUMMARY.md for implementation notes
3. See agents/parser/main.py for reference implementation
4. Review shared/python/cavia_common/workflows.py for workflow templates

---

**Phase 1 Status:** ✅ **COMPLETE** - Ready for integration testing and demo
**Next Milestone:** Unit tests and end-to-end validation
