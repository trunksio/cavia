# Phase 1 - Quick Start Guide

## Services Running ✅

All required services are now running:
- ✅ Backend API (localhost:8000)
- ✅ Parser Agent
- ✅ Agent Registry
- ✅ PostgreSQL, Redis, MinIO, Ollama

---

## Testing Phase 1 Features

### 1. List Available Workflows

```bash
curl http://localhost:8000/api/v1/workflows | jq
```

This shows 4 workflows:
- `cv_evaluation` - Digital CV evaluation
- `cv_evaluation_scanned` - Scanned CV with OCR
- `expense_evaluation` - Receipt/expense validation
- `invoice_processing` - Invoice approval workflow

### 2. Get Specific Workflow

```bash
curl http://localhost:8000/api/v1/workflows/cv_evaluation | jq
```

Shows full workflow template with:
- Intent template with placeholders
- Constraints (min experience, required skills, etc.)
- Success criteria (score >= 70, etc.)
- Example intents

### 3. List Categories

```bash
curl http://localhost:8000/api/v1/workflows/categories | jq
```

Returns: `["finance", "hr"]`

### 4. Create Intent from Template

```bash
curl -X POST http://localhost:8000/api/v1/workflows/cv_evaluation/intent \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "cv_evaluation",
    "parameters": {
      "position": "Senior Python Developer",
      "department": "Engineering",
      "minimum_experience": 5,
      "required_skills": ["Python", "FastAPI", "Docker", "PostgreSQL"]
    }
  }' | jq
```

This returns a complete `StructuredIntent` ready for upload.

### 5. Upload CV with Structured Intent

First, create an intent and save it:

```bash
INTENT=$(curl -s -X POST http://localhost:8000/api/v1/workflows/cv_evaluation/intent \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "cv_evaluation",
    "parameters": {
      "position": "Senior Python Developer",
      "department": "Engineering",
      "minimum_experience": 5,
      "required_skills": ["Python", "FastAPI", "Docker"]
    }
  }')

# Upload CV with intent
curl -X POST http://localhost:8000/api/v1/cvs/upload \
  -F "file=@/path/to/your/cv.pdf" \
  -F "intent=$INTENT" | jq
```

**Response will include:**
```json
{
  "job_id": "uuid-here",
  "filename": "cv.pdf",
  "status": "pending",
  "message": "CV uploaded successfully. Processing started.",
  "created_at": "2025-10-26T..."
}
```

### 6. Track Intent Validation (New Endpoints)

```bash
# Get job's structured intent
curl http://localhost:8000/api/v1/cvs/{job_id}/intent | jq

# Get validation history (from all agents in chain)
curl http://localhost:8000/api/v1/cvs/{job_id}/validations | jq
```

**Validations Response:**
```json
[
  {
    "agent_id": "parser-001",
    "agent_type": "parser",
    "is_aligned": true,
    "alignment_score": 0.85,
    "drift_score": 0.15,
    "reasoning": "Agent work aligns well with intent goal",
    "suggestions": []
  }
]
```

### 7. Check Job Status

```bash
curl http://localhost:8000/api/v1/jobs/{job_id}/status | jq
```

---

## What Happens When You Upload

### With Structured Intent (New - Phase 1):

```
1. User uploads CV + StructuredIntent
2. Backend stores intent in job metadata
3. Creates AgentTaskV2 with intent
4. Routes to ParserAgent via semantic discovery
5. ParserAgent:
   ✅ Validates intent alignment (score: 0.85)
   ✅ Checks drift (0.15 < 0.4 threshold) ✓
   ✅ Parses CV
   ✅ Updates intent context with results
   ✅ Stores validations in DB
   ✅ Routes to next agent with intent
6. User can track validations in real-time
```

### With Legacy String Intent:

```
1. User uploads CV + string intent
2. Creates AgentTask (legacy)
3. Routes to ParserAgent
4. ParserAgent processes normally
5. No validation or drift detection
6. Backward compatible!
```

---

## Testing Drift Detection

To see drift detection in action, you'd need:
1. Upload with entry-level intent
2. Have evaluator agent accidentally apply senior criteria
3. System will detect drift and stop workflow
4. Job status = "failed", drift info stored

Example drift intent:
```bash
curl -X POST http://localhost:8000/api/v1/workflows/cv_evaluation/intent \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "cv_evaluation",
    "parameters": {
      "position": "Entry-Level Developer",
      "minimum_experience": 0,
      "required_skills": ["Python"]
    }
  }'
```

