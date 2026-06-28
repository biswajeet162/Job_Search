import { Component, OnInit } from '@angular/core';
import { CandidateService } from '../../core/services/candidate.service';
import { JobService } from '../../core/services/job.service';
import { LoadingSpinnerComponent } from '../../shared/components/loading-spinner/loading-spinner.component';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';
import { StatCardComponent } from '../../shared/components/stat-card/stat-card.component';

@Component({
  selector: 'app-analytics',
  standalone: true,
  imports: [LoadingSpinnerComponent, PageHeaderComponent, StatCardComponent],
  templateUrl: './analytics.component.html',
  styleUrl: './analytics.component.scss'
})
export class AnalyticsComponent implements OnInit {
  loading = true;
  skillStats: { skill: string; years: number }[] = [];
  domainMatches: { domain: string; count: number }[] = [];
  avgMatch = 0;
  highMatches = 0;

  constructor(
    private readonly candidateService: CandidateService,
    private readonly jobService: JobService
  ) {}

  ngOnInit(): void {
    this.jobService.getRecommendations().subscribe((jobs) => {
      const matching = this.candidateService.getSnapshot().resumeMatching;
      this.skillStats = matching.skillExperience;
      this.avgMatch = Math.round(jobs.reduce((sum, job) => sum + job.matchPercentage, 0) / jobs.length);
      this.highMatches = jobs.filter((job) => job.matchPercentage >= 75).length;

      const domainMap = new Map<string, number>();
      for (const job of jobs) {
        domainMap.set(job.domain, (domainMap.get(job.domain) ?? 0) + 1);
      }
      this.domainMatches = [...domainMap.entries()].map(([domain, count]) => ({ domain, count }));
      this.loading = false;
    });
  }
}
