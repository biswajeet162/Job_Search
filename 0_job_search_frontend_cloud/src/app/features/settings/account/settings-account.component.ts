import { Component } from '@angular/core';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';

@Component({
  selector: 'app-settings-account',
  standalone: true,
  imports: [PageHeaderComponent],
  template: `
    <app-page-header title="Account" subtitle="Account management placeholder for future backend integration." />

    <section class="form-card">
      <p><strong>Candidate ID:</strong> candidate-001</p>
      <p><strong>Auth:</strong> Mock session (no backend yet)</p>
      <button type="button" class="btn btn-secondary" disabled>Change Password</button>
    </section>
  `
})
export class SettingsAccountComponent {}
