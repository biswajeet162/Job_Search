import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-empty-state',
  standalone: true,
  template: `
    <div class="empty-state">
      <div class="icon">{{ icon }}</div>
      <h3>{{ title }}</h3>
      <p>{{ message }}</p>
      <ng-content />
    </div>
  `,
  styles: `
    .empty-state {
      text-align: center;
      padding: 3rem 1.5rem;
      background: var(--surface);
      border: 1px dashed var(--border);
      border-radius: var(--radius);
      color: var(--text-muted);
    }

    .icon {
      font-size: 2rem;
      margin-bottom: 0.75rem;
    }

    h3 {
      margin: 0 0 0.5rem;
      color: var(--text);
    }

    p {
      margin: 0 auto 1rem;
      max-width: 28rem;
    }
  `
})
export class EmptyStateComponent {
  @Input() icon = '📭';
  @Input({ required: true }) title!: string;
  @Input({ required: true }) message!: string;
}
