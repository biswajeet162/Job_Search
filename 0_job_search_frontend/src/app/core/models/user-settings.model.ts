export interface UserSettingsModel {
  candidateId: string;
  preferredCompanies: string[];
  blockedCompanies: string[];
  currentLocation: string;
  preferredLocations: string[];
  currentCTC: number;
  expectedCTC: number;
  noticePeriodDays: number;
  openToWork: boolean;
}
