import { Job } from '../../core/models/job.model';
import { JobRecommendation, MatchBreakdown } from '../../core/models/job-recommendation.model';
import { ResumeMatchingModel } from '../../core/models/resume-matching.model';
import { UserSettingsModel } from '../../core/models/user-settings.model';

const WEIGHTS = {
  skills: 0.4,
  experience: 0.25,
  domain: 0.15,
  certifications: 0.1,
  location: 0.1
};

function normalizeSkill(skill: string): string {
  return skill.trim().toLowerCase();
}

function scoreSkills(matching: ResumeMatchingModel, job: Job): number {
  if (!job.requiredSkills.length) {
    return 100;
  }

  const candidateSkills = new Map(
    matching.skillExperience.map((entry) => [normalizeSkill(entry.skill), entry.years])
  );

  let total = 0;
  for (const required of job.requiredSkills) {
    const candidateYears = candidateSkills.get(normalizeSkill(required.skill)) ?? 0;
    if (candidateYears >= required.years) {
      total += 100;
    } else if (candidateYears > 0) {
      total += Math.round((candidateYears / required.years) * 100);
    }
  }

  return Math.round(total / job.requiredSkills.length);
}

function scoreExperience(matching: ResumeMatchingModel, job: Job): number {
  if (matching.totalExperience >= job.yearsOfExperience) {
    return 100;
  }

  if (matching.totalExperience <= 0) {
    return 0;
  }

  return Math.round((matching.totalExperience / job.yearsOfExperience) * 100);
}

function scoreDomain(matching: ResumeMatchingModel, job: Job): number {
  const domains = matching.domains.map((domain) => domain.toLowerCase());
  return domains.includes(job.domain.toLowerCase()) ? 100 : 0;
}

function scoreCertifications(matching: ResumeMatchingModel, job: Job): number {
  if (!job.certifications.length) {
    return 100;
  }

  const candidateCerts = matching.certifications.map((cert) => cert.toLowerCase());
  const matched = job.certifications.filter((cert) =>
    candidateCerts.some((candidateCert) => candidateCert.includes(cert.toLowerCase()))
  );

  return Math.round((matched.length / job.certifications.length) * 100);
}

function scoreLocation(matching: ResumeMatchingModel, settings: UserSettingsModel, job: Job): number {
  const preferred = [...matching.preferredLocations, ...settings.preferredLocations].map((location) =>
    location.toLowerCase()
  );
  const jobLocation = job.location.toLowerCase();

  if (preferred.some((location) => jobLocation.includes(location) || location.includes(jobLocation))) {
    return 100;
  }

  if (preferred.includes('remote') && jobLocation.includes('remote')) {
    return 100;
  }

  return 0;
}

export function buildMatchBreakdown(
  matching: ResumeMatchingModel,
  settings: UserSettingsModel,
  job: Job
): MatchBreakdown {
  return {
    skills: scoreSkills(matching, job),
    experience: scoreExperience(matching, job),
    domain: scoreDomain(matching, job),
    certifications: scoreCertifications(matching, job),
    location: scoreLocation(matching, settings, job)
  };
}

export function calculateMatchPercentage(breakdown: MatchBreakdown): number {
  const score =
    breakdown.skills * WEIGHTS.skills +
    breakdown.experience * WEIGHTS.experience +
    breakdown.domain * WEIGHTS.domain +
    breakdown.certifications * WEIGHTS.certifications +
    breakdown.location * WEIGHTS.location;

  return Math.round(score);
}

export function buildJobRecommendation(
  matching: ResumeMatchingModel,
  settings: UserSettingsModel,
  job: Job,
  savedJobIds: Set<string>,
  appliedJobIds: Set<string>
): JobRecommendation {
  const matchBreakdown = buildMatchBreakdown(matching, settings, job);

  return {
    ...job,
    matchBreakdown,
    matchPercentage: calculateMatchPercentage(matchBreakdown),
    saved: savedJobIds.has(job.jobId),
    applied: appliedJobIds.has(job.jobId)
  };
}

export function rankRecommendations(recommendations: JobRecommendation[]): JobRecommendation[] {
  return [...recommendations].sort((left, right) => right.matchPercentage - left.matchPercentage);
}

export function filterBlockedCompanies(
  recommendations: JobRecommendation[],
  settings: UserSettingsModel
): JobRecommendation[] {
  const blocked = settings.blockedCompanies.map((company) => company.toLowerCase());
  return recommendations.filter((job) => !blocked.includes(job.company.toLowerCase()));
}

export function boostPreferredCompanies(
  recommendations: JobRecommendation[],
  settings: UserSettingsModel
): JobRecommendation[] {
  const preferred = settings.preferredCompanies.map((company) => company.toLowerCase());

  return recommendations.map((job) => {
    if (!preferred.includes(job.company.toLowerCase())) {
      return job;
    }

    const boosted = Math.min(100, job.matchPercentage + 5);
    return { ...job, matchPercentage: boosted };
  });
}
