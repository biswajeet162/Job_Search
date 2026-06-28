import { SkillExperience } from './skill-experience.model';

export interface ResumeMatchingModel {
  candidateId: string;
  skillExperience: SkillExperience[];
  totalExperience: number;
  domains: string[];
  certifications: string[];
  preferredLocations: string[];
}
