import { Routes } from '@angular/router';
import { MainLayoutComponent } from './core/layouts/main-layout/main-layout.component';

export const routes: Routes = [
  {
    path: '',
    component: MainLayoutComponent,
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
      {
        path: 'dashboard',
        loadComponent: () =>
          import('./features/dashboard/dashboard.component').then((m) => m.DashboardComponent)
      },
      {
        path: 'jobs/recommended',
        loadComponent: () =>
          import('./features/jobs/recommended-jobs/recommended-jobs.component').then(
            (m) => m.RecommendedJobsComponent
          )
      },
      {
        path: 'jobs/list',
        loadComponent: () =>
          import('./features/jobs/job-list/job-list.component').then((m) => m.JobListComponent)
      },
      {
        path: 'jobs/saved',
        loadComponent: () =>
          import('./features/jobs/saved-jobs/saved-jobs.component').then((m) => m.SavedJobsComponent)
      },
      {
        path: 'jobs/applied',
        loadComponent: () =>
          import('./features/jobs/applied-jobs/applied-jobs.component').then((m) => m.AppliedJobsComponent)
      },
      {
        path: 'jobs/:id',
        loadComponent: () =>
          import('./features/jobs/job-details/job-details.component').then((m) => m.JobDetailsComponent)
      },
      {
        path: 'resume/upload',
        loadComponent: () =>
          import('./features/resume/upload/upload.component').then((m) => m.UploadComponent)
      },
      {
        path: 'resume/profile',
        loadComponent: () =>
          import('./features/resume/resume-profile/resume-profile.component').then(
            (m) => m.ResumeProfileComponent
          )
      },
      {
        path: 'resume/matching',
        loadComponent: () =>
          import('./features/resume/resume-matching/resume-matching.component').then(
            (m) => m.ResumeMatchingComponent
          )
      },
      {
        path: 'resume/preview',
        loadComponent: () =>
          import('./features/resume/resume-preview/resume-preview.component').then(
            (m) => m.ResumePreviewComponent
          )
      },
      {
        path: 'settings/profile',
        loadComponent: () =>
          import('./features/settings/profile/settings-profile.component').then(
            (m) => m.SettingsProfileComponent
          )
      },
      {
        path: 'settings/preferences',
        loadComponent: () =>
          import('./features/settings/preferences/settings-preferences.component').then(
            (m) => m.SettingsPreferencesComponent
          )
      },
      {
        path: 'settings/companies',
        loadComponent: () =>
          import('./features/settings/companies/settings-companies.component').then(
            (m) => m.SettingsCompaniesComponent
          )
      },
      {
        path: 'settings/notifications',
        loadComponent: () =>
          import('./features/settings/notifications/settings-notifications.component').then(
            (m) => m.SettingsNotificationsComponent
          )
      },
      {
        path: 'settings/account',
        loadComponent: () =>
          import('./features/settings/account/settings-account.component').then(
            (m) => m.SettingsAccountComponent
          )
      },
      {
        path: 'analytics',
        loadComponent: () => import('./features/analytics/analytics.component').then((m) => m.AnalyticsComponent)
      },
      {
        path: 'admin',
        loadComponent: () => import('./features/admin/admin.component').then((m) => m.AdminComponent)
      }
    ]
  },
  { path: '**', redirectTo: 'dashboard' }
];
