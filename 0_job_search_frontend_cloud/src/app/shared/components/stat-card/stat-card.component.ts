import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-stat-card',
  standalone: true,
  template: `
    <article class="stat-card">
      <span class="label">{{ label }}</span>
      <strong class="value">{{ value }}</strong>
      @if (hint) {
        <span class="hint">{{ hint }}</span>
      }
    </article>
  `,
  styles: `
    .stat-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 1.25rem;
      display: flex;
      flex-direction: column;
      gap: 0.35rem;
      box-shadow: var(--shadow-sm);
    }

    .label {
      font-size: 0.85rem;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }

    .value {
      font-size: 1.75rem;
      color: var(--text);
    }

    .hint {
      font-size: 0.85rem;
      color: var(--success);
    }
  `
})
export class StatCardComponent {
  @Input({ required: true }) label!: string;
  @Input({ required: true }) value!: string | number;
  @Input() hint = '';
}
