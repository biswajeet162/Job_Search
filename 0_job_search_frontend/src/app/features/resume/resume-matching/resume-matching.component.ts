import { Component, OnInit } from '@angular/core';
import { ResumeMatchingModel } from '../../../core/models/resume-matching.model';
import { ResumeService } from '../../../core/services/resume.service';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';

@Component({
  selector: 'app-resume-matching',
  standalone: true,
  imports: [LoadingSpinnerComponent, PageHeaderComponent],
  templateUrl: './resume-matching.component.html',
  styleUrl: './resume-matching.component.scss'
})
export class ResumeMatchingComponent implements OnInit {
  loading = true;
  matching?: ResumeMatchingModel;

  constructor(private readonly resumeService: ResumeService) {}

  ngOnInit(): void {
    this.resumeService.getMatchingModel().subscribe((matching) => {
      this.matching = matching;
      this.loading = false;
    });
  }

  skillBarWidth(years: number): number {
    return Math.min(100, (years / 6) * 100);
  }
}
