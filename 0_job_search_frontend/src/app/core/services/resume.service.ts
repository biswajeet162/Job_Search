import { Injectable } from '@angular/core';
import { Observable, of, switchMap } from 'rxjs';
import { Candidate } from '../models/candidate.model';
import { ResumeMatchingModel } from '../models/resume-matching.model';
import { ResumeProfileModel } from '../models/resume-profile.model';
import { mockDelay } from '../../shared/utils/mock-delay.util';
import parsedResumeData from '../../../assets/mock-data/candidate.json';
import { CandidateService } from './candidate.service';

export interface ResumeUploadResult {
  success: boolean;
  message: string;
  candidate: Candidate;
}

@Injectable({ providedIn: 'root' })
export class ResumeService {
  private readonly parsingDelayMs = 1800;

  constructor(private readonly candidateService: CandidateService) {}

  uploadAndParse(_file: File): Observable<ResumeUploadResult> {
    return of(null).pipe(
      switchMap(() => mockDelay(parsedResumeData as Candidate, this.parsingDelayMs)),
      switchMap((candidate) => {
        this.candidateService.setCandidate(candidate);
        return mockDelay<ResumeUploadResult>({
          success: true,
          message: 'Resume parsed successfully. Matching profile generated.',
          candidate
        });
      })
    );
  }

  getMatchingModel(): Observable<ResumeMatchingModel> {
    return this.candidateService.getResumeMatching();
  }

  getProfileModel(): Observable<ResumeProfileModel> {
    return this.candidateService.getResumeProfile();
  }
}
