# CAVIA Architecture - Visual Reference

## Quick System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CAVIA: CV Processing via AOA                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  User Upload ──▶ Backend API ──▶ Parser ──▶ Evaluator ──▶ Reporter  │
│                                     │            │            │       │
│                                     │            │            │       │
│                                     ▼            ▼            ▼       │
│                              ChromaDB Discovery Service               │
│                                     │                                 │
│                                     ▼                                 │
│                         Ollama LLM (GPU-Accelerated)                  │
│                                                                       │
│  Storage: PostgreSQL + MinIO + Redis + ChromaDB                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Core Architectural Pattern

### Pure Agent-Oriented Architecture (AOA)

```
Traditional Workflow (Hardcoded):
──────────────────────────────────
Service A ─────┬───▶ Service B ─────┬───▶ Service C
               │                     │
           (direct call)        (direct call)
         = Tight coupling    = Brittle system


CAVIA AOA (Semantic Discovery):
────────────────────────────────
Agent A ───────┬───▶ Agent B ───────┬───▶ Agent C
               │                     │
          (discover via           (discover via
           capability)             capability)
         = Loose coupling       = Flexible system

Discovery Process:
  1. Query: "Who can evaluate CVs?"
  2. ChromaDB: Vector similarity search
  3. Result: Evaluator Agent (queue: cv-evaluation)
  4. Enqueue task to discovered agent
```

## Agent Communication Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                  Semantic Discovery Pattern                          │
└─────────────────────────────────────────────────────────────────────┘

Step 1: Agent Registration (Startup)
─────────────────────────────────────
    ┌──────────┐
    │  Agent   │
    └────┬─────┘
         │
         │ Register capabilities:
         │ "I can evaluate CV against criteria using LLM"
         │
         ▼
    ┌─────────────────────┐
    │  ChromaDB Registry  │
    │                     │
    │  - Generate         │──── Sentence transformer
    │    embedding        │     converts text to
    │  - Store:           │     384-dim vector
    │    * agent_id       │
    │    * capabilities   │
    │    * queue_name     │
    │    * embedding      │
    └─────────────────────┘


Step 2: Agent Discovery (Runtime)
──────────────────────────────────
    ┌──────────┐
    │ Agent A  │
    └────┬─────┘
         │
         │ Discover next agent:
         │ "evaluate CV against job criteria"
         │
         ▼
    ┌─────────────────────┐
    │  ChromaDB Registry  │
    │                     │
    │  1. Embed query     │
    │  2. Vector search   │
    │  3. Find closest:   │
    │     similarity=0.95 │
    │  4. Return:         │
    │     - agent_type    │
    │     - queue_name    │
    └─────┬───────────────┘
          │
          │ Result: {
          │   agent_type: "evaluator",
          │   queue_name: "cv-evaluation"
          │ }
          ▼
    ┌──────────┐
    │ Agent A  │──── Enqueue task to
    └──────────┘     discovered queue


Step 3: Task Processing
────────────────────────
    ┌────────────────┐
    │ Redis RQ Queue │
    │ cv-evaluation  │
    └────────┬───────┘
             │
             │ Task: {
             │   job_id,
             │   parsed_cv_path,
             │   criteria
             │ }
             ▼
    ┌──────────────┐
    │  Evaluator   │
    │    Agent     │
    │              │
    │  1. Dequeue  │
    │  2. Process  │
    │  3. Store    │
    │  4. Discover │──── Repeat cycle
    │  5. Enqueue  │
    └──────────────┘
