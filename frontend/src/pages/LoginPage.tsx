import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(username, password);
      navigate("/", { replace: true });
    } catch {
      setError("Niepoprawne dane logowania");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-cream-100 paper-grain flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <span className="text-4xl">&#x1F4D6;</span>
          <h1 className="font-display text-3xl font-bold text-bark-700 mt-2">
            Przygoda
          </h1>
        </div>

        <form
          onSubmit={handleSubmit}
          className="bg-white rounded-2xl shadow-lg p-6 space-y-4"
        >
          {error && (
            <div className="text-rose-500 text-sm text-center font-semibold">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-semibold text-bark-500 mb-1">
              Login
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-bark-200 bg-cream-50 focus:outline-none focus:ring-2 focus:ring-bark-400 text-bark-700"
              required
              autoFocus
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-bark-500 mb-1">
              Has\u0142o
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-bark-200 bg-cream-50 focus:outline-none focus:ring-2 focus:ring-bark-400 text-bark-700"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 rounded-lg bg-bark-700 text-cream-50 font-semibold hover:bg-bark-600 transition-colors disabled:opacity-50"
          >
            {loading ? "Logowanie..." : "Zaloguj"}
          </button>
        </form>
      </div>
    </div>
  );
}
