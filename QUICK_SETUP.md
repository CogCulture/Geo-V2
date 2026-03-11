# Quick Setup Guide - Authentication

## 🚀 5-Minute Quick Start

### Step 1: Create Users Table (Supabase)

1. Go to Supabase Dashboard
2. Click "SQL Editor"
3. Create new query
4. Copy-paste this SQL:

```sql
-- Users table for authentication
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Update analysis_sessions to include user_id
ALTER TABLE analysis_sessions
ADD COLUMN user_id UUID NOT NULL DEFAULT gen_random_uuid() REFERENCES users(id) ON DELETE CASCADE;

-- Create index for faster lookups
CREATE INDEX idx_analysis_sessions_user_id ON analysis_sessions(user_id);
```

5. Click "Run" ✅

### Step 2: Install Dependencies

```bash
cd GEO-backend
pip install bcrypt PyJWT
```

Or just run:
```bash
pip install -r requirements.txt
```

### Step 3: Set Environment Variables

**Backend (`GEO-backend/.env`):**
```
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_key_here
JWT_SECRET=your-secret-key-change-in-production
```

**Frontend (`GEO-frontend/.env.local`):**
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Step 4: Start Your App

**Terminal 1 - Backend:**
```bash
cd GEO-backend
python app.py
```

**Terminal 2 - Frontend:**
```bash
cd GEO-frontend
npm run dev
```

### Step 5: Test It! 🎉

1. Open http://localhost:3000
2. Click "Get Started"
3. Fill email and password → Create Account
4. Now in analysis form
5. Fill brand details and run analysis
6. Go back to home and click "Get Started" again
7. Click "Sign In" with same email
8. Your previous analyses show in dropdown!

---

## 📋 What Changed in Your Code

### New Files
- `src/components/signup-page.tsx` - Login/signup form
- `src/contexts/AuthContext.tsx` - Auth state management
- `AUTHENTICATION_GUIDE.md` - Full documentation
- `IMPLEMENTATION_SUMMARY.md` - What was added

### Modified Files
- `app.py` - Added auth endpoints (lines ~140-250)
- `page.tsx` - Integrated login flow
- `database_manager.py` - Added user functions
- `queryClient.ts` - Added token to requests
- `requirements.txt` - Added bcrypt, PyJWT

### New Backend Endpoints

```
POST /api/auth/signup    - Create account
POST /api/auth/login     - Login to account
GET  /api/auth/me        - Get user profile
```

All analysis endpoints now require `Authorization: Bearer {token}`

---

## 🔒 How It Works

1. **Sign Up**: Email + Password → Hashed → Stored in DB
2. **Login**: Email + Password → Match with Hash → Get JWT Token
3. **Token**: Sent in every request → `Authorization: Bearer {token}`
4. **Analysis**: Automatically linked to logged-in user
5. **Logout**: Clear token from storage

---

## ✅ Verification Steps

After setup, verify each part works:

### 1. Database Created
```sql
-- In Supabase, run:
SELECT * FROM users;
-- Should return empty table (before signup)
```

### 2. Backend Running
```
http://localhost:8000/health
-- Should show: {"status": "healthy", ...}
```

### 3. Frontend Running
```
http://localhost:3000
-- Should load without errors
```

### 4. Full Flow Test
- Sign up with `test@test.com`
- Check Supabase users table - new user exists
- Run an analysis
- Check analysis_sessions table - has your user_id
- Logout
- Sign in with same email
- Your analysis shows in dropdown

---

## 🆘 Common Issues

### "No such table: users"
- Run SQL in Step 1 again
- Check you're in the right Supabase project

### "ModuleNotFoundError: No module named 'bcrypt'"
- Run: `pip install bcrypt PyJWT`
- Restart backend

### "Unauthorized" on API calls
- Check token in browser DevTools → Application → localStorage
- Should have `token` key with long string

### "CORS Error"
- Backend CORS already enabled in code
- Check SUPABASE_URL and SUPABASE_KEY are correct

---

## 📱 Mobile/Login Flow

**Before Authentication:**
- Landing page → Get Started → Analysis

**After Authentication:**
- Landing page → Get Started → **Login/Signup** → Analysis

This is the new Step 1!

---

## 🔐 Security Notes

- Passwords are hashed (bcrypt), never stored plain
- Tokens expire after 24 hours
- Each user can only see their own analyses
- All API calls require Bearer token

---

## 📚 More Info

- Full guide: `AUTHENTICATION_GUIDE.md`
- Implementation details: `IMPLEMENTATION_SUMMARY.md`
- Backend auth code: Check `app.py` lines ~140-250
- Frontend auth: `src/contexts/AuthContext.tsx`

---

## 🎯 Next Steps

After basic setup works:

1. ✅ Test signup/login thoroughly
2. ✅ Test analysis persistence
3. ✅ Test logout
4. ✅ Test user isolation (different users see different analyses)
5. ✅ Consider adding OAuth (Google login)
6. ✅ Consider adding password reset email

---

**Setup Time**: ~5 minutes
**Last Updated**: December 19, 2024
