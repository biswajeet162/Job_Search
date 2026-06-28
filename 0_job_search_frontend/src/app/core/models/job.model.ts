import { SkillExperience } from './skill-experience.model';

export interface Job {
  jobId: string;
  title: string;
  company: string;
  description: string;
  requiredSkills: SkillExperience[];
  yearsOfExperience: number;
  domain: string;
  certifications: string[];
  location: string;
  jobUrl: string;
  timestamp: string;
}
