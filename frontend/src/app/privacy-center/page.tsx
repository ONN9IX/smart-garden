"use client";
import { AuthGate } from "@/features/auth/auth-gate";
import { PrivacyCenter } from "@/features/privacy/center";

export default function PrivacyCenterPage() { return <AuthGate route="privacy"><PrivacyCenter /></AuthGate>; }
