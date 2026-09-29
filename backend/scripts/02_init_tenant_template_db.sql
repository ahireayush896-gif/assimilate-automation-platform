-- ====================================================================
-- Script B: Tenant Data Plane Template Schema
-- Target Database: tenant_template_db
-- ====================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Repositories
CREATE TABLE IF NOT EXISTS repositories (
    repository_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    repo_name VARCHAR(255) NOT NULL,
    github_repo_url TEXT NOT NULL,
    default_branch VARCHAR(100) DEFAULT 'main',
    github_installation_id BIGINT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Tickets
CREATE TABLE IF NOT EXISTS tickets (
    ticket_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    repo_id UUID REFERENCES repositories(repository_id),
    creator_id UUID NOT NULL,
    assigned_reviewer_id UUID,
    prompt TEXT NOT NULL,
    category VARCHAR(50) NOT NULL,
    priority VARCHAR(20) DEFAULT 'P2',
    status VARCHAR(50) DEFAULT 'DRAFT',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Attachments
CREATE TABLE IF NOT EXISTS attachments (
    attachment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id UUID REFERENCES tickets(ticket_id) ON DELETE CASCADE,
    file_url TEXT NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    uploaded_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Revisions (Diffs)
CREATE TABLE IF NOT EXISTS revisions (
    revision_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id UUID REFERENCES tickets(ticket_id) ON DELETE CASCADE,
    iteration_number INT NOT NULL,
    author_type VARCHAR(20) NOT NULL,
    diff_patch TEXT NOT NULL,
    files_modified JSONB DEFAULT '[]',
    ai_summary TEXT,
    reviewer_feedback TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Executions
CREATE TABLE IF NOT EXISTS executions (
    execution_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id UUID REFERENCES tickets(ticket_id) ON DELETE CASCADE,
    current_step VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    execution_logs JSONB DEFAULT '[]',
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Pull Requests
CREATE TABLE IF NOT EXISTS pull_requests (
    pr_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id UUID REFERENCES tickets(ticket_id) ON DELETE CASCADE,
    github_pr_number INT NOT NULL,
    github_pr_url TEXT NOT NULL,
    branch_name VARCHAR(255) NOT NULL,
    target_branch VARCHAR(100) DEFAULT 'main',
    status VARCHAR(50) DEFAULT 'OPEN',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
