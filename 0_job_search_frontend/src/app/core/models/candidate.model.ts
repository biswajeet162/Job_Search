import { ResumeMatchingModel } from './resume-matching.model';
import { ResumeProfileModel } from './resume-profile.model';
import { UserSettingsModel } from './user-settings.model';

export interface Candidate {
  resumeMatching: ResumeMatchingModel;
  resumeProfile: ResumeProfileModel;
  userSettings: UserSettingsModel;
}
