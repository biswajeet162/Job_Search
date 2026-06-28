import { DecimalPipe } from '@angular/common';
import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-match-badge',
  standalone: true,
  template: `
    <span class="match-badge" [class]="tier">{{ value | number: '1.0-0' }}%</span>
  `,
  imports: [DecimalPipe],
  styles: `
    .match-badge {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 3.25rem;
      padding: 0.25rem 0.6rem;
      border-radius: 999px;
      font-size: 0.8rem;
      font-weight: 700;
    }

    .high {
      background: rgba(16, 185, 129, 0.15);
      color: #059669;
    }

    .medium {
      background: rgba(245, 158, 11, 0.15);
      color: #d97706;
    }

    .low {
      background: rgba(239, 68, 68, 0.12);
      color: #dc2626;
    }
  `
})
export class MatchBadgeComponent {
  @Input({ required: true }) value!: number;

  get tier(): string {
    if (this.value >= 75) return 'high';
    if (this.value >= 50) return 'medium';
    return 'low';
  }
}
