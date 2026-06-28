import { Job } from './job.model';

export interface MatchBreakdown {
  skills: number;
  experience: number;
  domain: number;
  certifications: number;
  location: number;
}

export interface JobRecommendation extends Job {
  matchPercentage: number;
  matchBreakdown: MatchBreakdown;
  saved: boolean;
  applied: boolean;
}
