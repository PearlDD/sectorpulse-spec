import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import Dashboard from "./pages/Dashboard";

function Placeholder({ title }: { title: string }) {
  return (
    <div className="flex items-center justify-center py-32 text-slate-400">
      {title} — coming soon
    </div>
  );
}

const NAV_ITEMS = [
  { to: "/", label: "Dashboard" },
  { to: "/rrg", label: "RRG Chart" },
  { to: "/history", label: "History" },
];

function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <nav className="border-b border-slate-800 bg-gray-950/80 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center gap-8 px-6 py-3">
          <span className="text-lg font-bold tracking-tight text-indigo-400">
            SectorPulse
          </span>
          <div className="flex gap-1">
            {NAV_ITEMS.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                end={to === "/"}
                className={({ isActive }) =>
                  `rounded-md px-3 py-1.5 text-sm font-medium transition ${
                    isActive
                      ? "bg-slate-800 text-white"
                      : "text-slate-400 hover:text-slate-200"
                  }`
                }
              >
                {label}
              </NavLink>
            ))}
          </div>
        </div>
      </nav>
      <main className="mx-auto max-w-7xl px-6 py-6">{children}</main>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/rrg" element={<Placeholder title="RRG Chart" />} />
          <Route path="/history" element={<Placeholder title="History" />} />
          <Route
            path="/report/:id"
            element={<Placeholder title="Report Detail" />}
          />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
