import { DatePipe } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { JobRecommendation } from '../../../core/models/job-recommendation.model';
import { JobService } from '../../../core/services/job.service';
import { MatchBadgeComponent } from '../../../shared/components/match-badge/match-badge.component';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';

@Component({
  selector: 'app-job-details',
  standalone: true,
  imports: [RouterLink, MatchBadgeComponent, LoadingSpinnerComponent, PageHeaderComponent, DatePipe],
  templateUrl: './job-details.component.html',
  styleUrl: './job-details.component.scss'
})
export class JobDetailsComponent implements OnInit {
  loading = true;
  job?: JobRecommendation;

  constructor(
    private readonly route: ActivatedRoute,
    private readonly jobService: JobService
  ) {}

  ngOnInit(): void {
    const jobId = this.route.snapshot.paramMap.get('id') ?? '';
    this.jobService.getRecommendations().subscribe((jobs) => {
      this.job = jobs.find((item) => item.jobId === jobId);
      this.loading = false;
    });
  }

  toggleSave(): void {
    if (!this.job) return;
    this.jobService.toggleSaveJob(this.job.jobId).subscribe((jobs) => {
      this.job = jobs.find((item) => item.jobId === this.job!.jobId);
    });
  }

  apply(): void {
    if (!this.job) return;
    this.jobService.markAsApplied(this.job.jobId).subscribe((jobs) => {
      this.job = jobs.find((item) => item.jobId === this.job!.jobId);
    });
  }

  get breakdown(): { label: string; value: number }[] {
    if (!this.job) return [];
    return [
      { label: 'Skills', value: this.job.matchBreakdown.skills },
      { label: 'Experience', value: this.job.matchBreakdown.experience },
      { label: 'Domain', value: this.job.matchBreakdown.domain },
      { label: 'Certifications', value: this.job.matchBreakdown.certifications },
      { label: 'Location', value: this.job.matchBreakdown.location }
    ];
  }
}
