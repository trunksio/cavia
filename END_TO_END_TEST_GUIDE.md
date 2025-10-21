# CAVIA: End-to-End Pure AOA Test Guide

This guide demonstrates the complete CV processing workflow through the Pure Agent-Oriented Architecture.

---

## 🎯 What You'll See

### Pure AOA Agent Chain
```
Backend API → Parser → Evaluator → Reporter → DB-Writer → Database
            ↓         ↓           ↓           ↓
         semantic  semantic    semantic    semantic
         discovery discovery   discovery   discovery
```

**No orchestrator!** Each agent autonomously discovers the next agent using semantic search.

---

## 📋 Test Scenario

**Candidate**: John Smith
**Position**: Senior Sales Manager
**Experience**: 8+ years in B2B SaaS sales
**Key Achievements**:
- 145% quota attainment in 2023
- Managed team of 12 sales reps
- Grew territory revenue by 133%

---

## 🔍 What to Monitor

### 1. API Upload (Step 1)
```bash
curl -X POST http://localhost:8000/api/v1/cvs/upload \
  -F "file=@/tmp/john_smith_cv.pdf"
```

**Expected Response**:
```json
{
  "job_id": "uuid",
  "filename": "john_smith_cv.pdf",
  "status": "pending",
  "message": "CV uploaded successfully. Processing started."
}
```

**What Happens**:
- CV stored in MinIO (`cvs-raw` bucket)
- Job entry created in database (status: pending)
- Parser task enqueued directly (NO orchestrator!)

---

### 2. Parser Agent (Step 2)

**Monitor Logs**:
```bash
docker compose logs -f parser-agent
```

**What to Watch For**:

1. **Task Received**:
   ```
   {"event": "Starting CV parsing", "job_id": "xxx", "filename": "john_smith_cv.pdf"}
   ```

2. **Extraction**:
   ```
   {"event": "CV parsing completed successfully"}
   ```

3. **Semantic Discovery** (🔥 **KEY AOA MOMENT**):
   ```
   {"event": "Loading sentence transformers model"}  # Lazy-loading!
   {"event": "Discovered next agent", "capability": "evaluate CV against criteria", "agent_type": "evaluator"}
   ```

4. **Enqueue to Evaluator**:
   ```
   {"event": "Enqueued to evaluator via semantic discovery", "rq_job_id": "xxx"}
   ```

**What Parser Did**:
- Downloaded CV from MinIO
- Extracted: name, email, experience, education, skills
- **Autonomously discovered** evaluator (no hardcoded dependency!)
- Enqueued with intent: "Process CV and determine acceptance"
- Added "parser" to steps_completed

---

### 3. Evaluator Agent (Step 3)

**Monitor Logs**:
```bash
docker compose logs -f evaluator-agent
```

**What to Watch For**:

1. **Task Received**:
   ```
   {"event": "Evaluating CV", "job_id": "xxx"}
   ```

2. **Load Criteria**:
   ```
   {"event": "Loaded active criteria", "criteria_count": 3}
   ```

3. **Internal Loop Through Criteria** (🧠 **KEY INNOVATION**):
   ```
   {"event": "Evaluating criterion", "criterion": "Sales Experience"}
   {"event": "Calling LLM for evaluation with Instructor"}
   {"event": "Structured evaluation received", "reasoning_steps": 5, "sub_criteria": 4, "overall_score": 88}

   {"event": "Evaluating criterion", "criterion": "Communication Skills"}
   {"event": "Calling LLM for evaluation with Instructor"}
   {"event": "Structured evaluation received", "reasoning_steps": 4, "sub_criteria": 3, "overall_score": 82}

   {"event": "Evaluating criterion", "criterion": "Job Stability"}
   {"event": "Calling LLM for evaluation with Instructor"}
   {"event": "Structured evaluation received", "reasoning_steps": 3, "sub_criteria": 3, "overall_score": 75}
   ```

4. **Semantic Discovery** (🔥 **KEY AOA MOMENT**):
   ```
   {"event": "Discovered next agent", "capability": "generate final recommendation", "agent_type": "reporter"}
   ```

5. **Enqueue to Reporter**:
   ```
   {"event": "Enqueued to reporter via semantic discovery"}
   ```

**What Evaluator Did**:
- Loaded 3 active criteria from database
- FOR EACH criterion:
  - Built Chain-of-Thought prompt
  - Called Ollama via **Instructor** → StructuredEvaluation
  - Received 3-7 reasoning steps + 2-6 sub-criteria scores
  - Stored in database with metadata
- **Autonomously discovered** reporter
- Enqueued with all 3 evaluations
- Added "evaluator" to steps_completed

---

### 4. Reporter Agent (Step 4)

**Monitor Logs**:
```bash
docker compose logs -f reporter-agent
```

**What to Watch For**:

1. **Task Received** (Event-Driven!):
   ```
   {"event": "Generating evaluation report", "job_id": "xxx"}
   {"event": "Received evaluations from payload", "count": 3}  # No DB query!
   ```

2. **Synthesis**:
   ```
   {"event": "Calculating weighted aggregate score"}
   {"event": "Generating LLM synthesis"}
   ```

3. **Final Recommendation**:
   ```
   {"event": "Report generated", "recommendation": "SUITABLE", "overall_score": 82}
   ```

4. **Semantic Discovery** (🔥 **KEY AOA MOMENT**):
   ```
   {"event": "Discovered next agent", "capability": "persist job results", "agent_type": "db-writer"}
   ```

5. **Enqueue to DB-Writer**:
   ```
   {"event": "Enqueued to db-writer"}
   ```

