-- CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- -- =========================
-- -- USERS
-- -- =========================
-- CREATE TABLE users (
--     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--     email TEXT UNIQUE NOT NULL,
--     password_hash TEXT NOT NULL,
--     full_name TEXT,
--     role TEXT NOT NULL DEFAULT 'agent',
--     is_active BOOLEAN DEFAULT TRUE,
--     created_at TIMESTAMPTZ DEFAULT now(),
--     last_login_at TIMESTAMPTZ
-- );


-- CREATE TABLE user_sessions (
--     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--     user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

--     ip_address TEXT,
--     user_agent TEXT,

--     created_at TIMESTAMPTZ DEFAULT now(),
--     expires_at TIMESTAMPTZ,
--     revoked_at TIMESTAMPTZ
-- );

-- -- =========================
-- -- LISTINGS (ANCHOR)
-- -- =========================
-- CREATE TABLE listings (
--     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--     created_by UUID REFERENCES users(id),
--     status TEXT NOT NULL DEFAULT 'draft',
--     created_at TIMESTAMPTZ DEFAULT now(),
--     updated_at TIMESTAMPTZ DEFAULT now()
-- );

-- -- =========================
-- -- CANONICAL LISTING
-- -- =========================
-- CREATE TABLE canonical_listings (
--     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--     listing_id UUID UNIQUE NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
--     schema_version TEXT NOT NULL,
--     canonical_payload JSONB NOT NULL,
--     mode TEXT NOT NULL DEFAULT 'draft',
--     locked BOOLEAN DEFAULT FALSE,
--     validated_at TIMESTAMPTZ,
--     validated_by UUID REFERENCES users(id),
--     updated_at TIMESTAMPTZ DEFAULT now()
-- );

-- -- =========================
-- -- DOCUMENTS
-- -- =========================
-- CREATE TABLE documents (
--     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--     listing_id UUID REFERENCES listings(id) ON DELETE CASCADE,
--     filename TEXT NOT NULL,
--     storage_path TEXT NOT NULL,
--     uploaded_at TIMESTAMPTZ DEFAULT now()
-- );

-- CREATE TABLE document_pages (
--     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--     document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,

--     page_number INT NOT NULL,
--     extracted_text TEXT,

--     created_at TIMESTAMPTZ DEFAULT now(),
--     UNIQUE (document_id, page_number)
-- );

-- -- =========================
-- -- IMAGES
-- -- =========================
-- CREATE TABLE listing_images (
--     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--     listing_id UUID REFERENCES listings(id) ON DELETE CASCADE,

--     storage_path TEXT NOT NULL,
--     original_filename TEXT,

--     ai_suggested_label TEXT,
--     final_label TEXT,

--     ai_suggested_order INT,
--     final_order INT,
--     order_locked BOOLEAN DEFAULT FALSE,

--     display_order INT DEFAULT 0,
--     is_primary BOOLEAN DEFAULT FALSE,

--     uploaded_at TIMESTAMPTZ DEFAULT now()
-- );



-- -- =========================
-- -- IMAGE AI ANALYSIS
-- -- =========================
-- CREATE TABLE image_ai_analysis (
--     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--     image_id UUID REFERENCES listing_images(id) ON DELETE CASCADE,

--     description TEXT,
--     detected_features JSONB,

--     model_version TEXT,
--     created_at TIMESTAMPTZ DEFAULT now()
-- );


-- -- =========================
-- -- EXTRACTED FIELD FACTS
-- -- =========================
-- CREATE TABLE extracted_field_facts (
--     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--     listing_id UUID REFERENCES listings(id) ON DELETE CASCADE,

--     canonical_path TEXT NOT NULL,
--     extracted_value JSONB NOT NULL,

--     source_type TEXT NOT NULL,   -- document | image | manual | public_record
--     source_ref TEXT,

--     status TEXT DEFAULT 'proposed', -- proposed | accepted | rejected
--     created_at TIMESTAMPTZ DEFAULT now()
-- );


-- -- =========================
-- -- MLS SYSTEMS
-- -- =========================
-- CREATE TABLE mls_systems (
--     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--     code TEXT UNIQUE NOT NULL,
--     name TEXT NOT NULL,
--     is_active BOOLEAN DEFAULT TRUE
-- );

-- -- =========================
-- -- MLS CREDENTIALS (NO PASSWORDS)
-- -- =========================
-- CREATE TABLE mls_credentials (
--     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--     user_id UUID REFERENCES users(id),
--     mls_system_id UUID REFERENCES mls_systems(id),
--     username TEXT NOT NULL,
--     secret_reference TEXT NOT NULL,
--     is_saved BOOLEAN DEFAULT TRUE,
--     created_at TIMESTAMPTZ DEFAULT now(),
--     last_used_at TIMESTAMPTZ
-- );

-- -- =========================
-- -- LISTING SUBMISSIONS
-- -- =========================
-- CREATE TABLE listing_submissions (
--     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--     listing_id UUID REFERENCES listings(id),
--     mls_system_id UUID REFERENCES mls_systems(id),
--     credential_mode TEXT NOT NULL, -- auto | manual
--     status TEXT DEFAULT 'pending',
--     mls_listing_number TEXT,
--     created_at TIMESTAMPTZ DEFAULT now(),
--     completed_at TIMESTAMPTZ
-- );

-- -- =========================
-- -- AUTOMATION JOBS
-- -- =========================
-- CREATE TABLE automation_jobs (
--     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--     submission_id UUID REFERENCES listing_submissions(id),
--     trace_id TEXT,
--     logs JSONB,
--     screenshots TEXT[],
--     started_at TIMESTAMPTZ,
--     ended_at TIMESTAMPTZ,
--     error_message TEXT
-- );

-- CREATE TABLE pricing_plans (
--     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

--     code TEXT UNIQUE NOT NULL,         -- free | starter | pro | enterprise
--     name TEXT NOT NULL,
--     description TEXT,

--     price_monthly NUMERIC NOT NULL,
--     currency TEXT DEFAULT 'USD',

--     max_listings_per_month INT,
--     max_mls_submissions INT,
--     max_users INT,

--     features JSONB,                    -- feature flags
--     is_active BOOLEAN DEFAULT TRUE,

--     created_at TIMESTAMPTZ DEFAULT now()
-- );

-- CREATE TABLE user_subscriptions (
--     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

--     user_id UUID NOT NULL REFERENCES users(id),
--     pricing_plan_id UUID NOT NULL REFERENCES pricing_plans(id),

--     status TEXT NOT NULL DEFAULT 'active',  -- active | cancelled | expired
--     started_at TIMESTAMPTZ DEFAULT now(),
--     ends_at TIMESTAMPTZ
-- );
