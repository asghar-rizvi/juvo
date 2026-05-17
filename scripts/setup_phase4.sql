-- ============================================
-- Phase 4 Database Setup / Verification
-- Run this if you need to add missing tables
-- ============================================

-- Ensure PostGIS is enabled
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- Chat Sessions Table
-- ============================================
CREATE TABLE IF NOT EXISTS chat_sessions (
    id SERIAL PRIMARY KEY,
    session_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    current_step VARCHAR(50),
    intent_data JSONB,
    selected_providers JSONB,
    context_data JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    started_at TIMESTAMP DEFAULT NOW(),
    last_message_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_session_id 
    ON chat_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id 
    ON chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_is_active 
    ON chat_sessions(is_active);

-- ============================================
-- HTL Reservations Table
-- ============================================
CREATE TABLE IF NOT EXISTS htl_reservations (
    id SERIAL PRIMARY KEY,
    session_id UUID NOT NULL DEFAULT uuid_generate_v4(),
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    provider_id INTEGER REFERENCES providers(id),
    time_slot_id INTEGER REFERENCES time_slots(id),
    reserved_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    is_confirmed BOOLEAN DEFAULT FALSE,
    is_expired BOOLEAN DEFAULT FALSE,
    confirmed_at TIMESTAMP,
    expired_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_htl_reservations_session_id 
    ON htl_reservations(session_id);
CREATE INDEX IF NOT EXISTS idx_htl_reservations_user_id 
    ON htl_reservations(user_id);
CREATE INDEX IF NOT EXISTS idx_htl_reservations_expires_at 
    ON htl_reservations(expires_at);

-- ============================================
-- Notifications Table
-- ============================================
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    provider_account_id INTEGER REFERENCES provider_accounts(id) ON DELETE CASCADE,
    notification_type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    data JSONB,
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notifications_user_id 
    ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_provider_account_id 
    ON notifications(provider_account_id);
CREATE INDEX IF NOT EXISTS idx_notifications_is_read 
    ON notifications(is_read);

-- ============================================
-- Provider Reviews Table
-- ============================================
CREATE TABLE IF NOT EXISTS provider_reviews (
    id SERIAL PRIMARY KEY,
    booking_id INTEGER UNIQUE REFERENCES bookings(id),
    user_id INTEGER REFERENCES users(id),
    provider_id INTEGER REFERENCES providers(id),
    rating DECIMAL(3,2) NOT NULL,
    review_text TEXT,
    response_text TEXT,
    response_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT check_review_rating_range CHECK (rating >= 0 AND rating <= 5)
);

-- ============================================
-- Add htl_reservation_id to bookings (if missing)
-- ============================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'bookings'
        AND column_name = 'htl_reservation_id'
    ) THEN
        ALTER TABLE bookings
        ADD COLUMN htl_reservation_id INTEGER
        REFERENCES htl_reservations(id);
    END IF;
END $$;

-- ============================================
-- Provider Rating Auto-Update Function
-- ============================================
CREATE OR REPLACE FUNCTION update_provider_rating()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE providers
    SET 
        rating = (
            SELECT COALESCE(AVG(rating), 0)
            FROM provider_reviews
            WHERE provider_id = NEW.provider_id
        ),
        total_reviews = (
            SELECT COUNT(*)
            FROM provider_reviews
            WHERE provider_id = NEW.provider_id
        ),
        updated_at = NOW()
    WHERE id = NEW.provider_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_provider_rating ON provider_reviews;
CREATE TRIGGER trg_update_provider_rating
    AFTER INSERT OR UPDATE ON provider_reviews
    FOR EACH ROW
    EXECUTE FUNCTION update_provider_rating();

-- ============================================
-- Verify Tables
-- ============================================
DO $$
DECLARE
    tbl TEXT;
    tables TEXT[] := ARRAY[
        'users', 'providers', 'provider_accounts',
        'time_slots', 'bookings', 'chat_sessions',
        'htl_reservations', 'notifications',
        'provider_reviews', 'refresh_tokens',
        'conversation_logs', 'service_categories'
    ];
BEGIN
    RAISE NOTICE '=== Phase 4 Table Verification ===';
    FOREACH tbl IN ARRAY tables
    LOOP
        IF EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = tbl
            AND table_schema = 'public'
        ) THEN
            RAISE NOTICE '✓ Table exists: %', tbl;
        ELSE
            RAISE NOTICE '✗ MISSING TABLE: %', tbl;
        END IF;
    END LOOP;
    RAISE NOTICE '=== Verification Complete ===';
END $$;