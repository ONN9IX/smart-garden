export const PRODUCT_FEATURES = {
  polls: false,
  incidents: false,
  diary: false,
  photos: false,
  documentNotices: false,
  contractsBilling: false,
  entryKiosk: false,
  developmentSupport: false,
  tenantSubscription: false,
} as const;

export type ProductFeature = keyof typeof PRODUCT_FEATURES;

export function featureEnabled(feature: ProductFeature): boolean {
  return PRODUCT_FEATURES[feature];
}

const DISABLED_ROUTES: ReadonlyArray<[string, ProductFeature]> = [
  ["/polls", "polls"],
  ["/incidents", "incidents"],
  ["/diary", "diary"],
  ["/document-notices", "documentNotices"],
  ["/photo-consents", "photos"],
  ["/teacher/polls", "polls"],
  ["/teacher/incidents", "incidents"],
  ["/teacher/diary", "diary"],
  ["/teacher/photos", "photos"],
];

export function routeEnabled(pathname: string): boolean {
  return !DISABLED_ROUTES.some(([prefix, feature]) =>
    pathname.startsWith(prefix) && !featureEnabled(feature),
  );
}
