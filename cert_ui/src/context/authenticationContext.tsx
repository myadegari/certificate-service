import React, { createContext, useContext, useReducer, useState } from "react";
import { useNavigate } from "react-router";
import { toast } from "react-toastify";
import { useQueryClient } from "@tanstack/react-query";
import { jwtDecode, type JwtPayload } from "jwt-decode";

import { AuthenticationMessages } from "@/constant/toastMessages";
import RoutesPaths from "@/core/routes";

interface myJwtDecode extends JwtPayload {
  user_id: string;
  role: string;
}
interface props {
  children: React.ReactNode;
}
interface State {
  accessToken: string | null;
  refreshToken: string | null;
  accountID: string | null;
  accountType: string | null;
}
interface Actions {
  type: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  payload: any;
}
interface IAuthContext {
  Auth: State;
  isLoading: boolean;
  AuthDispatch: (action: Actions) => void;
  logoutUser: () => void;
  userLogin: (res: any, from: string) => void;
}
function AuthReducer(state: State, action: Actions) {
  switch (action.type) {
    case "SET_ACCESS_TOKEN":
      return {
        ...state,
        accessToken: action.payload,
      };
    case "SET_AUTH_TOKENS":
      return {
        ...state,
        accessToken: action.payload.accessToken,
        refreshToken: action.payload.refreshToken,
      };
    case "SET_ACCOUNT":
      return {
        ...state,
        accountID: action.payload.accountID,
        accountType: action.payload.accountType,
      };
    default:
      return state;
  }
}
export const AuthenticationContext = createContext<IAuthContext | undefined>(undefined);

export default function AuthenticationProvider({ children }: props) {
  const [isLoading, setIsLoading] = useState(true);
  const [Auth, AuthDispatch] = useReducer(AuthReducer, {
    accessToken: null,
    refreshToken: null,
    accountID: null,
    accountType: null,
  });
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  async function userLogin(res: any, from: string) {
    setIsLoading(true);
    const accessToken = res?.data.accessToken;
    const refreshToken = res?.data.refreshToken;
    const decode = jwtDecode<myJwtDecode>(accessToken);
    if (accessToken) {
      localStorage.setItem("accessToken", accessToken);
      sessionStorage.setItem("refreshToken", refreshToken);
      AuthDispatch({
        type: "SET_AUTH_TOKENS",
        payload: {
          accessToken: accessToken,
          refreshToken: refreshToken,
        },
      });
      AuthDispatch({
        type: "SET_ACCOUNT",
        payload: {
          accountID: decode.user_id,
          accountType: decode.role,
        },
      });
      setIsLoading(false);
      toast.success(AuthenticationMessages.login.loginSuccess);
      if (from == RoutesPaths.user_panel) {
        navigate(from, { replace: true, state: { preserveFilters: true } });
      } else {
        navigate(from, { replace: true });
      }
    }
  }

  function logoutUser() {
    localStorage.removeItem("accessToken");
    sessionStorage.removeItem("refreshToken");
    AuthDispatch({
      type: "SET_AUTH_TOKENS",
      payload: { accessToken: null, refreshToken: null },
    });
    queryClient.clear();
  }

  return (
    <AuthenticationContext.Provider
      value={{
        Auth,
        AuthDispatch,
        logoutUser,
        userLogin,
        isLoading,
      }}
    >
      {children}
    </AuthenticationContext.Provider>
  );
}

export function useAuthentication() {
  const context = useContext(AuthenticationContext);
  if (!context) {
    throw new Error(
      "useAuthentication must be used within a AuthenticationProvider",
    );
  }
  return context;
}