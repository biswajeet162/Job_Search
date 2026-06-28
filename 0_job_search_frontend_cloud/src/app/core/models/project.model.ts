import { ProjectType } from '../../shared/enums/project-type.enum';

export interface Project {
  title: string;
  type: ProjectType | string;
}
