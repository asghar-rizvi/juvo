
DROP TABLE IF EXISTS htl_reservations CASCADE;

-- Create htl_reservations correctly
CREATE TABLE htl_reservations (
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

-- Create partial unique index (correct syntax)
CREATE UNIQUE INDEX idx_htl_unique_unconfirmed 
ON htl_reservations (time_slot_id) 
WHERE is_confirmed = false;

-- Regular indexes
CREATE INDEX idx_htl_session ON htl_reservations(session_id);
CREATE INDEX idx_htl_user ON htl_reservations(user_id);
CREATE INDEX idx_htl_slot ON htl_reservations(time_slot_id);
CREATE INDEX idx_htl_expires ON htl_reservations(expires_at) WHERE is_confirmed = false;

COMMENT ON TABLE htl_reservations IS 'Temporary slot reservations (5 min hold)';

-- Verify table exists
SELECT 'htl_reservations created successfully' as status;