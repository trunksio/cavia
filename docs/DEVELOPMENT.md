# Development Guide

This guide explains how to develop new Agentic Units and extend the CAVIA system.

## Table of Contents

1. [Setting Up Development Environment](#setting-up-development-environment)
2. [Creating a New Agent](#creating-a-new-agent)
3. [Testing Agents](#testing-agents)
4. [Debugging](#debugging)
5. [Best Practices](#best-practices)

---

## Setting Up Development Environment

### Prerequisites

```bash
# Install Python dependencies
cd shared/python
pip install -e ".[dev]"

# Install pre-commit hooks (optional)
pip install pre-commit
pre-commit install
```

### IDE Setup

**VS Code:**
```json
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "black"
}
```

---

## Creating a New Agent

### Step 1: Choose Agent Type

Determine your agent's role:
- `parser` - Extracts data from documents
- `evaluator` - Evaluates against criteria
- `orchestrator` - Coordinates other agents
- `reporter` - Generates reports
- `custom` - Any other specialized task

### Step 2: Create Agent Directory

```bash
# Create new agent directory
mkdir -p agents/myagent

# Copy template files
cp agents/template/main.py agents/myagent/
cp agents/template/requirements.txt agents/myagent/
cp agents/template/Dockerfile agents/myagent/
```

### Step 3: Implement Agent Class

Edit `agents/myagent/main.py`:

```python
from cavia_common import BaseAgent, AgentTask, AgentTaskResult, get_ollama_client

class MyAgent(BaseAgent):
    def __init__(self, agent_id=None):
        super().__init__(agent_id)
        self.ollama = get_ollama_client()  # If using LLM

    def get_agent_type(self) -> str:
        return "myagent"  # Must be unique

    def get_agent_info(self):
        return {
            "name": "My Custom Agent",
            "description": "Does something amazing",
            "capabilities": {
                "tasks": ["task_type_1", "task_type_2"],
                "version": "1.0.0"
            }
        }

    def process_task(self, task: AgentTask) -> AgentTaskResult:
        try:
            # Your task processing logic here
            if task.task_type == "task_type_1":
                result = self._handle_task_type_1(task.payload)
            else:
                raise ValueError(f"Unknown task: {task.task_type}")

            return AgentTaskResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                status="success",
                result=result
            )
        except Exception as e:
            self.logger.error("Task failed", error=str(e))
            return AgentTaskResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                status="error",
                error=str(e)
            )

    def _handle_task_type_1(self, payload):
        # Implement your logic
        # Use self.ollama for LLM inference
        # Use self.logger for logging
        return {"result": "success"}
```

### Step 4: Add Dependencies

Edit `agents/myagent/requirements.txt`:

```txt
# Add any additional packages
# Example:
PyPDF2==3.0.1
beautifulsoup4==4.12.0
```

### Step 5: Update Dockerfile

Edit `agents/myagent/Dockerfile`:

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY shared/python /shared
RUN pip install --no-cache-dir -e /shared

COPY agents/myagent/ /app/
RUN pip install --no-cache-dir -r requirements.txt

HEALTHCHECK --interval=30s --timeout=10s CMD python -c "import sys; sys.exit(0)"

CMD ["python", "main.py"]
```

### Step 6: Build and Test

```bash
# Build agent image
docker build -f agents/myagent/Dockerfile -t cavia-myagent .

# Run agent
docker run -it --rm \
  --name myagent-test \
  --network cavia_cavia-network \
  -e DATABASE_URL=postgresql://cavia:caviadev123@cavia-postgres:5432/cavia \
  -e REDIS_URL=redis://cavia-redis:6379/0 \
  -e OLLAMA_HOST=http://cavia-ollama:11434 \
  -e AGENT_ID=myagent-001 \
  cavia-myagent
```

### Step 7: Verify Registration

```bash
# Check agent is registered
curl http://localhost:8001/agents | jq '.[] | select(.agent_type=="myagent")'
```

---

## Testing Agents

### Unit Tests

Create `tests/test_myagent.py`:

```python
import pytest
from agents.myagent.main import MyAgent
from cavia_common import AgentTask

def test_agent_info():
    agent = MyAgent(agent_id="test-001")
    info = agent.get_agent_info()
    assert info["name"] == "My Custom Agent"
    assert "task_type_1" in info["capabilities"]["tasks"]

def test_process_task():
    agent = MyAgent(agent_id="test-001")
    task = AgentTask(
        task_id="task-001",
        task_type="task_type_1",
        payload={"test": "data"}
    )
    result = agent.process_task(task)
    assert result.status == "success"
```

Run tests:
```bash
pytest tests/test_myagent.py -v
```

### Integration Tests

Test with actual Redis queue:

```python
from cavia_common import get_redis_client

def test_agent_queue_processing():
    redis = get_redis_client()

    # Enqueue task
    job = redis.enqueue_task(
        queue_name="myagent-queue",
        func=lambda: {"test": "result"},
        job_id="test-job-001"
    )

    # Wait for processing
    import time
    time.sleep(2)

    # Check result
    result = redis.get_job_result(job.id)
    assert result is not None
```

---

## Debugging

### View Agent Logs

```bash
# View logs for running agent
docker logs -f <container-id>

# Or by name
docker logs -f myagent-test
```

### Interactive Shell in Agent Container

```bash
# Start container with shell
docker run -it --rm \
  --network cavia_cavia-network \
  -e DATABASE_URL=postgresql://cavia:caviadev123@cavia-postgres:5432/cavia \
  -e REDIS_URL=redis://cavia-redis:6379/0 \
  cavia-myagent /bin/bash

# Inside container
python
>>> from main import MyAgent
>>> agent = MyAgent("debug-001")
>>> agent.get_agent_info()
```

### Debug Queue Issues

```bash
# Check RQ Dashboard
open http://localhost:9181

# Or use RQ CLI
docker-compose exec redis redis-cli
> KEYS *rq*
> LLEN rq:queue:myagent-queue
```

### Database Debugging

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U cavia -d cavia

# Check registered agents
SELECT agent_id, name, status FROM agent_registry;

# Check job status
SELECT job_id, status, error_message FROM cv_jobs;
```

---

## Best Practices

### 1. Logging

Always use structured logging:

```python
self.logger.info("Processing started", task_id=task.task_id, user_id=user)
self.logger.error("Processing failed", task_id=task.task_id, error=str(e))
```

### 2. Error Handling

Always catch and return errors in AgentTaskResult:

```python
try:
    result = process_something()
    return AgentTaskResult(status="success", result=result, ...)
except Exception as e:
    return AgentTaskResult(status="error", error=str(e), ...)
```

### 3. Timeouts

Set appropriate timeouts for LLM calls:

```python
self.ollama.generate(prompt, timeout=30)  # seconds
```

### 4. Resource Cleanup

Clean up resources in finally blocks:

```python
try:
    file = open_file()
    process(file)
finally:
    file.close()
```

### 5. Agent Capabilities

Document capabilities clearly:

```python
"capabilities": {
    "tasks": ["parse_pdf", "parse_docx"],  # What it can do
    "input_formats": ["pdf", "docx"],      # What it accepts
    "output_format": "ParsedCV",           # What it returns
    "version": "1.0.0",
    "max_file_size_mb": 10,
}
```

### 6. Idempotency

Make task processing idempotent when possible:

```python
def process_task(self, task):
    # Check if already processed
    if self._is_cached(task.task_id):
        return self._get_cached_result(task.task_id)

    # Process
    result = self._do_work(task)

    # Cache result
    self._cache_result(task.task_id, result)
    return result
```

### 7. Testing with LLMs

Mock Ollama in tests:

```python
from unittest.mock import Mock, patch

def test_with_mocked_llm():
    with patch('cavia_common.get_ollama_client') as mock_ollama:
        mock_ollama.return_value.generate.return_value = "Test response"
        agent = MyAgent()
        result = agent.process_task(...)
        assert result.status == "success"
```

---

## Common Patterns

### Pattern 1: Multi-Step Processing

```python
def process_task(self, task):
    # Step 1: Validate
    self._validate(task.payload)

    # Step 2: Transform
    data = self._transform(task.payload)

    # Step 3: Process with LLM
    result = self.ollama.generate(self._build_prompt(data))

    # Step 4: Parse and structure
    structured = self._parse_result(result)

    return AgentTaskResult(status="success", result=structured, ...)
```

### Pattern 2: Retry with Backoff

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _call_llm(self, prompt):
    return self.ollama.generate(prompt)
```

### Pattern 3: Streaming Large Files

```python
from cavia_common import get_minio_client

def process_large_file(self, file_path):
    minio = get_minio_client()
    stream = minio.download_file_stream("bucket", file_path)

    for chunk in stream.iter_chunks():
        self._process_chunk(chunk)
```

---

## Adding to Docker Compose

To auto-start your agent with infrastructure:

Edit `docker-compose.yml`:

```yaml
  myagent:
    build:
      context: .
      dockerfile: agents/myagent/Dockerfile
    container_name: cavia-myagent
    environment:
      DATABASE_URL: postgresql://cavia:${POSTGRES_PASSWORD:-caviadev123}@postgres:5432/cavia
      REDIS_URL: redis://redis:6379/0
      OLLAMA_HOST: http://ollama:11434
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      agent-registry:
        condition: service_healthy
    networks:
      - cavia-network
```

---

## Performance Optimization

### 1. Connection Pooling

Reuse database connections:

```python
# Already handled by DatabaseManager
db = get_db_manager()  # Uses connection pool
```

### 2. Batch Processing

Process multiple items together:

```python
def process_batch(self, tasks):
    # Process all at once for efficiency
    prompts = [self._build_prompt(t) for t in tasks]
    results = self.ollama.batch_generate(prompts)
    return results
```

### 3. Caching

Cache expensive operations:

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def _parse_schema(self, schema_id):
    # Expensive operation, cache result
    return load_and_parse_schema(schema_id)
```

---

## Next Steps

- Read [AOA.md](../AOA.md) for architectural principles
- See [getting-started.md](./getting-started.md) for setup
- Check [STATUS.md](../STATUS.md) for current progress
- Review existing agents in `agents/` directory
