import { Component, OnInit } from '@angular/core';
import { ResumeProfileModel } from '../../../core/models/resume-profile.model';
import { ResumeService } from '../../../core/services/resume.service';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';

@Component({
  selector: 'app-resume-profile',
  standalone: true,
  imports: [LoadingSpinnerComponent, PageHeaderComponent],
  templateUrl: './resume-profile.component.html',
  styleUrl: './resume-profile.component.scss'
})
export class ResumeProfileComponent implements OnInit {
  loading = true;
  profile?: ResumeProfileModel;

  constructor(private readonly resumeService: ResumeService) {}

  ngOnInit(): void {
    this.resumeService.getProfileModel().subscribe((profile) => {
      this.profile = profile;
      this.loading = false;
    });
  }
}
