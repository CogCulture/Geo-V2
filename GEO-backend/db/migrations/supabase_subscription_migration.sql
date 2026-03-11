-- ============================================================
-- GEO Subscription Schema Migration
-- Run this in the Supabase SQL Editor
-- ============================================================

-- 1. Immutable Audit Table (one row per verified payment)
--    razorpay_payment_id is UNIQUE — this is the idempotency key
CREATE TABLE IF NOT EXISTS payment_transactions (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID        NOT NULL REFERENCES users(id),
    user_email          TEXT,
    razorpay_order_id   TEXT        NOT NULL,
    razorpay_payment_id TEXT        NOT NULL UNIQUE,
    razorpay_signature  TEXT        NOT NULL,
    plan_name           TEXT        NOT NULL,
    billing_cycle       TEXT        NOT NULL,
    status              TEXT        NOT NULL DEFAULT 'verified',
    subscription_end    TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Add subscription columns to the users table
ALTER TABLE users
ADD COLUMN IF NOT EXISTS subscription_plan   TEXT,
ADD COLUMN IF NOT EXISTS subscription_status TEXT        DEFAULT 'inactive',
ADD COLUMN IF NOT EXISTS subscription_start  TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS subscription_end    TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS billing_cycle       TEXT,
ADD COLUMN IF NOT EXISTS razorpay_payment_id TEXT;
