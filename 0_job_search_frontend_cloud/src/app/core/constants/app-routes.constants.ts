export const APP_ROUTES = {
  dashboard: '/dashboard',
  jobs: {
    recommended: '/jobs/recommended',
    list: '/jobs/list',
    saved: '/jobs/saved',
    applied: '/jobs/applied',
    details: (id: string) => `/jobs/${id}`
  },
  resume: {
    upload: '/resume/upload',
    profile: '/resume/profile',
    matching: '/resume/matching',
    preview: '/resume/preview'
  },
  settings: {
    profile: '/settings/profile',
    preferences: '/settings/preferences',
    companies: '/settings/companies',
    notifications: '/settings/notifications',
    account: '/settings/account'
  },
  analytics: '/analytics',
  admin: '/admin'
} as const;

export const CANDIDATE_ID = 'candidate-001';
