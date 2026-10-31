"use client";

import { LuLogOut } from "react-icons/lu";

export default function LogoutButton() {
  const logout = async () => {
    await fetch("/api/auth/logout", { method: "POST" });
    window.location.href = "/login";
  };
  return (
    <button onClick={logout} className="flex items-center gap-2 text-sm text-teal-200 hover:text-white">
      <LuLogOut /> Sign out
    </button>
  );
}
