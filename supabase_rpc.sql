-- RPC function to safely claim the next available comment in a batch
-- This ensures atomic operations to prevent two users from getting the same comment

CREATE OR REPLACE FUNCTION claim_next_comment_in_batch(
    p_user_id TEXT,
    p_batch_id UUID
)
RETURNS TABLE(
    id UUID,
    original_index INTEGER,
    comment_text TEXT,
    batch_id UUID,
    status TEXT,
    assigned_to UUID,
    claimed_at TIMESTAMPTZ,
    lock_expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ
)
LANGUAGE plpgsql
AS $$
DECLARE
    claimed_comment_id UUID;
    lock_duration INTERVAL := '30 minutes';
BEGIN
    -- Find and claim the next available comment atomically
    UPDATE comments 
    SET 
        status = 'claimed',
        assigned_to = p_user_id::UUID,
        claimed_at = NOW(),
        lock_expires_at = NOW() + lock_duration
    WHERE id = (
        SELECT c.id 
        FROM comments c
        WHERE c.batch_id = p_batch_id
        AND c.status = 'unassigned'
        ORDER BY c.original_index ASC
        LIMIT 1
        FOR UPDATE SKIP LOCKED
    )
    RETURNING id INTO claimed_comment_id;
    
    -- If no comment was claimed, return empty result
    IF claimed_comment_id IS NULL THEN
        RETURN;
    END IF;
    
    -- Return the claimed comment details
    RETURN QUERY
    SELECT c.id, c.original_index, c.comment_text, c.batch_id, c.status, 
           c.assigned_to, c.claimed_at, c.lock_expires_at, c.created_at
    FROM comments c
    WHERE c.id = claimed_comment_id;
END;
$$;

-- Optional: Function to release expired locks
-- This can be called periodically to free up comments that were claimed but not annotated
CREATE OR REPLACE FUNCTION release_expired_locks()
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    released_count INTEGER;
BEGIN
    UPDATE comments 
    SET 
        status = 'unassigned',
        assigned_to = NULL,
        claimed_at = NULL,
        lock_expires_at = NULL
    WHERE status = 'claimed'
    AND lock_expires_at < NOW();
    
    GET DIAGNOSTICS released_count = ROW_COUNT;
    RETURN released_count;
END;
$$;

-- Grant execute permissions (adjust as needed for your setup)
-- GRANT EXECUTE ON FUNCTION claim_next_comment_in_batch(TEXT, UUID) TO authenticated;
-- GRANT EXECUTE ON FUNCTION release_expired_locks() TO authenticated;
