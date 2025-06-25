import type { JwtPayload } from "jwt-decode";


export interface myJwtDecode extends JwtPayload {
    user_id: string;
    role: string;
  }