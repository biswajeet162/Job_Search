import { Component } from '@angular/core';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [PageHeaderComponent],
  template: `
    <app-page-header
      title="Admin"
      subtitle="Placeholder for future admin tools — job scraper monitoring, candidate management."
    />

    <section class="form-card">
      <ul>
        <li>Job scraper status: <strong>Not connected (mock)</strong></li>
        <li>Total scraped jobs: <strong>8</strong></li>
        <li>Active candidates: <strong>1</strong></li>
        <li>Backend API: <strong>Pending integration</strong></li>
      </ul>
    </section>
  `
})
export class AdminComponent {}