```

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    End-to-End Data Flow                              │
└─────────────────────────────────────────────────────────────────────┘

┌────────┐
│  User  │
└───┬────┘
    │
    │ 1. POST /api/v1/cvs/upload
    │    - File: cv.pdf
    │    - Criteria: [{...}, {...}]
    │
    ▼
┌────────────────┐
│  Backend API   │
│                │
│ • Upload to    │──┐
│   MinIO        │  │ Raw Storage
│ • Create job   │  │ cvs-raw/uuid/cv.pdf
│ • Enqueue      │──┘
└────────┬───────┘
         │
         │ 2. Enqueue to cv-parsing
         │
         ▼
    ╔════════════════════════╗
    ║    Parser Agent        ║
    ╠════════════════════════╣
    ║ • Download from MinIO  ║
    ║ • Extract text (PyPDF2)║
    ║ • Parse structured data║
    ║ • Validate with Pydantic║
    ╚════════┬═══════════════╝
             │
             │ 3. Upload parsed_cv.json
             │
             ▼
    ┌──────────────────┐
    │  MinIO Storage   │
    │  cvs-processed/  │──── Processed Data
    │  parsed/{uuid}/  │     parsed_cv.json
    └──────────────────┘
             │
             │ 4. Discover: "evaluate CV..."
             │    → Result: evaluator, cv-evaluation
             │
             ▼
    ╔════════════════════════╗
    ║   Evaluator Agent      ║
    ╠════════════════════════╣
    ║ For each criterion:    ║
    ║  • Load parsed CV      ║
    ║  • Call Ollama LLM ────╬───▶ ┌──────────────┐
    ║  • Get structured      ║     │ Ollama (GPU) │
    ║    evaluation          ║◀────┤ gpt-oss:20b  │
    ║  • Store in DB         ║     └──────────────┘
    ╚════════┬═══════════════╝
             │
             │ 5. INSERT INTO cv_evaluations
             │    (score, confidence, evidence, reasoning)
             │
             ▼
    ┌──────────────────┐
    │   PostgreSQL     │
    │ cv_evaluations   │──── Evaluation Results
    │ table            │
    └──────────────────┘
             │
             │ 6. Discover: "generate report..."
             │    → Result: reporter, cv-reporting
             │
             ▼
    ╔════════════════════════╗
    ║    Reporter Agent      ║
    ╠════════════════════════╣
    ║ • Load all evaluations ║
    ║ • Call Ollama for  ────╬───▶ Generate summary
    ║   summary              ║     and recommendations
    ║ • Create PDF (ReportLab)║
    ║ • Upload to MinIO      ║
    ╚════════┬═══════════════╝
             │
             │ 7. Upload report.pdf
             │
             ▼
    ┌──────────────────┐
    │  MinIO Storage   │
    │  agent-artifacts/│──── Final Report
    │  {uuid}/         │     report.pdf
    └──────────────────┘
             │
             │ 8. UPDATE jobs SET status='completed'
             │
             ▼
    ┌──────────────────┐
    │   PostgreSQL     │
    │   jobs table     │
    └──────────────────┘
```

## LLM Integration Pattern

```
┌─────────────────────────────────────────────────────────────────────┐
│              Centralized LLM Architecture                            │
└─────────────────────────────────────────────────────────────────────┘

Multiple Agents ──────▶ Single Ollama Service ──────▶ Single GPU
                        (Shared Resource)

┌──────────────┐
│ Evaluator    │───┐
│ Agent 1      │   │
└──────────────┘   │
                   │
┌──────────────┐   │     ┌─────────────────────────┐
│ Evaluator    │───┤────▶│   Ollama Service        │
│ Agent 2      │   │     │   :11434                │
└──────────────┘   │     │                         │
                   │     │ • Model: gpt-oss:20b    │
┌──────────────┐   │     │ • Size: 13 GB           │
│ Reporter     │───┘     │ • GPU: NVIDIA GB10      │
│ Agent        │         │ • Latency: ~32s/request │
└──────────────┘         └────────┬────────────────┘
                                  │
                                  │ GPU Acceleration
                                  ▼
                         ┌─────────────────┐
                         │ NVIDIA GB10     │
                         │ (Blackwell)     │
                         │                 │
                         │ CUDA 13.0       │
                         │ Memory: 193 MiB │
                         └─────────────────┘

Benefits:
─────────
✓ Single model in memory (efficient)
✓ Shared GPU utilization
✓ Centralized model updates
✓ No agent-side PyTorch dependencies
✓ 5-9x faster than CPU
```

## Structured LLM Output

