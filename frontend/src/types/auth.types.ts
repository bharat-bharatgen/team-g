export interface User {
  id: string;
  name: string;
  phone_number: string;
}

export interface SignupRequest {
  name: string;
  phone_number: string;
  password: string;
}

export interface SigninRequest {
  phone_number: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user?: User;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (token: string, user: User) => void;
  logout: () => void;
  setUser: (user: User) => void;
}
