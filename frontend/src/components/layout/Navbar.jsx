import React, { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

export default function Navbar() {
  const { user, logout } = useAuth();
  const { pathname } = useLocation();
  const [open, setOpen] = useState(false);

  const navLink = (to, label) => (
    <Link
      to={to}
      onClick={() => setOpen(false)}
      className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
        pathname === to
          ? "bg-green-700 text-white"
          : "text-green-100 hover:bg-green-700 hover:text-white"
      }`}
    >
      {label}
    </Link>
  );

  return (
    <nav className="bg-green-800 shadow-lg">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center space-x-2">
            <span className="text-2xl">♻️</span>
            <span className="text-white font-bold text-xl">EcoStream AI</span>
          </Link>

          {/* Desktop nav */}
          <div className="hidden md:flex items-center space-x-2">
            {navLink("/", "Home")}
            {navLink("/scan", "Scan Waste")}
            {user?.role === "admin" || user?.role === "government"
              ? navLink("/dashboard", "Dashboard")
              : null}
            {navLink("/about", "About")}
            {user ? (
              <div className="flex items-center space-x-3 ml-4">
                <span className="text-green-200 text-sm">{user.username}</span>
                <button
                  onClick={logout}
                  className="bg-green-600 hover:bg-green-500 text-white text-sm px-3 py-1.5 rounded-md"
                >
                  Logout
                </button>
              </div>
            ) : (
              <Link
                to="/login"
                className="ml-4 bg-white text-green-800 font-semibold text-sm px-4 py-1.5 rounded-md hover:bg-green-50"
              >
                Login
              </Link>
            )}
          </div>

          {/* Mobile hamburger */}
          <button
            className="md:hidden text-white p-2"
            onClick={() => setOpen(!open)}
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              {open
                ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              }
            </svg>
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {open && (
        <div className="md:hidden px-4 pb-4 space-y-1">
          {navLink("/", "Home")}
          {navLink("/scan", "Scan Waste")}
          {(user?.role === "admin" || user?.role === "government") && navLink("/dashboard", "Dashboard")}
          {navLink("/about", "About")}
          {user ? (
            <button onClick={logout} className="w-full text-left text-green-100 px-3 py-2 text-sm">
              Logout ({user.username})
            </button>
          ) : (
            <Link to="/login" className="block text-green-100 px-3 py-2 text-sm" onClick={() => setOpen(false)}>
              Login
            </Link>
          )}
        </div>
      )}
    </nav>
  );
}
