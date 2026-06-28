import { EducationLevel } from '../../shared/enums/education-level.enum';

export interface Education {
  level: EducationLevel | string;
  degree: string;
  specialization?: string;
  institution: string;
  startYear: number;
  endYear: number;
}