**What Reporter Did**:
- Received all data from payload (pure event-driven!)
- Calculated weighted aggregate: (88×0.4) + (82×0.3) + (75×0.3) = 82.1
- Used LLM to synthesize final recommendation
- Recommendation: **SUITABLE** (score > 70 threshold)
- **Autonomously discovered** db-writer (non-agentic unit!)
- Enqueued final report
- Added "reporter" to steps_completed

---

### 5. DB-Writer (Step 5)

**Monitor Logs**:
```bash
docker compose logs -f db-writer
```

**What to Watch For**:

1. **Task Received**:
   ```
   {"event": "Processing database task", "task_type": "update_job_result"}
   ```

2. **Database Update**:
   ```
   {"event": "Job result updated", "job_id": "xxx", "status": "completed"}
   ```

**What DB-Writer Did**:
- Updated `cv_jobs` table
- Set status: "completed"
- Set result: {final_report with scores, recommendation}
- Set completed_at timestamp
- **Did NOT discover another agent** (non-agentic boundary!)

---

### 6. Query Results (Step 6)

**Check Final Result**:
```bash
curl http://localhost:8000/api/v1/jobs/{job_id} | python3 -m json.tool
```

**Expected Response**:
```json
{
  "job_id": "xxx",
  "filename": "john_smith_cv.pdf",
  "status": "completed",
  "result": {
    "overall_score": 82,
    "recommendation": "SUITABLE",
    "summary": "Strong sales professional with proven track record...",
    "evaluations": [
      {
        "criterion": "Sales Experience",
        "score": 88,
        "evidence": "8 years progressive sales experience, managed team of 12, exceeded quota by 145%",
        "reasoning_steps": [
          {"step_number": 1, "observation": "...", "analysis": "..."},
          ...
        ],
        "sub_criteria": [
          {"name": "Experience Duration", "score": 5, "evidence": "...", "reasoning": "..."},
          {"name": "Leadership Scale", "score": 4, "evidence": "...", "reasoning": "..."},
          ...
        ],
        "key_strengths": ["Strong leadership", "Quantified achievements"],
        "key_weaknesses": ["Limited international experience"]
      },
      {
        "criterion": "Communication Skills",
        "score": 82,
        ...
      },
      {
        "criterion": "Job Stability",
        "score": 75,
        ...
      }
    ],
    "strengths": [
      "Exceptional sales leadership (145% quota achievement)",
      "Progressive career growth from Account Manager to Senior Sales Manager",
      "Strong team management experience (12 direct reports)"
    ],
    "concerns": [
      "Moderate job stability (2 roles in 8 years)",
      "Limited international sales experience"
    ]
  },
  "completed_at": "2025-10-21T15:XX:XX"
}
```

---

## 🎓 Key Observations

### 1. Pure AOA - No Orchestrator
- ✅ Each agent autonomously discovered next agent
- ✅ No central coordinator
- ✅ Semantic discovery via pgvector
- ✅ Intent passed through entire chain
- ✅ Steps tracking showed: ["parser", "evaluator", "reporter"]

### 2. Lazy-Loading Pattern
- ✅ Sentence transformers loaded ONCE during registration
- ✅ RQ workers never loaded model (no hanging!)
- ✅ Only evaluator/reporter triggered lazy-load during discovery

### 3. Instructor + Chain-of-Thought
- ✅ Automatic Pydantic validation
- ✅ 3-7 reasoning steps per criterion
- ✅ 2-6 atomic sub-criteria per criterion
- ✅ No manual JSON parsing
- ✅ 3 automatic retries on failures

### 4. Event-Driven Architecture
- ✅ Reporter received data from payload (not database)
- ✅ DB-Writer as boundary between events and UI
- ✅ Pure queue-based coordination

---

## 📊 Performance Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| **Total Time** | ~30-45 seconds | Depends on LLM speed |
| **Parser** | ~2 seconds | PDF extraction |
| **Evaluator** | ~25-35 seconds | 3 criteria × LLM calls |
| **Reporter** | ~3-5 seconds | LLM synthesis |
| **DB-Writer** | <1 second | Simple DB update |

---

## 🚀 What Makes This Special

1. **Zero Hardcoded Dependencies**: Parser doesn't know "Evaluator" exists by name
2. **Semantic Capability Matching**: "evaluate CV" → finds agent with that capability
3. **Self-Organizing Chain**: Agents coordinate autonomously
4. **Production-Ready Patterns**: Lazy-loading, event-driven, boundary units
5. **Advanced LLM Integration**: Instructor + CoT + Atomic criteria
6. **Full Traceability**: Intent + steps tracking through entire chain

---

## 🔧 Troubleshooting

If something goes wrong, check these logs in order:

1. **Backend API**: `docker compose logs backend-api --tail=50`
2. **Parser**: `docker compose logs parser-agent --tail=50`
3. **Evaluator**: `docker compose logs evaluator-agent --tail=50`
4. **Reporter**: `docker compose logs reporter-agent --tail=50`
5. **DB-Writer**: `docker compose logs db-writer --tail=50`

**Common Issues**:
- Parser hanging: Check for "Loading sentence transformers" in worker context (should NOT happen with lazy-loading)
- Evaluator errors: Check Ollama is running (`curl http://localhost:11434/api/tags`)
- No semantic discovery: Check pgvector extension (`docker exec cavia-postgres psql -U cavia -c "\dx"`)

---

**Generated**: 2025-10-21
**System**: CAVIA v2.0.0 (Pure AOA)