---

## Next Steps to See UI

The UI components are ready but need to be integrated into your frontend app:

### Option 1: Test UI Components in Isolation

You can create a test page:

```jsx
// frontend/src/pages/TestPhase1.jsx
import WorkflowSelector from '../components/WorkflowSelector';
import IntentCapture from '../components/IntentCapture';
import IntentTracker from '../components/IntentTracker';

export default function TestPhase1() {
  const [step, setStep] = useState('select');
  const [workflow, setWorkflow] = useState(null);
  const [jobId, setJobId] = useState(null);

  if (step === 'select') {
    return (
      <WorkflowSelector
        onWorkflowSelect={(wf) => {
          setWorkflow(wf);
          setStep('capture');
        }}
      />
    );
  }

  if (step === 'capture') {
    return (
      <IntentCapture
        workflow={workflow}
        onIntentCreated={(intent) => {
          // Upload file with intent
          // Set jobId
          setStep('track');
        }}
        onBack={() => setStep('select')}
      />
    );
  }

  return <IntentTracker jobId={jobId} />;
}
```

### Option 2: Direct API Testing

You can test everything via curl/Postman while UI is being integrated.

---

## Verification Checklist

Test each feature:

- [ ] List workflows: `curl http://localhost:8000/api/v1/workflows`
- [ ] Get specific workflow: `curl http://localhost:8000/api/v1/workflows/cv_evaluation`
- [ ] Create intent from template
- [ ] Upload CV with structured intent
- [ ] Get job intent: `curl http://localhost:8000/api/v1/cvs/{job_id}/intent`
- [ ] Get validations: `curl http://localhost:8000/api/v1/cvs/{job_id}/validations`
- [ ] Check that ParserAgent validates intent (check logs)
- [ ] Verify backward compatibility (upload with string intent)

---

## Logs to Monitor

Watch agent processing:
```bash
# Parser agent logs (shows intent validation)
docker compose logs -f parser-agent

# Backend API logs
docker compose logs -f backend-api

# Agent registry logs (semantic discovery)
docker compose logs -f agent-registry
```

---

## Files to Review

**UI Components:**
- `frontend/src/components/WorkflowSelector.jsx`
- `frontend/src/components/IntentCapture.jsx`
- `frontend/src/components/IntentTracker.jsx`

**Backend:**
- `backend/api/routers/workflows_router.py` (workflow endpoints)
- `backend/api/routers/cv_router.py` (intent upload support)

**Agent Reference:**
- `agents/parser/main.py` (shows how to use intent validation)

**Documentation:**
- `PHASE1_INTEGRATION_GUIDE.md` (complete guide)
- `INTENT_ARCHITECTURE_PROGRESS.md` (architecture details)

---

## Quick Demo Script

```bash
# 1. List workflows
echo "=== Available Workflows ==="
curl -s http://localhost:8000/api/v1/workflows | jq -r '.[].name'

# 2. Get CV evaluation workflow
echo -e "\n=== CV Evaluation Workflow ==="
curl -s http://localhost:8000/api/v1/workflows/cv_evaluation | jq '.name, .description'

# 3. Create intent
echo -e "\n=== Creating Intent ==="
INTENT=$(curl -s -X POST http://localhost:8000/api/v1/workflows/cv_evaluation/intent \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "cv_evaluation",
    "parameters": {
      "position": "Senior Python Developer",
      "minimum_experience": 5,
      "required_skills": ["Python", "FastAPI", "Docker"]
    }
  }')
echo "$INTENT" | jq '.goal'

# 4. Upload CV (replace with your CV file)
# curl -X POST http://localhost:8000/api/v1/cvs/upload \
#   -F "file=@your_cv.pdf" \
#   -F "intent=$INTENT"
```

---

## Troubleshooting

### Workflows endpoint returns 404
- Make sure backend-api container has latest code
- Rebuild: `docker compose build --no-cache backend-api`
- Restart: `docker compose restart backend-api`

### Intent validation not showing
- Check parser-agent logs for validation messages
- Ensure you're using StructuredIntent (JSON), not string
- Verify job metadata contains intent

### Legacy uploads not working
- System should still accept string intents
- Check cv_router.py handles both formats
- Review error logs

---

**Phase 1 is ready for testing!** 🎉

Start with the workflow API tests, then try uploading with structured intents.
