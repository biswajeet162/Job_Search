import { Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { AsyncPipe } from '@angular/common';
import { CandidateService } from '../../services/candidate.service';

interface NavItem {
  label: string;
  route: string;
  icon: string;
}

interface NavGroup {
  title: string;
  items: NavItem[];
}

@Component({
  selector: 'app-main-layout',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, AsyncPipe],
  templateUrl: './main-layout.component.html',
  styleUrl: './main-layout.component.scss'
})
export class MainLayoutComponent {
  private readonly candidateService = inject(CandidateService);
  readonly candidate$ = this.candidateService.candidate$;

  readonly navGroups: NavGroup[] = [
    {
      title: 'Overview',
      items: [{ label: 'Dashboard', route: '/dashboard', icon: '📊' }]
    },
    {
      title: 'Jobs',
      items: [
        { label: 'Recommended', route: '/jobs/recommended', icon: '✨' },
        { label: 'All Jobs', route: '/jobs/list', icon: '📋' },
        { label: 'Saved', route: '/jobs/saved', icon: '🔖' },
        { label: 'Applied', route: '/jobs/applied', icon: '✅' }
      ]
    },
    {
      title: 'Resume',
      items: [
        { label: 'Upload', route: '/resume/upload', icon: '📄' },
        { label: 'Profile', route: '/resume/profile', icon: '👤' },
        { label: 'Matching Model', route: '/resume/matching', icon: '🎯' },
        { label: 'Preview', route: '/resume/preview', icon: '👁️' }
      ]
    },
    {
      title: 'Settings',
      items: [
        { label: 'Profile', route: '/settings/profile', icon: '⚙️' },
        { label: 'Preferences', route: '/settings/preferences', icon: '🎛️' },
        { label: 'Companies', route: '/settings/companies', icon: '🏢' },
        { label: 'Notifications', route: '/settings/notifications', icon: '🔔' },
        { label: 'Account', route: '/settings/account', icon: '🔐' }
      ]
    },
    {
      title: 'Insights',
      items: [
        { label: 'Analytics', route: '/analytics', icon: '📈' },
        { label: 'Admin', route: '/admin', icon: '🛠️' }
      ]
    }
  ];

}
