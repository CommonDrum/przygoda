import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Layout() {
  const { pathname } = useLocation();
  const { logout } = useAuth();
  const navigate = useNavigate();

  const navLink = (to: string, label: string, icon: string) => {
    const active = pathname === to || (to === "/" && pathname === "/");
    return (
      <Link
        to={to}
        className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-sm font-semibold transition-all duration-200 ${
          active
            ? "bg-cream-50/15 text-cream-100"
            : "text-cream-200 hover:text-cream-50 hover:bg-cream-50/8"
        }`}
      >
        <span className="text-base">{icon}</span>
        {label}
      </Link>
    );
  };

  return (
    <div className="min-h-screen bg-cream-100 paper-grain">
      <header className="bg-bark-700 text-cream-50 shadow-lg shadow-bark-700/20">
        <div className="max-w-6xl mx-auto px-5 py-3.5 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5 group">
            <span className="text-2xl" role="img" aria-label="book">
              &#x1F4D6;
            </span>
            <span className="font-display text-xl font-bold tracking-tight text-cream-50 group-hover:text-amber-400 transition-colors duration-200">
              Przygoda
            </span>
          </Link>
          <nav className="flex gap-1.5 items-center">
            {navLink("/", "Projekty", "\u2302")}
            {navLink("/settings", "Opcje", "\u2699")}
            <button
              onClick={() => { logout(); navigate("/login"); }}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-sm font-semibold text-cream-200 hover:text-cream-50 hover:bg-cream-50/8 transition-all duration-200"
            >
              Wyloguj
            </button>
          </nav>
        </div>
      </header>
      <main className="max-w-6xl mx-auto px-5 py-8">
        <Outlet />
      </main>
    </div>
  );
}
