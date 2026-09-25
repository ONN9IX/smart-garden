/**
 * Stage 1 transport types.
 * Source of truth: docs/03-api-contract-v0.1.md; keep JSON names unchanged.
 */
export const ROLES = {
  DIRECTOR: "DIRECTOR",
  ADMIN: "ADMIN",
} as const;

export type Role = (typeof ROLES)[keyof typeof ROLES];

export interface AuthContext {
  user: {
    id: string;
    username: string;
    role: Role;
    status: "active" | "blocked";
    must_change_password: boolean;
  };
  organization: {
    id: string;
    name: string;
  };
}

export interface ChangePasswordResult {
  success: true;
  must_change_password: false;
}

export interface LogoutResult {
  success: true;
}

export const ROLE_LABELS: Record<Role, string> = {
  [ROLES.DIRECTOR]: "Директор",
  [ROLES.ADMIN]: "Администратор",
};


/**
 * Centralized frontend role check for role-aware rendering.
 * Security: this only controls UI visibility; Backend remains the authorization source of truth.
 */
export function hasRole(role: Role, allowedRoles: readonly Role[]): boolean {
  return allowedRoles.includes(role);
}
