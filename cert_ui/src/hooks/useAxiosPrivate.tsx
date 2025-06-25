import { useEffect } from "react";

import { PrivateClient } from "@/api/axios";
import { useAuthentication } from "@/context/authenticationContext";
import useRefreshToken from "@/hooks/useRefreshToken";

const useAxiosPrivate = () => {
  const refresh = useRefreshToken();
  const { Auth } = useAuthentication();

  useEffect(() => {
    const requestIntercept = PrivateClient.interceptors.request.use(
      (config) => {
        if (!config.headers["Authorization"]) {
          config.headers["Authorization"] = `Bearer ${Auth.accessToken}`;
        }
        return config;
      },
      (error) => Promise.reject(error),
    );
    const responseIntercept = PrivateClient.interceptors.response.use(
      (response) => response,
      async (error) => {
        const prevRequest = error?.config;
        if (error?.response?.status === 403 && !prevRequest?.sent) {
          prevRequest.sent = true;
          const newAccessToken = await refresh();
          prevRequest.headers["Authorization"] = `Bearer ${newAccessToken}`;
          return PrivateClient(prevRequest);
        }
        return Promise.reject(error);
      },
    );
    return () => {
        PrivateClient.interceptors.request.eject(requestIntercept);
        PrivateClient.interceptors.response.eject(responseIntercept);
    };
  }, [Auth.accessToken, refresh]);

  return PrivateClient;
};

export default useAxiosPrivate;