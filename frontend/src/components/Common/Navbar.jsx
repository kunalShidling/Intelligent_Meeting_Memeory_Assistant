import { Link, useLocation } from 'react-router-dom';
import { Home, Users, Settings, Video } from 'lucide-react';

export default function Navbar() {
  const location = useLocation();

  const isActive = (path) => {
    return location.pathname === path;
  };

  return (
    <nav className="sticky top-0 z-40 border-b border-amber-100/70 bg-[#f6f3ee]/85 backdrop-blur">
      <div className="mx-auto w-full max-w-6xl px-6">
        <div className="flex flex-wrap items-center justify-between gap-4 py-4">
          <Link to="/" className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-teal-500 to-emerald-400 text-white shadow-sm">
              <Video className="h-5 w-5" />
            </span>
            <div className="leading-tight">
              <span className="text-[0.6rem] uppercase tracking-[0.35em] text-slate-500">Meeting</span>
              <span className="block text-lg font-semibold text-slate-900">Assistant</span>
            </div>
          </Link>

          <div className="flex flex-wrap items-center gap-2 rounded-full border border-amber-100 bg-white/70 px-2 py-1 shadow-sm">
            <Link
              to="/"
              className={`flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition ${
                isActive('/')
                  ? 'bg-slate-900 text-white shadow'
                  : 'text-slate-600 hover:bg-white hover:text-slate-900'
              }`}
            >
              <Home className="h-4 w-4" />
              <span>Home</span>
            </Link>

            <Link
              to="/people"
              className={`flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition ${
                isActive('/people')
                  ? 'bg-slate-900 text-white shadow'
                  : 'text-slate-600 hover:bg-white hover:text-slate-900'
              }`}
            >
              <Users className="h-4 w-4" />
              <span>People</span>
            </Link>

            <Link
              to="/settings"
              className={`flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition ${
                isActive('/settings')
                  ? 'bg-slate-900 text-white shadow'
                  : 'text-slate-600 hover:bg-white hover:text-slate-900'
              }`}
            >
              <Settings className="h-4 w-4" />
              <span>Settings</span>
            </Link>
          </div>

          <Link
            to="/start-meeting"
            className="flex items-center gap-2 rounded-full bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-slate-900/20 transition hover:-translate-y-0.5 hover:bg-slate-800"
          >
            <Video className="h-4 w-4" />
            <span>Start Meeting</span>
          </Link>
        </div>
      </div>
    </nav>
  );
}
