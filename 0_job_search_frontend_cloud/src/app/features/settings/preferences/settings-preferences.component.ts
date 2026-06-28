import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { UserSettingsModel } from '../../../core/models/user-settings.model';
import { CandidateService } from '../../../core/services/candidate.service';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';

@Component({
  selector: 'app-settings-preferences',
  standalone: true,
  imports: [ReactiveFormsModule, LoadingSpinnerComponent, PageHeaderComponent],
  templateUrl: './settings-preferences.component.html'
})
export class SettingsPreferencesComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly candidateService = inject(CandidateService);
  loading = true;
  saved = false;

  readonly form = this.fb.nonNullable.group({
    currentLocation: '',
    preferredLocations: '',
    currentCTC: 0,
    expectedCTC: 0,
    noticePeriodDays: 0,
    openToWork: true
  });

  ngOnInit(): void {
    this.candidateService.getUserSettings().subscribe((settings) => {
      this.form.patchValue({
        ...settings,
        preferredLocations: settings.preferredLocations.join(', ')
      });
      this.loading = false;
    });
  }

  save(): void {
    const raw = this.form.getRawValue();
    const current = this.candidateService.getSnapshot().userSettings;
    const updated: UserSettingsModel = {
      ...current,
      currentLocation: raw.currentLocation,
      preferredLocations: raw.preferredLocations.split(',').map((item) => item.trim()).filter(Boolean),
      currentCTC: Number(raw.currentCTC),
      expectedCTC: Number(raw.expectedCTC),
      noticePeriodDays: Number(raw.noticePeriodDays),
      openToWork: raw.openToWork
    };

    this.candidateService.updateUserSettings(updated).subscribe(() => {
      this.saved = true;
      setTimeout(() => (this.saved = false), 2500);
    });
  }
}
