import { Component, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';
import { JobRecommendation } from '../../core/models/job-recommendation.model';
import { JobService } from '../../core/services/job.service';
import { CandidateService } from '../../core/services/candidate.service';
import { JobCardComponent } from '../../shared/components/job-card/job-card.component';
import { LoadingSpinnerComponent } from '../../shared/components/loading-spinner/loading-spinner.component';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';
import { StatCardComponent } from '../../shared/components/stat-card/stat-card.component';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [RouterLink, JobCardComponent, LoadingSpinnerComponent, PageHeaderComponent, StatCardComponent],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss'
})
export class DashboardComponent implements OnInit {
  loading = true;
  recommendations: JobRecommendation[] = [];
  stats = {
    totalMatches: 0,
    topMatch: 0,
    savedJobs: 0,
    appliedJobs: 0
  };

  constructor(
    private readonly jobService: JobService,
    private readonly candidateService: CandidateService
  ) {}

  ngOnInit(): void {
    this.jobService.getRecommendations().subscribe((jobs) => {
      this.recommendations = jobs.slice(0, 5);
      this.stats = {
        totalMatches: jobs.length,
        topMatch: jobs[0]?.matchPercentage ?? 0,
        savedJobs: jobs.filter((job) => job.saved).length,
        appliedJobs: jobs.filter((job) => job.applied).length
      };
      this.loading = false;
    });
  }

  onSave(jobId: string): void {
    this.jobService.toggleSaveJob(jobId).subscribe((jobs) => {
      this.recommendations = jobs.slice(0, 5);
    });
  }

  onApply(jobId: string): void {
    this.jobService.markAsApplied(jobId).subscribe((jobs) => {
      this.recommendations = jobs.slice(0, 5);
    });
  }

  get candidateName(): string {
    return this.candidateService.getSnapshot().resumeProfile.name;
  }
}
