export type PlatformIdentity = {
  username: string;
  role: "PLATFORM_OWNER";
  csrf_token: string;
  credential_handoff_enabled: boolean;
  step_up_required: boolean;
};
export type Subscription = {
  status:
    | "trial"
    | "active"
    | "past_due"
    | "cancel_at_period_end"
    | "cancelled";
  plan_code: "standard";
  currency: "RUB";
  interval: "monthly" | "half_year" | "yearly";
  price_minor: number;
  trial_ends_at: string | null;
  period_start: string | null;
  period_end: string | null;
};
export type PlatformOrganization = {
  id: string;
  name: string;
  timezone: string;
  status: "active" | "blocked" | "archived";
  created_at: string;
  onboarding_status: string;
  operating_profile: "KINDERGARTEN" | "GYMNASTICS";
  subscription: Subscription | null;
};
export type PlatformAudit = {
  id: string;
  action: string;
  organization_id: string | null;
  operator_id: string | null;
  created_at: string;
  details: Record<string, unknown>;
};
export type PlatformOverview = {
  organizations: Record<string, number>;
  subscriptions: Record<string, number>;
  pending_director_setup: number;
};
export type CreateOrganization = {
  idempotency_key: string;
  name: string;
  timezone: string;
  operating_profile: "KINDERGARTEN" | "GYMNASTICS";
  director_username: string;
  credential_handoff_confirmed: true;
  subscription: Subscription;
};
export type Provisioning = {
  organization: PlatformOrganization;
  replayed: boolean;
  temporary_password?: string;
};
