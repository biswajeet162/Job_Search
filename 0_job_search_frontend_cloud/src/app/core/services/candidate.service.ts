import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { CANDIDATE_ID } from '../constants/app-routes.constants';
import { Candidate } from '../models/candidate.model';
import { ResumeMatchingModel } from '../models/resume-matching.model';
import { ResumeProfileModel } from '../models/resume-profile.model';
import { UserSettingsModel } from '../models/user-settings.model';
import { mockDelay } from '../../shared/utils/mock-delay.util';
import candidateData from '../../../assets/mock-data/candidate.json';

@Injectable({ providedIn: 'root' })
export class CandidateService {
  private readonly candidateSubject = new BehaviorSubject<Candidate>(candidateData as Candidate);
  readonly candidate$ = this.candidateSubject.asObservable();

  getCandidate(): Observable<Candidate> {
    return mockDelay(this.candidateSubject.value);
  }

  getResumeMatching(): Observable<ResumeMatchingModel> {
    return mockDelay(this.candidateSubject.value.resumeMatching);
  }

  getResumeProfile(): Observable<ResumeProfileModel> {
    return mockDelay(this.candidateSubject.value.resumeProfile);
  }

  getUserSettings(): Observable<UserSettingsModel> {
    return mockDelay(this.candidateSubject.value.userSettings);
  }

  updateResumeMatching(matching: ResumeMatchingModel): Observable<ResumeMatchingModel> {
    const candidate = this.candidateSubject.value;
    const updated = { ...candidate, resumeMatching: { ...matching, candidateId: CANDIDATE_ID } };
    this.candidateSubject.next(updated);
    return mockDelay(updated.resumeMatching);
  }

  updateResumeProfile(profile: ResumeProfileModel): Observable<ResumeProfileModel> {
    const candidate = this.candidateSubject.value;
    const updated = { ...candidate, resumeProfile: { ...profile, candidateId: CANDIDATE_ID } };
    this.candidateSubject.next(updated);
    return mockDelay(updated.resumeProfile);
  }

  updateUserSettings(settings: UserSettingsModel): Observable<UserSettingsModel> {
    const candidate = this.candidateSubject.value;
    const updated = { ...candidate, userSettings: { ...settings, candidateId: CANDIDATE_ID } };
    this.candidateSubject.next(updated);
    return mockDelay(updated.userSettings);
  }

  setCandidate(candidate: Candidate): void {
    this.candidateSubject.next({ ...candidate, resumeMatching: { ...candidate.resumeMatching, candidateId: CANDIDATE_ID }, resumeProfile: { ...candidate.resumeProfile, candidateId: CANDIDATE_ID }, userSettings: { ...candidate.userSettings, candidateId: CANDIDATE_ID } });
  }

  getSnapshot(): Candidate {
    return this.candidateSubject.value;
  }

  hasResumeData(): boolean {
    const profile = this.candidateSubject.value.resumeProfile;
    return Boolean(profile.name && profile.email);
  }
}
