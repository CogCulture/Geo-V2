import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Eye, EyeOff, Loader2, AlertCircle } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/contexts/AuthContext";
import { GoogleLogin, CredentialResponse } from "@react-oauth/google";

interface SignupPageProps {
  onSuccess: (token: string, userId: string) => void;
}

export function SignupPage({ onSuccess }: SignupPageProps) {
  const { toast } = useToast();
  const { login } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isSignUp, setIsSignUp] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const validateForm = () => {
    setError("");

    if (!email.trim()) {
      setError("Email is required");
      return false;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      setError("Please enter a valid email");
      return false;
    }

    if (!password.trim()) {
      setError("Password is required");
      return false;
    }

    if (password.length < 6) {
      setError("Password must be at least 6 characters");
      return false;
    }

    if (isSignUp && password !== confirmPassword) {
      setError("Passwords do not match");
      return false;
    }

    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setIsLoading(true);

    try {
      const endpoint = isSignUp ? "/api/auth/signup" : "/api/auth/login";
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email,
          password,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        setError(data.detail || (isSignUp ? "Signup failed" : "Login failed"));
        toast({
          id: "signup-error",
          title: "Error",
          description: data.detail || (isSignUp ? "Signup failed" : "Login failed"),
          variant: "destructive",
        });
        return;
      }

      // Store token and user info
      localStorage.setItem("token", data.token);
      localStorage.setItem("userId", data.user_id);
      localStorage.setItem("userEmail", data.email);

      // Update auth context
      login(data.token, data.user_id, data.email, data.subscription);

      toast({
        id: "signup-success",
        title: "Success",
        description: data.message,
        variant: "default",
      });

      onSuccess(data.token, data.user_id);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "An error occurred";
      setError(errorMessage);
      toast({
        id: "signup-catch-error",
        title: "Error",
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleSuccess = async (credentialResponse: CredentialResponse) => {
    if (!credentialResponse.credential) {
      toast({
        id: "google-error",
        title: "Google Login Failed",
        description: "No credentials returned from Google.",
        variant: "destructive",
      });
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/google`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: credentialResponse.credential }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Google authentication failed");
      }

      login(data.token, data.user_id, data.email, data.subscription);
      toast({
        id: "google-success",
        title: "Success",
        description: "Successfully signed in with Google",
      });
      onSuccess(data.token, data.user_id);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "An error occurred during Google sign-in";
      toast({
        id: "google-auth-error",
        title: "Google Error",
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-80px)] w-full flex flex-col items-center justify-center bg-gray-50/50 p-4">
      <div className="w-full max-w-[480px] bg-white rounded-2xl shadow-sm border border-gray-100 p-8 md:p-10">
        {/* Header Section */}
        <div className="flex flex-col items-center mb-8">
          <div className="h-12 w-12 bg-gray-50 rounded-xl flex items-center justify-center mb-4">
            <img
              src="favicon.png"
              alt="Logo"
              className="h-10 w-10 object-contain"
              onError={(e) => {
                e.currentTarget.style.display = "none";
              }}
            />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">
            {isSignUp ? "Create Account" : "Welcome Back"}
          </h1>
          <p className="text-sm text-gray-500 mt-2">
            {isSignUp
              ? "Get started with AI visibility analytics"
              : "Access your brand visibility analysis"}
          </p>
        </div>

        {/* Error Display */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {/* Social Login */}
        <div className="w-full flex justify-center mb-6">
          <GoogleLogin
            onSuccess={handleGoogleSuccess}
            onError={() => {
              toast({
                id: "google-lib-error",
                title: "Google Login Failed",
                description: "An error occurred with the Google Login library.",
                variant: "destructive",
              });
            }}
            useOneTap={false}
            theme="outline"
            size="large"
            width="400"
            shape="rectangular"
            text="continue_with"
          />
        </div>

        {/* Divider */}
        <div className="relative mb-8">
          <div className="absolute inset-0 flex items-center">
            <span className="w-full border-t border-gray-100" />
          </div>
          <div className="relative flex justify-center text-xs uppercase tracking-widest font-bold">
            <span className="bg-white px-4 text-gray-400">Or continue with email</span>
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-semibold text-gray-900">
              Email Address
            </label>
            <Input
              type="email"
              placeholder="Enter your email"
              className="h-12 bg-white border-gray-200 focus:border-gray-900 focus:ring-gray-900 rounded-lg text-base"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                setError("");
              }}
              disabled={isLoading}
              required
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-semibold text-gray-900">Password</label>
            <div className="relative">
              <Input
                type={showPassword ? "text" : "password"}
                placeholder="Enter your password"
                className="h-12 bg-white border-gray-200 focus:border-gray-900 focus:ring-gray-900 rounded-lg text-base pr-10"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  setError("");
                }}
                disabled={isLoading}
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 disabled:opacity-50"
                disabled={isLoading}
              >
                {showPassword ? (
                  <EyeOff className="h-5 w-5" />
                ) : (
                  <Eye className="h-5 w-5" />
                )}
              </button>
            </div>
          </div>

          {isSignUp && (
            <div className="space-y-2">
              <label className="text-sm font-semibold text-gray-900">
                Confirm Password
              </label>
              <div className="relative">
                <Input
                  type={showConfirmPassword ? "text" : "password"}
                  placeholder="Confirm your password"
                  className="h-12 bg-white border-gray-200 focus:border-gray-900 focus:ring-gray-900 rounded-lg text-base pr-10"
                  value={confirmPassword}
                  onChange={(e) => {
                    setConfirmPassword(e.target.value);
                    setError("");
                  }}
                  disabled={isLoading}
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 disabled:opacity-50"
                  disabled={isLoading}
                >
                  {showConfirmPassword ? (
                    <EyeOff className="h-5 w-5" />
                  ) : (
                    <Eye className="h-5 w-5" />
                  )}
                </button>
              </div>
            </div>
          )}

          <Button
            type="submit"
            disabled={isLoading}
            className="w-full h-12 text-base font-medium bg-[#1a1f2e] hover:bg-black text-white mt-2 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                {isSignUp ? "Creating account..." : "Signing in..."}
              </>
            ) : isSignUp ? (
              "Create Account"
            ) : (
              "Sign In"
            )}
          </Button>
        </form>

        {/* Toggle Sign Up / Login */}
        <div className="mt-6 text-center">
          <p className="text-sm text-gray-500">
            {isSignUp ? "Already have an account? " : "Don't have an account? "}
            <button
              onClick={() => {
                setIsSignUp(!isSignUp);
                setError("");
                setEmail("");
                setPassword("");
                setConfirmPassword("");
              }}
              className="font-semibold text-gray-900 hover:underline disabled:opacity-50"
              disabled={isLoading}
            >
              {isSignUp ? "Sign In" : "Sign Up"}
            </button>
          </p>
        </div>
      </div>

      <div className="mt-8 text-center space-y-2">
        <p className="text-xs text-gray-400">
          By continuing, you agree to our{" "}
          <a href="#" className="hover:text-gray-600">
            Terms of Service
          </a>{" "}
          and{" "}
          <a href="#" className="hover:text-gray-600">
            Privacy Policy
          </a>
        </p>
      </div>
    </div>
  );
}
