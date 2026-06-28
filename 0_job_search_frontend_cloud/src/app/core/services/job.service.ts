import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Job } from '../models/job.model';
import { JobRecommendation } from '../models/job-recommendation.model';
import { mockDelay } from '../../shared/utils/mock-delay.util';
import jobsData from '../../../assets/mock-data/jobs.json';
import { CandidateService } from './candidate.service';
import { MatchingService } from './matching.service';

@Injectable({ providedIn: 'root' })
export class JobService {
  private readonly jobs: Job[] = jobsData as Job[];
  private readonly savedJobIds = new Set<string>(['job-002', 'job-003']);
  private readonly appliedJobIds = new Set<string>(['job-007']);

  constructor(
    private readonly candidateService: CandidateService,
    private readonly matchingService: MatchingService
  ) {}

  getAllJobs(): Observable<Job[]> {
    return mockDelay(this.jobs);
  }

  getJobById(jobId: string): Observable<Job | undefined> {
    return mockDelay(this.jobs.find((job) => job.jobId === jobId));
  }

  getRecommendations(): Observable<JobRecommendation[]> {
    const candidate = this.candidateService.getSnapshot();
    const recommendations = this.matchingService.buildRecommendations(
      candidate.resumeMatching,
      candidate.userSettings,
      this.jobs,
      this.savedJobIds,
      this.appliedJobIds
    );
    return mockDelay(recommendations);
  }

  getSavedJobs(): Observable<JobRecommendation[]> {
    return mockDelay(
      this.getRecommendationsSync().filter((job) => this.savedJobIds.has(job.jobId))
    );
  }

  getAppliedJobs(): Observable<JobRecommendation[]> {
    return mockDelay(
      this.getRecommendationsSync().filter((job) => this.appliedJobIds.has(job.jobId))
    );
  }

  toggleSaveJob(jobId: string): Observable<JobRecommendation[]> {
    if (this.savedJobIds.has(jobId)) {
      this.savedJobIds.delete(jobId);
    } else {
      this.savedJobIds.add(jobId);
    }
    return this.getRecommendations();
  }

  markAsApplied(jobId: string): Observable<JobRecommendation[]> {
    this.appliedJobIds.add(jobId);
    return this.getRecommendations();
  }

  getRecommendationsSync(): JobRecommendation[] {
    const candidate = this.candidateService.getSnapshot();
    return this.matchingService.buildRecommendations(
      candidate.resumeMatching,
      candidate.userSettings,
      this.jobs,
      this.savedJobIds,
      this.appliedJobIds
    );
  }
}
