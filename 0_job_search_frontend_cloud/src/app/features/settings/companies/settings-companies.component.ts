import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { UserSettingsModel } from '../../../core/models/user-settings.model';
import { CandidateService } from '../../../core/services/candidate.service';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';

@Component({
  selector: 'app-settings-companies',
  standalone: true,
  imports: [ReactiveFormsModule, LoadingSpinnerComponent, PageHeaderComponent],
  templateUrl: './settings-companies.component.html'
})
export class SettingsCompaniesComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly candidateService = inject(CandidateService);
  loading = true;
  saved = false;

  readonly form = this.fb.nonNullable.group({
    preferredCompanies: '',
    blockedCompanies: ''
  });

  ngOnInit(): void {
    this.candidateService.getUserSettings().subscribe((settings) => {
      this.form.patchValue({
        preferredCompanies: settings.preferredCompanies.join(', '),
        blockedCompanies: settings.blockedCompanies.join(', ')
      });
      this.loading = false;
    });
  }

  save(): void {
    const raw = this.form.getRawValue();
    const current = this.candidateService.getSnapshot().userSettings;
    const updated: UserSettingsModel = {
      ...current,
      preferredCompanies: raw.preferredCompanies.split(',').map((item) => item.trim()).filter(Boolean),
      blockedCompanies: raw.blockedCompanies.split(',').map((item) => item.trim()).filter(Boolean)
    };

    this.candidateService.updateUserSettings(updated).subscribe(() => {
      this.saved = true;
      setTimeout(() => (this.saved = false), 2500);
    });
  }
}
