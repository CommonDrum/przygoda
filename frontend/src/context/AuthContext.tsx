import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import { getToken, setToken, clearToken } from "../lib/auth";
import { loginApi } from "../lib/api";

interface AuthContextType {
  isLoggedIn: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>(null!);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isLoggedIn, setIsLoggedIn] = useState(() => !!getToken());

  const login = useCallback(async (username: string, password: string) => {
    const { access_token } = await loginApi(username, password);
    setToken(access_token);
    setIsLoggedIn(true);
  }, []);

  const logout = useCallback(() => {
    clearToken();
    setIsLoggedIn(false);
  }, []);

  return (
    <AuthContext.Provider value={{ isLoggedIn, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