```
┌─────────────────────────────────────────────────────────────────────┐
│         Instructor + Pydantic Structured Outputs                     │
└─────────────────────────────────────────────────────────────────────┘

Request:
────────
evaluator_agent.py:
  result = instructor_client.chat.completions.create(
      model="gpt-oss:20b",
      messages=[
          {"role": "system", "content": "You are a CV evaluator..."},
          {"role": "user", "content": f"Evaluate: {cv_data}"}
      ],
      response_model=StructuredEvaluation  # ← Pydantic model
  )

Pydantic Schema:
────────────────
class StructuredEvaluation(BaseModel):
    reasoning_steps: List[ReasoningStep]      # Array of objects
    sub_criteria: List[SubCriterion]          # Array of objects
    overall_score: int                        # Integer 0-100
    confidence: float                         # Float 0-1
    key_strengths: List[str]                  # Array of strings
    key_weaknesses: List[str]                 # Array of strings
    summary: str                              # String

LLM Response (Validated):
─────────────────────────
{
  "reasoning_steps": [
    {
      "step_number": 1,
      "observation": "Candidate has 7 years experience",
      "analysis": "Meets minimum requirement of 5 years",
      "name": "Experience Duration"
    }
  ],
  "sub_criteria": [
    {
      "name": "Years of Experience",
      "score": 95,
      "evidence": "7+ years at major tech companies",
      "reasoning": "Far exceeds 5-year requirement"
    }
  ],
  "overall_score": 92,         # ← Type-safe integer
  "confidence": 0.95,          # ← Type-safe float
  "key_strengths": [
    "Strong technical background",
    "Leadership experience"
  ],
  "key_weaknesses": [
    "No industry-specific certifications"
  ],
  "summary": "Excellent candidate with strong background..."
}

Why This Works:
───────────────
✓ gpt-oss:20b (20B params) understands JSON schemas
✓ Instructor enforces Pydantic validation
✓ Retries on invalid responses (max 3)
✓ Type-safe data for downstream processing
✗ Smaller models (<10B) often fail validation
```

## Deployment Topology

```
┌─────────────────────────────────────────────────────────────────────┐
│               Docker Compose Deployment                              │
└─────────────────────────────────────────────────────────────────────┘

Host Machine (NVIDIA DGX Spark)
════════════════════════════════
├── GPU: NVIDIA GB10 (Blackwell)
├── OS: Linux 6.11.0-1016-nvidia
└── Docker Engine + Compose

Container Network: cavia-network (bridge)
══════════════════════════════════════════

┌─────────────────────────────────────────────────────────────────┐
│  Storage Layer                                                   │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ postgres:    │  │ redis:       │  │ minio:       │          │
│  │ 5432         │  │ 6379         │  │ 9000, 9001   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│         │                 │                   │                  │
│         ▼                 ▼                   ▼                  │
│  postgres-data      redis-data          minio-data              │
│  (volume)           (volume)            (volume)                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  Intelligence Layer                                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐         ┌──────────────────┐             │
│  │ agent-registry:  │         │ ollama:          │             │
│  │ 8001             │         │ 11434            │             │
│  │ (ChromaDB)       │         │ (GPU-enabled)    │             │
│  └──────────────────┘         └────────┬─────────┘             │
│         │                              │                        │
│         ▼                              ▼                        │
│  chromadb-data                  ollama-data                     │
│  (vector DB)                    (models: 13 GB)                 │
│                                       │                         │
│                                       └────▶ GPU passthrough    │
│                                             (nvidia runtime)    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  Service Layer                                                   │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌──────────────────┐                    │
│  │ backend-api:     │  │ frontend:        │                    │
│  │ 8000 (FastAPI)   │  │ 3000 (React)     │                    │
│  └──────────────────┘  └──────────────────┘                    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  Agentic Layer                                                   │
├─────────────────────────────────────────────────────────────────┤
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────┐ │
│  │ parser-    │  │ evaluator- │  │ reporter-  │  │ db-      │ │
│  │ agent      │  │ agent      │  │ agent      │  │ writer   │ │
│  └────────────┘  └────────────┘  └────────────┘  └──────────┘ │
│  (RQ workers listening on respective queues)                    │
└─────────────────────────────────────────────────────────────────┘

Scaling:
────────
docker compose up -d --scale evaluator-agent=3

┌────────────┐  ┌────────────┐  ┌────────────┐
│ evaluator-1│  │ evaluator-2│  │ evaluator-3│
└────────────┘  └────────────┘  └────────────┘
       │                │                │
       └────────────────┴────────────────┘
                        │
                   cv-evaluation
                      (queue)
```

