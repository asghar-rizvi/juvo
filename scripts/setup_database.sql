DROP TABLE IF EXISTS conversation_logs CASCADE;
DROP TABLE IF EXISTS bookings CASCADE;
DROP TABLE IF EXISTS time_slots CASCADE;
DROP TABLE IF EXISTS providers CASCADE;
DROP TABLE IF EXISTS service_categories CASCADE;

-- service catgory table
CREATE TABLE service_categories (
    id SERIAL PRIMARY KEY,
    name_en VARCHAR(100) NOT NULL UNIQUE,
    name_ur VARCHAR(100) NOT NULL,
    name_roman_ur VARCHAR(100),
    keywords TEXT[] DEFAULT '{}',
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexss
CREATE INDEX idx_service_keywords ON service_categories USING GIN(keywords);

COMMENT ON TABLE service_categories IS 'Master table for service types (AC Technician, Plumber, etc.)';

--PROVIDERS TABLE
CREATE TABLE providers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    email VARCHAR(255),
    service_category_id INTEGER NOT NULL REFERENCES service_categories(id) ON DELETE CASCADE,
    location GEOGRAPHY(POINT, 4326) NOT NULL,
    address_text TEXT,
    rating DECIMAL(3,2) DEFAULT 0.00 CHECK (rating >= 0 AND rating <= 5),
    total_reviews INTEGER DEFAULT 0,
    is_available BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    years_experience INTEGER,
    price_range VARCHAR(50),
    profile_image_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Spatial index for location-based queries
CREATE INDEX idx_provider_location ON providers USING GIST(location);
CREATE INDEX idx_provider_category ON providers(service_category_id);
CREATE INDEX idx_provider_available ON providers(is_available) WHERE is_available = true;

COMMENT ON TABLE providers IS 'Service providers with geospatial data';
COMMENT ON COLUMN providers.location IS 'PostGIS geography point (latitude, longitude)';

-- TIMESLOTS TABLE
CREATE TABLE time_slots (
    id SERIAL PRIMARY KEY,
    provider_id INTEGER NOT NULL REFERENCES providers(id) ON DELETE CASCADE,
    slot_date DATE NOT NULL,
    slot_time TIME NOT NULL,
    duration_minutes INTEGER DEFAULT 60,
    is_booked BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_provider_slot UNIQUE(provider_id, slot_date, slot_time)
);

-- Indexes for availability checks
CREATE INDEX idx_timeslot_provider ON time_slots(provider_id);
CREATE INDEX idx_timeslot_date ON time_slots(slot_date);
CREATE INDEX idx_timeslot_available ON time_slots(is_booked) WHERE is_booked = false;

COMMENT ON TABLE time_slots IS 'Available time slots for each provider';

-- Booking Table
CREATE TABLE bookings (
    id SERIAL PRIMARY KEY,
    booking_reference VARCHAR(50) UNIQUE NOT NULL,
    session_id UUID NOT NULL,
    user_phone VARCHAR(20) NOT NULL,
    user_name VARCHAR(200),
    provider_id INTEGER NOT NULL REFERENCES providers(id),
    service_category_id INTEGER NOT NULL REFERENCES service_categories(id),
    time_slot_id INTEGER NOT NULL REFERENCES time_slots(id),
    location_requested GEOGRAPHY(POINT, 4326),
    address_requested TEXT,
    status booking_status DEFAULT 'pending',
    special_instructions TEXT,
    estimated_price DECIMAL(10,2),
    actual_price DECIMAL(10,2),
    user_rating DECIMAL(3,2) CHECK (user_rating >= 0 AND user_rating <= 5),
    user_review TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    confirmed_at TIMESTAMP,
    completed_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    cancellation_reason TEXT
);

CREATE INDEX idx_booking_session ON bookings(session_id);
CREATE INDEX idx_booking_user_phone ON bookings(user_phone);
CREATE INDEX idx_booking_provider ON bookings(provider_id);
CREATE INDEX idx_booking_status ON bookings(status);
CREATE INDEX idx_booking_created ON bookings(created_at DESC);

COMMENT ON TABLE bookings IS 'Service booking records with full lifecycle tracking';

-- conversation logs table for proper logging (no change in phase 2 today- 16th)
CREATE TABLE conversation_logs (
    id SERIAL PRIMARY KEY,
    session_id UUID NOT NULL,
    booking_id INTEGER REFERENCES bookings(id),
    user_input TEXT,
    user_input_language language_code,
    extracted_intent JSONB,
    agent_name VARCHAR(100),
    agent_response TEXT,
    tool_calls JSONB,
    reasoning TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for conversation tracking
CREATE INDEX idx_conversation_session ON conversation_logs(session_id);
CREATE INDEX idx_conversation_booking ON conversation_logs(booking_id);
CREATE INDEX idx_conversation_created ON conversation_logs(created_at DESC);
CREATE INDEX idx_conversation_intent ON conversation_logs USING GIN(extracted_intent);

COMMENT ON TABLE conversation_logs IS 'Complete audit trail of agent interactions';

--TRIGGERS FOR AUTO-UPDATE TIMESTAMPS

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_service_categories_updated_at
    BEFORE UPDATE ON service_categories
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_providers_updated_at
    BEFORE UPDATE ON providers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

--FUNCTION: Generate Booking Reference

CREATE OR REPLACE FUNCTION generate_booking_reference()
RETURNS TRIGGER AS $$
BEGIN
    NEW.booking_reference := 'BK' || TO_CHAR(NEW.created_at, 'YYYYMMDD') || '-' || LPAD(NEW.id::TEXT, 6, '0');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_booking_reference
    BEFORE INSERT ON bookings
    FOR EACH ROW
    EXECUTE FUNCTION generate_booking_reference();

-- FUNCTION: Prevent Double Booking

CREATE OR REPLACE FUNCTION prevent_double_booking()
RETURNS TRIGGER AS $$
BEGIN
    -- Check if time slot is already booked
    IF EXISTS (
        SELECT 1 FROM time_slots 
        WHERE id = NEW.time_slot_id AND is_booked = true
    ) THEN
        RAISE EXCEPTION 'Time slot already booked';
    END IF;
    
    -- Mark slot as booked
    UPDATE time_slots 
    SET is_booked = true 
    WHERE id = NEW.time_slot_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER enforce_single_booking
    BEFORE INSERT ON bookings
    FOR EACH ROW
    EXECUTE FUNCTION prevent_double_booking();

--VIEW: Available Provider Slots

CREATE OR REPLACE VIEW available_provider_slots AS
SELECT 
    p.id AS provider_id,
    p.name AS provider_name,
    sc.name_en AS service_category,
    ts.slot_date,
    ts.slot_time,
    ts.id AS slot_id,
    p.rating,
    p.location
FROM providers p
JOIN service_categories sc ON p.service_category_id = sc.id
JOIN time_slots ts ON p.id = ts.provider_id
WHERE p.is_available = true 
  AND ts.is_booked = false
  AND ts.slot_date >= CURRENT_DATE
ORDER BY ts.slot_date, ts.slot_time;

COMMENT ON VIEW available_provider_slots IS 'Quick view of all available slots across providers';

--MAKING SAMPLE FUNCTIONS FOR QUERIES

-- Function: Find nearby providers
CREATE OR REPLACE FUNCTION find_nearby_providers(
    p_service_category TEXT,
    p_latitude DOUBLE PRECISION,
    p_longitude DOUBLE PRECISION,
    p_max_distance_km DOUBLE PRECISION DEFAULT 10,
    p_limit INTEGER DEFAULT 5
)
RETURNS TABLE (
    provider_id INTEGER,
    provider_name VARCHAR(200),
    phone VARCHAR(20),
    rating DECIMAL(3,2),
    distance_km DOUBLE PRECISION,
    available_slots_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.id,
        p.name,
        p.phone,
        p.rating,
        ROUND(
            ST_Distance(
                p.location::geography,
                ST_SetSRID(ST_MakePoint(p_longitude, p_latitude), 4326)::geography
            )::numeric / 1000, 2
        ) AS distance_km,
        COUNT(ts.id) AS available_slots_count
    FROM providers p
    JOIN service_categories sc ON p.service_category_id = sc.id
    LEFT JOIN time_slots ts ON p.id = ts.provider_id 
        AND ts.is_booked = false 
        AND ts.slot_date >= CURRENT_DATE
    WHERE 
        sc.name_en ILIKE '%' || p_service_category || '%'
        AND p.is_available = true
        AND ST_DWithin(
            p.location::geography,
            ST_SetSRID(ST_MakePoint(p_longitude, p_latitude), 4326)::geography,
            p_max_distance_km * 1000
        )
    GROUP BY p.id, p.name, p.phone, p.rating, p.location
    ORDER BY distance_km ASC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION find_nearby_providers IS 'Find providers within radius with available slots';

-- ============================================
-- GRANT PERMISSIONS (if using specific user)
-- ============================================

-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_app_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO your_app_user;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO your_app_user;

-- ============================================
-- VERIFICATION QUERIES
-- ============================================

-- Verify PostGIS installation
SELECT PostGIS_Full_Version();

-- List all tables
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

-- Show all custom types
SELECT typname FROM pg_type WHERE typtype = 'e';