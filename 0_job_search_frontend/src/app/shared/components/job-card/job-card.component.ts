import { Component, EventEmitter, Input, Output } from '@angular/core';
import { RouterLink } from '@angular/router';
import { JobRecommendation } from '../../../core/models/job-recommendation.model';
import { MatchBadgeComponent } from '../match-badge/match-badge.component';

@Component({
  selector: 'app-job-card',
  standalone: true,
  imports: [RouterLink, MatchBadgeComponent],
  template: `
    <article class="job-card">
      <div class="job-card__top">
        <div>
          <h3>
            <a [routerLink]="['/jobs', job.jobId]">{{ job.title }}</a>
          </h3>
          <p class="company">{{ job.company }} · {{ job.location }}</p>
        </div>
        <app-match-badge [value]="job.matchPercentage" />
      </div>

      <p class="description">{{ job.description }}</p>

      <div class="meta">
        <span>{{ job.domain }}</span>
        <span>{{ job.yearsOfExperience }}+ yrs</span>
        @if (job.saved) { <span class="tag saved">Saved</span> }
        @if (job.applied) { <span class="tag applied">Applied</span> }
      </div>

      <div class="skills">
        @for (skill of job.requiredSkills.slice(0, 4); track skill.skill) {
          <span>{{ skill.skill }} ({{ skill.years }}y)</span>
        }
      </div>

      <div class="actions">
        <a class="btn btn-secondary" [routerLink]="['/jobs', job.jobId]">View Details</a>
        <button type="button" class="btn btn-primary" (click)="save.emit(job.jobId)">
          {{ job.saved ? 'Unsave' : 'Save Job' }}
        </button>
        @if (!job.applied) {
          <button type="button" class="btn btn-ghost" (click)="apply.emit(job.jobId)">Apply</button>
        }
      </div>
    </article>
  `,
  styles: `
    .job-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 1.25rem;
      box-shadow: var(--shadow-sm);
      display: flex;
      flex-direction: column;
      gap: 0.85rem;
    }

    .job-card__top {
      display: flex;
      justify-content: space-between;
      gap: 1rem;
      align-items: flex-start;
    }

    h3 {
      margin: 0;
      font-size: 1.1rem;
    }

    h3 a {
      color: var(--text);
      text-decoration: none;
    }

    h3 a:hover {
      color: var(--primary);
    }

    .company {
      margin: 0.25rem 0 0;
      color: var(--text-muted);
      font-size: 0.9rem;
    }

    .description {
      margin: 0;
      color: var(--text-muted);
      line-height: 1.5;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }

    .meta, .skills {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
    }

    .meta span, .skills span {
      background: var(--surface-muted);
      color: var(--text-muted);
      padding: 0.2rem 0.55rem;
      border-radius: 999px;
      font-size: 0.78rem;
    }

    .tag.saved { background: rgba(59, 130, 246, 0.12); color: #2563eb; }
    .tag.applied { background: rgba(16, 185, 129, 0.12); color: #059669; }

    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      margin-top: 0.25rem;
    }
  `
})
export class JobCardComponent {
  @Input({ required: true }) job!: JobRecommendation;
  @Output() save = new EventEmitter<string>();
  @Output() apply = new EventEmitter<string>();
}
