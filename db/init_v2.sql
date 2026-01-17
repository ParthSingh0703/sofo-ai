-- Enhanced schema for MLS automation (non-destructive to init.sql)
-- Includes enums, indexes, and constraints aligned to microservice-friendly patterns.
-- Run with: psql "$DATABASE_URL" -f db/init_v2.sql

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =========================
-- ENUMS (avoid magic strings)
-- =========================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role') THEN
        CREATE TYPE user_role AS ENUM ('agent', 'admin', 'support');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'listing_status') THEN
        CREATE TYPE listing_status AS ENUM ('draft', 'in_review', 'ready', 'submitted', 'published', 'archived');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'canonical_mode') THEN
        CREATE TYPE canonical_mode AS ENUM ('draft', 'locked');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'fact_status') THEN
        CREATE TYPE fact_status AS ENUM ('proposed', 'accepted', 'rejected');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'credential_mode') THEN
        CREATE TYPE credential_mode AS ENUM ('auto', 'manual');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'submission_status') THEN
        CREATE TYPE submission_status AS ENUM ('pending', 'in_progress', 'succeeded', 'failed');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'subscription_status') THEN
        CREATE TYPE subscription_status AS ENUM ('active', 'cancelled', 'expired', 'past_due');
    END IF;
END$$;

-- =========================
-- USERS
-- =========================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    role user_role NOT NULL DEFAULT 'agent',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT now(),
    last_login_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);

-- =========================
-- LISTINGS (ANCHOR)
-- =========================
CREATE TABLE IF NOT EXISTS listings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_by UUID REFERENCES users(id),
    status listing_status NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_listings_status ON listings(status);
CREATE INDEX IF NOT EXISTS idx_listings_created_by ON listings(created_by);

-- =========================
-- CANONICAL LISTING
-- =========================
CREATE TABLE IF NOT EXISTS canonical_listings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id UUID UNIQUE NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    schema_version TEXT NOT NULL,
    canonical_payload JSONB NOT NULL,
    mode canonical_mode NOT NULL DEFAULT 'draft',
    locked BOOLEAN DEFAULT FALSE,
    validated_at TIMESTAMPTZ,
    validated_by UUID REFERENCES users(id),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- =========================
-- DOCUMENTS
-- =========================
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id UUID REFERENCES listings(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    uploaded_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_documents_listing_id ON documents(listing_id);

CREATE TABLE IF NOT EXISTS document_pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_number INT NOT NULL,
    extracted_text TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (document_id, page_number)
);

-- =========================
-- IMAGES
-- =========================
CREATE TABLE IF NOT EXISTS listing_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id UUID REFERENCES listings(id) ON DELETE CASCADE,
    storage_path TEXT NOT NULL,
    original_filename TEXT,
    ai_suggested_label TEXT,
    final_label TEXT,
    ai_suggested_order INT,
    final_order INT,
    order_locked BOOLEAN DEFAULT FALSE,
    display_order INT DEFAULT 0,
    is_primary BOOLEAN DEFAULT FALSE,
    uploaded_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_listing_images_listing_id ON listing_images(listing_id);

-- =========================
-- IMAGE AI ANALYSIS
-- =========================
CREATE TABLE IF NOT EXISTS image_ai_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    image_id UUID REFERENCES listing_images(id) ON DELETE CASCADE,
    description TEXT,
    detected_features JSONB,
    model_version TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- =========================
-- EXTRACTED FIELD FACTS
-- =========================
CREATE TABLE IF NOT EXISTS extracted_field_facts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id UUID REFERENCES listings(id) ON DELETE CASCADE,
    canonical_path TEXT NOT NULL,
    extracted_value JSONB NOT NULL,
    source_type TEXT NOT NULL,   -- document | image | manual | public_record
    source_ref TEXT,
    status fact_status DEFAULT 'proposed',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_extracted_facts_listing_id ON extracted_field_facts(listing_id);
CREATE INDEX IF NOT EXISTS idx_extracted_facts_path ON extracted_field_facts(canonical_path);

-- =========================
-- MLS SYSTEMS & CREDS
-- =========================
CREATE TABLE IF NOT EXISTS mls_systems (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS mls_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    mls_system_id UUID REFERENCES mls_systems(id),
    username TEXT NOT NULL,
    secret_reference TEXT NOT NULL, -- reference to vault/secret manager
    is_saved BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT now(),
    last_used_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_mls_credentials_user_mls ON mls_credentials(user_id, mls_system_id);

-- =========================
-- MLS FIELD MAPPINGS
-- =========================
CREATE TABLE IF NOT EXISTS mls_field_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id UUID NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    mls_system_id UUID NOT NULL REFERENCES mls_systems(id),
    mapped_fields JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (listing_id, mls_system_id)
);

CREATE INDEX IF NOT EXISTS idx_mls_mappings_listing ON mls_field_mappings(listing_id);
CREATE INDEX IF NOT EXISTS idx_mls_mappings_system ON mls_field_mappings(mls_system_id);

-- =========================
-- MLS MAPPING CONFIGS (LEARNED FIELD MAPPINGS)
-- =========================
CREATE TABLE IF NOT EXISTS mls_mapping_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mls_system_id UUID NOT NULL REFERENCES mls_systems(id) ON DELETE CASCADE,
    field_selectors JSONB NOT NULL DEFAULT '[]'::jsonb,
    page_structure JSONB NOT NULL DEFAULT '{}'::jsonb,
    enum_mappings JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (mls_system_id)
);

CREATE INDEX IF NOT EXISTS idx_mls_mapping_configs_system ON mls_mapping_configs(mls_system_id);

-- =========================
-- LISTING SUBMISSIONS
-- =========================
CREATE TABLE IF NOT EXISTS listing_submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id UUID REFERENCES listings(id),
    mls_system_id UUID REFERENCES mls_systems(id),
    credential_mode credential_mode NOT NULL,
    status submission_status DEFAULT 'pending',
    mls_listing_number TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_submissions_listing ON listing_submissions(listing_id);

-- =========================
-- AUTOMATION JOBS
-- =========================
CREATE TABLE IF NOT EXISTS automation_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id UUID REFERENCES listing_submissions(id),
    trace_id TEXT,
    logs JSONB,
    screenshots TEXT[],
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_jobs_submission ON automation_jobs(submission_id);

-- =========================
-- PRICING & SUBSCRIPTIONS
-- =========================
CREATE TABLE IF NOT EXISTS pricing_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code TEXT UNIQUE NOT NULL,         -- free | starter | pro | enterprise
    name TEXT NOT NULL,
    description TEXT,
    price_monthly NUMERIC NOT NULL,
    currency TEXT DEFAULT 'USD',
    max_listings_per_month INT,
    max_mls_submissions INT,
    max_users INT,
    features JSONB,                    -- feature flags
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS user_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    pricing_plan_id UUID NOT NULL REFERENCES pricing_plans(id),
    status subscription_status NOT NULL DEFAULT 'active',
    started_at TIMESTAMPTZ DEFAULT now(),
    ends_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_user_subscriptions_user ON user_subscriptions(user_id);
