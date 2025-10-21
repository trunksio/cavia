-- Initialize CAVIA database with pgvector extension

-- Enable pgvector extension for semantic search
CREATE EXTENSION IF NOT EXISTS vector;

-- Agent Registry Table
CREATE TABLE IF NOT EXISTS agent_registry (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(255) UNIQUE NOT NULL,
    agent_type VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    capabilities JSONB,
    queue_name VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    semantic_embedding vector(384),  -- sentence-transformers default dimension
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    agent_metadata JSONB DEFAULT '{}'
);

-- Index for semantic search
CREATE INDEX IF NOT EXISTS agent_registry_embedding_idx ON agent_registry
USING ivfflat (semantic_embedding vector_cosine_ops)
WITH (lists = 100);

-- Index for agent lookups
CREATE INDEX IF NOT EXISTS agent_registry_agent_id_idx ON agent_registry (agent_id);
CREATE INDEX IF NOT EXISTS agent_registry_type_idx ON agent_registry (agent_type);
CREATE INDEX IF NOT EXISTS agent_registry_status_idx ON agent_registry (status);

-- CV Processing Jobs Table
CREATE TABLE IF NOT EXISTS cv_jobs (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(255) UNIQUE NOT NULL,
    filename VARCHAR(512) NOT NULL,
    minio_path VARCHAR(512) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',  -- pending, processing, completed, failed
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    result JSONB,  -- Final evaluation result
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS cv_jobs_job_id_idx ON cv_jobs (job_id);
CREATE INDEX IF NOT EXISTS cv_jobs_status_idx ON cv_jobs (status);
CREATE INDEX IF NOT EXISTS cv_jobs_submitted_at_idx ON cv_jobs (submitted_at DESC);

-- Evaluation Criteria Table
CREATE TABLE IF NOT EXISTS evaluation_criteria (
    id SERIAL PRIMARY KEY,
    criterion_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    evaluation_prompt TEXT NOT NULL,
    weight FLOAT DEFAULT 1.0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS evaluation_criteria_criterion_id_idx ON evaluation_criteria (criterion_id);
CREATE INDEX IF NOT EXISTS evaluation_criteria_is_active_idx ON evaluation_criteria (is_active);

-- CV Evaluation Results Table (per criterion)
CREATE TABLE IF NOT EXISTS cv_evaluations (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(255) NOT NULL,
    criterion_id VARCHAR(255) NOT NULL,
    agent_id VARCHAR(255) NOT NULL,
    score FLOAT NOT NULL,  -- 0-100
    confidence FLOAT,  -- 0-1
    evidence TEXT,
    reasoning TEXT,
    evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    FOREIGN KEY (job_id) REFERENCES cv_jobs(job_id) ON DELETE CASCADE,
    FOREIGN KEY (criterion_id) REFERENCES evaluation_criteria(criterion_id)
);

CREATE INDEX IF NOT EXISTS cv_evaluations_job_id_idx ON cv_evaluations (job_id);
CREATE INDEX IF NOT EXISTS cv_evaluations_criterion_id_idx ON cv_evaluations (criterion_id);

-- Agent Performance Metrics (for ACE loop)
CREATE TABLE IF NOT EXISTS agent_metrics (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(255) NOT NULL,
    job_id VARCHAR(255),
    metric_type VARCHAR(100) NOT NULL,  -- latency, accuracy, error_rate, etc.
    metric_value FLOAT NOT NULL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    FOREIGN KEY (agent_id) REFERENCES agent_registry(agent_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS agent_metrics_agent_id_idx ON agent_metrics (agent_id);
CREATE INDEX IF NOT EXISTS agent_metrics_recorded_at_idx ON agent_metrics (recorded_at DESC);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_agent_registry_updated_at BEFORE UPDATE ON agent_registry
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_evaluation_criteria_updated_at BEFORE UPDATE ON evaluation_criteria
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default evaluation criteria (examples - configurable via UI)
INSERT INTO evaluation_criteria (criterion_id, name, description, evaluation_prompt, weight) VALUES
('tech_skills', 'Technical Skills Match', 'Evaluate technical skills alignment with job requirements',
 'Evaluate the candidate''s technical skills based on the CV. Look for relevant programming languages, frameworks, tools, and technologies. Score from 0-100 based on breadth and depth of skills.',
 1.0),
('experience', 'Relevant Experience', 'Assess years and quality of relevant work experience',
 'Evaluate the candidate''s work experience. Consider years of experience, relevance to the role, progression in responsibilities, and achievements. Score from 0-100.',
 1.5),
('education', 'Educational Background', 'Evaluate educational qualifications and continuous learning',
 'Evaluate the candidate''s educational background including degrees, certifications, and ongoing learning. Score from 0-100 based on relevance and quality of education.',
 0.8)
ON CONFLICT (criterion_id) DO NOTHING;

-- Create views for common queries
CREATE OR REPLACE VIEW active_agents AS
SELECT * FROM agent_registry
WHERE status = 'active'
  AND last_heartbeat > NOW() - INTERVAL '5 minutes';

CREATE OR REPLACE VIEW cv_job_summary AS
SELECT
    j.job_id,
    j.filename,
    j.status,
    j.submitted_at,
    j.completed_at,
    j.result,
    COALESCE(AVG(e.score), 0) as avg_score,
    COUNT(e.id) as evaluations_count
FROM cv_jobs j
LEFT JOIN cv_evaluations e ON j.job_id = e.job_id
GROUP BY j.id, j.job_id, j.filename, j.status, j.submitted_at, j.completed_at, j.result;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO cavia;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO cavia;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'CAVIA database initialized successfully!';
END $$;
