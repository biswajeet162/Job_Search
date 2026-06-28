import { Component, OnInit } from '@angular/core';
import { JobRecommendation } from '../../../core/models/job-recommendation.model';
import { JobService } from '../../../core/services/job.service';
import { JobCardComponent } from '../../../shared/components/job-card/job-card.component';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';

@Component({
  selector: 'app-job-list',
  standalone: true,
  imports: [JobCardComponent, LoadingSpinnerComponent, PageHeaderComponent],
  template: `
    <app-page-header
      title="All Jobs"
      subtitle="Browse every scraped job in the database with match scores for your profile."
    />

    @if (loading) {
      <app-loading-spinner message="Loading jobs..." />
    } @else {
      <div class="job-grid">
        @for (job of jobs; track job.jobId) {
          <app-job-card [job]="job" (save)="onSave($event)" (apply)="onApply($event)" />
        }
      </div>
    }
  `,
  styles: `.job-grid { display: grid; gap: 1rem; }`
})
export class JobListComponent implements OnInit {
  loading = true;
  jobs: JobRecommendation[] = [];

  constructor(private readonly jobService: JobService) {}

  ngOnInit(): void {
    this.jobService.getRecommendations().subscribe((jobs) => {
      this.jobs = jobs;
      this.loading = false;
    });
  }

  onSave(jobId: string): void {
    this.jobService.toggleSaveJob(jobId).subscribe((jobs) => (this.jobs = jobs));
  }

  onApply(jobId: string): void {
    this.jobService.markAsApplied(jobId).subscribe((jobs) => (this.jobs = jobs));
  }
}
