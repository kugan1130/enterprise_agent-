import React, { useState, FormEvent } from "react";
import { User } from "../../types";
import { authService } from "../../services/authService";

interface AuthModalProps {
  onAuthSuccess: (user: User) => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({ onAuthSuccess }) => {
  const [activeTab, setActiveTab] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const resetForm = () => {
    setError(null);
    setSuccessMsg(null);
  };

  const handleTabSwitch = (tab: "login" | "register") => {
    setActiveTab(tab);
    resetForm();
  };

  const handleLoginSubmit = async (e: FormEvent) => {
    e.preventDefault();
    resetForm();

    if (!username.trim() || !password.trim()) {
      setError("Please fill in both username and password.");
      return;
    }

    setLoading(true);
    try {
      const response = await authService.login(username.trim(), password.trim());
      onAuthSuccess(response.user);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to sign in.");
    } finally {
      setLoading(false);
    }
  };

  const handleRegisterSubmit = async (e: FormEvent) => {
    e.preventDefault();
    resetForm();

    if (!username.trim() || !email.trim() || !password.trim()) {
      setError("Please fill in all registration fields.");
      return;
    }

    if (password.length < 6) {
      setError("Password must be at least 6 characters long.");
      return;
    }

    setLoading(true);
    try {
      await authService.register(username.trim(), email.trim(), password.trim());
      setSuccessMsg("Account created successfully! Redirecting to sign in...");
      setTimeout(() => {
        setSuccessMsg(null);
        setActiveTab("login");
      }, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-modal-overlay">
      <div className="auth-card">
        <div className="auth-header">
          <div className="auth-logo">
            <i className="fa-solid fa-robot"></i>
          </div>
          <h2>Enterprise AI Assistant</h2>
          <p>Sign in or create an employee account</p>
        </div>

        <div className="auth-tabs">
          <button
            type="button"
            className={`tab-btn ${activeTab === "login" ? "active" : ""}`}
            onClick={() => handleTabSwitch("login")}
          >
            Sign In
          </button>
          <button
            type="button"
            className={`tab-btn ${activeTab === "register" ? "active" : ""}`}
            onClick={() => handleTabSwitch("register")}
          >
            Create Account
          </button>
        </div>

        {error && <div className="error-banner">{error}</div>}
        {successMsg && <div className="success-banner">{successMsg}</div>}

        {activeTab === "login" ? (
          <form className="auth-form active" onSubmit={handleLoginSubmit}>
            <div className="input-group">
              <label htmlFor="login-username">Username or Email</label>
              <div className="input-wrapper">
                <i className="fa-solid fa-user"></i>
                <input
                  id="login-username"
                  type="text"
                  placeholder="Enter your username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  disabled={loading}
                  required
                />
              </div>
            </div>

            <div className="input-group">
              <label htmlFor="login-password">Password</label>
              <div className="input-wrapper">
                <i className="fa-solid fa-lock"></i>
                <input
                  id="login-password"
                  type="password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={loading}
                  required
                />
              </div>
            </div>

            <button type="submit" className="primary-btn full-width" disabled={loading}>
              {loading ? (
                <>
                  <i className="fa-solid fa-spinner fa-spin"></i> Signing In...
                </>
              ) : (
                <>
                  <span>Sign In</span> <i className="fa-solid fa-arrow-right"></i>
                </>
              )}
            </button>
          </form>
        ) : (
          <form className="auth-form active" onSubmit={handleRegisterSubmit}>
            <div className="input-group">
              <label htmlFor="reg-username">Username</label>
              <div className="input-wrapper">
                <i className="fa-solid fa-user"></i>
                <input
                  id="reg-username"
                  type="text"
                  placeholder="Choose a username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  disabled={loading}
                  required
                />
              </div>
            </div>

            <div className="input-group">
              <label htmlFor="reg-email">Work Email</label>
              <div className="input-wrapper">
                <i className="fa-solid fa-envelope"></i>
                <input
                  id="reg-email"
                  type="email"
                  placeholder="name@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={loading}
                  required
                />
              </div>
            </div>

            <div className="input-group">
              <label htmlFor="reg-password">Password</label>
              <div className="input-wrapper">
                <i className="fa-solid fa-lock"></i>
                <input
                  id="reg-password"
                  type="password"
                  placeholder="Minimum 6 characters"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={loading}
                  required
                  minLength={6}
                />
              </div>
            </div>

            <button type="submit" className="primary-btn full-width" disabled={loading}>
              {loading ? (
                <>
                  <i className="fa-solid fa-spinner fa-spin"></i> Creating Account...
                </>
              ) : (
                <>
                  <span>Create Account</span> <i className="fa-solid fa-user-plus"></i>
                </>
              )}
            </button>
          </form>
        )}
      </div>
    </div>
  );
};
