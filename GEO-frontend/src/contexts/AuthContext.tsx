"use client";

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from "react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ─── Types ────────────────────────────────────────────────────────────────────

interface SubscriptionStatus {
  is_active: boolean;
  subscription_plan: string | null;
  subscription_status: string | null;
  subscription_start: string | null;
  subscription_end: string | null;
  billing_cycle: string | null;
}

const DEFAULT_SUBSCRIPTION: SubscriptionStatus = {
  is_active: false,
  subscription_plan: null,
  subscription_status: null,
  subscription_start: null,
  subscription_end: null,
  billing_cycle: null,
};

interface AuthContextType {
  isAuthenticated: boolean;
  userId: string | null;
  email: string | null;
  token: string | null;
  subscription: SubscriptionStatus;
  isLoading: boolean;
  login: (token: string, userId: string, email: string, subscription?: SubscriptionStatus) => void;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

// ─── Context ──────────────────────────────────────────────────────────────────

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// ─── Provider ─────────────────────────────────────────────────────────────────

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userId, setUserId] = useState<string | null>(null);
  const [email, setEmail] = useState<string | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [subscription, setSubscription] = useState<SubscriptionStatus>(DEFAULT_SUBSCRIPTION);
  const [isLoading, setIsLoading] = useState(true);

  // ── Internal helper: fetch both /api/auth/me AND /api/payments/subscription-status concurrently ──
  const fetchUserProfile = useCallback(async (storedToken: string) => {
    try {
      const headers = { Authorization: `Bearer ${storedToken}` };
      const [meRes, subRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/auth/me`, { headers }),
        fetch(`${API_BASE_URL}/api/payments/subscription-status`, { headers }),
      ]);

      if (!meRes.ok) throw new Error("Token invalid or expired");

      const subData = subRes.ok ? await subRes.json() : null;
      const subscriptionData: SubscriptionStatus =
        subData?.subscription ?? DEFAULT_SUBSCRIPTION;

      setSubscription(subscriptionData);
    } catch (err) {
      console.error("Auth profile fetch failed:", err);
      // Don't force logout here — token may still be valid for other purposes
      setSubscription(DEFAULT_SUBSCRIPTION);
    }
  }, []);

  // ── Load auth state from localStorage on mount ────────────────────────────
  useEffect(() => {
    const storedToken = localStorage.getItem("token");
    const storedUserId = localStorage.getItem("userId");
    const storedEmail = localStorage.getItem("userEmail");

    if (storedToken && storedUserId) {
      setToken(storedToken);
      setUserId(storedUserId);
      setEmail(storedEmail);
      setIsAuthenticated(true);

      // Fetch latest subscription from the server (source of truth)
      fetchUserProfile(storedToken).finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, [fetchUserProfile]);

  // ── login: called right after successful auth response ────────────────────
  const login = (
    newToken: string,
    newUserId: string,
    newEmail: string,
    newSubscription: SubscriptionStatus = DEFAULT_SUBSCRIPTION
  ) => {
    localStorage.setItem("token", newToken);
    localStorage.setItem("userId", newUserId);
    localStorage.setItem("userEmail", newEmail);

    try {
      document.cookie = `token=${newToken}; path=/`;
    } catch (e) {
      // ignore in non-browser environments
    }

    setToken(newToken);
    setUserId(newUserId);
    setEmail(newEmail);
    setSubscription(newSubscription);
    setIsAuthenticated(true);
  };

  // ── logout ────────────────────────────────────────────────────────────────
  const logout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("userId");
    localStorage.removeItem("userEmail");

    try {
      document.cookie = `token=; Max-Age=0; path=/`;
    } catch (e) { }

    setToken(null);
    setUserId(null);
    setEmail(null);
    setSubscription(DEFAULT_SUBSCRIPTION);
    setIsAuthenticated(false);
  };

  // ── refreshUser: called by pricing page after payment to force-sync state ──
  const refreshUser = useCallback(async () => {
    const storedToken = localStorage.getItem("token");
    if (!storedToken) return;
    await fetchUserProfile(storedToken);
  }, [fetchUserProfile]);

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated,
        userId,
        email,
        token,
        subscription,
        isLoading,
        login,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
