import { Component, OnInit } from '@angular/core';
import { JobRecommendation } from '../../../core/models/job-recommendation.model';
import { JobService } from '../../../core/services/job.service';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { JobCardComponent } from '../../../shared/components/job-card/job-card.component';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';

@Component({
  selector: 'app-applied-jobs',
  standalone: true,
  imports: [JobCardComponent, LoadingSpinnerComponent, PageHeaderComponent, EmptyStateComponent],
  template: `
    <app-page-header title="Applied Jobs" subtitle="Track jobs you've marked as applied." />

    @if (loading) {
      <app-loading-spinner message="Loading applied jobs..." />
    } @else if (!jobs.length) {
      <app-empty-state
        icon="✅"
        title="No applications yet"
        message="Apply to recommended jobs and they'll appear here."
      />
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
export class AppliedJobsComponent implements OnInit {
  loading = true;
  jobs: JobRecommendation[] = [];

  constructor(private readonly jobService: JobService) {}

  ngOnInit(): void {
    this.jobService.getAppliedJobs().subscribe((jobs) => {
      this.jobs = jobs;
      this.loading = false;
    });
  }

  onSave(jobId: string): void {
    this.jobService.toggleSaveJob(jobId).subscribe(() => {
      this.jobService.getAppliedJobs().subscribe((jobs) => (this.jobs = jobs));
    });
  }

  onApply(jobId: string): void {
    this.jobService.markAsApplied(jobId).subscribe((jobs) => (this.jobs = jobs));
  }
}
