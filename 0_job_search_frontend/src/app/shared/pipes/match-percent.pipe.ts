import { Pipe, PipeTransform } from '@angular/core';

@Pipe({ name: 'matchPercent', standalone: true })
export class MatchPercentPipe implements PipeTransform {
  transform(value: number | null | undefined): string {
    if (value == null) {
      return '0%';
    }
    return `${Math.round(value)}%`;
  }
}