## Agent Lifecycle State Machine

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Agent State Transitions                           │
└─────────────────────────────────────────────────────────────────────┘

                    ┌──────────────┐
                    │  Container   │
                    │   Start      │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                ┌───│   STARTING   │
                │   └──────────────┘
                │          │
                │          │ Initialize:
                │          │  - Load config
                │          │  - Connect to services
                │          │
                │          ▼
                │   ┌──────────────┐
                │   │ REGISTERING  │──────────┐
                │   └──────────────┘          │
                │          │                  │ Registration
                │          │ POST /register   │ failed
                │          │                  │
                │          ▼                  ▼
                │   ┌──────────────┐   ┌──────────────┐
                │   │   ACTIVE     │   │    ERROR     │
                │   │              │   │              │
                │   │ • Heartbeat  │   │ Exit code: 1 │
                │   │ • RQ Worker  │   └──────────────┘
                │   │ • Process    │
                │   │   tasks      │
                │   └──────┬───────┘
                │          │
                │          │ SIGTERM/SIGINT
                │          │
                │          ▼
                │   ┌──────────────┐
                └──▶│  STOPPING    │
                    │              │
                    │ • Stop       │
                    │   heartbeat  │
                    │ • Finish     │
                    │   current    │
                    │   task       │
                    │ • Close      │
                    │   connections│
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   INACTIVE   │
                    │              │
                    │ Exit code: 0 │
                    └──────────────┘
```

## Key Architectural Decisions

### Decision Matrix

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Discovery Mechanism** | ChromaDB vector search | • Semantic matching<br>• No hardcoded routes<br>• Dynamic agent addition |
| **Communication** | Redis RQ queues | • Async processing<br>• Built-in retries<br>• Failure isolation |
| **LLM Architecture** | Centralized Ollama | • Single GPU instance<br>• Model sharing<br>• Easy updates |
| **Structured Outputs** | Instructor + Pydantic | • Type safety<br>• Validation<br>• Retries |
| **Agent Framework** | Python RQ workers | • Simple<br>• Mature<br>• Redis integration |
| **Storage** | MinIO + PostgreSQL | • S3-compatible<br>• Relational + vector<br>• Proven stack |

---

## Performance Metrics (Production)

```
┌─────────────────────────────────────────────────────────────────────┐
│                  System Performance Profile                          │
└─────────────────────────────────────────────────────────────────────┘

End-to-End Latency (3 criteria evaluation):
════════════════════════════════════════════

┌────────────────────────────────────────────────────────────────┐
│                                                                 │
│  0s        30s       60s       90s      120s      150s      180s│
│  │─────────│─────────│─────────│─────────│─────────│─────────│ │
│  │         │         │         │         │         │         │ │
│  │ Upload  │ Parse   │ Eval 1  │ Eval 2  │ Eval 3  │ Report  │ │
│  │         │         │         │         │         │         │ │
│  │ 100ms   │ 150ms   │  32s    │  32s    │  32s    │  45s    │ │
│  │         │         │  (GPU)  │  (GPU)  │  (GPU)  │  (GPU)  │ │
│  └─────────┴─────────┴─────────┴─────────┴─────────┴─────────┘ │
│                                                                 │
│  Total: ~2 minutes 20 seconds                                   │
└─────────────────────────────────────────────────────────────────┘

Throughput (per minute):
════════════════════════

Parser:    ~100 CVs/min  ████████████████████████████████████████
Evaluator:   ~2 CVs/min  ████
Reporter:    ~1 CV/min   ██

Bottleneck: LLM inference (GPU-bound)
Solution: Scale evaluator agents or add GPUs

GPU Utilization:
════════════════

Idle:        10W, 0%
Inference:  ~50W, 80-100% utilization
Memory:      193 MiB per request
Speedup:     5-9x vs CPU

Model Performance (gpt-oss:20b):
═════════════════════════════════

Structured Output Success Rate: 100%
Pydantic Validation Failures:   0%
Average Tokens/Request:          ~2000 tokens
Latency:                         32s per criterion
```

---

**Document Version**: 1.0
**Last Updated**: 2025-10-22
**System**: CAVIA - CV Analysis via Intelligent Agents
**Architecture**: Pure Agent-Oriented (AOA)
