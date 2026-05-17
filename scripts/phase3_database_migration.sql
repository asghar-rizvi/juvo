--- 1. USERS TABLE (Customers)
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(200) NOT NULL,
    profile_picture_url TEXT,
    address TEXT,
    city VARCHAR(100),
    location GEOGRAPHY(POINT, 4326),
    preferred_language VARCHAR(10) DEFAULT 'en',
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    is_phone_verified BOOLEAN DEFAULT false,
    email_verified_at TIMESTAMP,
    phone_verified_at TIMESTAMP,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_phone ON users(phone);
CREATE INDEX idx_users_active ON users(is_active) WHERE is_active = true;

COMMENT ON TABLE users IS 'Customer accounts for the Juvo app';

-- ============================================
-- 2. PROVIDER ACCOUNTS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS provider_accounts (
    id SERIAL PRIMARY KEY,
    provider_id INTEGER UNIQUE NOT NULL REFERENCES providers(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    email_verified_at TIMESTAMP,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_provider_accounts_email ON provider_accounts(email);
CREATE INDEX idx_provider_accounts_provider ON provider_accounts(provider_id);

COMMENT ON TABLE provider_accounts IS 'Service provider login accounts';

-- ============================================
-- 3. REFRESH TOKENS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    provider_account_id INTEGER REFERENCES provider_accounts(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    is_revoked BOOLEAN DEFAULT false,
    revoked_at TIMESTAMP,
    user_agent TEXT,
    ip_address INET,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_user_or_provider CHECK (
        (user_id IS NOT NULL AND provider_account_id IS NULL) OR
        (user_id IS NULL AND provider_account_id IS NOT NULL)
    )
);

CREATE INDEX idx_refresh_tokens_hash ON refresh_tokens(token_hash);
CREATE INDEX idx_refresh_tokens_user ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_provider ON refresh_tokens(provider_account_id);

COMMENT ON TABLE refresh_tokens IS 'JWT refresh tokens for session management';

-- ============================================
-- 4. HTL (HOLD-TO-LOCK) RESERVATIONS
-- ============================================
CREATE TABLE IF NOT EXISTS htl_reservations (
    id SERIAL PRIMARY KEY,
    session_id UUID NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    provider_id INTEGER REFERENCES providers(id),
    time_slot_id INTEGER REFERENCES time_slots(id),
    reserved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    is_confirmed BOOLEAN DEFAULT false,
    is_expired BOOLEAN DEFAULT false,
    confirmed_at TIMESTAMP,
    expired_at TIMESTAMP
);

-- Partial unique index (PostgreSQL 9.5+)
CREATE UNIQUE INDEX idx_htl_unique_unconfirmed 
ON htl_reservations (time_slot_id) 
WHERE is_confirmed = false;

CREATE INDEX idx_htl_session ON htl_reservations(session_id);
CREATE INDEX idx_htl_user ON htl_reservations(user_id);
CREATE INDEX idx_htl_slot ON htl_reservations(time_slot_id);
CREATE INDEX idx_htl_expires ON htl_reservations(expires_at) WHERE is_confirmed = false;

COMMENT ON TABLE htl_reservations IS 'Temporary slot reservations (5 min hold)';

-- ============================================
-- 5. NOTIFICATIONS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    provider_account_id INTEGER REFERENCES provider_accounts(id) ON DELETE CASCADE,
    notification_type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    data JSONB,
    is_read BOOLEAN DEFAULT false,
    read_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_recipient CHECK (
        (user_id IS NOT NULL AND provider_account_id IS NULL) OR
        (user_id IS NULL AND provider_account_id IS NOT NULL)
    )
);

CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_provider ON notifications(provider_account_id);
CREATE INDEX idx_notifications_unread ON notifications(is_read) WHERE is_read = false;
CREATE INDEX idx_notifications_type ON notifications(notification_type);

COMMENT ON TABLE notifications IS 'In-app notifications for users and providers';

-- ============================================
-- 6. CHAT SESSIONS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS chat_sessions (
    id SERIAL PRIMARY KEY,
    session_id UUID UNIQUE NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    current_step VARCHAR(50),
    intent_data JSONB,
    selected_providers JSONB,
    context_data JSONB,
    is_active BOOLEAN DEFAULT true,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_message_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX idx_chat_session_id ON chat_sessions(session_id);
CREATE INDEX idx_chat_user ON chat_sessions(user_id);
CREATE INDEX idx_chat_active ON chat_sessions(is_active) WHERE is_active = true;

COMMENT ON TABLE chat_sessions IS 'Active agent conversation sessions';

-- ============================================
-- 7. PROVIDER REVIEWS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS provider_reviews (
    id SERIAL PRIMARY KEY,
    booking_id INTEGER UNIQUE REFERENCES bookings(id),
    user_id INTEGER REFERENCES users(id),
    provider_id INTEGER REFERENCES providers(id),
    rating DECIMAL(3,2) NOT NULL CHECK (rating >= 0 AND rating <= 5),
    review_text TEXT,
    response_text TEXT,
    response_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_reviews_provider ON provider_reviews(provider_id);
CREATE INDEX idx_reviews_user ON provider_reviews(user_id);
CREATE INDEX idx_reviews_booking ON provider_reviews(booking_id);

COMMENT ON TABLE provider_reviews IS 'User reviews and ratings for providers';

-- ============================================
-- 8. UPDATE EXISTING BOOKINGS TABLE
-- ============================================
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id);
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS htl_reservation_id INTEGER REFERENCES htl_reservations(id);

CREATE INDEX IF NOT EXISTS idx_bookings_user ON bookings(user_id);

-- ============================================
-- 9. AUTO-UPDATE TRIGGERS
-- ============================================

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_provider_accounts_updated_at
    BEFORE UPDATE ON provider_accounts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_provider_reviews_updated_at
    BEFORE UPDATE ON provider_reviews
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 10. HTL EXPIRATION FUNCTION
-- ============================================

CREATE OR REPLACE FUNCTION expire_htl_reservations()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE htl_reservations
    SET is_expired = true, expired_at = CURRENT_TIMESTAMP
    WHERE expires_at < CURRENT_TIMESTAMP
      AND is_confirmed = false
      AND is_expired = false;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Run expiration check periodically (handled by API background task instead)

-- ============================================
-- 11. AUTO-UPDATE PROVIDER RATING
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
        )
    WHERE id = NEW.provider_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_provider_rating_trigger
    AFTER INSERT OR UPDATE ON provider_reviews
    FOR EACH ROW
    EXECUTE FUNCTION update_provider_rating();

-- ============================================
-- VERIFICATION QUERIES
-- ============================================

-- Check all new tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name IN (
    'users', 
    'provider_accounts', 
    'refresh_tokens', 
    'htl_reservations', 
    'notifications', 
    'chat_sessions',
    'provider_reviews'
  )
ORDER BY table_name;

-- Should return 7 rows