import { CompanyEntry } from './company-entry.model';
import { Education } from './education.model';
import { Project } from './project.model';

export interface ResumeProfileModel {
  candidateId: string;
  name: string;
  email: string;
  phone: string;
  linkedin: string;
  github: string;
  portfolio: string;
  education: Education[];
  projects: Project[];
  companies: CompanyEntry[];
  currentCompany: string;
}
