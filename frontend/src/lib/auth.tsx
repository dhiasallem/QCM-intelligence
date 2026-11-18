"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, setToken, clearToken, getToken } from "./api";

export interface User {
  id: number;
  name: string;
  email: string;
  role: "teacher" | "student" | "admin";
  is_active: boolean;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, pass: string) => Promise<void>;
  register: (data: { name: string; email: string; password: string; role: "teacher" | "student" }) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  login: async () => {},
  register: async () => {},
  logout: () => {},
  refreshUser: async () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  const fetchCurrentUser = async () => {
    try {
      if (!getToken()) {
        setUser(null);
        setLoading(false);
        return;
      }
      const data = await api.users.me();
      setUser(data as User);
    } catch {
      clearToken();
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCurrentUser();
  }, []);

  const login = async (email: string, pass: string) => {
    const res = await api.auth.login(email, pass);
    await startSession(res.access_token);
  };

  const register = async (data: { name: string; email: string; password: string; role: "teacher" | "student" }) => {
    const res = await api.auth.register(data);
    await startSession(res.access_token);
  };

  // Enregistre le jeton, charge le profil puis redirige vers l'espace personnel
  const startSession = async (token: string) => {
    setToken(token);
    const me = await api.users.me();
    setUser(me as User);

    if (me.role === "teacher" || me.role === "admin") {
      router.push("/teacher");
    } else {
      router.push("/student");
    }
  };

  const logout = () => {
    clearToken();
    setUser(null);
    router.push("/login");
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        register,
        logout,
        refreshUser: fetchCurrentUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
