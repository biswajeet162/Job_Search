import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';

@Component({
  selector: 'app-settings-notifications',
  standalone: true,
  imports: [ReactiveFormsModule, PageHeaderComponent],
  template: `
    <app-page-header title="Notifications" subtitle="Configure how you receive job alerts (mock UI)." />

    <form class="form-card" [formGroup]="form">
      <label class="checkbox"><input type="checkbox" formControlName="emailAlerts" /> Email job alerts</label>
      <label class="checkbox"><input type="checkbox" formControlName="weeklyDigest" /> Weekly digest</label>
      <label class="checkbox"><input type="checkbox" formControlName="newMatchAlerts" /> New high-match job alerts</label>
      <button type="button" class="btn btn-primary" (click)="saved = true">Save Notifications</button>
      @if (saved) { <span class="saved">Saved (mock)</span> }
    </form>
  `
})
export class SettingsNotificationsComponent {
  private readonly fb = inject(FormBuilder);
  saved = false;
  readonly form = this.fb.nonNullable.group({
    emailAlerts: true,
    weeklyDigest: true,
    newMatchAlerts: true
  });
}
