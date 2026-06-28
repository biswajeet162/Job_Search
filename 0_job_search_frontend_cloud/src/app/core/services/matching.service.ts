import { Injectable } from '@angular/core';
import { Job } from '../models/job.model';
import { JobRecommendation } from '../models/job-recommendation.model';
import { ResumeMatchingModel } from '../models/resume-matching.model';
import { UserSettingsModel } from '../models/user-settings.model';
import {
  boostPreferredCompanies,
  buildJobRecommendation,
  filterBlockedCompanies,
  rankRecommendations
} from '../../shared/utils/match-calculator.util';

@Injectable({ providedIn: 'root' })
export class MatchingService {
  buildRecommendations(
    matching: ResumeMatchingModel,
    settings: UserSettingsModel,
    jobs: Job[],
    savedJobIds: Set<string>,
    appliedJobIds: Set<string>
  ): JobRecommendation[] {
    const recommendations = jobs.map((job) =>
      buildJobRecommendation(matching, settings, job, savedJobIds, appliedJobIds)
    );

    const filtered = filterBlockedCompanies(recommendations, settings);
    const boosted = boostPreferredCompanies(filtered, settings);
    return rankRecommendations(boosted);
  }
}
