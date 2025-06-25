import { jwtDecode } from "jwt-decode";

import { GeneralClient } from "@/api/axios";
import { USER_REFRESH_TOKEN_URL } from "@/api/server";
import { useAuthentication } from "@/context/authenticationContext";
import type { myJwtDecode } from "@/core/types";

const useRefreshToken = () => {
  const { AuthDispatch } = useAuthentication();
  const refreshToken = sessionStorage.getItem("refreshToken");
  const refresh = async () => {
    const response = await GeneralClient.post(USER_REFRESH_TOKEN_URL, {
      refresh: refreshToken,
    });
    const decode = jwtDecode<myJwtDecode>(response.data.access);
    AuthDispatch({ type: "SET_ACCESS_TOKEN", payload: response.data.access });
    AuthDispatch({
      type: "SET_ACCOUNT",
      payload: {
        accountID: decode.user_id,
        accountType: decode.role,
      },
    });
    return response.data.access;
  };

  return refresh;
};

export default useRefreshToken;