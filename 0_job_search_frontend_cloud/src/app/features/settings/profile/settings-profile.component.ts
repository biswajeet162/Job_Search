import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { ResumeProfileModel } from '../../../core/models/resume-profile.model';
import { CandidateService } from '../../../core/services/candidate.service';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';

@Component({
  selector: 'app-settings-profile',
  standalone: true,
  imports: [ReactiveFormsModule, LoadingSpinnerComponent, PageHeaderComponent],
  templateUrl: './settings-profile.component.html'
})
export class SettingsProfileComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly candidateService = inject(CandidateService);
  loading = true;
  saved = false;

  readonly form = this.fb.nonNullable.group({
    name: '',
    email: '',
    phone: '',
    linkedin: '',
    github: '',
    portfolio: ''
  });

  ngOnInit(): void {
    this.candidateService.getResumeProfile().subscribe((profile) => {
      this.form.patchValue(profile);
      this.loading = false;
    });
  }

  save(): void {
    const current = this.candidateService.getSnapshot().resumeProfile;
    const updated: ResumeProfileModel = { ...current, ...this.form.getRawValue() };
    this.candidateService.updateResumeProfile(updated).subscribe(() => {
      this.saved = true;
      setTimeout(() => (this.saved = false), 2500);
    });
  }
}
