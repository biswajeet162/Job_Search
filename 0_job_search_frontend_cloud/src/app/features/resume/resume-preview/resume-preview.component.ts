import { Component, OnInit } from '@angular/core';
import { Candidate } from '../../../core/models/candidate.model';
import { CandidateService } from '../../../core/services/candidate.service';
import { CtcFormatPipe } from '../../../shared/pipes/ctc-format.pipe';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';

@Component({
  selector: 'app-resume-preview',
  standalone: true,
  imports: [LoadingSpinnerComponent, PageHeaderComponent, CtcFormatPipe],
  templateUrl: './resume-preview.component.html',
  styleUrl: './resume-preview.component.scss'
})
export class ResumePreviewComponent implements OnInit {
  loading = true;
  candidate?: Candidate;

  constructor(private readonly candidateService: CandidateService) {}

  ngOnInit(): void {
    this.candidateService.getCandidate().subscribe((candidate) => {
      this.candidate = candidate;
      this.loading = false;
    });
  }

  skillSummary(candidate: Candidate): string {
    return candidate.resumeMatching.skillExperience
      .slice(0, 4)
      .map((skill) => `${skill.skill} (${skill.years}y)`)
      .join(', ');
  }
}
